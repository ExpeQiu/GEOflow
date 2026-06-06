<?php

namespace Tests\Feature;

use App\Models\AiModel;
use App\Models\Article;
use App\Models\Author;
use App\Models\Category;
use App\Models\ContentAgentRequest;
use App\Models\KnowledgeBase;
use App\Models\KnowledgeChunk;
use App\Models\Prompt;
use App\Models\Task;
use App\Models\Title;
use App\Models\TitleLibrary;
use App\Services\GeoFlow\ContentAgent\ContentAgentCallbackSigningService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Str;
use Tests\TestCase;

class ContentAgentCallbackTest extends TestCase
{
    use RefreshDatabase;

    public function test_rejects_unsigned_callback(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $response = $this->postJson('/internal/content-agent/callback', [
            'request_id' => Str::uuid()->toString(),
            'workflow_type' => 'content',
            'status' => 'success',
        ]);

        $response->assertUnauthorized();
    }

    public function test_accepts_signed_callback_for_unknown_request(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $requestId = (string) Str::uuid();
        $payload = [
            'contract_version' => '1.0',
            'request_id' => $requestId,
            'workflow_type' => 'content',
            'status' => 'success',
            'engine' => 'langgraph',
            'result' => ['content' => 'hello'],
            'error' => null,
        ];
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        $headers = app(ContentAgentCallbackSigningService::class)->signHeaders('POST', (string) $body);

        $response = $this->call(
            'POST',
            '/internal/content-agent/callback',
            [],
            [],
            [],
            $this->transformHeadersToServerVars(array_merge(['CONTENT_TYPE' => 'application/json'], $headers)),
            $body,
        );

        $response->assertUnprocessable();
        $response->assertJsonPath('message', 'unknown_request_id');
    }

    public function test_idempotent_when_request_already_completed(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $requestId = (string) Str::uuid();
        ContentAgentRequest::query()->create([
            'request_id' => $requestId,
            'workflow_type' => 'content',
            'backend' => 'external',
            'status' => 'completed',
            'correlation_type' => 'task_run',
            'correlation_id' => 1,
            'contract_version' => '1.0',
            'submitted_at' => now(),
            'completed_at' => now(),
        ]);

        $payload = [
            'contract_version' => '1.0',
            'request_id' => $requestId,
            'workflow_type' => 'content',
            'status' => 'success',
            'engine' => 'langgraph',
            'result' => ['content' => 'hello'],
            'error' => null,
        ];
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        $headers = app(ContentAgentCallbackSigningService::class)->signHeaders('POST', (string) $body);

        $response = $this->call(
            'POST',
            '/internal/content-agent/callback',
            [],
            [],
            [],
            $this->transformHeadersToServerVars(array_merge(['CONTENT_TYPE' => 'application/json'], $headers)),
            $body,
        );

        $response->assertOk();
        $response->assertJsonPath('data.status', 'already_completed');
    }

    public function test_accepts_signed_semantic_chunk_callback(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $knowledgeBase = KnowledgeBase::query()->create([
            'name' => '测试知识库',
            'content' => "# 标题\n\n段落一。\n\n段落二。",
            'file_type' => 'markdown',
            'character_count' => 20,
            'word_count' => 20,
        ]);

        $requestId = (string) \Illuminate\Support\Str::uuid();
        ContentAgentRequest::query()->create([
            'request_id' => $requestId,
            'workflow_type' => 'semantic_chunk',
            'backend' => 'external',
            'status' => 'running',
            'correlation_type' => 'knowledge_base',
            'correlation_id' => (int) $knowledgeBase->id,
            'contract_version' => '1.0',
            'payload_json' => json_encode(['knowledge_base_id' => (int) $knowledgeBase->id], JSON_UNESCAPED_UNICODE),
            'submitted_at' => now(),
        ]);

        $payload = [
            'contract_version' => '1.0',
            'request_id' => $requestId,
            'workflow_type' => 'semantic_chunk',
            'status' => 'success',
            'engine' => 'langgraph',
            'result' => [
                'knowledge_base_id' => (int) $knowledgeBase->id,
                'chunks' => [
                    [
                        'content' => '段落一。',
                        'title' => '块1',
                        'section_path' => '1',
                        'strategy' => 'semantic_llm',
                        'metadata' => [],
                    ],
                ],
                'trace' => ['steps' => ['plan_blocks', 'build_chunks']],
            ],
            'error' => null,
        ];
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        $headers = app(ContentAgentCallbackSigningService::class)->signHeaders('POST', (string) $body);

        $response = $this->call(
            'POST',
            '/internal/content-agent/callback',
            [],
            [],
            [],
            $this->transformHeadersToServerVars(array_merge(['CONTENT_TYPE' => 'application/json'], $headers)),
            $body,
        );

        $response->assertOk();
        $response->assertJsonPath('data.status', 'completed');
        $this->assertSame(1, KnowledgeChunk::query()->where('knowledge_base_id', $knowledgeBase->id)->count());
        $this->assertSame('completed', ContentAgentRequest::query()->where('request_id', $requestId)->value('status'));
        $this->assertSame('langgraph', ContentAgentRequest::query()->where('request_id', $requestId)->value('engine_hint'));
    }

