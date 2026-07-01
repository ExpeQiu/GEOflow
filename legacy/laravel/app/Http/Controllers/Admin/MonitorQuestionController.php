<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\GeoMonitorQuestion;
use App\Services\GeoEval\Monitor\MonitorPlatformConfigService;
use App\Services\GeoEval\Monitor\MonitorQuestionService;
use App\Services\GeoEval\Monitor\MonitorScanOrchestrator;
use App\Services\GeoEval\Monitor\MonitorSettingsService;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class MonitorQuestionController extends Controller
{
    public function __construct(
        private readonly MonitorQuestionService $questionService,
        private readonly MonitorScanOrchestrator $scanOrchestrator,
        private readonly MonitorPlatformConfigService $platformConfigService,
        private readonly MonitorSettingsService $monitorSettingsService,
    ) {}

    public function store(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'question_text' => ['required', 'string', 'max:2000'],
            'category' => ['nullable', 'string', 'max:120'],
            'intent_type' => ['nullable', 'string', 'max:32'],
            'knowledge_base_id' => ['nullable', 'integer', 'min:1'],
            'task_id' => ['nullable', 'integer', 'min:1'],
            'target_article_id' => ['nullable', 'integer', 'min:1'],
            'target_content_snapshot' => ['nullable', 'string'],
            'priority' => ['nullable', 'integer', 'min:1', 'max:100'],
        ]);

        $adminId = auth('admin')->id();
        $this->questionService->create($validated, $adminId ? (int) $adminId : null);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.created'));
    }

    public function update(Request $request, int $questionId): RedirectResponse
    {
        $question = GeoMonitorQuestion::query()->findOrFail($questionId);
        $validated = $request->validate([
            'question_text' => ['sometimes', 'string', 'max:2000'],
            'category' => ['nullable', 'string', 'max:120'],
            'intent_type' => ['nullable', 'string', 'max:32'],
            'knowledge_base_id' => ['nullable', 'integer', 'min:1'],
            'is_active' => ['nullable', 'boolean'],
            'priority' => ['nullable', 'integer', 'min:1', 'max:100'],
        ]);

        $this->questionService->update($question, $validated);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.updated'));
    }

    public function destroy(int $questionId): RedirectResponse
    {
        $question = GeoMonitorQuestion::query()->findOrFail($questionId);
        $this->questionService->delete($question);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.deleted'));
    }

    public function import(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'library_id' => ['required', 'integer', 'min:1'],
            'knowledge_base_id' => ['nullable', 'integer', 'min:1'],
        ]);

        $adminId = auth('admin')->id();
        $created = $this->questionService->importFromKeywordLibrary(
            (int) $validated['library_id'],
            isset($validated['knowledge_base_id']) ? (int) $validated['knowledge_base_id'] : null,
            $adminId ? (int) $adminId : null,
        );

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.imported', ['count' => count($created)]));
    }

    public function scan(Request $request): RedirectResponse
    {
        $async = (bool) $request->boolean('async');
        $this->scanOrchestrator->run('manual', $async);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', $async
                ? __('admin.strategy.monitor.scan_queued')
                : __('admin.strategy.monitor.scan_done'));
    }

    public function importBatch(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'questions_text' => ['required', 'string', 'max:50000'],
            'knowledge_base_id' => ['nullable', 'integer', 'min:1'],
        ]);

        $adminId = auth('admin')->id();
        $created = $this->questionService->importFromTextBatch(
            (string) $validated['questions_text'],
            isset($validated['knowledge_base_id']) ? (int) $validated['knowledge_base_id'] : null,
            $adminId ? (int) $adminId : null,
        );

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.batch_imported', ['count' => count($created)]));
    }

    public function importTechKeywords(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'tech_keywords' => ['required', 'string', 'max:10000'],
            'knowledge_base_id' => ['nullable', 'integer', 'min:1'],
        ]);

        $this->monitorSettingsService->saveTechKeywords((string) $validated['tech_keywords']);

        $adminId = auth('admin')->id();
        $created = $this->questionService->importFromTechKeywords(
            (string) $validated['tech_keywords'],
            isset($validated['knowledge_base_id']) ? (int) $validated['knowledge_base_id'] : null,
            $adminId ? (int) $adminId : null,
        );

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.tech_imported', ['count' => count($created)]));
    }

    public function saveConfig(Request $request): RedirectResponse
    {
        $validated = $request->validate([
            'tech_keywords' => ['nullable', 'string', 'max:10000'],
            'platform_model_ids' => ['nullable', 'array'],
            'platform_model_ids.*' => ['integer', 'min:1'],
        ]);

        if (array_key_exists('tech_keywords', $validated) && $validated['tech_keywords'] !== null) {
            $this->monitorSettingsService->saveTechKeywords((string) $validated['tech_keywords']);
        }

        $ids = is_array($validated['platform_model_ids'] ?? null) ? $validated['platform_model_ids'] : [];
        $this->platformConfigService->syncPlatforms($ids);

        return redirect()
            ->route('admin.strategy.index', ['tab' => 'monitor'])
            ->with('status', __('admin.strategy.monitor.config_saved'));
    }
}
