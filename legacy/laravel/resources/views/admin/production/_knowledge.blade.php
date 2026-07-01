@php
    $knowledgeBases = (int) ($stats['knowledge_bases'] ?? 0);
    $knowledgeChunks = (int) ($stats['knowledge_chunks'] ?? 0);
    $vectorizedChunks = (int) ($stats['vectorized_chunks'] ?? 0);
    $unvectorizedChunks = (int) ($stats['unvectorized_chunks'] ?? 0);
    $activeEmbeddingModels = (int) ($stats['active_embedding_models'] ?? 0);
    $vectorProgress = $knowledgeChunks > 0 ? min(100, (int) round(($vectorizedChunks / max(1, $knowledgeChunks)) * 100)) : 0;
    $knowledgeHealth = $knowledgeBases <= 0
        ? 'empty'
        : ($activeEmbeddingModels <= 0 ? 'no_embedding' : ($unvectorizedChunks > 0 ? 'needs_vectorization' : 'ready'));
    $knowledgeHealthStyles = [
        'ready' => 'bg-emerald-50 text-emerald-700 ring-emerald-200',
        'needs_vectorization' => 'bg-amber-50 text-amber-700 ring-amber-200',
        'no_embedding' => 'bg-red-50 text-red-700 ring-red-200',
        'empty' => 'bg-slate-100 text-slate-700 ring-slate-200',
    ];
    $strategyLabels = [
        'rule' => __('admin.materials.chunk_strategy_rule'),
        'auto' => __('admin.materials.chunk_strategy_auto'),
        'semantic_llm' => __('admin.materials.chunk_strategy_semantic_llm'),
    ];
    $orch = is_array($orchestrationStats ?? null) ? $orchestrationStats : [];
    $orchBackend = (string) ($orch['backend'] ?? 'internal');
    $orchKnowledgePending = (int) ($orch['knowledge_pending'] ?? 0);
    $orchKnowledgeRecent = is_array($orch['knowledge_recent'] ?? null) ? $orch['knowledge_recent'] : [];
@endphp

