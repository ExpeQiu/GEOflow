<?php

namespace App\Services\GeoFlow;

use Symfony\Component\Yaml\Yaml;

/** 将 Article wiki_meta + Markdown 正文组装为 Gweb MDX。 */
final class WikiMdxAssembler
{
    public function __construct(
        private readonly WikiArticleMetaBuilder $metaBuilder,
    ) {}

    /**
     * @param  array<string, mixed>  $wikiMeta
     */
    public function assemble(string $title, string $body, array $wikiMeta): string
    {
        $frontmatter = $this->normalizeFrontmatter($title, $wikiMeta);
        $yaml = Yaml::dump($frontmatter, 4, 2, Yaml::DUMP_MULTI_LINE_LITERAL_BLOCK);

        return "---\n".trim($yaml)."---\n\n".trim($body)."\n";
    }

    /**
     * @param  array<string, mixed>  $wikiMeta
     * @return array<string, mixed>
     */
    private function normalizeFrontmatter(string $title, array $wikiMeta): array
    {
        $type = (string) ($wikiMeta['type'] ?? 'concept');
        $output = [
            'title' => (string) ($wikiMeta['title'] ?? $title),
            'type' => $type,
        ];

        foreach ([
            'quick_answer', 'mind_tag', 'ip_layer', 'summary', 'target_query', 'schema_type', 'last_updated',
        ] as $key) {
            if (! empty($wikiMeta[$key])) {
                $output[$key] = (string) $wikiMeta[$key];
            }
        }

        if (empty($output['schema_type'])) {
            $output['schema_type'] = $this->metaBuilder->inferSchemaType($type);
        }

        foreach (['tags', 'related', 'models', 'sources'] as $listKey) {
            if (! empty($wikiMeta[$listKey]) && is_array($wikiMeta[$listKey])) {
                $output[$listKey] = array_values($wikiMeta[$listKey]);
            }
        }

        if (! empty($wikiMeta['faq']) && is_array($wikiMeta['faq'])) {
            $output['faq'] = collect($wikiMeta['faq'])
                ->map(static function ($item): ?array {
                    if (! is_array($item)) {
                        return null;
                    }
                    $q = trim((string) ($item['q'] ?? $item['question'] ?? ''));
                    $a = trim((string) ($item['a'] ?? $item['answer'] ?? ''));
                    if ($q === '' || $a === '') {
                        return null;
                    }

                    return ['q' => $q, 'a' => $a];
                })
                ->filter()
                ->values()
                ->all();
        }

        if (! empty($wikiMeta['variables']) && is_array($wikiMeta['variables'])) {
            $output['variables'] = $wikiMeta['variables'];
        }

        return $output;
    }

    public function routePrefixForType(string $type): string
    {
        return match ($type) {
            'compare' => 'compare',
            'guide' => 'guides',
            'glossary' => 'glossary',
            'data' => 'data',
            'thread' => 'threads',
            'topic' => 'topics',
            default => 'concepts',
        };
    }
}