    public function test_accepts_signed_content_pipeline_callback(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $aiModel = AiModel::query()->create([
            'name' => 'Pipeline Model',
            'model_id' => 'gpt-test',
            'model_type' => 'chat',
            'api_url' => 'https://api.example.com/v1',
            'status' => 'active',
        ]);
        $prompt = Prompt::query()->create([
            'name' => 'Pipeline Prompt',
            'type' => 'content',
            'content' => '写 {{title}}',
        ]);
        $titleLibrary = TitleLibrary::query()->create(['name' => 'Pipeline Titles']);
        $category = Category::query()->create(['name' => '科技', 'slug' => 'tech-pipeline']);
        $author = Author::query()->create(['name' => 'Pipeline Author']);
        $task = Task::query()->create([
            'name' => 'Pipeline Task',
            'title_library_id' => $titleLibrary->id,
            'prompt_id' => $prompt->id,
            'ai_model_id' => $aiModel->id,
            'status' => 'active',
            'schedule_enabled' => 1,
            'need_review' => 0,
            'content_pipeline_mode' => 'pipeline',
            'publish_interval' => 3600,
            'draft_limit' => 5,
            'article_limit' => 10,
        ]);
        $title = Title::query()->create([
            'library_id' => $titleLibrary->id,
            'title' => '测试标题',
            'keyword' => 'GEO',
            'used' => 0,
        ]);

        $requestId = (string) Str::uuid();
        $storedPayload = [
            'generation_context' => [
                'task_id' => (int) $task->id,
                'task_run_id' => 0,
                'title_id' => (int) $title->id,
                'category_id' => (int) $category->id,
                'author_id' => (int) $author->id,
                'keyword' => 'GEO',
                'knowledge_context' => '',
            ],
        ];
        ContentAgentRequest::query()->create([
            'request_id' => $requestId,
            'workflow_type' => 'content_pipeline',
            'backend' => 'external',
            'status' => 'running',
            'correlation_type' => 'task_run',
            'correlation_id' => 0,
            'contract_version' => '1.0',
            'payload_json' => json_encode($storedPayload, JSON_UNESCAPED_UNICODE),
            'submitted_at' => now(),
        ]);

        $payload = [
            'contract_version' => '1.0',
            'request_id' => $requestId,
            'workflow_type' => 'content_pipeline',
            'status' => 'success',
            'engine' => 'langgraph',
            'result' => [
                'pipeline_mode' => 'deep',
                'content' => "# 测试\n\n正文 [K1]",
                'citations' => ['K1'],
                'cross_validation' => [['node' => 'post_writer', 'passed' => true]],
                'compliance' => ['passed' => true, 'violations' => []],
                'memory_patch' => ['summary' => '测试摘要'],
                'trace' => ['steps' => ['chief', 'deputy_route', 'writer', 'deputy_finalize']],
            ],
            'error' => null,
        ];
        $body = json_encode($payload, JSON_UNESCAPED_UNICODE);
        $headers = app(ContentAgentCallbackSigningService::class)->signHeaders('POST', (string) $body);

        $response = $this->call(
            'POST',
            '/internal/content-agent/callback',
            [],
            [],
            [],
            $this->transformHeadersToServerVars(array_merge(['CONTENT_TYPE' => 'application/json'], $headers)),
            $body,
        );

        $response->assertOk();
        $response->assertJsonPath('data.status', 'completed');
        $this->assertSame('completed', ContentAgentRequest::query()->where('request_id', $requestId)->value('status'));
        $this->assertSame(1, Article::query()->where('task_id', $task->id)->count());
        $this->assertDatabaseHas('content_agent_memories', [
            'task_id' => (int) $task->id,
            'scope' => 'task',
        ]);
    }
}
