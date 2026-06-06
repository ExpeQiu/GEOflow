@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        <div class="mb-6">
            <h1 class="text-2xl font-bold text-gray-900">{{ __('admin.knowledge_bases.rag_sandbox_title') }}</h1>
            <p class="mt-1 text-sm text-gray-600">{{ __('admin.knowledge_bases.rag_sandbox_desc') }}</p>
        </div>

        <form method="GET" action="{{ route('admin.knowledge-bases.rag-sandbox') }}" class="bg-white shadow rounded-lg p-6 mb-6 space-y-4">
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">{{ __('admin.knowledge_bases.rag_sandbox_kb') }}</label>
                    <select name="knowledge_base_id" class="w-full border-gray-300 rounded-md text-sm" required>
                        <option value="">{{ __('admin.knowledge_bases.rag_sandbox_select_kb') }}</option>
                        @foreach ($knowledgeBases as $kb)
                            <option value="{{ $kb->id }}" @selected((int) $selectedKnowledgeBaseId === (int) $kb->id)>{{ $kb->name }}</option>
                        @endforeach
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">{{ __('admin.knowledge_bases.rag_sandbox_query') }}</label>
                    <input type="text" name="query" value="{{ $query }}" class="w-full border-gray-300 rounded-md text-sm" required>
                </div>
            </div>
            <button type="submit" class="inline-flex items-center px-4 py-2 bg-orange-600 text-white text-sm rounded-md hover:bg-orange-700">
                {{ __('admin.knowledge_bases.rag_sandbox_run') }}
            </button>
        </form>

        @if ($query !== '')
            <div class="bg-white shadow rounded-lg">
                <div class="px-6 py-4 border-b border-gray-200 text-sm font-medium text-gray-900">
                    {{ __('admin.knowledge_bases.rag_sandbox_results', ['count' => count($evidence)]) }}
                </div>
                @forelse ($evidence as $index => $item)
                    <div class="px-6 py-4 border-b border-gray-100">
                        <div class="text-xs text-gray-500 mb-2">#{{ $index + 1 }} score={{ number_format((float) ($item['score'] ?? 0), 4) }}</div>
                        <pre class="text-sm text-gray-800 whitespace-pre-wrap">{{ $item['content'] ?? '' }}</pre>
                    </div>
                @empty
                    <div class="px-6 py-8 text-sm text-gray-500">{{ __('admin.knowledge_bases.rag_sandbox_empty') }}</div>
                @endforelse
            </div>
        @endif
    </div>
@endsection
