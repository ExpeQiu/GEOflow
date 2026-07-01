<?php

namespace App\Services\GeoFlow;

use App\Services\GeoFlow\ContentAgent\AiModelRuntimeBuilder;
use App\Models\AiModel;
use App\Models\Article;
use App\Models\Author;
use App\Models\Category;
use App\Models\KnowledgeBase;
use App\Models\KnowledgeChunk;
use App\Models\Prompt;
use App\Models\Task;
use App\Models\Title;
use App\Services\GeoFlow\Contracts\ContentAgentClientInterface;
use App\Services\GeoEval\ArticleEvaluationService;
use App\Services\GeoEval\InsightTemplateService;
use App\Support\GeoFlow\ApiKeyCrypto;
use App\Support\GeoFlow\ImageUrlNormalizer;
use App\Support\GeoFlow\KnowledgeEvidenceFormatter;
use App\Support\GeoFlow\OpenAiRuntimeProvider;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\DB;
use RuntimeException;
use Throwable;

/**
 * Worker 任务执行器：将队列任务落地为文章记录（占位实现，先打通 worker/队列链路）。
 */
class WorkerExecutionService
{
    /**
     * 复用统一 API Key 解密组件，确保 worker 与后台配置端解密行为一致。
     */
    public function __construct(
        private readonly ApiKeyCrypto $apiKeyCrypto,
        private readonly KnowledgeChunkSyncService $knowledgeChunkSyncService,
        private readonly KnowledgeRetrievalService $knowledgeRetrievalService,
        private readonly ArticlePublishService $articlePublishService,
        private readonly KnowledgeConfigService $knowledgeConfigService,
        private readonly ArticleEvaluationService $articleEvaluationService,
        private readonly InsightTemplateService $insightTemplateService,
        private readonly ContentAgentClientInterface $contentAgentClient,
        private readonly WorkerArticlePersistenceService $articlePersistenceService,
        private readonly JobQueueService $jobQueueService,
        private readonly AiModelRuntimeBuilder $aiModelRuntimeBuilder,
        private readonly ContentPipelineContextService $contentPipelineContextService,
    ) {}

