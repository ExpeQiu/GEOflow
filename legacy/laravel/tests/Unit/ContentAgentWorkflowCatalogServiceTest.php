<?php

namespace Tests\Unit;

use App\Services\GeoFlow\ContentAgent\ContentAgentWorkflowCatalogService;
use Tests\TestCase;

class ContentAgentWorkflowCatalogServiceTest extends TestCase
{
    public function test_catalog_includes_content_pipeline_with_visual_steps(): void
    {
        $catalog = app(ContentAgentWorkflowCatalogService::class)->catalog();

        $this->assertArrayHasKey('workflows', $catalog);
        $this->assertArrayHasKey('content_pipeline', $catalog['workflows']);

        $pipeline = $catalog['workflows']['content_pipeline'];
        $this->assertNotEmpty($pipeline['nodes']);
        $this->assertSame('pipeline_fork', $pipeline['visual_layout']);
        $this->assertIsArray($pipeline['visual_pipeline']);
        $this->assertArrayHasKey('paths', $pipeline['visual_pipeline']);
        $this->assertArrayHasKey('fast', $pipeline['visual_pipeline']['paths']);
        $this->assertArrayHasKey('deep', $pipeline['visual_pipeline']['paths']);
        $this->assertArrayHasKey('chief', $pipeline['nodes']);
        $this->assertSame('content_pipeline', $catalog['default_workflow']);
    }
}
