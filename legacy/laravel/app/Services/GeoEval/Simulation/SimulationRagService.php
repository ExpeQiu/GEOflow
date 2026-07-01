<?php

namespace App\Services\GeoEval\Simulation;

use App\Models\KnowledgeChunk;
use App\Services\GeoFlow\KnowledgeRetrievalService;

/**
 * 基于任务知识库的 RAG 排名仿真（不生成 LLM 答案）。
 */
final class SimulationRagService
{
    public function __construct(
        private readonly KnowledgeRetrievalService $knowledgeRetrievalService
    ) {}

    /**
     * @return array{found: bool, rank: int, top_k: int, top_scores: list<float>, doc_count: int, target_score: float}
     */
    public function simulate(int $knowledgeBaseId, string $question, string $targetPlainText): array
    {
        $topK = max(1, (int) config('geo_eval.simulation.top_k', config('geo_eval.simulation.k', 5)));
        $noiseRatio = max(0, (int) config('geo_eval.simulation.noise_ratio', 100));
        $candidateLimit = min(200, max($topK * 4, 16) + min($noiseRatio, 50));

        $targetPlainText = trim(strip_tags($targetPlainText));
        if ($targetPlainText === '') {
            return [
                'found' => false,
                'rank' => 99,
                'top_k' => $topK,
                'top_scores' => [],
                'doc_count' => 0,
                'target_score' => 0.0,
            ];
        }

        $evidence = $this->knowledgeRetrievalService->retrieveEvidence(
            $knowledgeBaseId,
            $question,
            $candidateLimit
        );

        $targetScore = $this->scoreText($question, $targetPlainText) + 0.15;

        /** @var list<array{is_target: bool, score: float}> $candidates */
        $candidates = [
            ['is_target' => true, 'score' => $targetScore],
        ];

        foreach ($evidence as $row) {
            $content = trim((string) ($row['content'] ?? ''));
            if ($content === '') {
                continue;
            }
            if ($this->isNearDuplicate($targetPlainText, $content)) {
                continue;
            }
            $candidates[] = [
                'is_target' => false,
                'score' => (float) ($row['score'] ?? $this->scoreText($question, $content)),
            ];
        }

        $noiseChunks = $this->sampleNoiseChunks($knowledgeBaseId, $targetPlainText, min($noiseRatio, 30));
        foreach ($noiseChunks as $noiseContent) {
            $candidates[] = [
                'is_target' => false,
                'score' => $this->scoreText($question, $noiseContent) * 0.85,
            ];
        }

        usort($candidates, static fn (array $a, array $b): int => $b['score'] <=> $a['score']);

        $rank = 99;
        $position = 0;
        foreach ($candidates as $index => $candidate) {
            if ($candidate['is_target']) {
                $rank = $index + 1;
                $position = $index;
                break;
            }
        }

        $topScores = array_map(
            static fn (array $c): float => round((float) $c['score'], 4),
            array_slice($candidates, 0, $topK)
        );

        return [
            'found' => $rank <= $topK,
            'rank' => $rank,
            'top_k' => $topK,
            'top_scores' => $topScores,
            'doc_count' => count($candidates),
            'target_score' => round($targetScore, 4),
            'target_position' => $position + 1,
        ];
    }

    private function scoreText(string $question, string $text): float
    {
        $qTerms = $this->terms($question);
        $tTerms = $this->terms($text);
        if ($qTerms === [] || $tTerms === []) {
            return 0.0;
        }

        $overlap = count(array_intersect_key($qTerms, $tTerms));
        $union = count($qTerms + $tTerms);

        return $union > 0 ? $overlap / sqrt($union) : 0.0;
    }

    /**
     * @return array<string, int>
     */
    private function terms(string $text): array
    {
        $normalized = mb_strtolower($text, 'UTF-8');
        preg_match_all('/[\p{L}\p{N}]{2,}/u', $normalized, $matches);
        $freq = [];
        foreach ($matches[0] ?? [] as $term) {
            $freq[$term] = ($freq[$term] ?? 0) + 1;
        }

        return $freq;
    }

    private function isNearDuplicate(string $target, string $candidate): bool
    {
        $a = mb_substr($target, 0, 200, 'UTF-8');
        $b = mb_substr($candidate, 0, 200, 'UTF-8');

        return $a !== '' && ($a === $b || str_contains($candidate, $a) || str_contains($target, $b));
    }

    /**
     * @return list<string>
     */
    private function sampleNoiseChunks(int $knowledgeBaseId, string $targetPlainText, int $limit): array
    {
        if ($limit <= 0) {
            return [];
        }

        $rows = KnowledgeChunk::query()
            ->where('knowledge_base_id', $knowledgeBaseId)
            ->whereNotNull('content')
            ->inRandomOrder()
            ->limit($limit * 3)
            ->get(['content']);

        $out = [];
        foreach ($rows as $row) {
            $content = trim(strip_tags((string) $row->content));
            if ($content === '' || $this->isNearDuplicate($targetPlainText, $content)) {
                continue;
            }
            $out[] = $content;
            if (count($out) >= $limit) {
                break;
            }
        }

        return $out;
    }
}
