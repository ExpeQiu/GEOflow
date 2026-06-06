<?php

namespace Tests\Unit\GeoEval;

use App\Models\KnowledgeBase;
use App\Models\KnowledgeChunk;
use App\Services\GeoEval\Simulation\SimulationRagService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class SimulationRagServiceTest extends TestCase
{
    use RefreshDatabase;

    public function test_target_ranks_in_top_k_when_chunk_matches(): void
    {
        $kb = KnowledgeBase::query()->create([
            'name' => 'Eval KB',
            'description' => 'test',
        ]);

        KnowledgeChunk::query()->create([
            'knowledge_base_id' => $kb->id,
            'chunk_index' => 0,
            'content' => '电动汽车续航里程与电池技术详解',
            'chunk_title' => 'EV',
        ]);

        $service = app(SimulationRagService::class);
        $metrics = $service->simulate(
            (int) $kb->id,
            '电动汽车续航里程',
            '电动汽车续航里程达到700公里，电池技术领先行业。'
        );

        $this->assertTrue($metrics['found']);
        $this->assertLessThanOrEqual((int) config('geo_eval.simulation.top_k', 5), $metrics['rank']);
    }
}
