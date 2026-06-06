<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\SiteSetting;
use App\Services\GeoFlow\KnowledgeConfigService;
use App\Support\AdminWeb;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class KnowledgeSettingsController extends Controller
{
    public function index(KnowledgeConfigService $config): View
    {
        return view('admin.knowledge-settings.index', [
            'pageTitle' => __('admin.knowledge_settings.page_title'),
            'activeMenu' => 'ai_config',
            'adminSiteName' => AdminWeb::siteName(),
            'settings' => [
                'knowledge_retrieval_limit' => $config->retrievalLimit(),
                'knowledge_retrieval_max_chars' => $config->retrievalMaxChars(),
                'knowledge_chunk_max_chars' => $config->chunkMaxChars(),
            ],
        ]);
    }

    public function update(Request $request): RedirectResponse
    {
        $payload = $request->validate([
            'knowledge_retrieval_limit' => ['required', 'integer', 'min:1', 'max:20'],
            'knowledge_retrieval_max_chars' => ['required', 'integer', 'min:500', 'max:12000'],
            'knowledge_chunk_max_chars' => ['required', 'integer', 'min:500', 'max:20000'],
        ]);

        foreach ($payload as $key => $value) {
            SiteSetting::query()->updateOrCreate(
                ['setting_key' => $key],
                ['setting_value' => (string) $value]
            );
        }

        return redirect()
            ->route('admin.knowledge-settings.index')
            ->with('status', __('admin.knowledge_settings.saved'));
    }
}
