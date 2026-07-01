<?php

namespace App\Support\GeoFlow;

/** 将知识库检索结果格式化为 Content Agent evidence 结构。 */
final class KnowledgeEvidenceFormatter
{
    /**
     * @param  list<array<string, mixed>>  $rows
     * @return list<array{id:string,content:string}>
     */
    public static function fromRetrievedRows(array $rows): array
    {
        $evidence = [];
        $index = 1;

        foreach ($rows as $row) {
            if (! is_array($row)) {
                continue;
            }

            $content = trim((string) ($row['content'] ?? ''));
            if ($content === '') {
                continue;
            }

            $title = trim((string) ($row['chunk_title'] ?? ''));
            $section = trim((string) ($row['section_path'] ?? ''));
            $parts = [];
            if ($title !== '') {
                $parts[] = '标题：'.$title;
            }
            if ($section !== '') {
                $parts[] = '章节：'.$section;
            }
            $parts[] = '内容：'.$content;

            $evidence[] = [
                'id' => 'K'.$index,
                'content' => implode("\n", $parts),
            ];
            $index++;
        }

        return $evidence;
    }

    /**
     * @return list<array{id:string,content:string}>
     */
    public static function fromContextText(string $knowledgeContext): array
    {
        if (trim($knowledgeContext) === '') {
            return [];
        }

        $evidence = [];
        if (preg_match_all('/【证据\s*(K\d+)】\s*(.*?)(?=【证据\s*K\d+】|$)/su', $knowledgeContext, $matches, PREG_SET_ORDER)) {
            foreach ($matches as $match) {
                $evidence[] = [
                    'id' => (string) ($match[1] ?? ''),
                    'content' => trim((string) ($match[2] ?? '')),
                ];
            }
        }

        if ($evidence === []) {
            $evidence[] = ['id' => 'K1', 'content' => $knowledgeContext];
        }

        return $evidence;
    }
}
