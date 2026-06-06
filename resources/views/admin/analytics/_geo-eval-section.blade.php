@php
    $geo = $geoEvalSummary ?? [];
    $dash = $geoAdoptionDashboard ?? [];
    $kpis = is_array($dash['kpis'] ?? null) ? $dash['kpis'] : [];
    $trendRaw = is_array($dash['trend'] ?? null) ? $dash['trend'] : [];
    $chartSeries = [];
    foreach ($trendRaw as $row) {
        $chartSeries[] = [
            'date' => (string) ($row['date'] ?? ''),
            'created' => (int) round(((float) ($row['adoption_rate'] ?? 0)) * 100),
            'published' => (int) round(((float) ($row['first_position_rate'] ?? 0)) * 100),
        ];
    }
    $belowThreshold = (bool) ($dash['below_threshold'] ?? false);
@endphp
<section id="geo-eval-dashboard" class="mb-8 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
    <div class="mb-4 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
            <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.geo_eval.analytics_section_title') }}</h2>
            <p class="text-sm text-gray-500">{{ __('admin.geo_eval.analytics_section_subtitle') }}</p>
        </div>
        <form method="get" action="{{ route('admin.analytics') }}" class="flex flex-wrap items-end gap-2">
            @foreach (request()->except(['geo_days', 'geo_platform', 'page']) as $key => $value)
                @if (is_array($value))
                    @continue
                @endif
                <input type="hidden" name="{{ $key }}" value="{{ $value }}">
            @endforeach
            <div>
                <label class="text-xs text-gray-500">{{ __('admin.geo_eval.filter_days') }}</label>
                <select name="geo_days" class="mt-1 block rounded-md border-gray-300 text-sm">
                    @foreach ([7, 30, 90] as $d)
                        <option value="{{ $d }}" @selected((int) ($geoDays ?? 30) === $d)>{{ $d }}</option>
                    @endforeach
                </select>
            </div>
            <div>
                <label class="text-xs text-gray-500">{{ __('admin.geo_eval.filter_platform') }}</label>
                <select name="geo_platform" class="mt-1 block rounded-md border-gray-300 text-sm">
                    <option value="">{{ __('admin.geo_eval.all_platforms') }}</option>
                    @foreach ($geoPlatformOptions ?? [] as $id => $name)
                        <option value="{{ $name }}" @selected(($geoPlatform ?? '') === $name)>{{ $name }}</option>
                    @endforeach
                </select>
            </div>
            <button type="submit" class="rounded-md bg-blue-600 px-3 py-2 text-sm text-white hover:bg-blue-700">{{ __('admin.geo_eval.apply_filter') }}</button>
            <a href="{{ route('admin.geo-eval.diagnostics') }}" class="text-sm font-medium text-blue-600 hover:text-blue-800">
                {{ __('admin.geo_eval.open_diagnostics') }}
            </a>
        </form>
    </div>

    @if ($belowThreshold)
        <div class="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            {{ __('admin.geo_eval.analytics_low_adoption_hint') }}
            <a href="{{ route('admin.geo-eval.diagnostics') }}" class="ml-2 font-medium text-amber-800 underline">{{ __('admin.geo_eval.open_diagnostics') }}</a>
            <a href="{{ route('admin.insight-templates.index') }}" class="ml-2 font-medium text-amber-800 underline">{{ __('admin.nav.insight_templates') }}</a>
            <a href="{{ route('admin.knowledge-bases.index') }}" class="ml-2 font-medium text-amber-800 underline">{{ __('admin.nav.materials') }}</a>
        </div>
    @endif

    <div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="rounded-md p-4 {{ $belowThreshold ? 'bg-red-50 ring-1 ring-red-200' : 'bg-gray-50' }}">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.adoption_rate') }}</p>
            <p class="mt-1 text-2xl font-semibold {{ $belowThreshold ? 'text-red-700' : 'text-gray-900' }}">
                {{ number_format((float) ($kpis['adoption_rate'] ?? 0) * 100, 1) }}%
            </p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.first_position_rate') }}</p>
            <p class="mt-1 text-2xl font-semibold text-gray-900">{{ number_format((float) ($kpis['first_position_rate'] ?? 0) * 100, 1) }}%</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.sample_size') }}</p>
            <p class="mt-1 text-2xl font-semibold text-gray-900">{{ (int) ($kpis['sample_size'] ?? 0) }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.passed') }}</p>
            <p class="mt-1 text-2xl font-semibold text-emerald-600">{{ (int) ($kpis['passed_count'] ?? 0) }}</p>
        </div>
    </div>

    <div class="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.pending_eval') }}</p>
            <p class="mt-1 text-xl font-semibold text-amber-600">{{ (int) ($geo['pending_eval'] ?? 0) }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.passed') }}</p>
            <p class="mt-1 text-xl font-semibold text-emerald-600">{{ (int) ($geo['passed'] ?? 0) }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.failed') }}</p>
            <p class="mt-1 text-xl font-semibold text-red-600">{{ (int) ($geo['failed'] ?? 0) }}</p>
        </div>
        <div class="rounded-md bg-gray-50 p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.skipped') }}</p>
            <p class="mt-1 text-xl font-semibold text-gray-700">{{ (int) ($geo['skipped'] ?? 0) }}</p>
        </div>
    </div>

    @if ($chartSeries !== [])
        <div class="rounded-md border border-dashed border-gray-200 p-4">
            <p class="mb-2 text-xs text-gray-500">{{ __('admin.geo_eval.trend_chart_legend') }}</p>
            @include('admin.analytics._line-chart', ['series' => $chartSeries, 'primaryKey' => 'created', 'secondaryKey' => 'published'])
        </div>
    @else
        <p class="text-sm text-gray-400">{{ __('admin.geo_eval.no_trend_data') }}</p>
    @endif
</section>
