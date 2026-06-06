<?php

namespace App\Services\GeoFlow\ContentAgent;

use App\Ai\Agents\MarkdownContentWriterAgent;
use App\Models\AiModel;
use App\Services\GeoFlow\ContentAgent\Dto\ContentAgentResult;
use App\Support\GeoFlow\OpenAiRuntimeProvider;
use Illuminate\Support\Facades\DB;
use Throwable;

/** URL 导入 AI 分析（internal 路径复用现有 prompt 结构）。 */
final class UrlImportAnalysisRunner
{
    public function __construct(private readonly AiModelRuntimeBuilder $runtimeBuilder) {}

    /**
     * @param  array<string, mixed>  $payload
     */
    public function run(array $payload): ContentAgentResult
    {
        $pageJson = is_array($payload['page_json'] ?? null) ? $payload['page_json'] : [];
        if ($pageJson === []) {
            return new ContentAgentResult(false, [], 'page_json 不能为空');
        }

        $modelId = (int) ($payload['ai_model_id'] ?? 0);
        $model = AiModel::query()->whereKey($modelId)->where('status', 'active')->first();
        if (! $model) {
            return new ContentAgentResult(false, [], 'AI 模型不可用');
        }

        try {
            $runtime = $this->runtimeBuilder->buildFromModel($model);
            $cleaned = $this->requestJson(
                $runtime,
                '你是网页内容清洗助手，输出 JSON。',
                '请清洗以下页面 JSON，返回 {"title":"","description":"","text":"","summary":""}：'.json_encode($pageJson, JSON_UNESCAPED_UNICODE)
            );

            $knowledgePayload = $this->requestJson(
                $runtime,
                '你是知识库构建助手，输出 JSON。',
                '基于页面生成知识库，返回 {"summary":"","library_name":"","knowledge_markdown":""}：'
                .json_encode(['page' => $pageJson, 'cleaned' => $cleaned], JSON_UNESCAPED_UNICODE)
            );

            $knowledgeMarkdown = trim((string) ($knowledgePayload['knowledge_markdown'] ?? ''));
            if ($knowledgeMarkdown === '') {
                return new ContentAgentResult(false, [], '知识库内容为空');
            }

            $keywordPayload = $this->requestJson(
                $runtime,
                '你是 SEO 关键词助手，输出 JSON。',
                '返回 {"keywords":["..."]}，基于：'.json_encode(['knowledge' => $knowledgeMarkdown], JSON_UNESCAPED_UNICODE),
                'keywords'
            );
            $keywords = $this->normalizeList($keywordPayload['keywords'] ?? []);
            if ($keywords === []) {
                return new ContentAgentResult(false, [], '关键词为空');
            }

            $titlePayload = $this->requestJson(
                $runtime,
                '你是标题生成助手，输出 JSON。',
                '返回 {"titles":["..."]}，基于关键词：'.implode('、', $keywords),
                'titles'
            );
            $titles = $this->normalizeList($titlePayload['titles'] ?? []);
            if ($titles === []) {
                return new ContentAgentResult(false, [], '标题为空');
            }

            AiModel::query()->whereKey((int) $model->id)->update([
                'used_today' => DB::raw('COALESCE(used_today,0)+1'),
                'total_used' => DB::raw('COALESCE(total_used,0)+1'),
                'updated_at' => now(),
            ]);

            return new ContentAgentResult(true, [
                'summary' => trim((string) ($knowledgePayload['summary'] ?? $cleaned['summary'] ?? '')),
                'library_name' => trim((string) ($knowledgePayload['library_name'] ?? $cleaned['title'] ?? '导入知识库')),
                'keywords' => array_slice($keywords, 0, 10),
                'titles' => array_slice($titles, 0, 50),
                'knowledge_markdown' => $knowledgeMarkdown,
                'analysis_source' => 'ai',
                'model' => ['id' => (int) $model->id, 'name' => (string) $model->name],
                'page_json' => $pageJson,
                'cleaned' => $cleaned,
            ]);
        } catch (Throwable $exception) {
            return new ContentAgentResult(false, [], $exception->getMessage());
        }
    }

    /**
     * @param  array{provider:string,model_id:string,provider_url:string}  $runtime
     * @return array<string, mixed>
     */
    private function requestJson(array $runtime, string $systemPrompt, string $userPrompt, ?string $listKey = null): array
    {
        $agent = new MarkdownContentWriterAgent($systemPrompt);
        $response = $agent->prompt($userPrompt, [], $runtime['provider'], $runtime['model_id']);
        $text = OpenAiRuntimeProvider::normalizeGeneratedText((string) ($response->text ?? ''));
        if ($text === '') {
            throw new \RuntimeException('AI 返回空内容');
        }

        $decoded = json_decode($text, true);
        if (is_array($decoded)) {
            return $decoded;
        }

        if ($listKey !== null) {
            $lines = array_values(array_filter(array_map('trim', preg_split('/\R/u', $text) ?: [])));
            if ($lines !== []) {
                return [$listKey => $lines];
            }
        }

        throw new \RuntimeException('AI 返回无效 JSON');
    }

    /**
     * @return list<string>
     */
    private function normalizeList(mixed $values): array
    {
        if (! is_array($values)) {
            return [];
        }

        return array_values(array_filter(array_map(
            static fn (mixed $item): string => trim(is_string($item) || is_numeric($item) ? (string) $item : ''),
            $values
        ), static fn (string $item): bool => $item !== ''));
    }
}
