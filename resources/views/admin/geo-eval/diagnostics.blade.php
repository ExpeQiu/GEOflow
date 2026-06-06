@extends('admin.layouts.app')

@section('content')
    @php
        $gate = $gateConfig ?? [];
    @endphp
    <div class="px-4 sm:px-0">
        <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
                <h1 class="text-2xl font-bold text-gray-900">{{ __('admin.geo_eval.diagnostics_title') }}</h1>
                <p class="mt-1 text-sm text-gray-500">{{ __('admin.geo_eval.diagnostics_subtitle') }}</p>
            </div>
            <div class="flex flex-wrap gap-2">
                <a href="{{ route('admin.analytics', ['geo_days' => 30]) }}#geo-eval-dashboard" class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                    {{ __('admin.geo_eval.open_adoption_dashboard') }}
                </a>
                <a href="{{ route('admin.insight-templates.index') }}" class="inline-flex items-center rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white hover:bg-indigo-700">
                    {{ __('admin.geo_eval.insight_templates_title') }}
                </a>
            </div>
        </div>

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {{ session('status') }}
            </div>
        @endif

        <div class="mb-6 rounded-lg border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900">
            <p class="font-semibold">{{ __('admin.geo_eval.gate_status_title') }}</p>
            <ul class="mt-2 list-inside list-disc space-y-1 text-cyan-800">
                <li>{{ __('admin.geo_eval.gate_enabled_label') }}: {{ ($gate['enabled'] ?? false) ? __('admin.geo_eval.yes') : __('admin.geo_eval.no') }}</li>
                <li>{{ __('admin.geo_eval.gate_publish_label') }}: {{ ($gate['gate_enabled'] ?? false) ? __('admin.geo_eval.yes') : __('admin.geo_eval.no') }}</li>
                <li>{{ __('admin.geo_eval.gate_rollout_label', ['percent' => (int) ($gate['rollout_percent'] ?? 0)]) }}</li>
            </ul>
            <p class="mt-3 text-xs text-cyan-700">{{ __('admin.geo_eval.manual_publish_hint') }}</p>
        </div>

        <div class="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            @foreach (['pending_eval', 'passed', 'failed', 'skipped'] as $key)
                <div class="rounded-lg border border-gray-200 bg-white p-4">
                    <p class="text-xs text-gray-500">{{ __('admin.geo_eval.'.$key) }}</p>
                    <p class="mt-1 text-xl font-semibold">{{ (int) ($summary[$key] ?? 0) }}</p>
                </div>
            @endforeach
        </div>

        <div class="mb-6 flex flex-wrap gap-3">
            <form method="post" action="{{ route('admin.geo-eval.reevaluate-failed') }}">
                @csrf
                <button type="submit" class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                    {{ __('admin.geo_eval.batch_reevaluate') }}
                </button>
            </form>
        </div>

        @include('admin.geo-eval._alerts', ['recentAlerts' => $recentAlerts ?? []])

        <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <div class="rounded-lg border border-gray-200 bg-white p-4">
                <h2 class="mb-3 text-sm font-semibold text-gray-900">{{ __('admin.geo_eval.failure_topn') }}</h2>
                <ul class="space-y-2 text-sm text-gray-700">
                    @forelse ($failureTopN as $row)
                        <li>{{ $row['failure_reason'] }} ({{ $row['total'] }})</li>
                    @empty
                        <li class="text-gray-400">{{ __('admin.geo_eval.no_failures') }}</li>
                    @endforelse
                </ul>
            </div>
            <div class="rounded-lg border border-gray-200 bg-white p-4">
                <h2 class="mb-3 text-sm font-semibold text-gray-900">{{ __('admin.geo_eval.recent_failures') }}</h2>
                <ul class="space-y-3 text-sm text-gray-700">
                    @forelse ($recentFailures as $row)
                        <li class="border-b border-gray-100 pb-2">
                            <a href="{{ route('admin.articles.edit', ['articleId' => $row['article_id']]) }}" class="font-medium text-blue-600 hover:underline">#{{ $row['article_id'] }}</a>
                            — {{ $row['failure_reason'] }}
                            <div class="mt-1 text-xs text-gray-500">
                                {{ __('admin.geo_eval.metric_rank') }}: {{ (int) ($row['rank'] ?? 0) }}
                                · {{ __('admin.geo_eval.metric_found') }}: {{ ($row['found'] ?? false) ? __('admin.geo_eval.yes') : __('admin.geo_eval.no') }}
                                @if (!empty($row['audit_status']))
                                    · {{ __('admin.geo_eval.metric_audit') }}: {{ $row['audit_status'] }}
                                @endif
                            </div>
                            <form class="mt-1 inline" method="post" action="{{ route('admin.geo-eval.reevaluate', ['articleId' => $row['article_id']]) }}">
                                @csrf
                                <button type="submit" class="text-blue-600 hover:underline">{{ __('admin.geo_eval.reevaluate_one') }}</button>
                            </form>
                            @if (!empty($row['task_id']) || !empty($row['knowledge_base_id']) || !empty($row['insight_template_id']))
                                <div class="mt-2 text-xs text-gray-500">
                                    {{ __('admin.geo_eval.action_links') }}:
                                    @if (!empty($row['task_id']))
                                        <a href="{{ route('admin.tasks.edit', ['taskId' => (int) $row['task_id']]) }}" class="text-blue-600 hover:underline">{{ __('admin.geo_eval.link_task') }} #{{ (int) $row['task_id'] }}</a>
                                    @endif
                                    @if (!empty($row['knowledge_base_id']))
                                        <span class="mx-1">·</span>
                                        <a href="{{ route('admin.knowledge-bases.detail', ['knowledgeBaseId' => (int) $row['knowledge_base_id']]) }}" class="text-blue-600 hover:underline">{{ __('admin.geo_eval.link_knowledge_base') }}</a>
                                    @endif
                                    @if (!empty($row['insight_template_id']))
                                        <span class="mx-1">·</span>
                                        <a href="{{ route('admin.insight-templates.show', ['templateId' => (int) $row['insight_template_id']]) }}" class="text-blue-600 hover:underline">{{ __('admin.geo_eval.link_insight_template') }}</a>
                                    @endif
                                </div>
                            @endif
                        </li>
                    @empty
                        <li class="text-gray-400">{{ __('admin.geo_eval.no_failures') }}</li>
                    @endforelse
                </ul>
            </div>
        </div>

        <div class="mt-6 rounded-lg border border-gray-200 bg-white p-4">
            <h2 class="mb-3 text-sm font-semibold text-gray-900">{{ __('admin.geo_eval.recent_events') }}</h2>
            <div class="overflow-x-auto">
                <table class="min-w-full text-left text-sm text-gray-700">
                    <thead>
                        <tr class="border-b text-xs text-gray-500">
                            <th class="py-2 pr-4">request_id</th>
                            <th class="py-2 pr-4">event</th>
                            <th class="py-2 pr-4">eval_status</th>
                            <th class="py-2 pr-4">article</th>
                            <th class="py-2 pr-4">{{ __('admin.geo_eval.column_task') }}</th>
                            <th class="py-2">time</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach ($recentEvents as $event)
                            <tr class="border-b border-gray-100">
                                <td class="py-2 pr-4 font-mono text-xs">{{ \Illuminate\Support\Str::limit($event['request_id'], 12) }}</td>
                                <td class="py-2 pr-4">{{ $event['event'] }}</td>
                                <td class="py-2 pr-4">{{ $event['eval_status'] }}</td>
                                <td class="py-2 pr-4">
                                    @if (!empty($event['article_id']))
                                        <a href="{{ route('admin.articles.edit', ['articleId' => (int) $event['article_id']]) }}" class="text-blue-600 hover:underline">#{{ (int) $event['article_id'] }}</a>
                                    @else
                                        -
                                    @endif
                                </td>
                                <td class="py-2 pr-4">
                                    @if (!empty($event['task_id']))
                                        <a href="{{ route('admin.tasks.edit', ['taskId' => (int) $event['task_id']]) }}" class="text-blue-600 hover:underline">#{{ (int) $event['task_id'] }}</a>
                                    @else
                                        -
                                    @endif
                                </td>
                                <td class="py-2">{{ $event['created_at'] }}</td>
                            </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
        </div>
    </div>
@endsection
