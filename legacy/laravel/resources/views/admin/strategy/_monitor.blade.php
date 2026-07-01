@php
    $dash = $monitorDashboard ?? [];
    $matrix = $monitorRankMatrix ?? [];
    $brandTrend = $monitorBrandTrend ?? [];
    $ragTrend = $monitorRagTrend ?? [];
    $platformModels = $monitorPlatformModels ?? [];
    $techKeywordsText = $monitorTechKeywords ?? '';
    $configuredIds = collect($platformModels)->filter(fn ($m) => $m['configured'] && $m['enabled'])->pluck('id')->all();
@endphp

{{-- 可视化看板 --}}
<section class="mb-6 rounded-lg border border-violet-200 bg-white p-5 shadow-sm">
    <div class="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.strategy.monitor.dashboard_title') }}</h2>
            <p class="text-sm text-gray-500">{{ __('admin.strategy.monitor.dashboard_subtitle') }}</p>
        </div>
        <form method="post" action="{{ route('admin.strategy.monitor.scan') }}">
            @csrf
            <button type="submit" class="rounded-md bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-700">
                {{ __('admin.strategy.monitor.scan_all') }}
            </button>
        </form>
    </div>

    <div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="rounded-md bg-violet-50 p-4">
            <p class="text-xs text-violet-700">{{ __('admin.strategy.monitor.kpi_questions') }}</p>
            <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (int) ($dash['question_count'] ?? 0) }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.kpi_probes') }}</p>
            <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (int) ($dash['probe_count'] ?? 0) }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.kpi_avg_rank') }}</p>
            <p class="mt-1 text-2xl font-semibold text-gray-900">{{ $dash['avg_brand_rank'] ?? '—' }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.kpi_mention_rate') }}</p>
            <p class="mt-1 text-2xl font-semibold text-gray-900">{{ number_format((float) ($dash['mention_rate'] ?? 0) * 100, 1) }}%</p>
        </div>
    </div>

    @if (!empty($dash['platform_summary']))
        <h3 class="mb-2 text-sm font-semibold text-gray-800">{{ __('admin.strategy.monitor.platform_rank_title') }}</h3>
        <div class="mb-6 overflow-x-auto">
            <table class="min-w-full text-sm">
                <thead>
                    <tr class="border-b text-left text-xs text-gray-500">
                        <th class="py-2 pr-4">{{ __('admin.strategy.monitor.platform_col') }}</th>
                        <th class="py-2 pr-4">{{ __('admin.strategy.monitor.avg_rank_col') }}</th>
                        <th class="py-2 pr-4">{{ __('admin.strategy.monitor.mention_col') }}</th>
                        <th class="py-2">{{ __('admin.strategy.monitor.probes_col') }}</th>
                    </tr>
                </thead>
                <tbody>
                    @foreach ($dash['platform_summary'] as $row)
                        <tr class="border-b border-gray-100">
                            <td class="py-2 pr-4 font-medium">{{ $row['platform'] }}</td>
                            <td class="py-2 pr-4">
                                @if (($row['avg_rank'] ?? 0) > 0)
                                    <span class="{{ ($row['avg_rank'] ?? 99) <= 3 ? 'text-emerald-700' : 'text-amber-700' }}">#{{ $row['avg_rank'] }}</span>
                                @else
                                    —
                                @endif
                            </td>
                            <td class="py-2 pr-4">{{ number_format((float) ($row['mention_rate'] ?? 0) * 100, 1) }}%</td>
                            <td class="py-2">{{ (int) ($row['probes'] ?? 0) }}</td>
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @endif

    @if ($brandTrend !== [])
        <h3 class="mb-2 text-sm font-semibold text-gray-800">{{ __('admin.strategy.monitor.brand_trend_title') }}</h3>
        @include('admin.analytics._line-chart', [
            'series' => array_map(static fn (array $r): array => [
                'date' => $r['date'],
                'created' => (int) ($r['mention_pct'] ?? 0),
                'published' => max(0, 10 - (int) ($r['avg_rank'] ?? 10)),
            ], $brandTrend),
            'primaryKey' => 'created',
            'secondaryKey' => 'published',
        ])
        <p class="mt-1 text-xs text-gray-400">{{ __('admin.strategy.monitor.brand_trend_legend') }}</p>
    @endif

    @if ($matrix !== [])
        <h3 class="mt-6 mb-2 text-sm font-semibold text-gray-800">{{ __('admin.strategy.monitor.matrix_title') }}</h3>
        <div class="overflow-x-auto">
            <table class="min-w-full text-xs">
                <thead>
                    <tr class="border-b text-left text-gray-500">
                        <th class="py-2 pr-3">{{ __('admin.strategy.monitor.question') }}</th>
                        @php
                            $platformLabels = [];
                            foreach ($matrix as $row) {
                                foreach ($row['platforms'] ?? [] as $p) {
                                    $platformLabels[$p['platform']] = true;
                                }
                            }
                            $platformLabels = array_keys($platformLabels);
                        @endphp
                        @foreach ($platformLabels as $pl)
                            <th class="py-2 px-2 text-center">{{ Str::limit($pl, 12) }}</th>
                        @endforeach
                    </tr>
                </thead>
                <tbody>
                    @foreach ($matrix as $row)
                        <tr class="border-b border-gray-50">
                            <td class="py-2 pr-3 max-w-[12rem] truncate" title="{{ $row['question_text'] }}">{{ $row['question_text'] }}</td>
                            @foreach ($platformLabels as $pl)
                                @php
                                    $cell = collect($row['platforms'] ?? [])->firstWhere('platform', $pl);
                                @endphp
                                <td class="py-2 px-2 text-center">
                                    @if ($cell)
                                        <span class="{{ ($cell['brand_rank'] ?? 99) <= 3 ? 'font-semibold text-emerald-700' : 'text-gray-600' }}">
                                            {{ ($cell['brand_rank'] ?? 99) < 99 ? '#'.$cell['brand_rank'] : '—' }}
                                        </span>
                                    @else
                                        <span class="text-gray-300">·</span>
                                    @endif
                                </td>
                            @endforeach
                        </tr>
                    @endforeach
                </tbody>
            </table>
        </div>
    @endif
</section>

<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
    {{-- 配置：技术关键词 + AI 平台 --}}
    <div class="rounded-lg border border-gray-200 bg-white p-5 lg:col-span-2">
        <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.strategy.monitor.config_title') }}</h2>
        <form method="post" action="{{ route('admin.strategy.monitor.config') }}" class="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
            @csrf
            <div>
                <label class="text-sm font-medium text-gray-700">{{ __('admin.strategy.monitor.tech_keywords_label') }}</label>
                <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.tech_keywords_hint') }}</p>
                <textarea name="tech_keywords" rows="4" class="mt-2 block w-full rounded-md border-gray-300 text-sm" placeholder="品牌A&#10;品牌B">{{ $techKeywordsText }}</textarea>
            </div>
            <div>
                <label class="text-sm font-medium text-gray-700">{{ __('admin.strategy.monitor.platforms_label') }}</label>
                <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.platforms_hint') }}</p>
                <div class="mt-2 max-h-40 space-y-2 overflow-y-auto rounded-md border border-gray-200 p-3">
                    @forelse ($platformModels as $model)
                        <label class="flex items-center gap-2 text-sm">
                            <input type="checkbox" name="platform_model_ids[]" value="{{ $model['id'] }}"
                                @checked(in_array($model['id'], $configuredIds, true))>
                            <span>{{ $model['name'] }}</span>
                            <span class="text-xs text-gray-400">{{ $model['model_id'] }}</span>
                        </label>
                    @empty
                        <p class="text-sm text-gray-400">{{ __('admin.strategy.monitor.no_ai_models') }}</p>
                    @endforelse
                </div>
                <a href="{{ route('admin.ai-models.index') }}" class="mt-2 inline-block text-xs text-violet-700 hover:underline">{{ __('admin.strategy.monitor.manage_ai_models') }}</a>
            </div>
            <div class="lg:col-span-2">
                <button type="submit" class="rounded-md bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700">{{ __('admin.strategy.monitor.save_config') }}</button>
            </div>
        </form>
    </div>

    <div class="rounded-lg border border-gray-200 bg-white p-5">
        <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.strategy.monitor.add_title') }}</h2>
        <form method="post" action="{{ route('admin.strategy.monitor.store') }}" class="mt-4 space-y-3">
            @csrf
            <div>
                <label class="text-sm text-gray-700">{{ __('admin.strategy.monitor.question') }}</label>
                <textarea name="question_text" rows="3" required class="mt-1 block w-full rounded-md border-gray-300 text-sm"></textarea>
            </div>
            <div>
                <label class="text-sm text-gray-700">{{ __('admin.strategy.monitor.knowledge_base') }}</label>
                <select name="knowledge_base_id" class="mt-1 block w-full rounded-md border-gray-300 text-sm">
                    <option value="">{{ __('admin.strategy.monitor.optional') }}</option>
                    @foreach ($knowledgeBases as $kb)
                        <option value="{{ $kb->id }}">{{ $kb->name }}</option>
                    @endforeach
                </select>
            </div>
            <button type="submit" class="rounded-md bg-violet-600 px-4 py-2 text-sm text-white hover:bg-violet-700">{{ __('admin.strategy.monitor.save') }}</button>
        </form>

        <form method="post" action="{{ route('admin.strategy.monitor.import-batch') }}" class="mt-6 space-y-3 border-t border-gray-100 pt-4">
            @csrf
            <h3 class="text-sm font-semibold text-gray-800">{{ __('admin.strategy.monitor.batch_import_title') }}</h3>
            <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.batch_import_hint') }}</p>
            <textarea name="questions_text" rows="5" required class="block w-full rounded-md border-gray-300 text-sm" placeholder="{{ __('admin.strategy.monitor.batch_import_placeholder') }}"></textarea>
            <select name="knowledge_base_id" class="block w-full rounded-md border-gray-300 text-sm">
                <option value="">{{ __('admin.strategy.monitor.optional') }}</option>
                @foreach ($knowledgeBases as $kb)
                    <option value="{{ $kb->id }}">{{ $kb->name }}</option>
                @endforeach
            </select>
            <button type="submit" class="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-800 hover:bg-violet-50">{{ __('admin.strategy.monitor.batch_import_btn') }}</button>
        </form>

        <form method="post" action="{{ route('admin.strategy.monitor.import-tech-keywords') }}" class="mt-6 space-y-3 border-t border-gray-100 pt-4">
            @csrf
            <h3 class="text-sm font-semibold text-gray-800">{{ __('admin.strategy.monitor.tech_gen_title') }}</h3>
            <p class="text-xs text-gray-500">{{ __('admin.strategy.monitor.tech_gen_hint') }}</p>
            <textarea name="tech_keywords" rows="3" required class="block w-full rounded-md border-gray-300 text-sm" placeholder="纯电SUV&#10;800V平台"></textarea>
            <button type="submit" class="rounded-md border border-violet-300 px-4 py-2 text-sm text-violet-800 hover:bg-violet-50">{{ __('admin.strategy.monitor.tech_gen_btn') }}</button>
        </form>

        <form method="post" action="{{ route('admin.strategy.monitor.import') }}" class="mt-6 space-y-3 border-t border-gray-100 pt-4">
            @csrf
            <h3 class="text-sm font-semibold text-gray-800">{{ __('admin.strategy.monitor.import_title') }}</h3>
            <select name="library_id" required class="block w-full rounded-md border-gray-300 text-sm">
                @foreach ($keywordLibraries as $lib)
                    <option value="{{ $lib->id }}">{{ $lib->name }}</option>
                @endforeach
            </select>
            <button type="submit" class="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50">{{ __('admin.strategy.monitor.import_btn') }}</button>
        </form>
    </div>

    <div class="rounded-lg border border-gray-200 bg-white p-5">
        <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.strategy.monitor.list_title') }}</h2>
        <ul class="mt-4 max-h-[32rem] divide-y divide-gray-100 overflow-y-auto">
            @forelse ($monitorQuestions as $q)
                <li class="py-3 text-sm">
                    <p class="font-medium text-gray-900">{{ Str::limit($q->question_text, 100) }}</p>
                    <p class="mt-1 text-xs text-gray-500">
                        {{ $q->category }} · {{ $q->is_active ? __('admin.strategy.monitor.active') : __('admin.strategy.monitor.inactive') }}
                    </p>
                    <form method="post" action="{{ route('admin.strategy.monitor.destroy', ['questionId' => $q->id]) }}" class="mt-2" onsubmit="return confirm('{{ __('admin.strategy.monitor.confirm_delete') }}')">
                        @csrf
                        @method('DELETE')
                        <button type="submit" class="text-xs text-red-600 hover:underline">{{ __('admin.strategy.monitor.delete') }}</button>
                    </form>
                </li>
            @empty
                <li class="py-4 text-sm text-gray-400">{{ __('admin.strategy.monitor.empty') }}</li>
            @endforelse
        </ul>
    </div>
</div>
