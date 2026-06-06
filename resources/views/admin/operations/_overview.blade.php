@php
    $stats = $stats ?? [];
@endphp
<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
    <div class="rounded-lg border border-blue-200 bg-blue-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-blue-700">{{ __('admin.operations.tabs.tasks') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ (int) ($stats['total_tasks'] ?? 0) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ __('admin.operations.overview.active_tasks', ['count' => (int) ($stats['active_tasks'] ?? 0)]) }}</p>
        <a href="{{ route('admin.operations.index', ['tab' => 'tasks']) }}" class="mt-3 inline-block text-sm text-blue-800 hover:underline">{{ __('admin.operations.view_detail') }}</a>
    </div>
    <div class="rounded-lg border border-emerald-200 bg-emerald-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-emerald-700">{{ __('admin.operations.tabs.articles') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ (int) ($stats['total_articles'] ?? 0) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ __('admin.operations.overview.pending_review', ['count' => (int) ($stats['pending_review'] ?? 0)]) }}</p>
        <a href="{{ route('admin.operations.index', ['tab' => 'articles']) }}" class="mt-3 inline-block text-sm text-emerald-800 hover:underline">{{ __('admin.operations.view_detail') }}</a>
    </div>
    <div class="rounded-lg border border-violet-200 bg-violet-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-violet-700">{{ __('admin.operations.tabs.distribution') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ (int) ($stats['channels_active'] ?? 0) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ __('admin.operations.overview.distribution_pending', ['count' => (int) ($stats['distribution_pending'] ?? 0)]) }}</p>
        <a href="{{ route('admin.operations.index', ['tab' => 'distribution']) }}" class="mt-3 inline-block text-sm text-violet-800 hover:underline">{{ __('admin.operations.view_detail') }}</a>
    </div>
</div>

<div class="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
    <div class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 class="text-sm font-semibold text-gray-900">{{ __('admin.operations.overview.queue_health') }}</h2>
        <dl class="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
                <dt class="text-gray-500">{{ __('admin.operations.overview.running_jobs') }}</dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">{{ (int) ($stats['running_jobs'] ?? 0) }}</dd>
            </div>
            <div>
                <dt class="text-gray-500">{{ __('admin.operations.overview.pending_jobs') }}</dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">{{ (int) ($stats['pending_jobs'] ?? 0) }}</dd>
            </div>
            <div>
                <dt class="text-gray-500">{{ __('admin.operations.overview.failed_jobs') }}</dt>
                <dd class="mt-1 text-xl font-semibold text-red-600">{{ (int) ($stats['failed_jobs'] ?? 0) }}</dd>
            </div>
            <div>
                <dt class="text-gray-500">{{ __('admin.operations.overview.published_articles') }}</dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">{{ (int) ($stats['published_articles'] ?? 0) }}</dd>
            </div>
        </dl>
    </div>
    <div class="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h2 class="text-sm font-semibold text-gray-900">{{ __('admin.operations.overview.distribution_health') }}</h2>
        <dl class="mt-4 grid grid-cols-2 gap-4 text-sm">
            <div>
                <dt class="text-gray-500">{{ __('admin.operations.overview.channels_total') }}</dt>
                <dd class="mt-1 text-xl font-semibold text-gray-900">{{ (int) ($stats['channels_total'] ?? 0) }}</dd>
            </div>
            <div>
                <dt class="text-gray-500">{{ __('admin.operations.overview.distribution_failed') }}</dt>
                <dd class="mt-1 text-xl font-semibold text-red-600">{{ (int) ($stats['distribution_failed'] ?? 0) }}</dd>
            </div>
        </dl>
        <div class="mt-4 flex flex-wrap gap-2">
            <a href="{{ route('admin.tasks.create') }}" class="inline-flex items-center rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700">{{ __('admin.button.create_task') }}</a>
            <a href="{{ route('admin.distribution.jobs') }}" class="inline-flex items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">{{ __('admin.distribution.button.jobs') }}</a>
        </div>
    </div>
</div>
