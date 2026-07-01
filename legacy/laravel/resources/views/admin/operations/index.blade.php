@extends('admin.layouts.app')

@section('content')
    @php
        $currentTab = $currentTab ?? ($tab ?? 'overview');
    @endphp
    <div class="px-4 sm:px-0">
        @include('admin.operations._hub-header')
        @include('admin.operations._hub-nav', ['operationsHubCurrentTab' => $currentTab])

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {{ session('status') }}
            </div>
        @endif

        @if ($currentTab === 'overview')
            @include('admin.operations._overview', ['stats' => $stats ?? []])
        @endif

        @if ($currentTab === 'tasks')
            @include('admin.tasks._panel', ['standalone' => false])
        @endif

        @if ($currentTab === 'articles')
            @include('admin.articles._panel', ['standalone' => false])
        @endif

        @if ($currentTab === 'distribution')
            @include('admin.distribution._panel', [
                'standalone' => false,
                'stats' => $distributionStats ?? [],
                'channels' => $channels ?? collect(),
                'logs' => $logs ?? collect(),
            ])
        @endif
    </div>

    @if ($currentTab === 'tasks')
        @push('scripts')
            @include('admin.tasks._scripts')
        @endpush
    @endif

    @if ($currentTab === 'articles')
        @push('scripts')
            @include('admin.articles._scripts')
        @endpush
    @endif
@endsection
