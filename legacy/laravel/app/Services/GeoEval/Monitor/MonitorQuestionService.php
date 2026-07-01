<?php

namespace App\Services\GeoEval\Monitor;

use App\Models\Article;
use App\Models\GeoMonitorQuestion;
use App\Models\Keyword;
use App\Models\Task;
use Illuminate\Support\Collection;

final class MonitorQuestionService
{
    /**
     * @param  array<string, mixed>  $data
     */
    public function create(array $data, ?int $adminId = null): GeoMonitorQuestion
    {
        return GeoMonitorQuestion::query()->create([
            'question_text' => (string) ($data['question_text'] ?? ''),
            'category' => (string) ($data['category'] ?? ''),
            'intent_type' => (string) ($data['intent_type'] ?? 'factual'),
            'source' => (string) ($data['source'] ?? 'manual'),
            'knowledge_base_id' => isset($data['knowledge_base_id']) ? (int) $data['knowledge_base_id'] : null,
            'task_id' => isset($data['task_id']) ? (int) $data['task_id'] : null,
            'target_article_id' => isset($data['target_article_id']) ? (int) $data['target_article_id'] : null,
            'target_content_snapshot' => $data['target_content_snapshot'] ?? null,
            'is_active' => (bool) ($data['is_active'] ?? true),
            'priority' => (int) ($data['priority'] ?? 50),
            'tags' => is_array($data['tags'] ?? null) ? $data['tags'] : [],
            'created_by_admin_id' => $adminId,
        ]);
    }

    /**
     * @param  array<string, mixed>  $data
     */
    public function update(GeoMonitorQuestion $question, array $data): GeoMonitorQuestion
    {
        $fillable = [
            'question_text', 'category', 'intent_type', 'source',
            'knowledge_base_id', 'task_id', 'target_article_id',
            'target_content_snapshot', 'is_active', 'priority', 'tags',
        ];
        foreach ($fillable as $key) {
            if (array_key_exists($key, $data)) {
                $question->{$key} = $data[$key];
            }
        }
        $question->save();

        return $question->fresh() ?? $question;
    }

    public function delete(GeoMonitorQuestion $question): void
    {
        $question->delete();
    }

    /**
     * @return Collection<int, GeoMonitorQuestion>
     */
    public function listActive(int $limit = 0): Collection
    {
        $query = GeoMonitorQuestion::query()
            ->where('is_active', true)
            ->orderByDesc('priority')
            ->orderBy('id');

        if ($limit > 0) {
            $query->limit($limit);
        }

        return $query->get();
    }

    /**
     * 从关键词库批量导入监控问题。
     *
     * @return list<GeoMonitorQuestion>
     */
    public function importFromKeywordLibrary(int $libraryId, ?int $knowledgeBaseId = null, ?int $adminId = null): array
    {
        $keywords = Keyword::query()
            ->where('library_id', $libraryId)
            ->orderBy('id')
            ->limit(200)
            ->pluck('keyword');

        $created = [];
        foreach ($keywords as $keyword) {
            $text = trim((string) $keyword);
            if ($text === '') {
                continue;
            }
            $exists = GeoMonitorQuestion::query()
                ->where('question_text', '请基于以下内容回答：'.$text)
                ->exists();
            if ($exists) {
                continue;
            }
            $created[] = $this->create([
                'question_text' => '请基于以下内容回答：'.$text,
                'category' => 'keyword_library',
                'source' => 'keyword_library',
                'knowledge_base_id' => $knowledgeBaseId,
                'intent_type' => 'factual',
            ], $adminId);
        }

        return $created;
    }

