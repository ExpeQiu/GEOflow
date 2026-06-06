@php
    $nodeType = (string) ($step['type'] ?? 'rule');
    $isAgent = $nodeType === 'agent';
    $typeLabel = $isAgent
        ? __('admin.production.orchestration.node_agent')
        : __('admin.production.orchestration.node_rule');
    $tone = (string) ($tone ?? 'default');
    $borderClass = match ($tone) {
        'sky' => 'border-sky-200',
        'violet' => 'border-violet-200',
        default => $isAgent ? 'border-violet-200' : 'border-slate-200',
    };
    $iconBgClass = match ($tone) {
        'sky' => 'bg-sky-600',
        'violet' => 'bg-violet-600',
        default => $isAgent ? 'bg-violet-600' : 'bg-slate-600',
    };
    $badgeClass = match ($tone) {
        'sky' => 'bg-sky-100 text-sky-700',
        'violet' => 'bg-violet-100 text-violet-700',
        default => $isAgent ? 'bg-violet-100 text-violet-700' : 'bg-slate-100 text-slate-600',
    };
@endphp

<div class="w-full rounded-lg border bg-white px-3 py-2.5 shadow-sm {{ $borderClass }}">
    <div class="flex items-start gap-2.5">
        <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-white {{ $iconBgClass }}">
            <i data-lucide="{{ $isAgent ? 'bot' : 'git-branch' }}" class="h-3.5 w-3.5"></i>
        </div>
        <div class="min-w-0 flex-1">
            <div class="flex flex-wrap items-center gap-1.5">
                <p class="text-sm font-semibold text-gray-900">{{ (string) ($step['agent_label'] ?? $step['id']) }}</p>
                <span class="rounded px-1.5 py-0.5 text-[10px] font-medium {{ $badgeClass }}">{{ $typeLabel }}</span>
            </div>
            <p class="mt-0.5 font-mono text-[10px] text-gray-400">{{ (string) ($step['id'] ?? '') }}</p>
        </div>
    </div>
</div>
