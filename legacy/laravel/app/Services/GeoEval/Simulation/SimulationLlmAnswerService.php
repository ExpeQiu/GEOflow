<?php

namespace App\Services\GeoEval\Simulation;

use App\Services\GeoFlow\KnowledgeRetrievalService;

/**
 * 基于 RAG 上下文生成仿真答案（mock 模式返回摘录）。
 */
final class SimulationLlmAnswerService
{
    public function __construct(
        private readonly KnowledgeRetrievalService $knowledgeRetrievalService,
    ) {}

    public function generateAnswer(int $knowledgeBaseId, string $question, string $targetPlainText): string
    {
        $provider = (string) config('geo_eval.simulation.llm_provider', 'mock');
        $excerpt = mb_substr(trim(strip_tags($targetPlainText)), 0, 1200, 'UTF-8');

        if ($provider === 'mock') {
            return $excerpt;
        }

        $topK = max(1, (int) config('geo_eval.simulation.top_k', 5));
        $evidence = $this->knowledgeRetrievalService->retrieveEvidence(
            $knowledgeBaseId,
            $question,
            $topK * 4
        );

        $contextParts = [];
        foreach (array_slice($evidence, 0, $topK) as $row) {
            $content = trim((string) ($row['content'] ?? ''));
            if ($content !== '') {
                $contextParts[] = mb_substr($content, 0, 400, 'UTF-8');
            }
        }
        $contextParts[] = $excerpt;
        $context = implode("\n---\n", $contextParts);

        try {
            if (class_exists(\Laravel\Ai\Ai::class)) {
                $response = \Laravel\Ai\Ai::text()
                    ->prompt("基于以下资料回答问题：{$question}\n\n资料：\n{$context}")
                    ->generate();

                $text = (string) ($response->text ?? '');
                if ($text !== '') {
                    return mb_substr($text, 0, 1200, 'UTF-8');
                }
            }
        } catch (\Throwable) {
            // 回退到摘录模式
        }

        return $excerpt;
    }
}