    /**
     * 批量导入问题（每行一条）。
     *
     * @return list<GeoMonitorQuestion>
     */
    public function importFromTextBatch(string $text, ?int $knowledgeBaseId = null, ?int $adminId = null): array
    {
        $lines = preg_split('/\r\n|\r|\n/u', $text) ?: [];
        $created = [];
        foreach ($lines as $line) {
            $questionText = trim($line);
            if ($questionText === '' || mb_strlen($questionText, 'UTF-8') < 4) {
                continue;
            }
            if (GeoMonitorQuestion::query()->where('question_text', $questionText)->exists()) {
                continue;
            }
            $created[] = $this->create([
                'question_text' => $questionText,
                'category' => 'batch_import',
                'source' => 'manual',
                'knowledge_base_id' => $knowledgeBaseId,
                'intent_type' => 'factual',
            ], $adminId);
        }

        return $created;
    }

    /**
     * 根据技术关键词生成对比/推荐类监控问题。
     *
     * @param  list<string>|string  $keywords
     * @return list<GeoMonitorQuestion>
     */
    public function importFromTechKeywords(array|string $keywords, ?int $knowledgeBaseId = null, ?int $adminId = null): array
    {
        $list = is_array($keywords)
            ? $keywords
            : array_values(array_filter(array_map('trim', preg_split('/[\r\n,，、]+/u', (string) $keywords) ?: [])));

        $templates = [
            '目前市面上主流的%s有哪些？请按推荐优先级排序并说明理由。',
            '%s领域有哪些值得关注的品牌或产品？请给出 Top5 推荐。',
            '如果用户咨询「%s怎么选」，你会如何推荐？请列出品牌排名。',
        ];

        $created = [];
        foreach ($list as $keyword) {
            $kw = trim((string) $keyword);
            if ($kw === '') {
                continue;
            }
            foreach ($templates as $template) {
                $questionText = sprintf($template, $kw);
                if (GeoMonitorQuestion::query()->where('question_text', $questionText)->exists()) {
                    continue;
                }
                $created[] = $this->create([
                    'question_text' => $questionText,
                    'category' => 'tech_keyword',
                    'source' => 'tech_keyword',
                    'knowledge_base_id' => $knowledgeBaseId,
                    'intent_type' => 'comparison',
                    'tech_keywords' => [$kw],
                ], $adminId);
            }
        }

        return $created;
    }

    /**
     * 解析问题的目标正文与知识库 ID。
     *
     * @return array{knowledge_base_id: int, target_html: string, article_id: int|null}
     */
    public function resolveTarget(GeoMonitorQuestion $question): array
    {
        $knowledgeBaseId = (int) ($question->knowledge_base_id ?? 0);
        $articleId = $question->target_article_id ? (int) $question->target_article_id : null;
        $targetHtml = '';

        if ($articleId) {
            $article = Article::query()->find($articleId);
            if ($article) {
                $title = htmlspecialchars((string) $article->title, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                $targetHtml = '<article><h1>'.$title.'</h1><div>'.(string) $article->content.'</div></article>';
                if ($knowledgeBaseId <= 0) {
                    $article->loadMissing('task');
                    $knowledgeBaseId = (int) ($article->task?->knowledge_base_id ?? 0);
                }
            }
        } elseif ($question->target_content_snapshot) {
            $plain = trim((string) $question->target_content_snapshot);
            $targetHtml = '<article><div>'.htmlspecialchars($plain, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8').'</div></article>';
        } elseif ($question->task_id) {
            $task = Task::query()->find((int) $question->task_id);
            if ($task) {
                if ($knowledgeBaseId <= 0) {
                    $knowledgeBaseId = (int) ($task->knowledge_base_id ?? 0);
                }
                $latestArticle = Article::query()
                    ->where('task_id', $task->id)
                    ->whereNull('deleted_at')
                    ->orderByDesc('id')
                    ->first();
                if ($latestArticle) {
                    $articleId = (int) $latestArticle->id;
                    $title = htmlspecialchars((string) $latestArticle->title, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
                    $targetHtml = '<article><h1>'.$title.'</h1><div>'.(string) $latestArticle->content.'</div></article>';
                }
            }
        }

        return [
            'knowledge_base_id' => $knowledgeBaseId,
            'target_html' => $targetHtml,
            'article_id' => $articleId,
        ];
    }
}
