@extends('admin.layouts.app')

@section('content')
    @php
        $currentTab = $currentTab ?? ($tab ?? 'overview');
    @endphp
    <div class="px-4 sm:px-0">
        @include('admin.production._hub-header')
        @include('admin.production._hub-nav', ['productionHubCurrentTab' => $currentTab])

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {{ session('status') }}
            </div>
        @endif

        <div id="production-tab-panel" data-tab="{{ $currentTab }}">
            @if ($currentTab === 'overview')
                @include('admin.production._overview', ['stats' => $stats, 'aiStats' => $aiStats])
            @elseif ($currentTab === 'materials')
                @include('admin.production._materials', ['stats' => $stats])
            @elseif ($currentTab === 'knowledge')
                @include('admin.production._knowledge', ['stats' => $stats])
            @elseif ($currentTab === 'ai_config')
                @include('admin.production._ai_config', ['stats' => $aiStats])
            @else
                @include('admin.production._overview', ['stats' => $stats, 'aiStats' => $aiStats])
            @endif
        </div>
    </div>
@endsection