    /**
     * @return array{article_id:int|null, title:string, message:string, meta:array<string,mixed>}
     */
    public function executeTask(int $taskId, ?int $taskRunId = null): array
    {
        /** @var Task|null $task */
        $task = Task::query()->find($taskId);
        if (! $task) {
            throw new RuntimeException('任务不存在');
        }

        if (($task->status ?? 'paused') !== 'active' || (int) ($task->schedule_enabled ?? 1) !== 1) {
            throw new RuntimeException('任务未激活');
        }

        $publishResult = $this->articlePublishService->publishDueDraftForTask($task);
        if ($publishResult !== null) {
            return $publishResult;
        }

        if ($this->articlePublishService->hasDraftBlockedByEval($task)) {
            return [
                'article_id' => null,
                'title' => '',
                'message' => '存在等待 GEO 评估的已审核草稿，暂停生成',
                'meta' => [
                    'task_id' => (int) $task->id,
                    'action' => 'noop',
                    'reason' => 'eval_gate_pending',
                ],
            ];
        }

        $generationBlockReason = $this->getGenerationBlockReason($task);
        if ($generationBlockReason !== null) {
            return [
                'article_id' => null,
                'title' => '',
                'message' => $generationBlockReason,
                'meta' => [
                    'task_id' => (int) $task->id,
                    'action' => 'noop',
                    'reason' => $generationBlockReason,
                ],
            ];
        }

        $titleRow = $this->pickTitle($task);
        $author = $this->pickAuthor($task);
        $category = $this->pickCategory($task);
        $prompt = $task->prompt_id ? Prompt::query()->find((int) $task->prompt_id) : null;

        $keyword = (string) ($titleRow->keyword ?? '');
        $knowledgeContext = $this->resolveKnowledgeContext($task, (string) $titleRow->title, $keyword);
        $styleAppendix = $this->insightTemplateService->buildPromptAppendix(
            isset($task->insight_template_id) ? (int) $task->insight_template_id : null
        );
        $promptContent = trim((string) ($prompt?->content ?? ''));
        if ($styleAppendix !== '') {
            $promptContent = trim($promptContent."\n\n".$styleAppendix);
        }
        $contentPrompt = $this->buildContentPrompt((string) $titleRow->title, $keyword, $promptContent !== '' ? $promptContent : null, $knowledgeContext);

        $generationContext = [
            'task_id' => (int) $task->id,
            'task_run_id' => $taskRunId,
            'title_id' => (int) $titleRow->id,
            'author_id' => $author?->id,
            'category_id' => $category?->id,
            'keyword' => $keyword,
            'knowledge_context' => $knowledgeContext,
            'insight_template_id' => isset($task->insight_template_id) ? (int) $task->insight_template_id : null,
            'model_selection_mode' => (string) ($task->model_selection_mode ?? 'fixed'),
        ];

        if ($this->shouldUseContentPipeline($task)) {
            $agentPayload = $this->contentPipelineContextService->buildPayload(
                $task,
                (string) $titleRow->title,
                $keyword,
                $prompt,
                $styleAppendix,
                $taskRunId,
                $generationContext,
            );
            $dispatch = $this->contentAgentClient->dispatchContentPipelineGeneration($agentPayload);
        } else {
            $agentPayload = $this->buildContentAgentPayload($task, $contentPrompt, $knowledgeContext, $styleAppendix, $taskRunId, $generationContext);
            $dispatch = $this->contentAgentClient->dispatchContentGeneration($agentPayload);
        }

        if ($dispatch->isAsync()) {
            if ($taskRunId !== null && $taskRunId > 0) {
                $this->jobQueueService->markJobAwaitingExternalAgent($taskRunId, (int) $task->id, (string) $dispatch->requestId, [
                    'action' => 'awaiting_external_agent',
                    'content_agent_request_id' => $dispatch->requestId,
                    'title_id' => (int) $titleRow->id,
                ]);
            }

            return [
                'article_id' => null,
                'title' => (string) $titleRow->title,
                'message' => '已提交 Content Agent 异步生成',
                'meta' => [
                    'task_id' => (int) $task->id,
                    'action' => 'awaiting_external_agent',
                    'content_agent_request_id' => $dispatch->requestId,
                    'title_id' => (int) $titleRow->id,
                ],
            ];
        }

        $generation = $this->generateContentWithModelSelection($task, $contentPrompt, $generationContext, $taskRunId, $knowledgeContext, $styleAppendix);
        $persisted = $this->articlePersistenceService->persistGeneratedArticle([
            'task' => $task,
            'title_row' => $titleRow,
            'author' => $author,
            'category' => $category,
            'keyword' => $keyword,
            'knowledge_context' => $knowledgeContext,
            'task_run_id' => $taskRunId,
            'content' => $generation['content'],
            'generation_meta' => $generation['meta'],
        ]);

        return [
            'article_id' => $persisted['article_id'],
            'title' => (string) $titleRow->title,
            'message' => '草稿生成成功',
            'meta' => $persisted['meta'],
        ];
    }

    /**
     * @param  array<string, mixed>  $storedPayload
     * @return array{article_id:int,meta:array<string,mixed>}
     */
    public function completeContentGenerationFromCallback(array $storedPayload, \App\Models\ContentAgentRequest $record): array
    {
        $contextData = is_array($storedPayload['generation_context'] ?? null) ? $storedPayload['generation_context'] : [];
        $taskId = (int) ($contextData['task_id'] ?? 0);
        $titleId = (int) ($contextData['title_id'] ?? 0);
        if ($taskId <= 0 || $titleId <= 0) {
            throw new RuntimeException('generation_context 不完整');
        }

        $task = Task::query()->findOrFail($taskId);
        $titleRow = Title::query()->findOrFail($titleId);
        $author = isset($contextData['author_id']) ? Author::query()->find((int) $contextData['author_id']) : null;
        $category = isset($contextData['category_id']) ? Category::query()->find((int) $contextData['category_id']) : null;

        $persisted = $this->articlePersistenceService->persistGeneratedArticle([
            'task' => $task,
            'title_row' => $titleRow,
            'author' => $author,
            'category' => $category,
            'keyword' => (string) ($contextData['keyword'] ?? ''),
            'knowledge_context' => (string) ($contextData['knowledge_context'] ?? ''),
            'task_run_id' => (int) ($contextData['task_run_id'] ?? $record->correlation_id ?? 0),
            'content' => (string) ($storedPayload['content'] ?? ''),
            'generation_meta' => is_array($contextData['generation_meta'] ?? null) ? $contextData['generation_meta'] : [],
        ]);

        $taskRunId = (int) ($contextData['task_run_id'] ?? $record->correlation_id ?? 0);
        if ($taskRunId > 0) {
            $this->jobQueueService->completeJob(
                jobId: $taskRunId,
                taskId: $taskId,
                articleId: $persisted['article_id'],
                durationMs: 0,
                meta: $persisted['meta']
            );
        }

        return $persisted;
    }

