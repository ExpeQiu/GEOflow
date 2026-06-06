@php
    $layout = is_array($pipeline ?? null) ? $pipeline : [];
    $header = is_array($layout['header'] ?? null) ? $layout['header'] : [];
    $paths = is_array($layout['paths'] ?? null) ? $layout['paths'] : [];
    $shared = is_array($layout['shared'] ?? null) ? $layout['shared'] : [];
    $finalize = is_array($layout['finalize'] ?? null) ? $layout['finalize'] : [];
    $footer = is_array($layout['footer'] ?? null) ? $layout['footer'] : [];
    $fastPath = is_array($paths['fast'] ?? null) ? $paths['fast'] : [];
    $deepPath = is_array($paths['deep'] ?? null) ? $paths['deep'] : [];
@endphp

<div class="mx-auto max-w-4xl space-y-3">
    {{-- 阶段 1：入口 --}}
    <div class="rounded-lg border border-slate-200 bg-white p-4">
        <p class="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{{ __('admin.production.orchestration.phase_entry') }}</p>
        <div class="space-y-2">
            @foreach ($header as $step)
                @if (! is_array($step))
                    @continue
                @endif
                @if (($step['kind'] ?? '') === 'external')
                    <div class="flex w-full items-center gap-3 rounded-lg border border-dashed border-emerald-300 bg-emerald-50 px-4 py-3">
                        <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-emerald-600 text-white">
                            <i data-lucide="{{ (string) ($step['icon'] ?? 'database') }}" class="h-4 w-4"></i>
                        </div>
                        <div class="min-w-0">
                            <p class="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">{{ __('admin.production.orchestration.layer_laravel') }}</p>
                            <p class="text-sm font-medium text-emerald-900">{{ __('admin.production.orchestration.external_'.$step['id']) }}</p>
                        </div>
                    </div>
                @else
                    @include('admin.production._orchestration_graph_node', ['step' => $step])
                @endif
                @if (! $loop->last)
                    <div class="flex justify-center py-0.5"><i data-lucide="arrow-down" class="h-4 w-4 text-slate-300"></i></div>
                @endif
            @endforeach
        </div>
    </div>

    <div class="flex justify-center"><i data-lucide="git-fork" class="h-5 w-5 text-slate-400"></i></div>

    {{-- 阶段 2：双路径分叉 --}}
    <div class="rounded-lg border border-slate-200 bg-white p-4">
        <p class="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{{ __('admin.production.orchestration.phase_fork') }}</p>
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            @foreach (['fast' => $fastPath, 'deep' => $deepPath] as $pathKey => $path)
                @php
                    $tone = (string) ($path['tone'] ?? ($pathKey === 'fast' ? 'sky' : 'violet'));
                    $laneBorder = $pathKey === 'fast' ? 'border-sky-200 bg-sky-50/40' : 'border-violet-200 bg-violet-50/40';
                    $laneHeader = $pathKey === 'fast' ? 'bg-sky-600' : 'bg-violet-600';
                    $pathNodes = is_array($path['nodes'] ?? null) ? $path['nodes'] : [];
                @endphp
                <div class="rounded-lg border-2 {{ $laneBorder }} p-3">
                    <div class="mb-3 flex items-start gap-2">
                        <span class="inline-flex rounded-md px-2 py-1 text-xs font-bold text-white {{ $laneHeader }}">
                            {{ __('admin.production.orchestration.'.($path['label_key'] ?? 'path_'.$pathKey.'_title')) }}
                        </span>
                    </div>
                    <p class="mb-3 text-xs leading-relaxed text-gray-600">
                        {{ __('admin.production.orchestration.'.($path['desc_key'] ?? 'path_'.$pathKey.'_desc')) }}
                    </p>
                    <div class="space-y-2">
                        @foreach ($pathNodes as $node)
                            @include('admin.production._orchestration_graph_node', ['step' => $node, 'tone' => $tone])
                            @if (! $loop->last)
                                <div class="flex justify-center py-0.5"><i data-lucide="arrow-down" class="h-3.5 w-3.5 text-slate-300"></i></div>
                            @endif
                        @endforeach
                    </div>
                </div>
            @endforeach
        </div>
    </div>

    <div class="flex flex-col items-center gap-1 py-1">
        <span class="rounded-full bg-slate-200 px-3 py-0.5 text-[10px] font-semibold text-slate-700">{{ __('admin.production.orchestration.phase_merge') }}</span>
        <i data-lucide="arrow-down" class="h-4 w-4 text-slate-400"></i>
    </div>

    {{-- 阶段 3：共享编辑链 --}}
    <div class="rounded-lg border border-slate-200 bg-white p-4">
        <p class="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{{ __('admin.production.orchestration.phase_shared') }}</p>
        <div class="space-y-2">
            @foreach ($shared as $node)
                @include('admin.production._orchestration_graph_node', ['step' => $node])
                @if (! $loop->last)
                    <div class="flex justify-center py-0.5"><i data-lucide="arrow-down" class="h-4 w-4 text-slate-300"></i></div>
                @endif
            @endforeach
        </div>
    </div>

    <div class="flex justify-center"><i data-lucide="git-fork" class="h-5 w-5 text-slate-400"></i></div>

    {{-- 阶段 4：终审分叉 --}}
    <div class="rounded-lg border border-slate-200 bg-white p-4">
        <p class="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{{ __('admin.production.orchestration.phase_finalize') }}</p>
        <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
            @foreach (['fast', 'deep'] as $pathKey)
                @php
                    $pathFinalize = is_array($finalize[$pathKey] ?? null) ? $finalize[$pathKey] : [];
                    $laneBorder = $pathKey === 'fast' ? 'border-sky-200 bg-sky-50/30' : 'border-violet-200 bg-violet-50/30';
                    $titleKey = $pathKey === 'fast' ? 'path_fast_finalize' : 'path_deep_finalize';
                @endphp
                <div class="rounded-lg border {{ $laneBorder }} p-3">
                    <p class="mb-2 text-xs font-semibold text-gray-700">{{ __('admin.production.orchestration.'.$titleKey) }}</p>
                    <div class="space-y-2">
                        @forelse ($pathFinalize as $node)
                            @include('admin.production._orchestration_graph_node', ['step' => $node, 'tone' => $pathKey === 'fast' ? 'sky' : 'violet'])
                            @if (! $loop->last)
                                <div class="flex justify-center py-0.5"><i data-lucide="arrow-down" class="h-3.5 w-3.5 text-slate-300"></i></div>
                            @endif
                        @empty
                            <p class="text-xs text-gray-500">—</p>
                        @endforelse
                    </div>
                    @if ($pathKey === 'deep')
                        <p class="mt-2 text-[10px] text-violet-700">{{ __('admin.production.orchestration.path_deep_compliance_note') }}</p>
                    @endif
                </div>
            @endforeach
        </div>
    </div>

    <div class="flex justify-center py-1"><i data-lucide="arrow-down" class="h-4 w-4 text-slate-400"></i></div>

    {{-- 阶段 5：Laravel 出口 --}}
    <div class="rounded-lg border border-slate-200 bg-white p-4">
        <p class="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-500">{{ __('admin.production.orchestration.phase_exit') }}</p>
        @foreach ($footer as $step)
            @if (is_array($step) && ($step['kind'] ?? '') === 'external')
                <div class="flex w-full items-center gap-3 rounded-lg border border-dashed border-emerald-300 bg-emerald-50 px-4 py-3">
                    <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-emerald-600 text-white">
                        <i data-lucide="{{ (string) ($step['icon'] ?? 'send') }}" class="h-4 w-4"></i>
                    </div>
                    <div class="min-w-0">
                        <p class="text-[10px] font-semibold uppercase tracking-wide text-emerald-700">{{ __('admin.production.orchestration.layer_laravel') }}</p>
                        <p class="text-sm font-medium text-emerald-900">{{ __('admin.production.orchestration.external_'.$step['id']) }}</p>
                    </div>
                </div>
            @endif
        @endforeach
    </div>

    <div class="rounded-md border border-blue-100 bg-blue-50 px-4 py-3 text-xs leading-relaxed text-blue-800">
        {{ __('admin.production.orchestration.graph_pipeline_hint') }}
    </div>
</div>
