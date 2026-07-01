@php
    $foundationCards = [
        [
            'title' => __('admin.materials.keyword_manage_title'),
            'summary' => __('admin.materials.keywords_summary'),
            'icon' => 'key',
            'tone' => 'bg-blue-50 text-blue-600',
            'href' => route('admin.keyword-libraries.index'),
            'action' => __('admin.materials.manage_keyword_libraries'),
            'metrics' => [
                __('admin.materials.keyword_library_count') => __('admin.materials.unit_libraries', ['count' => (int) $stats['keyword_libraries']]),
                __('admin.materials.keyword_total_count') => __('admin.materials.unit_items', ['count' => (int) $stats['total_keywords']]),
            ],
        ],
        [
            'title' => __('admin.materials.title_manage_title'),
            'summary' => __('admin.materials.titles_summary'),
            'icon' => 'type',
            'tone' => 'bg-emerald-50 text-emerald-600',
            'href' => route('admin.title-libraries.index'),
            'action' => __('admin.materials.manage_title_libraries'),
            'metrics' => [
                __('admin.materials.title_library_count') => __('admin.materials.unit_libraries', ['count' => (int) $stats['title_libraries']]),
                __('admin.materials.title_total_count') => __('admin.materials.unit_items', ['count' => (int) $stats['total_titles']]),
            ],
        ],
        [
            'title' => __('admin.materials.image_manage_title'),
            'summary' => __('admin.materials.images_summary'),
            'icon' => 'image',
            'tone' => 'bg-purple-50 text-purple-600',
            'href' => route('admin.image-libraries.index'),
            'action' => __('admin.materials.manage_image_libraries'),
            'metrics' => [
                __('admin.materials.image_library_count') => __('admin.materials.unit_libraries', ['count' => (int) $stats['image_libraries']]),
                __('admin.materials.image_total_count') => __('admin.materials.unit_images', ['count' => (int) $stats['total_images']]),
            ],
        ],
        [
            'title' => __('admin.materials.author_manage_title'),
            'summary' => __('admin.materials.authors_summary'),
            'icon' => 'users',
            'tone' => 'bg-indigo-50 text-indigo-600',
            'href' => route('admin.authors.index'),
            'action' => __('admin.materials.manage_authors'),
            'metrics' => [
                __('admin.materials.author_total_count') => __('admin.materials.author_count', ['count' => (int) $stats['authors']]),
                __('admin.materials.author_usage_label') => __('admin.materials.author_usage_desc'),
            ],
        ],
        [
            'title' => __('admin.materials.prompt_manage_title'),
            'summary' => __('admin.materials.prompts_summary'),
            'icon' => 'message-square-text',
            'tone' => 'bg-violet-50 text-violet-600',
            'href' => route('admin.ai-prompts'),
            'action' => __('admin.materials.manage_prompts'),
            'metrics' => [
                __('admin.materials.prompt_body_count') => __('admin.materials.unit_items', ['count' => (int) ($stats['body_prompts'] ?? 0)]),
                __('admin.materials.prompt_special_count') => __('admin.materials.unit_items', ['count' => (int) ($stats['special_prompts'] ?? 0)]),
            ],
        ],
    ];
@endphp