    /**
     * 判断是否允许继续生成草稿。
     */
    private function getGenerationBlockReason(Task $task, bool $lock = false): ?string
    {
        $articleLimit = max(1, (int) ($task->article_limit ?? $task->draft_limit ?? 10));
        if ((int) ($task->created_count ?? 0) >= $articleLimit) {
            return '已达到文章总数上限';
        }

        $draftLimit = max(1, (int) ($task->draft_limit ?? 10));
        $draftQuery = Article::query()
            ->where('task_id', (int) $task->id)
            ->where('status', 'draft')
            ->whereNull('deleted_at');
        // PostgreSQL 不允许在 count(*) 聚合查询上追加 FOR UPDATE。
        // 这里的并发保护由任务行锁和 task_runs 的单任务串行队列保证，草稿计数不需要再单独加锁。

        if ($draftQuery->count() >= $draftLimit) {
            return '草稿池已满，等待审核或按间隔发布';
        }

        return null;
    }

    private function normalizePublishInterval(Task $task): int
    {
        return max(60, (int) ($task->publish_interval ?? 3600));
    }

    /**
     * 解析并校验任务绑定的 AI 模型（必须是 active + chat）。
     */
    private function resolveAiModel(Task $task): AiModel
    {
        $aiModelId = (int) ($task->ai_model_id ?? 0);
        if ($aiModelId <= 0) {
            throw new RuntimeException('任务未配置 AI 模型');
        }

        $aiModel = AiModel::query()
            ->whereKey($aiModelId)
            ->where('status', 'active')
            ->where(function ($query): void {
                $query->whereNull('model_type')
                    ->orWhere('model_type', '')
                    ->orWhere('model_type', 'chat');
            })
            ->first();

        if (! $aiModel) {
            throw new RuntimeException('任务 AI 模型不可用');
        }

        return $aiModel;
    }

    /**
     * @param  array<string, mixed>  $generationContext
     * @return array{content:string,meta:array<string,mixed>}
     */
    private function generateContentWithModelSelection(
        Task $task,
        string $contentPrompt,
        array $generationContext,
        ?int $taskRunId,
        string $knowledgeContext,
        string $styleAppendix,
    ): array {
        $mode = (string) ($task->model_selection_mode ?? 'fixed');
        $attempts = [];
        $lastMessage = '';

        foreach ($this->resolveAiModelCandidates($task) as $candidate) {
            $unavailableReason = $this->getAiModelUnavailableReason($candidate);
            if ($unavailableReason !== null) {
                $attempts[] = $this->buildModelAttempt($candidate, 'skipped', $unavailableReason);
                $lastMessage = $unavailableReason;
                if ($mode !== 'smart_failover') {
                    throw new RuntimeException($unavailableReason);
                }

                continue;
            }

            try {
                $payload = $this->buildContentAgentPayload(
                    $task,
                    $contentPrompt,
                    $knowledgeContext,
                    $styleAppendix,
                    $taskRunId,
                    $generationContext
                );
                $payload['ai_model_id'] = (int) $candidate->id;
                $payload['model'] = $this->aiModelRuntimeBuilder->buildForExternalPayload($candidate);

                $result = $this->contentAgentClient->generateContent($payload);
                if (! $result->success) {
                    throw new RuntimeException($result->error ?? '内容生成失败');
                }

                $attempts[] = $this->buildModelAttempt($candidate, 'success', null);

                return [
                    'content' => $result->string('content'),
                    'meta' => [
                        'task_id' => (int) $task->id,
                        'insight_template_id' => isset($task->insight_template_id) ? (int) $task->insight_template_id : null,
                        'action' => 'generate_draft',
                        'title_id' => (int) ($generationContext['title_id'] ?? 0),
                        'author_id' => $generationContext['author_id'] ?? null,
                        'category_id' => $generationContext['category_id'] ?? null,
                        'knowledge_length' => mb_strlen($knowledgeContext, 'UTF-8'),
                        'model_selection_mode' => $mode,
                        'used_model_id' => (int) $candidate->id,
                        'used_model_name' => (string) $candidate->name,
                        'model_attempts' => $attempts,
                        'content_agent_backend' => $this->contentAgentClient->supportedBackend(),
                    ],
                ];
            } catch (Throwable $exception) {
                $lastMessage = trim($exception->getMessage());
                $attempts[] = $this->buildModelAttempt($candidate, 'failed', $lastMessage);

                if ($mode !== 'smart_failover') {
                    throw $exception;
                }
            }
        }

        if ($mode === 'smart_failover' && $attempts !== []) {
            throw new RuntimeException($this->buildFailoverErrorMessage($attempts, $lastMessage));
        }

        throw new RuntimeException('AI模型不可用或已达每日限制');
    }

