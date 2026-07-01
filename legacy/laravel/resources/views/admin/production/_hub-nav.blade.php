@php
    $productionHubCurrentTab = $productionHubCurrentTab ?? ($tab ?? 'overview');
    $navItems = [
        ['type' => 'tab', 'key' => 'overview', 'label' => __('admin.production.tabs.overview')],
        ['type' => 'tab', 'key' => 'ai_config', 'label' => __('admin.production.tabs.ai_config')],
        ['type' => 'tab', 'key' => 'materials', 'label' => __('admin.production.tabs.materials')],
        ['type' => 'tab', 'key' => 'knowledge', 'label' => __('admin.production.tabs.knowledge')],
    ];
@endphp
<nav class="mb-6 flex flex-wrap gap-2 border-b border-gray-200 pb-3">
    @foreach ($navItems as $item)
        @php
            $isActive = $productionHubCurrentTab === $item['key'];
            $activeClass = 'bg-emerald-100 text-emerald-800';
            $inactiveClass = 'text-gray-600 hover:bg-gray-50';
        @endphp
        <a href="{{ route('admin.production.index', ['tab' => $item['key']]) }}"
           class="rounded-md px-3 py-2 text-sm font-medium {{ $isActive ? $activeClass : $inactiveClass }}">
            {{ $item['label'] }}
        </a>
    @endforeach
</nav>
