<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
    <div class="rounded-lg border border-gray-200 bg-white p-5">
        <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.strategy.web_intel.add_source') }}</h2>
        <form method="post" action="{{ route('admin.strategy.web-intel.sources.store') }}" class="mt-4 space-y-3">
            @csrf
            <input type="url" name="url" required placeholder="https://" class="block w-full rounded-md border-gray-300 text-sm">
            <select name="label" class="block w-full rounded-md border-gray-300 text-sm">
                <option value="self">{{ __('admin.strategy.web_intel.label_self') }}</option>
                <option value="competitor">{{ __('admin.strategy.web_intel.label_competitor') }}</option>
                <option value="authority">{{ __('admin.strategy.web_intel.label_authority') }}</option>
            </select>
            <button type="submit" class="rounded-md bg-indigo-600 px-4 py-2 text-sm text-white hover:bg-indigo-700">{{ __('admin.strategy.web_intel.save') }}</button>
        </form>

        <form method="post" action="{{ route('admin.strategy.web-intel.reports.compose') }}" class="mt-6 space-y-3 border-t border-gray-100 pt-4">
            @csrf
            <h3 class="text-sm font-semibold text-gray-800">{{ __('admin.strategy.web_intel.compose_report') }}</h3>
            <select name="self_source_id" class="block w-full rounded-md border-gray-300 text-sm">
                <option value="">{{ __('admin.strategy.web_intel.self_optional') }}</option>
                @foreach ($webSources->where('label', 'self') as $src)
                    <option value="{{ $src->id }}">{{ Str::limit($src->url, 60) }}</option>
                @endforeach
            </select>
            <select name="competitor_source_ids[]" multiple class="block w-full rounded-md border-gray-300 text-sm" size="4">
                @foreach ($webSources->whereIn('label', ['competitor', 'authority']) as $src)
                    <option value="{{ $src->id }}">{{ Str::limit($src->url, 60) }}</option>
                @endforeach
            </select>
            <input type="text" name="template_name" placeholder="{{ __('admin.strategy.web_intel.template_name') }}" class="block w-full rounded-md border-gray-300 text-sm">
            <button type="submit" class="rounded-md border border-indigo-300 px-4 py-2 text-sm text-indigo-800 hover:bg-indigo-50">{{ __('admin.strategy.web_intel.generate') }}</button>
        </form>
    </div>

    <div class="rounded-lg border border-gray-200 bg-white p-5">
        <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.strategy.web_intel.sources_list') }}</h2>
        <ul class="mt-4 divide-y divide-gray-100">
            @forelse ($webSources as $src)
                @php
                    $features = is_array($src->features_json) ? $src->features_json : [];
                    $signals = is_array($features['adoption_signals'] ?? null) ? $features['adoption_signals'] : [];
                @endphp
                <li class="py-3 text-sm">
                    <p class="font-medium text-gray-900">{{ Str::limit($src->url, 80) }}</p>
                    <p class="mt-1 text-xs text-gray-500">
                        {{ $src->label }} · {{ $src->fetch_status }}
                        @if (!empty($signals['ai_bot_hits']))
                            · AI {{ $signals['ai_bot_hits'] }} hits
                        @endif
                    </p>
                    <div class="mt-2 flex gap-3">
                        <form method="post" action="{{ route('admin.strategy.web-intel.sources.refresh', ['sourceId' => $src->id]) }}">
                            @csrf
                            <button type="submit" class="text-xs text-blue-600 hover:underline">{{ __('admin.strategy.web_intel.refresh') }}</button>
                        </form>
                        <form method="post" action="{{ route('admin.strategy.web-intel.sources.destroy', ['sourceId' => $src->id]) }}" onsubmit="return confirm('{{ __('admin.strategy.web_intel.confirm_delete') }}')">
                            @csrf
                            @method('DELETE')
                            <button type="submit" class="text-xs text-red-600 hover:underline">{{ __('admin.strategy.monitor.delete') }}</button>
                        </form>
                    </div>
                </li>
            @empty
                <li class="py-4 text-gray-400">{{ __('admin.strategy.web_intel.empty') }}</li>
            @endforelse
        </ul>

        @if ($webReports->isNotEmpty())
            <h3 class="mt-6 text-sm font-semibold">{{ __('admin.strategy.web_intel.reports') }}</h3>
            <ul class="mt-2 space-y-2 text-sm">
                @foreach ($webReports as $report)
                    <li>
                        #{{ $report->id }}
                        @if ($report->insight_template_id)
                            · <a href="{{ route('admin.insight-templates.show', ['templateId' => $report->insight_template_id]) }}" class="text-indigo-600 hover:underline">{{ __('admin.nav.insight_templates') }} #{{ $report->insight_template_id }}</a>
                        @endif
                    </li>
                @endforeach
            </ul>
        @endif
    </div>
</div>
