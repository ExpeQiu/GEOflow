<?php

namespace Tests\Feature;

use App\Models\Admin;
use App\Models\KnowledgeBase;
use App\Models\SiteSetting;
use App\Services\GeoFlow\ContentAgent\ContentAgentAsyncSubmittedException;
use App\Services\GeoFlow\KnowledgeChunkSyncService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class KnowledgeSemanticChunkAsyncTest extends TestCase
{
    use RefreshDatabase;

    public function test_external_backend_submits_semantic_chunk_async(): void
    {
        config([
            'geoflow.content_agent.backend' => 'external',
            'geoflow.content_agent.service_url' => 'http://content-agent.test',
            'geoflow.content_agent.callback_url' => 'http://app.test/internal/content-agent/callback',
        ]);

        Http::fake([
            'http://content-agent.test/v1/workflows/semantic_chunk/run_async' => Http::response([
                'request_id' => 'async-req-001',
                'status' => 'accepted',
            ], 202),
        ]);

        SiteSetting::query()->create([
            'setting_key' => 'knowledge_chunk_strategy',
            'setting_value' => 'semantic_llm',
        ]);

        $knowledgeBase = KnowledgeBase::query()->create([
            'name' => '异步切片库',
            'content' => "# A\n\n段落内容。",
            'file_type' => 'markdown',
            'character_count' => 10,
            'word_count' => 10,
        ]);

        try {
            app(KnowledgeChunkSyncService::class)->sync((int) $knowledgeBase->id, (string) $knowledgeBase->content);
            $this->fail('应抛出 ContentAgentAsyncSubmittedException');
        } catch (ContentAgentAsyncSubmittedException $exception) {
            $this->assertSame('async-req-001', $exception->requestId);
        }

        $this->assertDatabaseHas('content_agent_requests', [
            'request_id' => 'async-req-001',
            'workflow_type' => 'semantic_chunk',
            'correlation_type' => 'knowledge_base',
            'correlation_id' => (int) $knowledgeBase->id,
        ]);
    }

    public function test_knowledge_store_shows_async_submitted_message(): void
    {
        config(['geoflow.content_agent.backend' => 'external']);

        $admin = Admin::query()->create([
            'username' => 'kb_async_admin',
            'password' => 'secret',
            'email' => 'kb-async@example.com',
            'display_name' => 'KB Async',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $service = $this->createMock(KnowledgeChunkSyncService::class);
        $service->method('sync')->willThrowException(new ContentAgentAsyncSubmittedException('req-async-99'));
        $this->app->instance(KnowledgeChunkSyncService::class, $service);

        $response = $this->actingAs($admin, 'admin')->post(route('admin.knowledge-bases.store'), [
            'name' => '异步测试库',
            'content' => "# 测试\n\n内容。",
            'file_type' => 'markdown',
            'import_action' => 'save_and_chunk',
        ]);

        $response->assertRedirect(route('admin.knowledge-bases.index'));
        $response->assertSessionHas('message', __('admin.knowledge_bases.message.chunks_async_submitted', [
            'request_id' => 'req-async-99',
        ]));
    }
}
