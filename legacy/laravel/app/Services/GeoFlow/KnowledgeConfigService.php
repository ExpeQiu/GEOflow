<?php

namespace App\Services\GeoFlow;

use App\Models\SiteSetting;

/**
 * L2 知识库与 RAG 相关配置集中读取。
 */
final class KnowledgeConfigService
{
    public function retrievalLimit(): int
    {
        return max(1, min(20, (int) $this->setting('knowledge_retrieval_limit', 5)));
    }

    public function retrievalMaxChars(): int
    {
        return max(500, min(12000, (int) $this->setting('knowledge_retrieval_max_chars', 3200)));
    }

    public function chunkMaxChars(): int
    {
        $configured = (int) $this->setting('knowledge_chunk_max_chars', (int) config('geoflow.semantic_chunking_max_chars', 2000));

        return max(500, min(20000, $configured > 0 ? $configured : 2000));
    }

    private function setting(string $key, int|float|string $default): mixed
    {
        $row = SiteSetting::query()->where('setting_key', $key)->value('setting_value');

        return $row !== null && $row !== '' ? $row : $default;
    }
}
