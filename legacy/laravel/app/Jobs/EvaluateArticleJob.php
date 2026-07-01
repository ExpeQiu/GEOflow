<?php

namespace App\Jobs;

use App\Services\GeoEval\ArticleEvaluationService;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class EvaluateArticleJob implements ShouldQueue
{
    use Queueable;

    public int $tries = 2;

    public int $timeout = 120;

    public function __construct(
        public readonly int $articleId,
        public readonly ?int $taskRunId = null,
        public readonly ?int $taskId = null,
    ) {
        $this->onQueue('geo_eval');
    }

    public function tags(): array
    {
        return [
            'geoflow',
            'geo_eval',
            'article:'.$this->articleId,
        ];
    }

    public function handle(ArticleEvaluationService $evaluationService): void
    {
        $evaluationService->evaluateArticle($this->articleId, $this->taskRunId, $this->taskId);
    }
}
