@php
    $gate = $sim['gateConfig'] ?? [];
    $summary = $sim['summary'] ?? [];
@endphp
<div class="mb-4 rounded-lg border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
    <p class="font-semibold">{{ __('admin.geo_eval.gate_status_title') }}</p>
    <ul class="mt-2 list-inside list-disc space-y-1">
        <li>{{ __('admin.geo_eval.gate_enabled_label') }}: {{ ($gate['enabled'] ?? false) ? __('admin.geo_eval.yes') : __('admin.geo_eval.no') }}</li>
        <li>{{ __('admin.geo_eval.gate_publish_label') }}: {{ ($gate['gate_enabled'] ?? false) ? __('admin.geo_eval.yes') : __('admin.geo_eval.no') }}</li>
    </ul>
</div>

<div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
    @foreach (['pending_eval', 'passed', 'failed', 'skipped'] as $key)
        <div class="rounded-lg border border-gray-200 bg-white p-4">
            <p class="text-xs text-gray-500">{{ __('admin.geo_eval.'.$key) }}</p>
            <p class="mt-1 text-xl font-semibold">{{ (int) ($summary[$key] ?? 0) }}</p>
        </div>
    @endforeach
</div>

<form method="post" action="{{ route('admin.strategy.simulator.batch-reevaluate') }}" class="mb-6">
    @csrf
    <button type="submit" class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">{{ __('admin.geo_eval.batch_reevaluate') }}</button>
</form>

@include('admin.geo-eval._alerts', ['recentAlerts' => $recentAlerts ?? []])

<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
    <div class="rounded-lg border border-gray-200 bg-white p-4">
        <h2 class="mb-3 text-sm font-semibold">{{ __('admin.geo_eval.failure_topn') }}</h2>
        <ul class="space-y-2 text-sm">
            @forelse ($sim['failureTopN'] ?? [] as $row)
                <li>{{ $row['failure_reason'] }} ({{ $row['total'] }})</li>
            @empty
                <li class="text-gray-400">{{ __('admin.geo_eval.no_failures') }}</li>
            @endforelse
        </ul>
    </div>
    <div class="rounded-lg border border-gray-200 bg-white p-4">
        <h2 class="mb-3 text-sm font-semibold">{{ __('admin.geo_eval.recent_failures') }}</h2>
        <ul class="space-y-3 text-sm">
            @forelse ($sim['recentFailures'] ?? [] as $row)
                <li class="border-b border-gray-100 pb-2">
                    <a href="{{ route('admin.articles.edit', ['articleId' => $row['article_id']]) }}" class="font-medium text-blue-600 hover:underline">#{{ $row['article_id'] }}</a>
                    — {{ $row['failure_reason'] }}
                    <div class="mt-2 flex flex-wrap gap-2">
                        <form method="post" action="{{ route('admin.strategy.simulator.reevaluate', ['articleId' => $row['article_id']]) }}">
                            @csrf
                            <button type="submit" class="text-xs text-blue-600 hover:underline">{{ __('admin.geo_eval.reevaluate') }}</button>
                        </form>
                        <form method="post" action="{{ route('admin.strategy.simulator.apply-recommendations', ['articleId' => $row['article_id']]) }}">
                            @csrf
                            <button type="submit" class="text-xs text-violet-600 hover:underline">{{ __('admin.strategy.simulator.apply_btn') }}</button>
                        </form>
                    </div>
                </li>
            @empty
                <li class="text-gray-400">{{ __('admin.geo_eval.no_failures') }}</li>
            @endforelse
        </ul>
    </div>
</div>
