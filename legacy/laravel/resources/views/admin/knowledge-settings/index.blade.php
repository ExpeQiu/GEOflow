@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        <div class="mb-8 flex items-center justify-between">
            <div class="flex items-center space-x-4">
                <a href="{{ route('admin.ai.configurator') }}" class="text-gray-400 hover:text-gray-600">
                    <i data-lucide="arrow-left" class="w-5 h-5"></i>
                </a>
                <div>
                    <h1 class="text-2xl font-bold text-gray-900">{{ __('admin.knowledge_settings.heading') }}</h1>
                    <p class="mt-1 text-sm text-gray-600">{{ __('admin.knowledge_settings.subtitle') }}</p>
                </div>
            </div>
        </div>

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
                {{ session('status') }}
            </div>
        @endif

        <form method="POST" action="{{ route('admin.knowledge-settings.update') }}" class="max-w-2xl space-y-6">
            @csrf
            @method('PUT')

            <div class="rounded-lg border border-gray-200 bg-white p-6 shadow space-y-5">
                <div>
                    <label for="knowledge_retrieval_limit" class="block text-sm font-medium text-gray-700">{{ __('admin.knowledge_settings.field_retrieval_limit') }}</label>
                    <input type="number" name="knowledge_retrieval_limit" id="knowledge_retrieval_limit" min="1" max="20" required
                           value="{{ old('knowledge_retrieval_limit', (int) ($settings['knowledge_retrieval_limit'] ?? 5)) }}"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm">
                    <p class="mt-1 text-xs text-gray-500">{{ __('admin.knowledge_settings.help_retrieval_limit') }}</p>
                    @error('knowledge_retrieval_limit')
                        <p class="mt-1 text-sm text-red-600">{{ $message }}</p>
                    @enderror
                </div>

                <div>
                    <label for="knowledge_retrieval_max_chars" class="block text-sm font-medium text-gray-700">{{ __('admin.knowledge_settings.field_retrieval_max_chars') }}</label>
                    <input type="number" name="knowledge_retrieval_max_chars" id="knowledge_retrieval_max_chars" min="500" max="12000" required
                           value="{{ old('knowledge_retrieval_max_chars', (int) ($settings['knowledge_retrieval_max_chars'] ?? 3200)) }}"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm">
                    <p class="mt-1 text-xs text-gray-500">{{ __('admin.knowledge_settings.help_retrieval_max_chars') }}</p>
                    @error('knowledge_retrieval_max_chars')
                        <p class="mt-1 text-sm text-red-600">{{ $message }}</p>
                    @enderror
                </div>

                <div>
                    <label for="knowledge_chunk_max_chars" class="block text-sm font-medium text-gray-700">{{ __('admin.knowledge_settings.field_chunk_max_chars') }}</label>
                    <input type="number" name="knowledge_chunk_max_chars" id="knowledge_chunk_max_chars" min="500" max="20000" required
                           value="{{ old('knowledge_chunk_max_chars', (int) ($settings['knowledge_chunk_max_chars'] ?? 2000)) }}"
                           class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-orange-500 focus:ring-orange-500 sm:text-sm">
                    <p class="mt-1 text-xs text-gray-500">{{ __('admin.knowledge_settings.help_chunk_max_chars') }}</p>
                    @error('knowledge_chunk_max_chars')
                        <p class="mt-1 text-sm text-red-600">{{ $message }}</p>
                    @enderror
                </div>
            </div>

            <p class="text-sm text-amber-700">{{ __('admin.knowledge_settings.chunk_refresh_hint') }}</p>

            <div class="flex justify-end gap-3">
                <a href="{{ route('admin.ai.configurator') }}" class="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                    {{ __('admin.button.cancel') }}
                </a>
                <button type="submit" class="inline-flex items-center rounded-md border border-transparent bg-orange-600 px-4 py-2 text-sm font-medium text-white hover:bg-orange-700">
                    {{ __('admin.knowledge_settings.save') }}
                </button>
            </div>
        </form>
    </div>
@endsection
