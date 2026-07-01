@php($m = is_array($techBrandMetrics ?? null) ? $techBrandMetrics : [])
<div class="mt-6 rounded-lg border border-slate-200 bg-white p-5">
    <h2 class="text-base font-semibold text-gray-900">{{ __('admin.strategy.tech_brand_title') }}</h2>
    <p class="mt-1 text-sm text-gray-500">{{ __('admin.strategy.wiki_pv_note') }}</p>
    <div class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div class="rounded-md border border-violet-100 bg-violet-50/50 p-4">
            <p class="text-xs font-medium text-violet-700">{{ __('admin.strategy.p0_coverage') }}</p>
            <p class="mt-1 text-2xl font-semibold">{{ $m['p0_ready'] ?? 0 }}/{{ $m['p0_total'] ?? 0 }}</p>
            <p class="text-xs text-violet-600">{{ $m['p0_coverage_pct'] ?? 0 }}%</p>
        </div>
        <div class="rounded-md border border-emerald-100 bg-emerald-50/50 p-4">
            <p class="text-xs font-medium text-emerald-700">{{ __('admin.strategy.wiki_compliance') }}</p>
            <p class="mt-1 text-2xl font-semibold">{{ $m['wiki_compliance_pct'] ?? 0 }}%</p>
            <p class="text-xs text-emerald-600">{{ $m['wiki_articles'] ?? 0 }} Wiki 页</p>
        </div>
        <div class="rounded-md border border-blue-100 bg-blue-50/50 p-4">
            <p class="text-xs font-medium text-blue-700">{{ __('admin.strategy.gweb_sync_rate') }}</p>
            <p class="mt-1 text-2xl font-semibold">{{ $m['gweb_sync_rate_pct'] ?? 0 }}%</p>
            <p class="text-xs text-blue-600">{{ $m['gweb_sync_success'] ?? 0 }}/{{ $m['gweb_sync_total'] ?? 0 }}</p>
        </div>
        <div class="rounded-md border border-amber-100 bg-amber-50/50 p-4">
            <p class="text-xs font-medium text-amber-700">{{ __('admin.tech_assets.page_title') }}</p>
            <p class="mt-1 text-2xl font-semibold">{{ $m['total_assets'] ?? 0 }}</p>
            <a href="{{ route('admin.tech-assets.index') }}" class="text-xs text-amber-800 hover:underline">{{ __('admin.strategy.view_detail') }}</a>
        </div>
    </div>
    @if (!empty($m['gweb_analytics_url']))
        <p class="mt-4 text-sm">
            <a href="{{ $m['gweb_analytics_url'] }}" target="_blank" rel="noopener" class="text-blue-600 hover:underline">{{ __('admin.strategy.gweb_analytics_link') }}</a>
        </p>
    @endif
    <div class="mt-4 flex flex-wrap gap-3 border-t border-slate-100 pt-4">
        <span class="text-xs font-semibold uppercase text-gray-500">{{ __('admin.strategy.loop_actions_title') }}</span>
        <a href="{{ route('admin.tasks.create', ['content_format' => 'wiki_mdx', 'publish_scope' => 'distribution_only']) }}" class="text-sm text-blue-600 hover:underline">{{ __('admin.strategy.create_wiki_task') }}</a>
        <a href="{{ route('admin.tech-assets.index') }}" class="text-sm text-blue-600 hover:underline">{{ __('admin.nav.tech_assets') }}</a>
        @if ((int) ($m['needs_update_assets'] ?? 0) > 0)
            <span class="text-sm text-amber-700">{{ __('admin.strategy.assets_need_update', ['count' => (int) $m['needs_update_assets']]) }}</span>
        @endif
    </div>
</div>
