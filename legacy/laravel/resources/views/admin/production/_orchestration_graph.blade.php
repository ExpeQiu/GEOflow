@php
    $catalog = is_array($workflowCatalog ?? null) ? $workflowCatalog : ['workflows' => [], 'default_workflow' => 'content_pipeline'];
    $workflows = is_array($catalog['workflows'] ?? null) ? $catalog['workflows'] : [];
    $defaultWorkflow = (string) ($catalog['default_workflow'] ?? 'content_pipeline');
    $orchByWorkflow = is_array(($orchestrationStats ?? [])['by_workflow'] ?? null)
        ? ($orchestrationStats ?? [])['by_workflow']
        : [];
    $workflowOrder = ['content_pipeline', 'content', 'url_import', 'semantic_chunk'];
    $workflowOrder = array_values(array_filter($workflowOrder, static fn (string $key): bool => isset($workflows[$key])));
    if ($workflowOrder === []) {
        $workflowOrder = array_keys($workflows);
    }
@endphp

@if ($workflows !== [])
    <div class="border-t border-gray-100 px-6 py-5" id="content-agent-orchestration-graph">
        <div class="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
                <h3 class="text-sm font-semibold text-gray-900">{{ __('admin.production.orchestration.graph_title') }}</h3>
                <p class="mt-1 text-xs text-gray-500">{{ __('admin.production.orchestration.graph_desc') }}</p>
            </div>
            <div class="flex flex-wrap gap-2" role="tablist" aria-label="{{ __('admin.production.orchestration.graph_title') }}">
                @foreach ($workflowOrder as $workflowKey)
                    @php
                        $wf = $workflows[$workflowKey];
                        $wfStats = is_array($orchByWorkflow[$workflowKey] ?? null) ? $orchByWorkflow[$workflowKey] : [];
                        $completed = (int) ($wfStats['completed'] ?? 0);
                    @endphp
                    <button
                        type="button"
                        class="orch-workflow-tab rounded-full px-3 py-1.5 text-xs font-medium ring-1 transition {{ $workflowKey === $defaultWorkflow ? 'bg-slate-800 text-white ring-slate-800' : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50' }}"
                        data-workflow-tab="{{ $workflowKey }}"
                        role="tab"
                        aria-selected="{{ $workflowKey === $defaultWorkflow ? 'true' : 'false' }}"
                    >
                        {{ __('admin.production.orchestration.workflow_'.$workflowKey) }}
                        @if ($completed > 0)
                            <span class="ml-1 opacity-80">({{ $completed }})</span>
                        @endif
                    </button>
                @endforeach
            </div>
        </div>

        <div class="mt-4 space-y-4">
            @foreach ($workflowOrder as $workflowKey)
                @php
                    $wf = $workflows[$workflowKey];
                    $steps = is_array($wf['visual_steps'] ?? null) ? $wf['visual_steps'] : [];
                    $wfStats = is_array($orchByWorkflow[$workflowKey] ?? null) ? $orchByWorkflow[$workflowKey] : [];
                    $isActive = $workflowKey === $defaultWorkflow;
                @endphp
                <div
                    class="orch-workflow-panel overflow-hidden rounded-lg border border-slate-200 bg-slate-50/50 {{ $isActive ? '' : 'hidden' }}"
                    data-workflow-panel="{{ $workflowKey }}"
                    role="tabpanel"
                >
                    <div class="border-b border-slate-200 bg-white px-4 py-3">
                        <p class="text-sm font-medium text-gray-900">{{ __('admin.production.orchestration.workflow_'.$workflowKey) }}</p>
                        @if ((string) ($wf['description'] ?? '') !== '')
                            <p class="mt-1 text-xs text-gray-500">{{ (string) $wf['description'] }}</p>
                        @endif
                        <div class="mt-2 flex flex-wrap gap-3 text-xs text-gray-600">
                            <span>{{ __('admin.production.orchestration.graph_stat_ok', ['count' => (int) ($wfStats['completed'] ?? 0)]) }}</span>
                            <span>{{ __('admin.production.orchestration.graph_stat_fail', ['count' => (int) ($wfStats['failed'] ?? 0)]) }}</span>
                            <span>{{ __('admin.production.orchestration.graph_stat_pending', ['count' => (int) ($wfStats['pending'] ?? 0) + (int) ($wfStats['running'] ?? 0)]) }}</span>
                        </div>
                    </div>

                    <div class="px-4 py-5">
                        @if ((string) ($wf['visual_layout'] ?? 'linear') === 'pipeline_fork' && is_array($wf['visual_pipeline'] ?? null))
                            @include('admin.production._orchestration_graph_pipeline', ['pipeline' => $wf['visual_pipeline']])
                        @else
                            @include('admin.production._orchestration_graph_linear', ['steps' => $steps])
                        @endif
                    </div>
                </div>
            @endforeach
        </div>

        <p class="mt-3 text-[11px] text-gray-400">{{ __('admin.production.orchestration.graph_config_hint') }}</p>
    </div>

    <script>
        (function () {
            const root = document.getElementById('content-agent-orchestration-graph');
            if (!root) return;

            const tabs = root.querySelectorAll('[data-workflow-tab]');
            const panels = root.querySelectorAll('[data-workflow-panel]');

            function activate(workflowKey) {
                tabs.forEach((tab) => {
                    const active = tab.getAttribute('data-workflow-tab') === workflowKey;
                    tab.setAttribute('aria-selected', active ? 'true' : 'false');
                    tab.classList.toggle('bg-slate-800', active);
                    tab.classList.toggle('text-white', active);
                    tab.classList.toggle('ring-slate-800', active);
                    tab.classList.toggle('bg-white', !active);
                    tab.classList.toggle('text-slate-700', !active);
                    tab.classList.toggle('ring-slate-200', !active);
                });
                panels.forEach((panel) => {
                    panel.classList.toggle('hidden', panel.getAttribute('data-workflow-panel') !== workflowKey);
                });
            }

            tabs.forEach((tab) => {
                tab.addEventListener('click', () => activate(tab.getAttribute('data-workflow-tab')));
            });

            if (window.location.hash === '#content-agent-orchestration') {
                const defaultTab = root.querySelector('[data-workflow-tab][aria-selected="true"]');
                if (defaultTab) {
                    activate(defaultTab.getAttribute('data-workflow-tab'));
                }
            }
        })();
    </script>
@endif
