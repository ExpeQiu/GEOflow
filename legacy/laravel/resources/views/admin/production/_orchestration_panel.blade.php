@php
    $orch = is_array($orchestrationStats ?? null) ? $orchestrationStats : [];
    $orchBackend = (string) ($orch['backend'] ?? 'internal');
    $orchHealthy = (bool) ($orch['sidecar_healthy'] ?? true);
    $orchTotals24h = is_array($orch['totals_24h'] ?? null) ? $orch['totals_24h'] : [];
    $orchByWorkflow = is_array($orch['by_workflow'] ?? null) ? $orch['by_workflow'] : [];
    $orchKnowledgePending = (int) ($orch['knowledge_pending'] ?? 0);
    $orchRecentFailures = is_array($orch['recent_failures'] ?? null) ? $orch['recent_failures'] : [];
    $panelId = $orchestrationPanelId ?? 'content-agent-orchestration';
@endphp

<section id="{{ $panelId }}" class="mb-6 overflow-hidden rounded-lg border border-slate-200 bg-white shadow">
    <div class="border-b border-slate-100 bg-slate-50/80 px-6 py-4">
        <div class="flex flex-wrap items-center justify-between gap-3">
            <div class="flex items-center gap-2">
                <i data-lucide="workflow" class="h-5 w-5 text-slate-600"></i>
                <h2 class="text-base font-semibold text-gray-900">{{ __('admin.production.orchestration.title') }}</h2>
            </div>
            <span class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold ring-1 {{ $orchHealthy ? 'bg-emerald-50 text-emerald-700 ring-emerald-200' : 'bg-red-50 text-red-700 ring-red-200' }}">
                <i data-lucide="activity" class="mr-1.5 h-3.5 w-3.5"></i>
                {{ $orchHealthy ? __('admin.production.orchestration.sidecar_healthy') : __('admin.production.orchestration.sidecar_unhealthy') }}
            </span>
        </div>
        <p class="mt-2 text-sm text-gray-600">{{ __('admin.ai_configurator.orchestration_desc') }}</p>
    </div>
    <div class="grid grid-cols-1 gap-4 px-6 py-5 md:grid-cols-2 xl:grid-cols-4">
        <div>
            <p class="text-xs font-medium uppercase text-gray-500">{{ __('admin.production.orchestration.backend') }}</p>
            <p class="mt-1 text-lg font-semibold text-gray-900">{{ __('admin.production.orchestration.backend_'.$orchBackend) }}</p>
            <p class="mt-1 text-xs text-gray-500">{{ __('admin.production.orchestration.driver', ['driver' => (string) ($orch['driver_hint'] ?? 'langgraph')]) }}</p>
        </div>
        <div>
            <p class="text-xs font-medium uppercase text-gray-500">{{ __('admin.production.orchestration.completed_24h') }}</p>
            <p class="mt-1 text-lg font-semibold text-emerald-700">{{ (int) ($orchTotals24h['completed'] ?? 0) }}</p>
            <p class="mt-1 text-xs text-gray-500">{{ __('admin.production.orchestration.failed_24h', ['count' => (int) ($orchTotals24h['failed'] ?? 0) + (int) ($orchTotals24h['expired'] ?? 0)]) }}</p>
        </div>
        <div>
            <p class="text-xs font-medium uppercase text-gray-500">{{ __('admin.production.orchestration.pending') }}</p>
            <p class="mt-1 text-lg font-semibold text-amber-700">{{ (int) ($orchTotals24h['pending'] ?? 0) + (int) ($orchTotals24h['running'] ?? 0) }}</p>
            @if ($orchKnowledgePending > 0)
                <a href="{{ route('admin.production.index', ['tab' => 'knowledge']) }}" class="mt-1 inline-block text-xs text-orange-700 hover:underline">
                    {{ __('admin.production.orchestration.knowledge_pending', ['count' => $orchKnowledgePending]) }}
                </a>
            @endif
        </div>
        <div>
            <p class="text-xs font-medium uppercase text-gray-500">{{ __('admin.production.orchestration.workflow_breakdown') }}</p>
            <dl class="mt-1 space-y-1 text-xs text-gray-600">
                @foreach (['content', 'content_pipeline', 'url_import', 'semantic_chunk'] as $workflowKey)
                    @php $wf = is_array($orchByWorkflow[$workflowKey] ?? null) ? $orchByWorkflow[$workflowKey] : []; @endphp
                    <div class="flex justify-between gap-2">
                        <dt>{{ __('admin.production.orchestration.workflow_'.$workflowKey) }}</dt>
                        <dd class="font-medium text-gray-900">{{ (int) ($wf['completed'] ?? 0) }}/{{ (int) ($wf['failed'] ?? 0) }}/{{ (int) ($wf['pending'] ?? 0) }}</dd>
                    </div>
                @endforeach
            </dl>
        </div>
    </div>

    @include('admin.production._orchestration_graph', [
        'workflowCatalog' => $workflowCatalog ?? [],
        'orchestrationStats' => $orchestrationStats ?? [],
    ])

    @if ($orchRecentFailures !== [])
        <div class="border-t border-gray-100 px-6 py-4">
            <p class="text-xs font-semibold uppercase text-gray-500">{{ __('admin.ai_configurator.orchestration_recent_failures') }}</p>
            <ul class="mt-2 space-y-1 text-xs text-gray-600">
                @foreach ($orchRecentFailures as $failure)
                    <li>
                        <span class="font-mono">{{ \Illuminate\Support\Str::limit((string) ($failure['request_id'] ?? ''), 12, '') }}</span>
                        · {{ (string) ($failure['workflow_type'] ?? '') }}
                        @if ((string) ($failure['error_message'] ?? '') !== '')
                            · {{ \Illuminate\Support\Str::limit((string) $failure['error_message'], 48) }}
                        @endif
                    </li>
                @endforeach
            </ul>
        </div>
    @endif

    <div class="flex flex-wrap gap-3 border-t border-gray-100 bg-gray-50 px-6 py-4">
        <a href="{{ route('admin.production.index', ['tab' => 'overview']) }}" class="text-sm font-medium text-slate-700 hover:text-slate-900">
            {{ __('admin.ai_configurator.orchestration_view_overview') }}
        </a>
        <a href="{{ route('admin.production.index', ['tab' => 'knowledge']) }}" class="text-sm font-medium text-orange-700 hover:text-orange-800">
            {{ __('admin.ai_configurator.orchestration_view_knowledge') }}
        </a>
        <a href="{{ route('admin.url-import') }}" class="text-sm font-medium text-blue-700 hover:text-blue-800">
            {{ __('admin.ai_configurator.orchestration_view_url_import') }}
        </a>
    </div>
</section>
