<?php

namespace Tests\Unit\GeoEval;

use App\Services\GeoEval\Simulation\OptimizationAdvisorService;
use Tests\TestCase;

class OptimizationAdvisorServiceTest extends TestCase
{
    public function test_advises_rank_improvement_when_not_found(): void
    {
        $advisor = new OptimizationAdvisorService;
        $items = $advisor->advise('测试问题', ['found' => false, 'rank' => 99, 'top_k' => 5], ['status' => 'fail', 'tech_accuracy' => 0.2]);

        $types = array_column($items, 'type');
        $this->assertContains('rank', $types);
        $this->assertContains('accuracy', $types);
    }

    public function test_advises_info_when_metrics_good(): void
    {
        config(['geo_eval.brand_keywords' => []]);
        $advisor = new OptimizationAdvisorService;
        $items = $advisor->advise('好问题', ['found' => true, 'rank' => 1, 'top_k' => 5], [
            'status' => 'pass',
            'tech_accuracy' => 0.9,
            'keyword_hit' => true,
        ]);

        $this->assertNotEmpty($items);
        $this->assertSame('info', $items[0]['type']);
    }
}
