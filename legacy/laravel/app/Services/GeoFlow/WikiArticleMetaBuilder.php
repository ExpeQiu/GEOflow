<?php

namespace App\Services\GeoFlow;

use App\Models\Article;
use App\Models\Task;
use App\Models\TechIpAsset;
use Illuminate\Support\Str;

/** 从 Task / TechIpAsset / 正文构建 Gweb Wiki frontmatter。 */
final class WikiArticleMetaBuilder
{
    /**
     * @return array<string, mixed>
     */
    public function buildForTask(Task $task, string $title, string $content, ?string $slug = null): array
    {
        $wikiType = (string) ($task->wiki_page_type ?? 'concept');
        $asset = null;
        if ((int) ($task->tech_ip_asset_id ?? 0) > 0) {
            $asset = TechIpAsset::query()->find((int) $task->tech_ip_asset_id);
        }

        $quickAnswer = $this->extractQuickAnswer($content);
        $faq = $this->extractFaq($content);

        $meta = [
            'slug' => $slug ?? ($asset?->wiki_slug ?: Str::slug($title)),
            'title' => $title,
            'type' => $wikiType,
            'quick_answer' => $quickAnswer,
            'last_updated' => now()->toDateString(),
            'schema_type' => $this->inferSchemaType($wikiType),
            'faq' => $faq,
            'related' => [],
            'sources' => [],
        ];

        if ($asset) {
            $meta['mind_tag'] = (string) ($asset->mind_tag ?? '');
            $meta['ip_layer'] = (string) ($asset->ip_layer ?? '');
            if ($asset->wiki_slug) {
                $meta['slug'] = (string) $asset->wiki_slug;
            }
            if ($asset->wiki_type) {
                $meta['type'] = (string) $asset->wiki_type;
                $meta['schema_type'] = $this->inferSchemaType($meta['type']);
            }
            $evidence = is_array($asset->evidence) ? $asset->evidence : [];
            $meta['sources'] = collect($evidence)
                ->map(static function ($item): ?string {
                    if (is_string($item)) {
                        return $item;
                    }
                    if (is_array($item) && isset($item['title'])) {
                        return (string) $item['title'];
                    }

                    return null;
                })
                ->filter()
                ->values()
                ->all();
            if (is_array($asset->models) && $asset->models !== []) {
                $meta['models'] = $asset->models;
            }
        }

        return $meta;
    }

    /**
     * @param  array<string, mixed>|null  $existing
     * @return array<string, mixed>
     */
    public function merge(Article $article, ?array $existing = null): array
    {
        $base = is_array($existing) ? $existing : (is_array($article->wiki_meta) ? $article->wiki_meta : []);
        if ($base !== []) {
            return $base;
        }

        $task = $article->task;
        if (! $task || ! WikiTaskPolicy::isWikiTask($task)) {
            return [];
        }

        return $this->buildForTask($task, (string) $article->title, (string) $article->content, (string) $article->slug);
    }

    public function inferSchemaType(string $wikiType): string
    {
        return match ($wikiType) {
            'compare' => 'FAQPage',
            'guide' => 'HowTo',
            'data' => 'Dataset',
            default => 'TechArticle',
        };
    }

    private function extractQuickAnswer(string $content): string
    {
        $plain = trim(preg_replace('/[#>*`\[\]]+/u', ' ', $content) ?? '');
        $plain = trim(preg_replace('/\s+/u', ' ', $plain) ?? '');

        if (preg_match('/快速结论[：:]\s*(.+?)(?:\n|$)/u', $content, $m)) {
            return mb_substr(trim($m[1]), 0, 200);
        }

        return mb_substr($plain, 0, 200);
    }

    /**
     * @return list<array{q:string,a:string}>
     */
    private function extractFaq(string $content): array
    {
        $faq = [];
        if (! preg_match('/##\s*常见问题\s*\n(.*)$/su', $content, $section)) {
            return $faq;
        }

        $block = (string) $section[1];
        if (preg_match_all('/###\s*(.+?)\n(.+?)(?=\n###|\z)/su', $block, $matches, PREG_SET_ORDER)) {
            foreach ($matches as $match) {
                $q = trim($match[1]);
                $a = trim(preg_replace('/\s+/u', ' ', $match[2]) ?? '');
                if ($q !== '' && $a !== '') {
                    $faq[] = ['q' => $q, 'a' => mb_substr($a, 0, 500)];
                }
            }
        }

        return array_slice($faq, 0, 6);
    }
}
