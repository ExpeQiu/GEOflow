<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\KnowledgeBase;
use App\Models\TechIpAsset;
use App\Support\AdminWeb;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;
use Illuminate\Validation\ValidationException;
use Symfony\Component\Yaml\Yaml;

class TechIpAssetController extends Controller
{
    public function index(): View
    {
        $assets = TechIpAsset::query()
            ->orderByRaw("CASE priority WHEN 'P0' THEN 0 WHEN 'P1' THEN 1 ELSE 2 END")
            ->orderBy('ip_name')
            ->paginate(20);

        $p0Total = TechIpAsset::query()->where('priority', 'P0')->count();
        $p0Ready = TechIpAsset::query()
            ->where('priority', 'P0')
            ->where('can_name', true)
            ->where('can_visualize', true)
            ->where('can_translate', true)
            ->count();

        return view('admin.tech-assets.index', [
            'pageTitle' => __('admin.tech_assets.page_title'),
            'activeMenu' => 'tech_assets'
            'adminSiteName' => AdminWeb::siteName(),
            'assets' => $assets,
            'p0Total' => $p0Total,
            'p0Ready' => $p0Ready,
        ]);
    }

    public function create(): View
    {
        return view('admin.tech-assets.form', [
            'pageTitle' => __('admin.tech_assets.create_title'),
            'activeMenu' => 'tech_assets',
            'adminSiteName' => AdminWeb::siteName(),
            'isEdit' => false,
            'assetId' => 0,
            'assetForm' => $this->emptyForm(),
            'knowledgeBases' => KnowledgeBase::query()->orderBy('name')->get(['id', 'name']),
        ]);
    }

    public function store(Request $request): RedirectResponse
    {
        $payload = $this->validateForm($request);
        TechIpAsset::query()->create($payload);

        return redirect()->route('admin.tech-assets.index')
            ->with('message', __('admin.tech_assets.message.created'));
    }

    public function edit(int $assetId): View
    {
        $asset = TechIpAsset::query()->findOrFail($assetId);

        return view('admin.tech-assets.form', [
            'pageTitle' => __('admin.tech_assets.edit_title'),
            'activeMenu' => 'tech_assets',
            'adminSiteName' => AdminWeb::siteName(),
            'isEdit' => true,
            'assetId' => $assetId,
            'assetForm' => $this->formFromModel($asset),
            'knowledgeBases' => KnowledgeBase::query()->orderBy('name')->get(['id', 'name']),
        ]);
    }

    public function update(Request $request, int $assetId): RedirectResponse
    {
        $asset = TechIpAsset::query()->findOrFail($assetId);
        $payload = $this->validateForm($request, $assetId);
        $asset->update($payload);

        return redirect()->route('admin.tech-assets.index')
            ->with('message', __('admin.tech_assets.message.updated'));
    }

    public function import(Request $request): RedirectResponse
    {
        $request->validate(['yaml_file' => ['required', 'file', 'max:5120']]);
        $raw = file_get_contents($request->file('yaml_file')->getRealPath());
        if (! is_string($raw) || trim($raw) === '') {
            return back()->withErrors(__('admin.tech_assets.error.empty_yaml'));
        }

        $parsed = Yaml::parse($raw);
        $rows = isset($parsed['ip_id']) ? [$parsed] : (is_array($parsed) ? $parsed : []);
        $imported = 0;

        foreach ($rows as $row) {
            if (! is_array($row) || empty($row['ip_id'])) {
                continue;
            }
            TechIpAsset::query()->updateOrCreate(
                ['ip_id' => (string) $row['ip_id']],
                $this->mapYamlRow($row)
            );
            $imported++;
        }

        return redirect()->route('admin.tech-assets.index')
            ->with('message', __('admin.tech_assets.message.imported', ['count' => $imported]));
    }

