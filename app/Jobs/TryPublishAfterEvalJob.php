<?php

namespace App\Jobs;

use App\Services\GeoFlow\ArticlePublishService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Log;

class TryPublishAfterEvalJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 1;

    public int $timeout = 60;

    public function __construct(
        public readonly int $articleId,
    ) {
        $this->onQueue('geoflow');
    }

    /**
     * @return array<int, string>
     */
    public function tags(): array
    {
        return ['geoflow', 'publish_after_eval', 'article:'.$this->articleId];
    }

    public function handle(ArticlePublishService $publishService): void
    {
        $result = $publishService->tryAutoPublishAfterEval($this->articleId);
        if ($result !== null) {
            Log::info('geo_eval_publish_bridge', [
                'article_id' => $this->articleId,
                'task_id' => $result['meta']['task_id'] ?? null,
            ]);
        }
    }
}
