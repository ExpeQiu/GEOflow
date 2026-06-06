<?php

namespace App\Services\GeoEval;

use App\Models\Article;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;
use App\Services\GeoEval\Insight\UrlInsightMinerService;
use App\Services\GeoEval\Simulation\AnswerAuditService;
use App\Services\GeoEval\Simulation\SimulationRagService;
use Illuminate\Support\Str;

/**
 * GEOworkflow 内置策略引擎（不调用外部 GEO-OS HTTP）。
 */
final class InternalGeoEvalEngine implements GeoEvalClientInterface
{
    public function __construct(
        private readonly SimulationRagService $simulationRagService,
        private readonly AnswerAuditService $answerAuditService,
        private readonly UrlInsightMinerService $urlInsightMinerService,
    ) {}

    public function runSimulation(array $payload, ?string $requestId = null): array
    {
        $requestId = $requestId ?: (string) Str::uuid();
        $knowledgeBaseId = (int) ($payload['knowledge_base_id'] ?? 0);
        $question = (string) ($payload['question'] ?? '');
        $targetHtml = (string) ($payload['target_html'] ?? '');

        if ($knowledgeBaseId <= 0) {
            throw new \RuntimeException('no_knowledge_base');
        }

        $targetPlain = trim(strip_tags($targetHtml));
        $metrics = $this->simulationRagService->simulate($knowledgeBaseId, $question, $targetPlain);

        $excerpt = mb_substr($targetPlain, 0, 1200, 'UTF-8');

        return [
            'request_id' => $requestId,
            'data' => [
                'trace_id' => $requestId,
                'answer' => $excerpt,
                'metrics' => $metrics,
                'doc_count' => (int) ($metrics['doc_count'] ?? 0),
            ],
        ];
    }

    public function auditAnswer(array $payload, ?string $requestId = null): array
    {
        $requestId = $requestId ?: (string) Str::uuid();
        $answer = (string) ($payload['answer'] ?? '');
        if ($answer === '' && isset($payload['target_html'])) {
            $answer = trim(strip_tags((string) $payload['target_html']));
        }

        $audit = $this->answerAuditService->audit(
            (string) ($payload['question'] ?? ''),
            mb_substr($answer, 0, 1200, 'UTF-8'),
            is_array($payload['brand_keywords'] ?? null) ? $payload['brand_keywords'] : []
        );

        return [
            'request_id' => $requestId,
            'data' => array_merge(['trace_id' => $requestId], $audit),
        ];
    }

    public function mineUrlInsight(array $payload, ?string $requestId = null): array
    {
        $requestId = $requestId ?: (string) Str::uuid();
        $mined = $this->urlInsightMinerService->mine((string) ($payload['url'] ?? ''));

        return [
            'request_id' => $requestId,
            'data' => array_merge(['trace_id' => $requestId, 'run_id' => 'internal-'.Str::uuid()], $mined),
        ];
    }

    public function getAdoptionStats(int $days = 30, string $platform = '', ?string $requestId = null): array
    {
        $requestId = $requestId ?: (string) Str::uuid();
        $aggregator = app(Adoption\AdoptionMetricsAggregator::class);
        $stats = $aggregator->summary($days, $platform);

        return [
            'request_id' => $requestId,
            'data' => [
                'trace_id' => $requestId,
                'stats' => $stats,
                'daily' => $aggregator->dailySeries($days, $platform),
            ],
        ];
    }

    public function getStrategyTrends(int $days = 30, ?string $requestId = null): array
    {
        $requestId = $requestId ?: (string) Str::uuid();
        $aggregator = app(Adoption\AdoptionMetricsAggregator::class);

        return [
            'request_id' => $requestId,
            'data' => [
                'trace_id' => $requestId,
                'trends' => $aggregator->dailySeries($days, ''),
                'days' => $days,
            ],
        ];
    }

    public function healthCheck(): bool
    {
        return (bool) config('geo_eval.enabled');
    }

    /**
     * @return array{knowledge_base_id: int, question: string, target_html: string}
     */
    public static function payloadFromArticle(Article $article): array
    {
        $article->loadMissing('task');
        $title = htmlspecialchars((string) $article->title, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
        $content = (string) $article->content;
        $keyword = trim((string) ($article->original_keyword ?? ''));
        $question = $keyword !== ''
            ? '请基于以下内容回答：'.$keyword
            : '请总结并评价以下文章的核心事实与品牌表达：'.(string) $article->title;

        return [
            'knowledge_base_id' => (int) ($article->task?->knowledge_base_id ?? 0),
            'question' => $question,
            'target_html' => '<article><h1>'.$title.'</h1><div>'.$content.'</div></article>',
        ];
    }
}
