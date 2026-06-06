@php
    $analyticsFormRoute = $analyticsFormRoute ?? 'admin.strategy.index';
    $analyticsFormParams = $analyticsFormParams ?? ['tab' => 'analytics'];
@endphp

<div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
    <div>
        <h2 class="text-xl font-semibold text-gray-900">{{ __('admin.analytics.heading') }}</h2>
        <p class="mt-1 text-sm text-gray-600">{{ __('admin.analytics.subtitle') }}</p>
    </div>
    <div class="flex items-center gap-3">
        <span class="text-sm text-gray-500">{{ __('admin.analytics.last_updated', ['time' => now()->format('Y-m-d H:i:s')]) }}</span>
        <button type="button" onclick="location.reload()" class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50">
            <i data-lucide="refresh-cw" class="mr-1 h-4 w-4"></i>
            {{ __('admin.analytics.refresh') }}
        </button>
    </div>
</div>

@include('admin.analytics._filters', [
    'filters' => $filters,
    'filterOptions' => $filterOptions,
    'analyticsFormRoute' => $analyticsFormRoute,
    'analyticsFormParams' => $analyticsFormParams,
])
@include('admin.analytics._global-overview', ['globalOverview' => $globalOverview])
@include('admin.analytics._geo-eval-section', [
    'geoEvalSummary' => $geoEvalSummary ?? [],
    'geoAdoptionDashboard' => $geoAdoptionDashboard ?? [],
    'geoDays' => $geoDays ?? 30,
    'geoPlatform' => $geoPlatform ?? '',
    'geoPlatformOptions' => $geoPlatformOptions ?? [],
    'analyticsFormRoute' => $analyticsFormRoute,
    'analyticsFormParams' => $analyticsFormParams,
])
@include('admin.analytics._single-site-section')
@include('admin.analytics._distribution-section')
@include('admin.analytics._log-section', ['logSummary' => $logSummary])
