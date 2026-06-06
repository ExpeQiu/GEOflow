<?php

namespace App\Services\GeoFlow;

use App\Models\Article;
use App\Models\Task;
use App\Services\GeoEval\ArticleEvaluationService;
use App\Support\GeoFlow\ArticleWorkflow;
use Illuminate\Support\Facades\DB;
use RuntimeException;

/**
 * 文章发布域服务：统一 publish_scope、评估门禁与分发入队。
 */
final class ArticlePublishService
{
    public function __construct(
        private readonly ArticleEvaluationService $articleEvaluationService,
        private readonly DistributionOrchestrator $distributionOrchestrator,
    ) {}

    /**
     * 按任务发布一条已到期的已审核草稿（Worker / 评估后自动发布）。
     *
     * @return array{article_id:int, title:string, message:string, meta:array<string,mixed>}|null
     */
    public function publishDueDraftForTask(Task $task): ?array
    {
        if ($task->next_publish_at !== null && $task->next_publish_at->greaterThan(now())) {
            return null;
        }

        return DB::transaction(function () use ($task): ?array {
            $freshTask = Task::query()
                ->whereKey((int) $task->id)
                ->lockForUpdate()
                ->first(['id', 'status', 'schedule_enabled', 'publish_interval', 'next_publish_at', 'publish_scope']);
            if (! $freshTask || ($freshTask->status ?? 'paused') !== 'active' || (int) ($freshTask->schedule_enabled ?? 1) !== 1) {
                throw new RuntimeException('任务未激活');
            }

            if ($freshTask->next_publish_at !== null && $freshTask->next_publish_at->greaterThan(now())) {
                return null;
            }

            /** @var Article|null $article */
            $article = Article::query()
                ->where('task_id', (int) $freshTask->id)
                ->where('status', 'draft')
                ->whereIn('review_status', ['approved', 'auto_approved'])
                ->whereNull('deleted_at')
                ->orderBy('id')
                ->lockForUpdate()
                ->first(['id', 'title', 'review_status', 'eval_status']);
            if (! $article) {
                return null;
            }

            if (! $this->canAutoPublish($article)) {
                return null;
            }

            $this->applyPublishState($article, $freshTask);
            $publishInterval = max(60, (int) ($freshTask->publish_interval ?? 3600));
            Task::query()->whereKey((int) $freshTask->id)->update([
                'published_count' => DB::raw('COALESCE(published_count,0)+1'),
                'next_publish_at' => now()->addSeconds($publishInterval),
                'updated_at' => now(),
            ]);

            $this->distributionOrchestrator->enqueueForArticle($article, 'publish');

            return [
                'article_id' => (int) $article->id,
                'title' => (string) $article->title,
                'message' => '草稿发布成功',
                'meta' => [
                    'task_id' => (int) $freshTask->id,
                    'action' => 'publish_draft',
                    'publish_interval' => $publishInterval,
                ],
            ];
        });
    }

    /**
     * GEO 评估通过后尝试自动发布（eval 桥接）。
     *
     * @return array{article_id:int, title:string, message:string, meta:array<string,mixed>}|null
     */
    public function tryAutoPublishAfterEval(int $articleId): ?array
    {
        $article = Article::query()
            ->with('task:id,publish_scope,publish_interval,next_publish_at,status,schedule_enabled')
            ->whereKey($articleId)
            ->first(['id', 'title', 'status', 'review_status', 'eval_status', 'task_id', 'published_at']);
        if (! $article || ! $article->task) {
            return null;
        }

        if ((string) $article->status !== 'draft') {
            return null;
        }

        if (! in_array((string) $article->review_status, ['approved', 'auto_approved'], true)) {
            return null;
        }

        if (! $this->canAutoPublish($article)) {
            return null;
        }

        return $this->publishDueDraftForTask($article->task);
    }

    /**
     * 后台 / API 发布或审核通过后的状态迁移。
     *
     * @return array{status:string, review_status:string, published_at:?string}
     */
    public function resolveWorkflowForApproval(Article $article, string $reviewStatus): array
    {
        $article->loadMissing('task:id,publish_scope,need_review');
        $publishScope = (string) ($article->task?->publish_scope ?? 'local_and_distribution');

        $desiredStatus = (string) ($article->status ?? 'draft');
        if (in_array($reviewStatus, ['approved', 'auto_approved'], true)) {
            $needsReview = (int) ($article->task?->need_review ?? 1);
            if ($reviewStatus === 'auto_approved' || $needsReview === 0) {
                $desiredStatus = $this->targetStatusForScope($publishScope);
            }
        }

        return ArticleWorkflow::normalizeState(
            $desiredStatus,
            $reviewStatus,
            $article->published_at?->format('Y-m-d H:i:s')
        );
    }

    /**
     * 后台/API 显式设为已发布。
     *
     * @return array{status:string, review_status:string, published_at:?string}
     */
    public function resolveWorkflowForExplicitPublish(Article $article): array
    {
        $article->loadMissing('task:id,publish_scope');
        $publishScope = (string) ($article->task?->publish_scope ?? 'local_and_distribution');
        $reviewStatus = (string) ($article->review_status ?? 'pending');
        if (! in_array($reviewStatus, ['approved', 'auto_approved'], true)) {
            throw new RuntimeException('当前文章状态不允许直接发布');
        }

        return ArticleWorkflow::normalizeState(
            $this->targetStatusForScope($publishScope),
            $reviewStatus,
            $article->published_at?->format('Y-m-d H:i:s')
        );
    }

    public function enqueueDistributionAfterPublish(Article|int $article, string $action = 'publish'): void
    {
        $this->distributionOrchestrator->enqueueForArticle($article, $action);
    }

    public function enqueueDistributionAfterDelete(Article|int $article): void
    {
        $this->distributionOrchestrator->enqueueDeleteForArticle($article);
    }

    /**
     * 任务是否存在因 GEO 评估而阻塞发布的草稿。
     */
    public function hasDraftBlockedByEval(Task $task): bool
    {
        if (! config('geo_eval.enabled') || ! config('geo_eval.gate_enabled')) {
            return false;
        }

        $draft = Article::query()
            ->where('task_id', (int) $task->id)
            ->where('status', 'draft')
            ->whereIn('review_status', ['approved', 'auto_approved'])
            ->whereNull('deleted_at')
            ->orderBy('id')
            ->first(['id', 'eval_status']);

        if (! $draft) {
            return false;
        }

        return ! $this->articleEvaluationService->canPublish($draft);
    }

    public function targetStatusForScope(?string $publishScope): string
    {
        return $publishScope === 'distribution_only' ? 'private' : 'published';
    }

    private function canAutoPublish(Article $article): bool
    {
        return $this->articleEvaluationService->canPublish($article);
    }

    private function applyPublishState(Article $article, Task $task): void
    {
        $publishScope = (string) ($task->publish_scope ?? 'local_and_distribution');
        $workflow = ArticleWorkflow::normalizeState(
            $this->targetStatusForScope($publishScope),
            (string) ($article->review_status ?: 'approved')
        );
        Article::query()->whereKey((int) $article->id)->update([
            'status' => $workflow['status'],
            'review_status' => $workflow['review_status'],
            'published_at' => $workflow['published_at'],
            'updated_at' => now(),
        ]);
        $article->refresh();
    }
}
