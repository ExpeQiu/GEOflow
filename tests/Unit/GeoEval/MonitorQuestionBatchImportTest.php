<?php

namespace Tests\Unit\GeoEval;

use App\Services\GeoEval\Monitor\MonitorQuestionService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MonitorQuestionBatchImportTest extends TestCase
{
    use RefreshDatabase;

    public function test_batch_import_creates_unique_questions(): void
    {
        $service = app(MonitorQuestionService::class);
        $created = $service->importFromTextBatch("监控问题第一条\n监控问题第二条\n监控问题第一条");

        $this->assertCount(2, $created);
    }

    public function test_tech_keywords_generate_comparison_questions(): void
    {
        $service = app(MonitorQuestionService::class);
        $created = $service->importFromTechKeywords(['纯电SUV']);

        $this->assertGreaterThanOrEqual(1, count($created));
        $this->assertStringContainsString('纯电SUV', (string) $created[0]->question_text);
    }
}
