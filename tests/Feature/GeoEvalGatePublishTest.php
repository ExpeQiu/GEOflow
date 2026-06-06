<?php

namespace Tests\Feature;

use App\Models\Article;
use App\Services\GeoEval\ArticleEvaluationService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class GeoEvalGatePublishTest extends TestCase
{
    use RefreshDatabase;

    public function test_gate_blocks_failed_eval_when_enabled(): void
    {
        config([
            'geo_eval.enabled' => true,
            'geo_eval.gate_enabled' => true,
        ]);

        $article = new Article(['eval_status' => 'failed']);
        $service = app(ArticleEvaluationService::class);

        $this->assertFalse($service->canPublish($article));

        $article->eval_status = 'passed';
        $this->assertTrue($service->canPublish($article));

        $article->eval_status = 'skipped';
        $this->assertTrue($service->canPublish($article));
    }

    public function test_gate_disabled_allows_failed_eval(): void
    {
        config([
            'geo_eval.enabled' => true,
            'geo_eval.gate_enabled' => false,
        ]);

        $article = new Article(['eval_status' => 'failed']);
        $this->assertTrue(app(ArticleEvaluationService::class)->canPublish($article));
    }

    public function test_rollout_skips_eval_for_out_of_bucket_article(): void
    {
        config([
            'geo_eval.enabled' => true,
            'geo_eval.gate_rollout_percent' => 10,
        ]);

        $outOfRollout = new Article;
        $outOfRollout->setAttribute('id', 50);
        $inRollout = new Article;
        $inRollout->setAttribute('id', 5);
        $service = app(ArticleEvaluationService::class);

        $this->assertFalse($service->shouldEvaluateArticle($outOfRollout));
        $this->assertTrue($service->shouldEvaluateArticle($inRollout));
    }
}
