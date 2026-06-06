@php
    $steps = is_array($steps ?? null) ? $steps : [];
@endphp

<div class="mx-auto max-w-3xl space-y-2">
    @foreach ($steps as $step)
        @php
            $kind = (string) ($step['kind'] ?? '');
            $indent = (int) ($step['indent'] ?? 0);
            $marginClass = $indent > 0 ? 'ml-6 sm:ml-10' : '';
        @endphp

        @if ($kind === 'external')
            <div class="{{ $marginClass }} flex justify-center">
                <div class="flex w-full max-w-md items-center gap-3 rounded-lg border border-dashed border-emerald-300 bg-emerald-50 px-4 py-3">
                    <div class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-emerald-600 text-white">
                        <i data-lucide="{{ (string) ($step['icon'] ?? 'layers') }}" class="h-4 w-4"></i>
                    </div>
                    <div class="min-w-0">
                        <p class="text-xs font-semibold uppercase tracking-wide text-emerald-800">{{ __('admin.production.orchestration.layer_laravel') }}</p>
                        <p class="text-sm font-medium text-emerald-900">{{ __('admin.production.orchestration.external_'.$step['id']) }}</p>
                    </div>
                </div>
            </div>
        @elseif ($kind === 'arrow')
            <div class="{{ $marginClass }} flex flex-col items-center py-1">
                @if (! empty($step['label_key']))
                    <span class="mb-1 rounded bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800">
                        {{ __('admin.production.orchestration.edge_'.$step['label_key']) }}
                    </span>
                @endif
                <i data-lucide="arrow-down" class="h-4 w-4 text-slate-400"></i>
            </div>
        @elseif ($kind === 'node')
            <div class="{{ $marginClass }} flex justify-center">
                <div class="w-full max-w-md">
                    @include('admin.production._orchestration_graph_node', ['step' => $step])
                </div>
            </div>
        @endif
    @endforeach
</div>
