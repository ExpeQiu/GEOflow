@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        @include('admin.strategy._hub-header')

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ session('status') }}</div>
        @endif

        @include('admin.strategy._hub-nav', ['strategyHubCurrentTab' => 'insight-templates'])

        <div class="max-w-4xl">
            <div class="mb-6 flex items-start justify-between gap-4">
                <div>
                    <h2 class="text-lg font-semibold text-gray-900">{{ $template->name }}</h2>
                    <p class="mt-1 text-sm text-gray-500 break-all">{{ $template->source_url }}</p>
                </div>
                <div class="flex flex-wrap gap-2">
                    <a href="{{ route('admin.insight-templates.edit', ['templateId' => $template->id]) }}" class="rounded-md border border-gray-300 px-3 py-2 text-sm">{{ __('admin.geo_eval.insight_edit') }}</a>
                    <form method="post" action="{{ route('admin.insight-templates.remine', ['templateId' => $template->id]) }}">
                        @csrf
                        <button type="submit" class="rounded-md border border-indigo-300 bg-indigo-50 px-3 py-2 text-sm text-indigo-800">{{ __('admin.geo_eval.insight_remine') }}</button>
                    </form>
                </div>
            </div>
            <div class="space-y-6">
                <div class="rounded-lg border bg-white p-4">
                    <h3 class="text-sm font-semibold text-gray-900">{{ __('admin.geo_eval.insight_eeat') }}</h3>
                    <p class="mt-2 text-2xl font-semibold">{{ $template->eeat_score ?? '—' }}</p>
                </div>
                <div class="rounded-lg border bg-white p-4">
                    <h3 class="text-sm font-semibold text-gray-900">{{ __('admin.geo_eval.insight_features') }}</h3>
                    <pre class="mt-2 overflow-x-auto rounded bg-gray-50 p-3 text-xs">{{ json_encode($template->features ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) }}</pre>
                </div>
                <div class="rounded-lg border bg-white p-4">
                    <h3 class="text-sm font-semibold text-gray-900">StyleGuide</h3>
                    <pre class="mt-2 overflow-x-auto rounded bg-gray-50 p-3 text-xs">{{ json_encode($template->style_guide ?? [], JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE) }}</pre>
                </div>
            </div>
            <a href="{{ route('admin.insight-templates.index') }}" class="mt-6 inline-block text-sm text-blue-600 hover:underline">{{ __('admin.geo_eval.back_templates') }}</a>
        </div>
    </div>
@endsection
