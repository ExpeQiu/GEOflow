<?php

namespace Tests\Unit\GeoEval;

use App\Models\GeoMonitorQuestion;
use App\Models\KnowledgeBase;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;
use App\Services\GeoEval\Monitor\MonitorScanOrchestrator;
use App\Services\GeoEval\Monitor\MonitorQuestionService;
use App\Services\GeoEval\Simulation\OptimizationAdvisorService;
use App\Services\GeoEval\GeoEvalStructuredLogger;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Mockery;
use Tests\TestCase;

class MonitorScanOrchestratorTest extends TestCase
{
    use RefreshDatabase;

    public function test_scan_question_writes_result_when_simulation_succeeds(): void
    {
        $kb = KnowledgeBase::query()->create(['name' => 'Test KB']);

        $question = GeoMonitorQuestion::query()->create([
            'question_text' => '请介绍产品核心优势',
            'knowledge_base_id' => $kb->id,
            'target_content_snapshot' => '我们的产品具有领先的技术优势与可靠的服务体系。',
            'is_active' => true,
            'priority' => 50,
        ]);

        $client = Mockery::mock(GeoEvalClientInterface::class);
        $client->shouldReceive('runSimulation')->once()->andReturn([
            'request_id' => 'req-1',
            'data' => [
                'answer' => '我们的产品具有领先的技术优势',
                'metrics' => [
                    'found' => true,
                    'rank' => 2,
                    'top_k' => 5,
                    'target_score' => 0.8,
                    'top_scores' => [0.9, 0.8],
                    'doc_count' => 3,
                ],
            ],
        ]);
        $client->shouldReceive('auditAnswer')->once()->andReturn([
            'request_id' => 'req-1',
            'data' => [
                'status' => 'pass',
                'tech_accuracy' => 0.8,
                'brand_consistency' => 1.0,
                'keyword_hit' => true,
            ],
        ]);

        $orchestrator = new MonitorScanOrchestrator(
            app(MonitorQuestionService::class),
            $client,
            app(OptimizationAdvisorService::class),
            app(\App\Services\GeoEval\Monitor\MonitorAiProbeService::class),
            app(GeoEvalStructuredLogger::class),
        );

        $run = \App\Models\GeoMonitorRun::query()->create([
            'run_type' => 'manual',
            'status' => 'running',
            'question_count' => 1,
        ]);

        $result = $orchestrator->scanQuestion($question, (int) $run->id);

        $this->assertNotNull($result);
        $this->assertSame(2, (int) $result->rank);
        $this->assertTrue((bool) $result->found);
        $this->assertIsArray($result->recommendations);
    }
}