<section class="mb-8 overflow-hidden rounded-lg border border-blue-200 bg-white shadow-sm">
    <div class="border-b border-blue-100 bg-blue-50/60 px-6 py-5">
        <h2 class="text-xl font-semibold text-gray-900">{{ __('admin.materials.heading') }}</h2>
        <p class="mt-1 text-sm text-gray-600">{{ __('admin.materials.subtitle') }}</p>
    </div>
    <div class="p-6">
    <div class="mb-4">
        <h3 class="text-lg font-semibold text-gray-900">{{ __('admin.materials.foundation_title') }}</h3>
        <p class="mt-1 text-sm text-gray-600">{{ __('admin.materials.foundation_subtitle') }}</p>
    </div>
    <div class="grid grid-cols-1 gap-6 md:grid-cols-2 xl:grid-cols-4">
        @foreach ($foundationCards as $card)
            <a href="{{ $card['href'] }}" class="block rounded-lg border border-gray-200 bg-white p-6 shadow transition hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md">
                <div class="flex items-start justify-between gap-4">
                    <div class="flex h-12 w-12 items-center justify-center rounded-md {{ $card['tone'] }}">
                        <i data-lucide="{{ $card['icon'] }}" class="h-6 w-6"></i>
                    </div>
                    <i data-lucide="arrow-up-right" class="h-5 w-5 text-gray-300"></i>
                </div>
                <h3 class="mt-5 text-lg font-semibold text-gray-900">{{ $card['title'] }}</h3>
                <p class="mt-2 min-h-12 text-sm leading-6 text-gray-600">{{ $card['summary'] }}</p>
                <div class="mt-5 space-y-2">
                    @foreach ($card['metrics'] as $label => $value)
                        <div class="flex items-center justify-between gap-4 text-sm">
                            <span class="text-gray-500">{{ $label }}</span>
                            <span class="shrink-0 font-semibold text-gray-900">{{ $value }}</span>
                        </div>
                    @endforeach
                </div>
                <div class="mt-5 text-sm font-semibold text-blue-600">{{ $card['action'] }}</div>
            </a>
        @endforeach
    </div>
    </div>
</section>

<section class="mb-8 overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
    <div class="p-6 lg:p-8">
        <div class="max-w-5xl">
            <span class="inline-flex items-center rounded-full bg-cyan-50 px-3 py-1 text-sm font-medium text-cyan-700">
                <i data-lucide="sparkles" class="mr-2 h-4 w-4"></i>
                {{ __('admin.materials.url_import') }}
            </span>
            <h2 class="mt-5 text-2xl font-bold tracking-tight text-gray-900">{{ __('admin.materials.url_import_title') }}</h2>
            <p class="mt-3 text-sm leading-6 text-gray-600">{{ __('admin.materials.url_import_description') }}</p>
        </div>

        <form method="POST" action="{{ route('admin.url-import.store') }}" class="mt-7">
            @csrf
            <label for="production_url_import_url" class="block text-sm font-semibold text-gray-800">{{ __('admin.materials.url_import_target_label') }}</label>
            <div class="mt-3 flex flex-col gap-3 lg:flex-row">
                <input
                    id="production_url_import_url"
                    name="url"
                    type="text"
                    required
                    value="{{ old('url') }}"
                    placeholder="{{ __('admin.materials.url_import_placeholder') }}"
                    class="block min-h-14 w-full rounded-md border-gray-300 px-5 text-base shadow-sm focus:border-blue-500 focus:ring-blue-500"
                >
                @foreach (['knowledge', 'keywords', 'titles'] as $output)
                    <input type="hidden" name="outputs[]" value="{{ $output }}">
                @endforeach
                <button type="submit" class="inline-flex min-h-14 shrink-0 items-center justify-center rounded-md border border-transparent bg-blue-600 px-7 text-base font-semibold text-white shadow-sm hover:bg-blue-700">
                    <i data-lucide="globe" class="mr-2 h-5 w-5"></i>
                    {{ __('admin.materials.url_import_start') }}
                </button>
            </div>
            <p class="mt-2 text-sm text-gray-500">{{ __('admin.url_import.help.url_optional_scheme') }}</p>
            @error('url')
                <p class="mt-2 text-sm text-red-600">{{ $message }}</p>
            @enderror
        </form>

        <div class="mt-5 flex flex-wrap items-center gap-3">
            <a href="{{ route('admin.url-import') }}" class="inline-flex items-center text-sm font-medium text-blue-600 hover:text-blue-800">
                <i data-lucide="settings" class="mr-2 h-4 w-4"></i>
                {{ __('admin.url_import.section.new_job') }}
            </a>
            <a href="{{ route('admin.url-import.history') }}" class="inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-800">
                <i data-lucide="history" class="mr-2 h-4 w-4"></i>
                {{ __('admin.materials.url_import_history') }}
            </a>
        </div>
    </div>
</section>
