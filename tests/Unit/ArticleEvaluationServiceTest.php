<?php

namespace Tests\Unit;

use App\Models\Article;
use App\Models\Author;
use App\Models\Category;
use App\Models\KnowledgeBase;
use App\Models\KnowledgeChunk;
use App\Models\Task;
use App\Services\GeoEval\ArticleEvaluationService;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ArticleEvaluationServiceTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        config([
            'geo_eval.enabled' => true,
            'geo_eval.gate_enabled' => true,
            'geo_eval.gate_rollout_percent' => 100,
        ]);
    }

    public function test_evaluate_article_passes_with_knowledge_base(): void
    {
        $article = $this->createDraftArticleWithKnowledge();
        $service = app(ArticleEvaluationService::class);

        $result = $service->evaluateArticle((int) $article->id);

        $this->assertContains($result['status'], ['passed', 'failed']);
        $article->refresh();
        $this->assertSame($result['status'], $article->eval_status);
    }

    public function test_evaluate_skips_without_knowledge_base(): void
    {
        $article = $this->createDraftArticle();
        $service = app(ArticleEvaluationService::class);

        $result = $service->evaluateArticle((int) $article->id);

        $this->assertSame('skipped', $result['status']);
        $this->assertSame('no_knowledge_base', $result['failure_reason']);
    }

    public function test_can_publish_only_when_passed_or_skipped(): void
    {
        $service = app(ArticleEvaluationService::class);
        $article = $this->createDraftArticle();
        $article->eval_status = 'failed';
        $article->save();

        $this->assertFalse($service->canPublish($article));

        $article->eval_status = 'passed';
        $article->save();
        $this->assertTrue($service->canPublish($article));
    }

    private function createDraftArticle(): Article
    {
        $category = Category::query()->create([
            'name' => 'Eval Cat',
            'slug' => 'eval-cat-'.uniqid(),
        ]);
        $author = Author::query()->create([
            'name' => 'Eval Author',
        ]);

        return Article::query()->create([
            'title' => 'Eval Article',
            'slug' => 'eval-article-'.uniqid(),
            'content' => '<p>test content</p>',
            'category_id' => $category->id,
            'author_id' => $author->id,
            'status' => 'draft',
            'review_status' => 'approved',
            'eval_status' => 'pending_eval',
            'original_keyword' => '测试关键词',
        ]);
    }

    private function createDraftArticleWithKnowledge(): Article
    {
        $kb = KnowledgeBase::query()->create(['name' => 'KB', 'description' => 'd']);
        KnowledgeChunk::query()->create([
            'knowledge_base_id' => $kb->id,
            'chunk_index' => 0,
            'content' => '测试关键词与行业领先技术说明',
        ]);

        $task = Task::query()->create([
            'name' => 'Eval Task',
            'knowledge_base_id' => $kb->id,
            'publish_interval' => 3600,
            'status' => 'active',
        ]);

        $article = $this->createDraftArticle();
        $article->task_id = $task->id;
        $article->content = '<p>测试关键词与行业领先技术说明，内容充实。'.str_repeat('详情。', 40).'</p>';
        $article->save();

        return $article;
    }
}
