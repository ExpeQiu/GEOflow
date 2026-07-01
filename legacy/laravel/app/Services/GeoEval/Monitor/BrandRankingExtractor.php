<?php

namespace App\Services\GeoEval\Monitor;

/**
 * 从 AI 回复文本中提取品牌/产品推荐排名。
 */
final class BrandRankingExtractor
{
    /**
     * @param  list<string>  $targetBrands  我方品牌词（技术关键词）
     * @return array{
     *   brand_rank: int,
     *   brand_mentioned: bool,
     *   brands_ordered: list<string>,
     *   mention_count: int
     * }
     */
    public function extract(string $responseText, array $targetBrands = []): array
    {
        $text = trim($responseText);
        if ($text === '') {
            return [
                'brand_rank' => 99,
                'brand_mentioned' => false,
                'brands_ordered' => [],
                'mention_count' => 0,
            ];
        }

        $ordered = $this->parseOrderedBrands($text);
        if ($ordered === []) {
            $ordered = $this->brandsByFirstMention($text);
        }

        $targetBrands = array_values(array_filter(array_map(
            static fn (string $b): string => mb_strtolower(trim($b), 'UTF-8'),
            $targetBrands
        ), static fn (string $b): bool => $b !== ''));

        $brandRank = 99;
        $brandMentioned = false;
        $mentionCount = 0;
        $textLower = mb_strtolower($text, 'UTF-8');

        foreach ($targetBrands as $brand) {
            if (str_contains($textLower, $brand)) {
                $brandMentioned = true;
                $mentionCount += substr_count($textLower, $brand);
            }
        }

        foreach ($ordered as $index => $name) {
            $nameLower = mb_strtolower($name, 'UTF-8');
            foreach ($targetBrands as $brand) {
                if ($brand !== '' && (str_contains($nameLower, $brand) || str_contains($brand, $nameLower))) {
                    $brandRank = min($brandRank, $index + 1);
                    $brandMentioned = true;
                }
            }
        }

        if ($brandRank === 99 && $brandMentioned && $ordered !== []) {
            $brandRank = count($ordered) + 1;
        }

        return [
            'brand_rank' => $brandRank,
            'brand_mentioned' => $brandMentioned,
            'brands_ordered' => $ordered,
            'mention_count' => $mentionCount,
        ];
    }

    /**
     * @return list<string>
     */
    private function parseOrderedBrands(string $text): array
    {
        $brands = [];
        $lines = preg_split('/\r\n|\r|\n/u', $text) ?: [];
        foreach ($lines as $line) {
            $line = trim($line);
            if (preg_match('/^(\d+)[\.\)、]\s*(.+)$/u', $line, $m)) {
                $candidate = trim((string) ($m[2] ?? ''));
                $candidate = preg_replace('/[：:].*$/u', '', $candidate) ?? $candidate;
                $candidate = trim($candidate);
                if ($candidate !== '' && mb_strlen($candidate, 'UTF-8') <= 80) {
                    $brands[] = $candidate;
                }
            }
        }

        return array_values(array_unique($brands));
    }

    /**
     * @return list<string>
     */
    private function brandsByFirstMention(string $text): array
    {
        preg_match_all('/[\p{Lu}][\p{L}\p{N}]{1,30}/u', $text, $matches);
        $seen = [];
        $out = [];
        foreach ($matches[0] ?? [] as $token) {
            $token = trim((string) $token);
            $key = mb_strtolower($token, 'UTF-8');
            if ($token === '' || isset($seen[$key]) || mb_strlen($token, 'UTF-8') < 2) {
                continue;
            }
            $seen[$key] = true;
            $out[] = $token;
            if (count($out) >= 10) {
                break;
            }
        }

        return $out;
    }
}
