@extends('admin.layouts.app')

@section('content')
    @php
        $currentTab = $tab ?? 'overview';
        $sim = $simulatorData ?? [];
    @endphp
    <div class="px-4 sm:px-0">
        @include('admin.strategy._hub-header')

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {{ session('status') }}
            </div>
        @endif

        @include('admin.strategy._hub-nav', ['strategyHubCurrentTab' => $currentTab])

        @if ($currentTab === 'overview')
            <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div class="rounded-lg border border-violet-200 bg-violet-50/60 p-5">
                    <p class="text-xs font-semibold uppercase text-violet-700">{{ __('admin.strategy.tabs.monitor') }}</p>
                    <p class="mt-2 text-2xl font-semibold">{{ $monitorQuestions->count() }}</p>
                    <a href="{{ route('admin.strategy.index', ['tab' => 'monitor']) }}" class="mt-3 inline-block text-sm text-violet-800 hover:underline">{{ __('admin.strategy.view_detail') }}</a>
                </div>
                <div class="rounded-lg border border-indigo-200 bg-indigo-50/60 p-5">
                    <p class="text-xs font-semibold uppercase text-indigo-700">{{ __('admin.strategy.tabs.web_intel') }}</p>
                    <p class="mt-2 text-2xl font-semibold">{{ $webSources->count() }}</p>
                    <a href="{{ route('admin.strategy.index', ['tab' => 'web-intel']) }}" class="mt-3 inline-block text-sm text-indigo-800 hover:underline">{{ __('admin.strategy.view_detail') }}</a>
                </div>
                <div class="rounded-lg border border-emerald-200 bg-emerald-50/60 p-5">
                    <p class="text-xs font-semibold uppercase text-emerald-700">{{ __('admin.geo_eval.passed') }}</p>
                    <p class="mt-2 text-2xl font-semibold">{{ (int) (($geoEvalSummary['passed'] ?? 0)) }}</p>
                    <a href="{{ route('admin.strategy.index', ['tab' => 'simulator']) }}" class="mt-3 inline-block text-sm text-emerald-800 hover:underline">{{ __('admin.strategy.view_detail') }}</a>
                </div>
            </div>

            @if (!empty($recentAlerts))
                <div class="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-4">
                    <h2 class="text-sm font-semibold text-amber-900">{{ __('admin.strategy.recent_alerts') }}</h2>
                    <ul class="mt-2 space-y-1 text-sm text-amber-800">
                        @foreach ($recentAlerts as $alert)
                            <li>{{ $alert['alert_type'] }} — {{ $alert['message'] }}</li>
                        @endforeach
                    </ul>
                </div>
            @endif
        @endif

        @if ($currentTab === 'monitor')
            @include('admin.strategy._monitor')
        @endif

        @if ($currentTab === 'web-intel')
            @include('admin.strategy._web-intel')
        @endif

        @if ($currentTab === 'simulator')
            @include('admin.strategy._simulator', ['sim' => $sim, 'recentAlerts' => $recentAlerts ?? []])
        @endif

        @if ($currentTab === 'analytics')
            @include('admin.strategy._analytics')
        @endif
    </div>
@endsection
