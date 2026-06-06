@php
    $operationsHubCurrentTab = $operationsHubCurrentTab ?? ($tab ?? 'overview');
    $navItems = [
        ['key' => 'overview', 'label' => __('admin.operations.tabs.overview')],
        ['key' => 'tasks', 'label' => __('admin.operations.tabs.tasks')],
        ['key' => 'articles', 'label' => __('admin.operations.tabs.articles')],
        ['key' => 'distribution', 'label' => __('admin.operations.tabs.distribution')],
    ];
@endphp
<nav class="mb-6 flex flex-wrap gap-2 border-b border-gray-200 pb-3">
    @foreach ($navItems as $item)
        @php
            $isActive = $operationsHubCurrentTab === $item['key'];
            $activeClass = 'bg-blue-100 text-blue-800';
            $inactiveClass = 'text-gray-600 hover:bg-gray-50';
        @endphp
        <a href="{{ route('admin.operations.index', ['tab' => $item['key']]) }}"
           class="rounded-md px-3 py-2 text-sm font-medium {{ $isActive ? $activeClass : $inactiveClass }}">
            {{ $item['label'] }}
        </a>
    @endforeach
</nav>
