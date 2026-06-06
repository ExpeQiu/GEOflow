@php
    $materialLibraryCount = (int) ($stats['keyword_libraries'] ?? 0)
        + (int) ($stats['title_libraries'] ?? 0)
        + (int) ($stats['image_libraries'] ?? 0)
        + (int) ($stats['authors'] ?? 0);
@endphp

<div class="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
    <div class="rounded-lg border border-emerald-200 bg-emerald-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-emerald-700">{{ __('admin.production.tabs.knowledge') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ (int) ($stats['knowledge_bases'] ?? 0) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ __('admin.materials.knowledge_hub_chunks') }}: {{ (int) ($stats['knowledge_chunks'] ?? 0) }}</p>
        <a href="{{ route('admin.production.index', ['tab' => 'knowledge']) }}" class="mt-3 inline-block text-sm text-emerald-800 hover:underline">{{ __('admin.production.view_detail') }}</a>
    </div>
    <div class="rounded-lg border border-blue-200 bg-blue-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-blue-700">{{ __('admin.production.tabs.materials') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ $materialLibraryCount }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ __('admin.materials.keyword_total_count') }}: {{ (int) ($stats['total_keywords'] ?? 0) }}</p>
        <a href="{{ route('admin.production.index', ['tab' => 'materials']) }}" class="mt-3 inline-block text-sm text-blue-800 hover:underline">{{ __('admin.production.view_detail') }}</a>
    </div>
    <div class="rounded-lg border border-violet-200 bg-violet-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-violet-700">{{ __('admin.production.tabs.ai_config') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ (int) ($aiStats['model_count'] ?? 0) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ __('admin.ai_configurator.prompt_templates') }}: {{ (int) ($aiStats['prompt_count'] ?? 0) }}</p>
        <a href="{{ route('admin.production.index', ['tab' => 'ai_config']) }}" class="mt-3 inline-block text-sm text-violet-800 hover:underline">{{ __('admin.production.view_detail') }}</a>
    </div>
    <div class="rounded-lg border border-amber-200 bg-amber-50/60 p-5">
        <p class="text-xs font-semibold uppercase text-amber-700">{{ __('admin.materials.knowledge_hub_vectorized') }}</p>
        <p class="mt-2 text-2xl font-semibold">{{ (int) ($stats['vectorized_chunks'] ?? 0) }}</p>
        <p class="mt-1 text-xs text-gray-500">{{ (int) ($stats['unvectorized_chunks'] ?? 0) }} {{ __('admin.materials.knowledge_hub_unvectorized') }}</p>
        <a href="{{ route('admin.knowledge-bases.index') }}" class="mt-3 inline-block text-sm text-amber-800 hover:underline">{{ __('admin.materials.manage_knowledge_bases') }}</a>
    </div>
</div>
