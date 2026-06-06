@php
    $strategyHubCurrentTab = $strategyHubCurrentTab ?? ($tab ?? 'overview');
    $navItems = [
        ['type' => 'tab', 'key' => 'overview', 'label' => __('admin.strategy.tabs.overview')],
        ['type' => 'tab', 'key' => 'monitor', 'label' => __('admin.strategy.tabs.monitor')],
        ['type' => 'link', 'key' => 'insight-templates', 'route' => 'admin.insight-templates.index', 'label' => __('admin.nav.insight_templates')],
        ['type' => 'tab', 'key' => 'web-intel', 'label' => __('admin.strategy.tabs.web_intel')],
        ['type' => 'tab', 'key' => 'simulator', 'label' => __('admin.strategy.tabs.simulator')],
        ['type' => 'tab', 'key' => 'analytics', 'label' => __('admin.strategy.tabs.analytics')],
    ];
@endphp
<nav class="mb-6 flex flex-wrap gap-2 border-b border-gray-200 pb-3">
    @foreach ($navItems as $item)
        @php
            $isActive = $strategyHubCurrentTab === $item['key'];
            $activeClass = 'bg-violet-100 text-violet-800';
            $inactiveClass = 'text-gray-600 hover:bg-gray-50';
        @endphp
        @if ($item['type'] === 'link')
            <a href="{{ route($item['route']) }}"
               class="rounded-md px-3 py-2 text-sm font-medium {{ $isActive ? $activeClass : $inactiveClass }}">
                {{ $item['label'] }}
            </a>
        @else
            <a href="{{ route('admin.strategy.index', ['tab' => $item['key']]) }}"
               class="rounded-md px-3 py-2 text-sm font-medium {{ $isActive ? $activeClass : $inactiveClass }}">
                {{ $item['label'] }}
            </a>
        @endif
    @endforeach
</nav>