<section class="mb-8 overflow-hidden rounded-lg border border-orange-100 bg-white shadow">
    <div class="border-b border-orange-100 bg-orange-50/50 px-6 py-5 lg:px-8">
        <div class="space-y-5">
            <div class="flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
                <span class="inline-flex items-center rounded-full bg-white px-3 py-1 text-sm font-semibold text-orange-700 ring-1 ring-orange-200">
                    <i data-lucide="brain" class="mr-2 h-4 w-4"></i>
                    {{ __('admin.materials.knowledge_hub_label') }}
                </span>
                <div class="grid w-full grid-cols-1 gap-3 sm:w-auto sm:grid-cols-3 lg:min-w-[560px]">
                    <a href="{{ route('admin.knowledge-bases.create') }}" class="inline-flex items-center justify-center whitespace-nowrap rounded-md bg-orange-600 px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-orange-700">
                        <i data-lucide="plus" class="mr-2 h-4 w-4"></i>
                        {{ __('admin.materials.knowledge_hub_create') }}
                    </a>
                    <a href="{{ route('admin.knowledge-bases.index') }}" class="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-orange-200 bg-white px-4 py-2 text-sm font-semibold text-orange-700 hover:bg-orange-50">
                        <i data-lucide="database" class="mr-2 h-4 w-4"></i>
                        {{ __('admin.materials.manage_knowledge_bases') }}
                    </a>
                    <a href="{{ route('admin.ai-models.index') }}" class="inline-flex items-center justify-center whitespace-nowrap rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
                        <i data-lucide="settings" class="mr-2 h-4 w-4"></i>
                        {{ __('admin.materials.knowledge_hub_vector_config') }}
                    </a>
                </div>
            </div>
            <div>
                <h2 class="text-2xl font-bold tracking-tight text-gray-900">{{ __('admin.materials.knowledge_hub_title') }}</h2>
                <p class="mt-2 text-sm leading-6 text-gray-600">{{ __('admin.materials.knowledge_hub_desc') }}</p>
            </div>
        </div>
    </div>

    <div class="grid grid-cols-1 divide-y divide-gray-200 lg:grid-cols-[minmax(0,1.35fr)_minmax(360px,0.65fr)] lg:divide-x lg:divide-y-0">
        <div class="px-6 py-6 lg:px-8">
            <div class="grid grid-cols-2 gap-x-8 gap-y-6 lg:grid-cols-4">
                <div>
                    <div class="text-sm font-medium text-gray-500">{{ __('admin.materials.knowledge_base_count') }}</div>
                    <div class="mt-2 text-3xl font-bold text-gray-900">{{ $knowledgeBases }}</div>
                </div>
                <div>
                    <div class="text-sm font-medium text-gray-500">{{ __('admin.materials.knowledge_hub_chunks') }}</div>
                    <div class="mt-2 text-3xl font-bold text-gray-900">{{ $knowledgeChunks }}</div>
                </div>
                <div>
                    <div class="text-sm font-medium text-gray-500">{{ __('admin.materials.knowledge_hub_vectorized') }}</div>
                    <div class="mt-2 text-3xl font-bold text-emerald-700">{{ $vectorizedChunks }}</div>
                </div>
                <div>
                    <div class="text-sm font-medium text-gray-500">{{ __('admin.materials.knowledge_hub_used_by_tasks') }}</div>
                    <div class="mt-2 text-3xl font-bold text-gray-900">{{ (int) $stats['knowledge_usage_count'] }}</div>
                </div>
            </div>

            <div class="mt-7">
                <div class="flex items-center justify-between text-sm">
                    <span class="font-medium text-gray-700">{{ __('admin.materials.knowledge_hub_vector_progress') }}</span>
                    <span class="font-semibold text-gray-900">{{ $vectorizedChunks }} / {{ $knowledgeChunks }}</span>
                </div>
                <div class="mt-2 h-2 overflow-hidden rounded-full bg-gray-100">
                    <div class="h-2 rounded-full bg-orange-500" style="width: {{ $vectorProgress }}%"></div>
                </div>
            </div>

            <div class="mt-7 grid grid-cols-1 gap-4 border-t border-gray-100 pt-6 md:grid-cols-5">
                @foreach ([
                    ['icon' => 'file-input', 'title' => __('admin.materials.knowledge_flow_ingest'), 'desc' => __('admin.materials.knowledge_flow_ingest_desc')],
                    ['icon' => 'scissors', 'title' => __('admin.materials.knowledge_flow_chunk'), 'desc' => __('admin.materials.knowledge_flow_chunk_desc')],
                    ['icon' => 'scan-search', 'title' => __('admin.materials.knowledge_flow_vector'), 'desc' => __('admin.materials.knowledge_flow_vector_desc')],
                    ['icon' => 'search-check', 'title' => __('admin.materials.knowledge_flow_recall'), 'desc' => __('admin.materials.knowledge_flow_recall_desc')],
                    ['icon' => 'wand-sparkles', 'title' => __('admin.materials.knowledge_flow_generate'), 'desc' => __('admin.materials.knowledge_flow_generate_desc')],
                ] as $step)
                    <div class="min-w-0">
                        <div class="flex h-10 w-10 items-center justify-center rounded-md bg-orange-50 text-orange-600">
                            <i data-lucide="{{ $step['icon'] }}" class="h-5 w-5"></i>
                        </div>
                        <div class="mt-3 text-sm font-semibold text-gray-900">{{ $step['title'] }}</div>
                        <p class="mt-1 text-xs leading-5 text-gray-500">{{ $step['desc'] }}</p>
                    </div>
                @endforeach
            </div>
        </div>

        <div class="px-6 py-6 lg:px-8">
            <div class="inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ring-1 {{ $knowledgeHealthStyles[$knowledgeHealth] ?? $knowledgeHealthStyles['empty'] }}">
                <i data-lucide="activity" class="mr-2 h-4 w-4"></i>
                {{ __('admin.materials.knowledge_health_'.$knowledgeHealth) }}
            </div>

            @if ($orchKnowledgePending > 0)
                <div class="mt-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    <i data-lucide="loader" class="mr-2 inline h-4 w-4"></i>
                    {{ __('admin.production.orchestration.knowledge_chunking_active', ['count' => $orchKnowledgePending]) }}
                </div>
            @endif

            @if ($orchKnowledgeRecent !== [])
                <div class="mt-4 rounded-md border border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-700">
                    <p class="font-semibold text-slate-900">{{ __('admin.production.orchestration.recent_knowledge_requests') }}</p>
                    <ul class="mt-2 space-y-1">
                        @foreach ($orchKnowledgeRecent as $requestRow)
                            <li>
                                <span class="font-mono">{{ \Illuminate\Support\Str::limit((string) ($requestRow['request_id'] ?? ''), 12, '') }}</span>
                                · {{ (string) ($requestRow['status'] ?? '') }}
                                @if ((string) ($requestRow['error_message'] ?? '') !== '')
                                    · {{ \Illuminate\Support\Str::limit((string) $requestRow['error_message'], 40) }}
                                @endif
                            </li>
                        @endforeach
                    </ul>
                </div>
            @endif

            <dl class="mt-6 space-y-4 text-sm">
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.production.orchestration.backend') }}</dt>
                    <dd class="text-right font-semibold text-gray-900">{{ __('admin.production.orchestration.backend_'.$orchBackend) }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_embedding_model') }}</dt>
                    <dd class="max-w-[220px] text-right font-semibold text-gray-900">{{ (string) ($stats['default_embedding_model'] ?? '') !== '' ? (string) $stats['default_embedding_model'] : __('admin.materials.knowledge_hub_embedding_missing') }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_chunk_strategy') }}</dt>
                    <dd class="text-right font-semibold text-gray-900">{{ $strategyLabels[(string) ($stats['chunk_strategy'] ?? 'rule')] ?? $strategyLabels['rule'] }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_retrieval_mode') }}</dt>
                    <dd class="text-right font-semibold text-gray-900">{{ __('admin.materials.knowledge_hub_retrieval_hybrid') }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_metadata_ready') }}</dt>
                    <dd class="text-right font-semibold text-gray-900">{{ (int) ($stats['metadata_ready_count'] ?? 0) }} / {{ $knowledgeBases }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_reviewed') }}</dt>
                    <dd class="text-right font-semibold text-gray-900">{{ (int) ($stats['reviewed_knowledge_bases'] ?? 0) }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_high_risk_pending') }}</dt>
                    <dd class="text-right font-semibold {{ (int) ($stats['high_risk_pending_count'] ?? 0) > 0 ? 'text-red-700' : 'text-gray-900' }}">{{ (int) ($stats['high_risk_pending_count'] ?? 0) }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_unvectorized') }}</dt>
                    <dd class="text-right font-semibold {{ $unvectorizedChunks > 0 ? 'text-amber-700' : 'text-gray-900' }}">{{ $unvectorizedChunks }}</dd>
                </div>
                <div class="flex items-start justify-between gap-4">
                    <dt class="text-gray-500">{{ __('admin.materials.knowledge_hub_latest_update') }}</dt>
                    <dd class="text-right font-semibold text-gray-900">{{ (string) ($stats['latest_knowledge_updated_at'] ?? '') !== '' ? (string) $stats['latest_knowledge_updated_at'] : __('admin.materials.knowledge_hub_never_updated') }}</dd>
                </div>
            </dl>

            <div class="mt-6 grid grid-cols-1 gap-3">
                <a href="{{ route('admin.knowledge-bases.index') }}" class="inline-flex items-center justify-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-gray-50">
                    <i data-lucide="database" class="mr-2 h-4 w-4"></i>
                    {{ __('admin.materials.knowledge_hub_manage') }}
                </a>
                <a href="{{ route('admin.knowledge-bases.rag-sandbox') }}" class="inline-flex items-center justify-center rounded-md border border-orange-200 bg-orange-50 px-4 py-2 text-sm font-semibold text-orange-700 hover:bg-orange-100">
                    <i data-lucide="search" class="mr-2 h-4 w-4"></i>
                    {{ __('admin.knowledge_bases.rag_sandbox_title') }}
                </a>
                <a href="{{ route('admin.url-import') }}" class="inline-flex items-center justify-center rounded-md border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-100">
                    <i data-lucide="globe" class="mr-2 h-4 w-4"></i>
                    {{ __('admin.materials.knowledge_hub_import_from_url') }}
                </a>
            </div>
        </div>
    </div>
</section>