    /**
     * @param  array<string, mixed>  $generationContext
     * @return array<string, mixed>
     */
    private function buildContentAgentPayload(
        Task $task,
        string $contentPrompt,
        string $knowledgeContext,
        string $styleAppendix,
        ?int $taskRunId,
        array $generationContext,
    ): array {
        $primaryModel = $this->resolveAiModel($task);

        return [
            'prompt' => $contentPrompt,
            'ai_model_id' => (int) $primaryModel->id,
            'model' => $this->aiModelRuntimeBuilder->buildForExternalPayload($primaryModel),
            'style_guide' => $styleAppendix,
            'evidence' => $this->parseEvidenceFromContext($knowledgeContext),
            'generation_context' => $generationContext,
            'correlation' => $taskRunId !== null && $taskRunId > 0
                ? ['type' => 'task_run', 'id' => $taskRunId]
                : null,
        ];
    }

    /**
     * @return list<array{id:string,content:string}>
     */
    private function parseEvidenceFromContext(string $knowledgeContext): array
    {
        return KnowledgeEvidenceFormatter::fromContextText($knowledgeContext);
    }

    private function shouldUseContentPipeline(Task $task): bool
    {
        $mode = (string) ($task->content_pipeline_mode ?? 'legacy');
        if ($mode === 'legacy') {
            return false;
        }

        $external = $this->contentAgentClient->supportedBackend() === 'external';
        if ($mode === 'pipeline') {
            if (! $external && filter_var(config('geoflow.content_agent.pipeline_requires_external', true), FILTER_VALIDATE_BOOLEAN)) {
                Log::channel('content_agent')->warning('content_pipeline.fallback_legacy', [
                    'task_id' => (int) $task->id,
                    'reason' => 'pipeline_requires_external',
                ]);

                return false;
            }

            return $external;
        }

        if ($mode === 'auto') {
            return $external;
        }

        return false;
    }

    /**
     * @return list<AiModel>
     */
    private function resolveAiModelCandidates(Task $task): array
    {
        $primaryModel = $this->resolveAiModel($task);
        if (($task->model_selection_mode ?? 'fixed') !== 'smart_failover') {
            return [$primaryModel];
        }

        $fallbackModels = AiModel::query()
            ->whereKeyNot((int) $primaryModel->id)
            ->where(function ($query): void {
                $query->whereNull('model_type')
                    ->orWhere('model_type', '')
                    ->orWhere('model_type', 'chat');
            })
            ->orderBy('failover_priority')
            ->orderBy('id')
            ->get()
            ->all();

        return array_values(array_merge([$primaryModel], $fallbackModels));
    }

    private function getAiModelUnavailableReason(AiModel $aiModel): ?string
    {
        if (($aiModel->status ?? 'inactive') !== 'active') {
            return 'AI模型不可用或已达每日限制';
        }

        $dailyLimit = (int) ($aiModel->daily_limit ?? 0);
        $usedToday = (int) ($aiModel->used_today ?? 0);
        if ($dailyLimit > 0 && $usedToday >= $dailyLimit) {
            return 'AI模型不可用或已达每日限制';
        }

        return null;
    }

    /**
     * @return array{model_id:int,model_name:string,status:string,reason:?string}
     */
    private function buildModelAttempt(AiModel $aiModel, string $status, ?string $reason): array
    {
        return [
            'model_id' => (int) $aiModel->id,
            'model_name' => (string) $aiModel->name,
            'status' => $status,
            'reason' => $reason,
        ];
    }

    /**
     * @param  list<array{model_id:int,model_name:string,status:string,reason:?string}>  $attempts
     */
    private function buildFailoverErrorMessage(array $attempts, string $lastMessage): string
    {
        $summaries = [];
        foreach ($attempts as $attempt) {
            $reason = trim((string) ($attempt['reason'] ?? ''));
            $summaries[] = (string) $attempt['model_name'].($reason !== '' ? '（'.$reason.'）' : '');
        }

        return '智能模型切换已尝试：'.implode('；', $summaries).'。最终失败：'.$lastMessage;
    }

