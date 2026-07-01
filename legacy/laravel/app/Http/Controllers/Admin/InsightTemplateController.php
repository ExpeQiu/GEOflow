<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\InsightTemplate;
use App\Services\GeoEval\InsightTemplateService;
use App\Support\AdminWeb;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class InsightTemplateController extends Controller
{
    public function __construct(
        private readonly InsightTemplateService $insightTemplateService
    ) {}

    public function index(): View
    {
        return view('admin.insight-templates.index', [
            'pageTitle' => __('admin.geo_eval.insight_templates_title'),
            'activeMenu' => 'strategy_hub',
            'adminSiteName' => AdminWeb::siteName(),
            'templates' => InsightTemplate::query()->orderByDesc('id')->limit(100)->get(),
        ]);
    }

    public function create(): View
    {
        return view('admin.insight-templates.create', [
            'pageTitle' => __('admin.geo_eval.insight_create_title'),
            'activeMenu' => 'strategy_hub',
            'adminSiteName' => AdminWeb::siteName(),
        ]);
    }

    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'name' => ['required', 'string', 'max:120'],
            'source_url' => ['required', 'url', 'max:500'],
        ]);

        $adminId = auth('admin')->id();
        $this->insightTemplateService->createFromUrl(
            (string) $validated['name'],
            (string) $validated['source_url'],
            is_numeric($adminId) ? (int) $adminId : null
        );

        return redirect()
            ->route('admin.insight-templates.index')
            ->with('status', __('admin.geo_eval.insight_created'));
    }

    public function show(int $templateId): View
    {
        $template = InsightTemplate::query()->findOrFail($templateId);

        return view('admin.insight-templates.show', [
            'pageTitle' => $template->name,
            'activeMenu' => 'strategy_hub',
            'adminSiteName' => AdminWeb::siteName(),
            'template' => $template,
        ]);
    }

    public function edit(int $templateId): View
    {
        $template = InsightTemplate::query()->findOrFail($templateId);

        return view('admin.insight-templates.edit', [
            'pageTitle' => __('admin.geo_eval.insight_edit_title'),
            'activeMenu' => 'strategy_hub',
            'adminSiteName' => AdminWeb::siteName(),
            'template' => $template,
        ]);
    }

    public function update(Request $request, int $templateId): RedirectResponse
    {
        $validated = $request->validate([
            'name' => ['required', 'string', 'max:120'],
        ]);

        $template = InsightTemplate::query()->findOrFail($templateId);
        $template->name = (string) $validated['name'];
        $template->save();

        return redirect()
            ->route('admin.insight-templates.show', ['templateId' => $templateId])
            ->with('status', __('admin.geo_eval.insight_updated'));
    }

    public function destroy(int $templateId): RedirectResponse
    {
        InsightTemplate::query()->whereKey($templateId)->delete();

        return redirect()
            ->route('admin.insight-templates.index')
            ->with('status', __('admin.geo_eval.insight_deleted'));
    }

    public function remine(int $templateId): RedirectResponse
    {
        $template = InsightTemplate::query()->findOrFail($templateId);
        $url = (string) ($template->source_url ?? '');
        if ($url === '') {
            return back()->withErrors(__('admin.geo_eval.insight_remine_no_url'));
        }

        $this->insightTemplateService->refreshFromUrl($template);

        return redirect()
            ->route('admin.insight-templates.show', ['templateId' => $templateId])
            ->with('status', __('admin.geo_eval.insight_remined'));
    }
}
