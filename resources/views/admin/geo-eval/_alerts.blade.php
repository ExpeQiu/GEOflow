<div class="mb-6 rounded-lg border border-amber-200 bg-white p-4">
    <div class="mb-3 flex items-center justify-between gap-3">
        <h2 class="text-sm font-semibold text-gray-900">{{ __('admin.geo_eval.recent_alerts_title') }}</h2>
        <a href="{{ route('admin.geo-eval.alerts') }}" class="text-xs font-medium text-amber-800 hover:underline">{{ __('admin.geo_eval.view_all_alerts') }}</a>
    </div>
    @forelse ($recentAlerts as $alert)
        <div class="mb-2 rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <span class="font-medium">{{ $alert['alert_type'] }}</span>
            — {{ $alert['message'] }}
            <span class="text-xs text-amber-700">({{ $alert['created_at'] }})</span>
        </div>
    @empty
        <p class="text-sm text-gray-400">{{ __('admin.geo_eval.no_alerts') }}</p>
    @endforelse
</div>