    /**
     * @return array<string, mixed>
     */
    private function validateForm(Request $request, ?int $ignoreId = null): array
    {
        $payload = $request->validate([
            'ip_id' => ['required', 'string', 'max:120'],
            'ip_name' => ['required', 'string', 'max:200'],
            'ip_layer' => ['required', 'string', 'in:架构层,模块层,参数层'],
            'mind_tag' => ['nullable', 'string', 'max:500'],
            'priority' => ['required', 'string', 'in:P0,P1,P2'],
            'can_name' => ['nullable', 'boolean'],
            'can_visualize' => ['nullable', 'boolean'],
            'can_translate' => ['nullable', 'boolean'],
            'tech_term' => ['nullable', 'string'],
            'user_language' => ['nullable', 'string'],
            'evidence_json' => ['nullable', 'string'],
            'models_text' => ['nullable', 'string'],
            'wiki_type' => ['nullable', 'string', 'in:concept,compare,guide,glossary,data,thread,topic,article,certification'],
            'wiki_slug' => ['nullable', 'string', 'max:120'],
            'status' => ['required', 'string', 'in:待封装,已发布,需更新'],
            'knowledge_base_id' => ['nullable', 'integer', 'min:1'],
        ]);

        $ipIdRule = TechIpAsset::query()->where('ip_id', $payload['ip_id']);
        if ($ignoreId) {
            $ipIdRule->where('id', '!=', $ignoreId);
        }
        if ($ipIdRule->exists()) {
            throw ValidationException::withMessages([
                'ip_id' => __('admin.tech_assets.error.ip_id_exists'),
            ]);
        }

        return [
            'ip_id' => trim((string) $payload['ip_id']),
            'ip_name' => trim((string) $payload['ip_name']),
            'ip_layer' => (string) $payload['ip_layer'],
            'mind_tag' => trim((string) ($payload['mind_tag'] ?? '')),
            'priority' => (string) $payload['priority'],
            'can_name' => $request->boolean('can_name'),
            'can_visualize' => $request->boolean('can_visualize'),
            'can_translate' => $request->boolean('can_translate'),
            'tech_term' => trim((string) ($payload['tech_term'] ?? '')),
            'user_language' => trim((string) ($payload['user_language'] ?? '')),
            'evidence' => $this->parseJsonField((string) ($payload['evidence_json'] ?? ''), []),
            'models' => $this->parseLines((string) ($payload['models_text'] ?? '')),
            'wiki_type' => trim((string) ($payload['wiki_type'] ?? '')) ?: null,
            'wiki_slug' => trim((string) ($payload['wiki_slug'] ?? '')) ?: null,
            'status' => (string) $payload['status'],
            'knowledge_base_id' => isset($payload['knowledge_base_id']) ? (int) $payload['knowledge_base_id'] : null,
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function emptyForm(): array
    {
        return [
            'ip_id' => '',
            'ip_name' => '',
            'ip_layer' => '模块层',
            'mind_tag' => '',
            'priority' => 'P1',
            'can_name' => false,
            'can_visualize' => false,
            'can_translate' => false,
            'tech_term' => '',
            'user_language' => '',
            'evidence_json' => '[]',
            'models_text' => '',
            'wiki_type' => 'concept',
            'wiki_slug' => '',
            'status' => '待封装',
            'knowledge_base_id' => '',
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function formFromModel(TechIpAsset $asset): array
    {
        return [
            'ip_id' => (string) $asset->ip_id,
            'ip_name' => (string) $asset->ip_name,
            'ip_layer' => (string) $asset->ip_layer,
            'mind_tag' => (string) ($asset->mind_tag ?? ''),
            'priority' => (string) $asset->priority,
            'can_name' => (bool) $asset->can_name,
            'can_visualize' => (bool) $asset->can_visualize,
            'can_translate' => (bool) $asset->can_translate,
            'tech_term' => (string) ($asset->tech_term ?? ''),
            'user_language' => (string) ($asset->user_language ?? ''),
            'evidence_json' => json_encode($asset->evidence ?? [], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT),
            'models_text' => implode("\n", is_array($asset->models) ? $asset->models : []),
            'wiki_type' => (string) ($asset->wiki_type ?? ''),
            'wiki_slug' => (string) ($asset->wiki_slug ?? ''),
            'status' => (string) $asset->status,
            'knowledge_base_id' => (string) (($asset->knowledge_base_id ?? '') ?: ''),
        ];
    }

    /**
     * @param  array<string, mixed>  $row
     * @return array<string, mixed>
     */
    private function mapYamlRow(array $row): array
    {
        return [
            'ip_name' => (string) ($row['ip_name'] ?? $row['ip_id']),
            'ip_layer' => (string) ($row['ip_layer'] ?? '模块层'),
            'mind_tag' => (string) ($row['mind_tag'] ?? ''),
            'priority' => (string) ($row['priority'] ?? 'P1'),
            'can_name' => (bool) ($row['can_name'] ?? false),
            'can_visualize' => (bool) ($row['can_visualize'] ?? false),
            'can_translate' => (bool) ($row['can_translate'] ?? false),
            'tech_term' => (string) ($row['tech_term'] ?? ''),
            'user_language' => (string) ($row['user_language'] ?? ''),
            'evidence' => is_array($row['evidence'] ?? null) ? $row['evidence'] : [],
            'models' => is_array($row['models'] ?? null) ? $row['models'] : [],
            'wiki_type' => (string) ($row['wiki_type'] ?? ''),
            'wiki_slug' => (string) ($row['wiki_slug'] ?? ($row['wiki_page'] ?? '')),
            'status' => (string) ($row['status'] ?? '待封装'),
            'knowledge_base_id' => isset($row['knowledge_base_id']) ? (int) $row['knowledge_base_id'] : null,
        ];
    }

    /**
     * @return array<int, mixed>
     */
    private function parseJsonField(string $raw, array $default): array
    {
        $trimmed = trim($raw);
        if ($trimmed === '') {
            return $default;
        }
        $decoded = json_decode($trimmed, true);

        return is_array($decoded) ? $decoded : $default;
    }

    /**
     * @return list<string>
     */
    private function parseLines(string $raw): array
    {
        return collect(preg_split('/\r\n|\r|\n/', $raw) ?: [])
            ->map(static fn (string $line): string => trim($line))
            ->filter(static fn (string $line): bool => $line !== '')
            ->values()
            ->all();
    }
}
