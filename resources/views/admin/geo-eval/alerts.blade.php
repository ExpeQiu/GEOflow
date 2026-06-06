@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
                <h1 class="text-2xl font-bold text-gray-900">{{ __('admin.geo_eval.alerts_page_title') }}</h1>
                <p class="mt-1 text-sm text-gray-500">{{ __('admin.geo_eval.alerts_page_subtitle') }}</p>
            </div>
            <a href="{{ route('admin.geo-eval.diagnostics') }}" class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                {{ __('admin.geo_eval.open_diagnostics') }}
            </a>
        </div>

        <form method="GET" action="{{ route('admin.geo-eval.alerts') }}" class="mb-6 flex flex-wrap items-end gap-4 rounded-lg border border-gray-200 bg-white p-4">
            <div>
                <label for="alert_type" class="block text-xs font-medium text-gray-500">{{ __('admin.geo_eval.filter_alert_type') }}</label>
                <select name="alert_type" id="alert_type" class="mt-1 rounded-md border-gray-300 text-sm shadow-sm focus:border-cyan-500 focus:ring-cyan-500">
                    <option value="">{{ __('admin.geo_eval.filter_all') }}</option>
                    @foreach ($alertTypes as $type)
                        <option value="{{ $type }}" @selected(($filters['alert_type'] ?? '') === $type)>{{ $type }}</option>
                    @endforeach
                </select>
            </div>
            <div>
                <label for="severity" class="block text-xs font-medium text-gray-500">{{ __('admin.geo_eval.filter_severity') }}</label>
                <select name="severity" id="severity" class="mt-1 rounded-md border-gray-300 text-sm shadow-sm focus:border-cyan-500 focus:ring-cyan-500">
                    <option value="">{{ __('admin.geo_eval.filter_all') }}</option>
                    @foreach ($severities as $level)
                        <option value="{{ $level }}" @selected(($filters['severity'] ?? '') === $level)>{{ $level }}</option>
                    @endforeach
                </select>
            </div>
            <button type="submit" class="rounded-md bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-700">
                {{ __('admin.geo_eval.filter_apply') }}
            </button>
        </form>

        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">ID</th>
                        <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">{{ __('admin.geo_eval.filter_alert_type') }}</th>
                        <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">{{ __('admin.geo_eval.filter_severity') }}</th>
                        <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">{{ __('admin.geo_eval.alerts_message') }}</th>
                        <th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wide text-gray-500">{{ __('admin.geo_eval.alerts_created_at') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100 bg-white">
                    @forelse ($alerts as $alert)
                        <tr class="hover:bg-gray-50">
                            <td class="px-4 py-3 text-gray-700">#{{ (int) $alert->id }}</td>
                            <td class="px-4 py-3 font-medium text-gray-900">{{ $alert->alert_type }}</td>
                            <td class="px-4 py-3">
                                <span class="inline-flex rounded-full px-2 py-0.5 text-xs font-medium {{ $alert->severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-amber-100 text-amber-800' }}">
                                    {{ $alert->severity }}
                                </span>
                            </td>
                            <td class="px-4 py-3 text-gray-700">{{ $alert->message }}</td>
                            <td class="px-4 py-3 whitespace-nowrap text-gray-500">{{ optional($alert->created_at)->format('Y-m-d H:i:s') }}</td>
                        </tr>
                    @empty
                        <tr>
                            <td colspan="5" class="px-4 py-8 text-center text-gray-400">{{ __('admin.geo_eval.no_alerts') }}</td>
                        </tr>
                    @endforelse
                </tbody>
            </table>
        </div>

        @if (method_exists($alerts, 'links'))
            <div class="mt-4">
                {{ $alerts->links() }}
            </div>
        @endif
    </div>
@endsection