    private function pickTitle(Task $task): Title
    {
        $libraryId = (int) ($task->title_library_id ?? 0);
        if ($libraryId <= 0) {
            throw new RuntimeException('任务未配置标题库');
        }

        $query = Title::query()->where('library_id', $libraryId);
        if ((int) ($task->is_loop ?? 0) !== 1) {
            $query->where(function ($builder): void {
                $builder->whereNull('used_count')->orWhere('used_count', '<=', 0);
            });
        }

        /** @var Title|null $title */
        $title = $query
            ->orderBy('used_count')
            ->orderBy('id')
            ->first();

        if (! $title) {
            throw new RuntimeException((int) ($task->is_loop ?? 0) === 1 ? '没有可用的标题' : '标题库已用尽');
        }

        return $title;
    }

    private function pickAuthor(Task $task): Author
    {
        $authorId = (int) ($task->custom_author_id ?: $task->author_id);
        if ($authorId > 0) {
            $author = Author::query()->find($authorId);
            if ($author) {
                return $author;
            }
        }

        $author = Author::query()->orderBy('id')->first();
        if ($author) {
            return $author;
        }

        return Author::query()->firstOrCreate(
            ['name' => 'GEOworkflow'],
            ['bio' => 'Default GEOworkflow author for automated content generation.']
        );
    }

    private function pickCategory(Task $task): ?Category
    {
        if (($task->category_mode ?? 'smart') === 'fixed' && (int) ($task->fixed_category_id ?? 0) > 0) {
            return Category::query()->find((int) $task->fixed_category_id);
        }

        return Category::query()->orderBy('sort_order')->orderBy('id')->first();
    }

    /**
     * 构造正文提示词：优先精确替换变量；无变量的自定义提示词自动补齐任务上下文。
     */
    private function buildContentPrompt(string $title, string $keyword, ?string $promptContent, string $knowledgeContext): string
    {
        $prompt = trim((string) $promptContent);
        $isFallbackPrompt = false;
        if ($prompt === '') {
            $prompt = "请围绕标题“{$title}”和关键词“{$keyword}”生成一篇结构清晰、语言自然的中文文章。";
            $isFallbackPrompt = true;
        }

        $hasExplicitContextVariables = $isFallbackPrompt || $this->promptHasKnownContextVariables($prompt);
        $renderedPrompt = $this->renderPromptTemplate($prompt, [
            'title' => $title,
            'keyword' => $keyword,
            'knowledge' => $knowledgeContext,
        ]);

        if (! $hasExplicitContextVariables) {
            $renderedPrompt = $this->appendSmartPromptContext($renderedPrompt, $title, $keyword, $knowledgeContext);
        }

        $finalInstructions = array_values(array_filter([
            $this->knowledgeCitationInstruction($renderedPrompt, $knowledgeContext),
            $this->finalPromptInstruction($renderedPrompt),
        ], static fn (string $instruction): bool => trim($instruction) !== ''));

        return trim($renderedPrompt)."\n\n".implode("\n", $finalInstructions);
    }

    private function promptHasKnownContextVariables(string $prompt): bool
    {
        return preg_match('/\{\{\s*(title|keyword|knowledge)\s*\}\}/iu', $prompt) === 1
            || preg_match('/\{\{#if\s+(title|keyword|knowledge)\s*\}\}/iu', $prompt) === 1;
    }

    /**
     * 渲染任务上下文变量，兼容 {{Knowledge}} 与 {{knowledge}} 等大小写写法。
     *
     * @param  array{title:string, keyword:string, knowledge:string}  $context
     */
    private function renderPromptTemplate(string $prompt, array $context): string
    {
        $renderedPrompt = preg_replace_callback('/\{\{#if\s+([A-Za-z_][A-Za-z0-9_]*)\s*\}\}(.*?)\{\{\/if\}\}/su', function (array $matches) use ($context): string {
            $name = (string) ($matches[1] ?? '');
            if (! $this->isKnownPromptContextName($name)) {
                return (string) ($matches[0] ?? '');
            }

            $value = $this->promptContextValue($name, $context);

            return trim($value) !== '' ? (string) ($matches[2] ?? '') : '';
        }, $prompt) ?? $prompt;

        return preg_replace_callback('/\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}/u', function (array $matches) use ($context): string {
            $name = (string) ($matches[1] ?? '');
            $value = $this->promptContextValue($name, $context);

            return $value !== '' || $this->isKnownPromptContextName($name) ? $value : (string) ($matches[0] ?? '');
        }, $renderedPrompt) ?? $renderedPrompt;
    }

