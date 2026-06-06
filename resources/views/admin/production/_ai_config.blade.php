<section class="mb-6 overflow-hidden rounded-lg border border-violet-200 bg-white shadow-sm">
    <div class="border-b border-violet-100 bg-violet-50/60 px-6 py-5">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
            <div>
                <h2 class="text-xl font-semibold text-gray-900">{{ __('admin.ai_configurator.heading') }}</h2>
                <p class="mt-1 text-sm text-gray-600">{{ __('admin.ai_configurator.subtitle') }}</p>
            </div>
            <a href="{{ route('admin.ai-models.index') }}" class="inline-flex h-10 items-center rounded-md bg-violet-600 px-4 text-sm font-semibold text-white hover:bg-violet-700">
                <i data-lucide="plug-zap" class="mr-2 h-4 w-4"></i>
                {{ __('admin.ai_configurator.models_action') }}
            </a>
        </div>
    </div>

    <div class="grid grid-cols-1 gap-6 p-6 md:grid-cols-2 lg:grid-cols-4">
        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div class="p-6">
                <div class="flex items-center">
                    <div class="flex h-10 w-10 items-center justify-center rounded-md bg-blue-500">
                        <i data-lucide="cpu" class="h-5 w-5 text-white"></i>
                    </div>
                    <div class="ml-4 min-w-0">
                        <p class="text-sm font-medium text-gray-500">{{ __('admin.ai_configurator.models_title') }}</p>
                        <p class="mt-1 text-base font-semibold text-gray-900">{{ __('admin.ai_configurator.models_desc') }}</p>
                    </div>
                </div>
            </div>
            <div class="border-t border-gray-100 bg-gray-50 px-6 py-3">
                <a href="{{ route('admin.ai-models.index') }}" class="text-sm font-medium text-blue-600 hover:text-blue-500">
                    {{ __('admin.ai_configurator.models_action') }} <span aria-hidden="true">&rarr;</span>
                </a>
            </div>
        </div>

        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div class="p-6">
                <div class="flex items-center">
                    <div class="flex h-10 w-10 items-center justify-center rounded-md bg-green-500">
                        <i data-lucide="message-square" class="h-5 w-5 text-white"></i>
                    </div>
                    <div class="ml-4 min-w-0">
                        <p class="text-sm font-medium text-gray-500">{{ __('admin.ai_configurator.prompts_title') }}</p>
                        <p class="mt-1 text-base font-semibold text-gray-900">{{ __('admin.ai_configurator.prompts_desc') }}</p>
                    </div>
                </div>
            </div>
            <div class="border-t border-gray-100 bg-gray-50 px-6 py-3">
                <a href="{{ route('admin.ai-prompts') }}" class="text-sm font-medium text-green-600 hover:text-green-500">
                    {{ __('admin.ai_configurator.prompts_action') }} <span aria-hidden="true">&rarr;</span>
                </a>
            </div>
        </div>

        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div class="p-6">
                <div class="flex items-center">
                    <div class="flex h-10 w-10 items-center justify-center rounded-md bg-purple-500">
                        <i data-lucide="settings" class="h-5 w-5 text-white"></i>
                    </div>
                    <div class="ml-4 min-w-0">
                        <p class="text-sm font-medium text-gray-500">{{ __('admin.ai_configurator.special_title') }}</p>
                        <p class="mt-1 text-base font-semibold text-gray-900">{{ __('admin.ai_configurator.special_desc') }}</p>
                    </div>
                </div>
            </div>
            <div class="border-t border-gray-100 bg-gray-50 px-6 py-3">
                <a href="{{ route('admin.ai-special-prompts') }}" class="text-sm font-medium text-purple-600 hover:text-purple-500">
                    {{ __('admin.ai_configurator.special_action') }} <span aria-hidden="true">&rarr;</span>
                </a>
            </div>
        </div>

        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <div class="p-6">
                <div class="flex items-center">
                    <div class="flex h-10 w-10 items-center justify-center rounded-md bg-orange-500">
                        <i data-lucide="layers" class="h-5 w-5 text-white"></i>
                    </div>
                    <div class="ml-4 min-w-0">
                        <p class="text-sm font-medium text-gray-500">{{ __('admin.ai_configurator.rag_title') }}</p>
                        <p class="mt-1 text-base font-semibold text-gray-900">{{ __('admin.ai_configurator.rag_desc') }}</p>
                    </div>
                </div>
            </div>
            <div class="border-t border-gray-100 bg-gray-50 px-6 py-3">
                <a href="{{ route('admin.knowledge-settings.index') }}" class="text-sm font-medium text-orange-600 hover:text-orange-500">
                    {{ __('admin.ai_configurator.rag_action') }} <span aria-hidden="true">&rarr;</span>
                </a>
            </div>
        </div>
    </div>
</section>

<div class="mb-8 overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
    <div class="border-b border-gray-200 px-6 py-4">
        <h3 class="text-lg font-semibold text-gray-900">{{ __('admin.ai_configurator.overview') }}</h3>
    </div>
    <div class="px-6 py-6">
        <div class="grid grid-cols-2 gap-6 md:grid-cols-4">
            <div class="rounded-md bg-blue-50 p-4 text-center">
                <div class="text-2xl font-bold text-blue-600">{{ (int) ($stats['model_count'] ?? 0) }}</div>
                <div class="mt-1 text-sm text-gray-600">{{ __('admin.ai_configurator.active_models') }}</div>
            </div>
            <div class="rounded-md bg-green-50 p-4 text-center">
                <div class="text-2xl font-bold text-green-600">{{ (int) ($stats['prompt_count'] ?? 0) }}</div>
                <div class="mt-1 text-sm text-gray-600">{{ __('admin.ai_configurator.prompt_templates') }}</div>
            </div>
            <div class="rounded-md bg-purple-50 p-4 text-center">
                <div class="text-2xl font-bold text-purple-600">{{ number_format((int) ($stats['total_usage'] ?? 0)) }}</div>
                <div class="mt-1 text-sm text-gray-600">{{ __('admin.ai_configurator.total_calls') }}</div>
            </div>
            <div class="rounded-md bg-orange-50 p-4 text-center">
                <div class="text-2xl font-bold text-orange-600">{{ number_format((int) ($stats['today_usage'] ?? 0)) }}</div>
                <div class="mt-1 text-sm text-gray-600">{{ __('admin.ai_configurator.today_calls') }}</div>
            </div>
        </div>
    </div>
</div>

<div class="rounded-lg border border-blue-200 bg-blue-50 p-6">
    <div class="flex">
        <div class="flex-shrink-0">
            <i data-lucide="info" class="h-5 w-5 text-blue-400"></i>
        </div>
        <div class="ml-3">
            <h3 class="text-sm font-medium text-blue-800">{{ __('admin.ai_configurator.help_title') }}</h3>
            <div class="mt-2 text-sm text-blue-700">
                <ul class="list-inside list-disc space-y-1">
                    <li>{{ __('admin.ai_configurator.help_models') }}</li>
                    <li>{{ __('admin.ai_configurator.help_content_prompts') }}</li>
                    <li>{{ __('admin.ai_configurator.help_special_prompts') }}</li>
                    <li>{{ __('admin.ai_configurator.help_pipeline') }}</li>
                </ul>
            </div>
        </div>
    </div>
</div>
