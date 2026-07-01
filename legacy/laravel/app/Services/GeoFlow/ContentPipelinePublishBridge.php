<?php

namespace App\Services\GeoFlow;

use App\Models\Article;
use App\Models\Task;
use Illuminate\Support\Facades\Log;

/** Pipeline 回调后按条件触发自动发布（终审通过 + schedule_enabled）。 */
final class ContentPipelinePublishBridge
{
    public function __construct(
        private readonly ArticlePublishService $articlePublishService,
    ) {}

    public function tryPublishAfterPipeline(int $articleId, Task $task): ?array
    {
        $article = Article::query()->whereKey($articleId)->first();
        if (! $article) {
            return null;
        }

        $reviewOk = in_array((string) ($article->review_status ?? ''), ['approved', 'auto_approved'], true);
        $scheduleOn = (int) ($task->schedule_enabled ?? 0) === 1;

        if (! $reviewOk || ! $scheduleOn) {
            Log::channel('content_agent')->info('content_pipeline.publish_skipped', [
                'article_id' => $articleId,
                'task_id' => (int) $task->id,
                'review_status' => (string) ($article->review_status ?? ''),
                'schedule_enabled' => (int) ($task->schedule_enabled ?? 0),
            ]);

            return null;
        }

        $result = $this->articlePublishService->publishDueDraftForTask($task);
        if ($result !== null) {
            Log::channel('content_agent')->info('content_pipeline.publish_triggered', [
                'article_id' => $articleId,
                'task_id' => (int) $task->id,
            ]);
        }

        return $result;
    }
}
