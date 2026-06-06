<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\Article;
use App\Models\ArticleEvaluation;
use App\Services\GeoEval\ArticleEvaluationService;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Schema;

class StrategySimulatorController extends Controller
{
    public function __construct(
        private readonly ArticleEvaluationService $evaluationService,
    ) {}

    public function reevaluate(int $articleId): RedirectResponse
    {
        $this->evaluationService->queueEvaluation($articleId);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'simulator'])
            ->with('status', __('admin.geo_eval.reevaluate_queued', ['id' => $articleId]));
    }

    public function batchReevaluate(): RedirectResponse
    {
        $ids = Article::query()
            ->where('eval_status', 'failed')
            ->whereNull('deleted_at')
            ->orderByDesc('id')
            ->limit(20)
            ->pluck('id');

        foreach ($ids as $id) {
            $this->evaluationService->queueEvaluation((int) $id);
        }

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'simulator'])
            ->with('status', __('admin.geo_eval.batch_reevaluate_queued', ['count' => $ids->count()]));
    }

    public function applyRecommendations(Request $request, int $articleId): RedirectResponse
    {
        $article = Article::query()->findOrFail($articleId);

        if ((string) ($article->status ?? '') !== 'draft') {
            return redirect()
                ->route('admin.strategy.index', ['tab' => 'simulator'])
                ->with('status', __('admin.strategy.simulator.apply_draft_only'));
        }

        if (! Schema::hasTable('article_evaluations')) {
            return redirect()
                ->route('admin.strategy.index', ['tab' => 'simulator'])
                ->with('status', __('admin.strategy.simulator.no_evaluation'));
        }

        $evaluation = ArticleEvaluation::query()
            ->where('article_id', $articleId)
            ->orderByDesc('id')
            ->first();

        $metrics = is_array($evaluation?->metrics) ? $evaluation->metrics : [];
        $recommendations = is_array($metrics['recommendations'] ?? null) ? $metrics['recommendations'] : [];

        if ($recommendations === []) {
            return redirect()
                ->route('admin.strategy.index', ['tab' => 'simulator'])
                ->with('status', __('admin.strategy.simulator.no_recommendations'));
        }

        $block = "\n\n<!-- geo-optimization-hints -->\n<div class=\"geo-opt-hints\">\n<h3>GEO 优化建议（待人工修订）</h3>\n<ul>\n";
        foreach ($recommendations as $rec) {
            $message = htmlspecialchars((string) ($rec['message'] ?? ''), ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
            if ($message !== '') {
                $block .= "<li>{$message}</li>\n";
            }
        }
        $block .= "</ul>\n</div>\n";

        $article->content = (string) $article->content.$block;
        $article->save();

        return redirect()
            ->route('admin.articles.edit', ['articleId' => $articleId])
            ->with('status', __('admin.strategy.simulator.applied'));
    }
}
