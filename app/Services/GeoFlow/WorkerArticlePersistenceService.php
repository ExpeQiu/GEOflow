<?php

namespace App\Services\GeoFlow;

use App\Models\Article;
use App\Models\ArticleImage;
use App\Models\Author;
use App\Models\Category;
use App\Models\Image;
use App\Models\Task;
use App\Models\Title;
use App\Support\GeoFlow\ArticleWorkflow;
use App\Support\GeoFlow\ImageUrlNormalizer;
use App\Services\GeoEval\ArticleEvaluationService;
use Illuminate\Support\Facades\DB;
use RuntimeException;

/** Worker 正文落库与插图逻辑，供同步执行与 Content Agent 回调复用。 */
final class WorkerArticlePersistenceService
{
    public function __construct(
        private readonly ArticleEvaluationService $articleEvaluationService,
    ) {}

    /**
     * @param  array<string, mixed>  $context
     * @return array{article_id:int,meta:array<string,mixed>}
     */
    public function persistGeneratedArticle(array $context): array
    {
        /** @var Task $task */
        $task = $context['task'];
        /** @var Title $titleRow */
        $titleRow = $context['title_row'];
        /** @var Author|null $author */
        $author = $context['author'] ?? null;
        /** @var Category|null $category */
        $category = $context['category'] ?? null;
        $keyword = (string) ($context['keyword'] ?? '');
        $content = (string) ($context['content'] ?? '');
        $knowledgeContext = (string) ($context['knowledge_context'] ?? '');
        $generationMeta = is_array($context['generation_meta'] ?? null) ? $context['generation_meta'] : [];

        $imageResult = $this->insertTaskImagesIntoContent($task, $content);
        $content = $imageResult['content'];
        $selectedImages = $imageResult['images'];
        $excerpt = $this->buildExcerpt($content);
        $workflow = [
            'status' => 'draft',
            'review_status' => (int) ($task->need_review ?? 1) === 1 ? 'pending' : 'approved',
            'published_at' => null,
        ];

        $articleId = DB::transaction(function () use ($task, $titleRow, $author, $category, $keyword, $content, $excerpt, $workflow, $selectedImages): int {
            $freshTask = Task::query()
                ->whereKey((int) $task->id)
                ->lockForUpdate()
                ->first(['id', 'status', 'schedule_enabled', 'created_count', 'draft_limit', 'article_limit', 'publish_interval', 'next_publish_at']);
            if (! $freshTask || ($freshTask->status ?? 'paused') !== 'active' || (int) ($freshTask->schedule_enabled ?? 1) !== 1) {
                throw new RuntimeException('任务未激活');
            }

            $article = Article::query()->create([
                'title' => (string) $titleRow->title,
                'slug' => ArticleWorkflow::generateUniqueSlug((string) $titleRow->title),
                'excerpt' => $excerpt,
                'content' => $content,
                'category_id' => $category?->id,
                'author_id' => $author?->id,
                'task_id' => (int) $task->id,
                'original_keyword' => $keyword,
                'keywords' => $keyword,
                'meta_description' => mb_substr($excerpt, 0, 120),
                'status' => $workflow['status'],
                'review_status' => $workflow['review_status'],
                'eval_status' => $this->articleEvaluationService->initialEvalStatusForArticle(),
                'is_ai_generated' => 1,
                'published_at' => $workflow['published_at'],
                'view_count' => 0,
            ]);

            foreach ($selectedImages as $position => $image) {
                ArticleImage::query()->create([
                    'article_id' => (int) $article->id,
                    'image_id' => (int) $image->id,
                    'position' => $position,
                ]);
                Image::query()->whereKey((int) $image->id)->update([
                    'used_count' => DB::raw('COALESCE(used_count,0)+1'),
                    'usage_count' => DB::raw('COALESCE(usage_count,0)+1'),
                ]);
            }

            Title::query()->whereKey($titleRow->id)->increment('used_count');
            Title::query()->whereKey($titleRow->id)->increment('usage_count');

            $taskUpdate = [
                'created_count' => DB::raw('COALESCE(created_count,0)+1'),
                'loop_count' => DB::raw('COALESCE(loop_count,0)+1'),
                'updated_at' => now(),
            ];
            if ($freshTask->next_publish_at === null || ! $freshTask->next_publish_at->greaterThan(now())) {
                $taskUpdate['next_publish_at'] = now()->addSeconds(max(60, (int) ($freshTask->publish_interval ?? 3600)));
            }
            Task::query()->whereKey($task->id)->update($taskUpdate);

            return (int) $article->id;
        });

        if ($articleId > 0) {
            Article::query()->whereKey($articleId)->update([
                'eval_status' => $this->articleEvaluationService->initialEvalStatusForArticle($articleId),
            ]);
            $this->articleEvaluationService->queueEvaluation($articleId, isset($context['task_run_id']) ? (int) $context['task_run_id'] : null, (int) $task->id);
        }

        return [
            'article_id' => $articleId,
            'meta' => array_merge([
                'task_id' => (int) $task->id,
                'action' => 'generate_draft',
                'title_id' => (int) $titleRow->id,
                'author_id' => $author?->id,
                'category_id' => $category?->id,
                'knowledge_length' => mb_strlen($knowledgeContext, 'UTF-8'),
                'image_count' => count($selectedImages),
            ], $generationMeta),
        ];
    }

    /**
     * @return array{content:string,images:list<Image>}
     */
    public function insertTaskImagesIntoContent(Task $task, string $content): array
    {
        $libraryId = (int) ($task->image_library_id ?? 0);
        if ($libraryId <= 0) {
            return ['content' => $content, 'images' => []];
        }

        $images = Image::query()
            ->where('library_id', $libraryId)
            ->orderBy('used_count')
            ->orderBy('id')
            ->limit(3)
            ->get();

        if ($images->isEmpty()) {
            return ['content' => $content, 'images' => []];
        }

        $blocks = [];
        foreach ($images as $image) {
            $url = ImageUrlNormalizer::toPublicUrl((string) ($image->file_path ?? ''));
            if ($url === '') {
                continue;
            }
            $alt = ImageUrlNormalizer::readableAlt((string) ($image->original_name ?? $image->filename ?? ''));
            $blocks[] = '!['.$alt.']('.$url.')';
        }

        if ($blocks === []) {
            return ['content' => $content, 'images' => []];
        }

        $prefix = implode("\n\n", $blocks)."\n\n";

        return [
            'content' => $prefix.$content,
            'images' => $images->all(),
        ];
    }

    public function buildExcerpt(string $content): string
    {
        $plain = trim(preg_replace('/\s+/u', ' ', strip_tags($content)) ?? '');

        return mb_strlen($plain, 'UTF-8') > 200 ? mb_substr($plain, 0, 200, 'UTF-8') : $plain;
    }
}