    /**
     * @param  array{title:string, keyword:string, knowledge:string}  $context
     */
    private function promptContextValue(string $name, array $context): string
    {
        return match (mb_strtolower($name, 'UTF-8')) {
            'title' => $context['title'],
            'keyword' => $context['keyword'],
            'knowledge' => $context['knowledge'],
            default => '',
        };
    }

    private function isKnownPromptContextName(string $name): bool
    {
        return in_array(mb_strtolower($name, 'UTF-8'), ['title', 'keyword', 'knowledge'], true);
    }

    private function appendSmartPromptContext(string $prompt, string $title, string $keyword, string $knowledgeContext): string
    {
        if ($this->isLikelyEnglishPrompt($prompt)) {
            $lines = [
                'Task context:',
                '- Article title: '.$title,
            ];
            if (trim($keyword) !== '') {
                $lines[] = '- Core keyword: '.$keyword;
            }
            if (trim($knowledgeContext) !== '') {
                $lines[] = '- Reference knowledge:';
                $lines[] = $knowledgeContext;
            }

            return trim($prompt)."\n\n".implode("\n", $lines);
        }

        $lines = [
            '【任务上下文】',
            '- 文章标题：'.$title,
        ];
        if (trim($keyword) !== '') {
            $lines[] = '- 核心关键词：'.$keyword;
        }
        if (trim($knowledgeContext) !== '') {
            $lines[] = '- 参考知识：';
            $lines[] = $knowledgeContext;
        }

        return trim($prompt)."\n\n".implode("\n", $lines);
    }

    private function finalPromptInstruction(string $prompt): string
    {
        if ($this->isLikelyEnglishPrompt($prompt)) {
            return 'Please output only the final article body in Markdown. Do not repeat the prompt or output placeholders.';
        }

        return '请直接输出最终文章正文（Markdown），不要重复提示词、不要输出占位符。';
    }

    private function knowledgeCitationInstruction(string $prompt, string $knowledgeContext): string
    {
        if (trim($knowledgeContext) === '') {
            return '';
        }

        if ($this->isLikelyEnglishPrompt($prompt)) {
            return 'Knowledge citation rule: when using facts, data, or business judgments from the reference knowledge, cite the evidence ID such as [K1] in the relevant sentence. If the evidence is insufficient, use cautious wording and do not invent sources or conclusions.';
        }

        return '知识库引用要求：涉及事实、数据或业务判断时，优先依据参考知识中的 [K1] 等证据编号，并在相关句子后标注证据编号；证据不足时不要编造来源或结论。';
    }

    private function isLikelyEnglishPrompt(string $prompt): bool
    {
        preg_match_all('/\p{Han}/u', $prompt, $cjkMatches);
        preg_match_all('/[A-Za-z]/', $prompt, $latinMatches);

        return count($latinMatches[0] ?? []) > 20 && count($cjkMatches[0] ?? []) <= 3;
    }

    /**
     * 按任务配置检索知识库上下文并回填到 {{Knowledge}}。
     */
    private function resolveKnowledgeContext(Task $task, string $title, string $keyword): string
    {
        $knowledgeBaseId = (int) ($task->knowledge_base_id ?? 0);
        if ($knowledgeBaseId <= 0) {
            return '';
        }

        $knowledgeBase = KnowledgeBase::query()
            ->whereKey($knowledgeBaseId)
            ->first(['id', 'content']);
        if (! $knowledgeBase) {
            return '';
        }

        $content = trim((string) ($knowledgeBase->content ?? ''));
        if ($content === '') {
            return '';
        }

        $chunkCount = KnowledgeChunk::query()->where('knowledge_base_id', $knowledgeBaseId)->count();
        if ($chunkCount <= 0) {
            \App\Jobs\SyncKnowledgeChunksJob::dispatch($knowledgeBaseId);

            return '';
        }

        $query = trim($title."\n".$keyword);
        $context = $this->knowledgeRetrievalService->retrieveContext(
            $knowledgeBaseId,
            $query,
            $this->knowledgeConfigService->retrievalLimit(),
            $this->knowledgeConfigService->retrievalMaxChars()
        );
        if ($context !== '') {
            return $context;
        }

        $chunkCount = KnowledgeChunk::query()->where('knowledge_base_id', $knowledgeBaseId)->count();
        if ($chunkCount > 0) {
            return '';
        }

        return mb_strlen($content, 'UTF-8') > 2400 ? mb_substr($content, 0, 2400, 'UTF-8') : $content;
    }
}
