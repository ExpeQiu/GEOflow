@extends('admin.layouts.app')

@php
    $f = is_array($assetForm ?? null) ? $assetForm : [];
@endphp

@section('content')
    <div class="px-4 sm:px-0 max-w-4xl">
        <h1 class="text-2xl font-bold text-gray-900 mb-6">{{ $isEdit ? __('admin.tech_assets.edit_title') : __('admin.tech_assets.create_title') }}</h1>

        <form method="POST" action="{{ $isEdit ? route('admin.tech-assets.update', ['assetId' => $assetId]) : route('admin.tech-assets.store') }}" class="space-y-6 bg-white shadow rounded-lg p-6">
            @csrf
            @if ($isEdit) @method('PUT') @endif

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium">ip_id *</label>
                    <input name="ip_id" value="{{ old('ip_id', $f['ip_id'] ?? '') }}" required class="mt-1 w-full rounded-md border-gray-300">
                </div>
                <div>
                    <label class="block text-sm font-medium">{{ __('admin.tech_assets.col.name') }} *</label>
                    <input name="ip_name" value="{{ old('ip_name', $f['ip_name'] ?? '') }}" required class="mt-1 w-full rounded-md border-gray-300">
                </div>
                <div>
                    <label class="block text-sm font-medium">{{ __('admin.tech_assets.field.layer') }}</label>
                    <select name="ip_layer" class="mt-1 w-full rounded-md border-gray-300">
                        @foreach (['架构层', '模块层', '参数层'] as $layer)
                            <option value="{{ $layer }}" @selected(old('ip_layer', $f['ip_layer'] ?? '') === $layer)>{{ $layer }}</option>
                        @endforeach
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium">{{ __('admin.tech_assets.col.priority') }}</label>
                    <select name="priority" class="mt-1 w-full rounded-md border-gray-300">
                        @foreach (['P0', 'P1', 'P2'] as $p)
                            <option value="{{ $p }}" @selected(old('priority', $f['priority'] ?? 'P1') === $p)>{{ $p }}</option>
                        @endforeach
                    </select>
                </div>
                <div class="md:col-span-2">
                    <label class="block text-sm font-medium">{{ __('admin.tech_assets.col.mind_tag') }}</label>
                    <input name="mind_tag" value="{{ old('mind_tag', $f['mind_tag'] ?? '') }}" class="mt-1 w-full rounded-md border-gray-300">
                </div>
            </div>

            <div class="flex flex-wrap gap-6">
                <label class="inline-flex items-center gap-2"><input type="checkbox" name="can_name" value="1" @checked(old('can_name', $f['can_name'] ?? false))> {{ __('admin.tech_assets.field.can_name') }}</label>
                <label class="inline-flex items-center gap-2"><input type="checkbox" name="can_visualize" value="1" @checked(old('can_visualize', $f['can_visualize'] ?? false))> {{ __('admin.tech_assets.field.can_visualize') }}</label>
                <label class="inline-flex items-center gap-2"><input type="checkbox" name="can_translate" value="1" @checked(old('can_translate', $f['can_translate'] ?? false))> {{ __('admin.tech_assets.field.can_translate') }}</label>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="block text-sm font-medium">Wiki type</label>
                    <select name="wiki_type" class="mt-1 w-full rounded-md border-gray-300">
                        <option value="">—</option>
                        @foreach (['concept', 'compare', 'guide', 'glossary', 'data', 'thread', 'topic'] as $type)
                            <option value="{{ $type }}" @selected(old('wiki_type', $f['wiki_type'] ?? '') === $type)>{{ $type }}</option>
                        @endforeach
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium">Wiki slug</label>
                    <input name="wiki_slug" value="{{ old('wiki_slug', $f['wiki_slug'] ?? '') }}" class="mt-1 w-full rounded-md border-gray-300">
                </div>
                <div>
                    <label class="block text-sm font-medium">{{ __('admin.tech_assets.col.status') }}</label>
                    <select name="status" class="mt-1 w-full rounded-md border-gray-300">
                        @foreach (['待封装', '已发布', '需更新'] as $st)
                            <option value="{{ $st }}" @selected(old('status', $f['status'] ?? '') === $st)>{{ $st }}</option>
                        @endforeach
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium">{{ __('admin.tech_assets.field.knowledge_base') }}</label>
                    <select name="knowledge_base_id" class="mt-1 w-full rounded-md border-gray-300">
                        <option value="">—</option>
                        @foreach ($knowledgeBases as $kb)
                            <option value="{{ $kb->id }}" @selected((string) old('knowledge_base_id', $f['knowledge_base_id'] ?? '') === (string) $kb->id)>{{ $kb->name }}</option>
                        @endforeach
                    </select>
                </div>
            </div>

            <div>
                <label class="block text-sm font-medium">{{ __('admin.tech_assets.field.tech_term') }}</label>
                <textarea name="tech_term" rows="2" class="mt-1 w-full rounded-md border-gray-300">{{ old('tech_term', $f['tech_term'] ?? '') }}</textarea>
            </div>
            <div>
                <label class="block text-sm font-medium">{{ __('admin.tech_assets.field.user_language') }}</label>
                <textarea name="user_language" rows="2" class="mt-1 w-full rounded-md border-gray-300">{{ old('user_language', $f['user_language'] ?? '') }}</textarea>
            </div>
            <div>
                <label class="block text-sm font-medium">evidence (JSON)</label>
                <textarea name="evidence_json" rows="4" class="mt-1 w-full rounded-md border-gray-300 font-mono text-xs">{{ old('evidence_json', $f['evidence_json'] ?? '[]') }}</textarea>
            </div>
            <div>
                <label class="block text-sm font-medium">{{ __('admin.tech_assets.field.models') }}</label>
                <textarea name="models_text" rows="3" class="mt-1 w-full rounded-md border-gray-300" placeholder="一行一个车型">{{ old('models_text', $f['models_text'] ?? '') }}</textarea>
            </div>

            <div class="flex gap-3">
                <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-md text-sm">{{ __('admin.common.save') }}</button>
                <a href="{{ route('admin.tech-assets.index') }}" class="px-4 py-2 border rounded-md text-sm">{{ __('admin.common.cancel') }}</a>
            </div>
        </form>
    </div>
@endsection
