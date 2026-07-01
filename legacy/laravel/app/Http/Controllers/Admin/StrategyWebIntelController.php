<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\GeoWebSource;
use App\Services\GeoEval\WebIntel\StrategyInsightComposer;
use App\Services\GeoEval\WebIntel\WebSourceRegistry;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class StrategyWebIntelController extends Controller
{
    public function __construct(
        private readonly WebSourceRegistry $webSourceRegistry,
        private readonly StrategyInsightComposer $insightComposer,
    ) {}

    public function storeSource(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'url' => ['required', 'url', 'max:500'],
            'label' => ['required', 'in:self,competitor,authority'],
            'question_id' => ['nullable', 'integer', 'min:1'],
        ]);

        $source = $this->webSourceRegistry->register($validated);
        $this->webSourceRegistry->refresh($source);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'web-intel'])
            ->with('status', __('admin.strategy.web_intel.source_added'));
    }

    public function destroySource(int $sourceId): RedirectResponse
    {
        $source = GeoWebSource::query()->findOrFail($sourceId);
        $this->webSourceRegistry->delete($source);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'web-intel'])
            ->with('status', __('admin.strategy.web_intel.source_deleted'));
    }

    public function refreshSource(int $sourceId): RedirectResponse
    {
        $source = GeoWebSource::query()->findOrFail($sourceId);
        $this->webSourceRegistry->refresh($source);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'web-intel'])
            ->with('status', __('admin.strategy.web_intel.source_refreshed'));
    }

    public function composeReport(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'question_id' => ['nullable', 'integer', 'min:1'],
            'self_source_id' => ['nullable', 'integer', 'min:1'],
            'competitor_source_ids' => ['nullable', 'array'],
            'competitor_source_ids.*' => ['integer', 'min:1'],
            'template_name' => ['nullable', 'string', 'max:120'],
        ]);

        $self = isset($validated['self_source_id'])
            ? GeoWebSource::query()->find((int) $validated['self_source_id'])
            : null;

        $competitorIds = is_array($validated['competitor_source_ids'] ?? null)
            ? $validated['competitor_source_ids']
            : [];
        $competitors = GeoWebSource::query()->whereIn('id', $competitorIds)->get();

        $report = $this->insightComposer->createReport(
            isset($validated['question_id']) ? (int) $validated['question_id'] : null,
            $self,
            $competitors,
            $validated['template_name'] ?? null,
        );

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'web-intel'])
            ->with('status', __('admin.strategy.web_intel.report_created', ['id' => $report->id]));
    }
}
