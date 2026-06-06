@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0 max-w-2xl">
        <h1 class="mb-6 text-2xl font-bold text-gray-900">{{ __('admin.geo_eval.insight_create_title') }}</h1>
        <form method="post" action="{{ route('admin.insight-templates.store') }}" class="space-y-4 rounded-lg border border-gray-200 bg-white p-6">
            @csrf
            <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">{{ __('admin.geo_eval.template_name') }}</label>
                <input type="text" name="name" value="{{ old('name') }}" required class="geo-input w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div>
                <label class="mb-1 block text-sm font-medium text-gray-700">URL</label>
                <input type="url" name="source_url" value="{{ old('source_url') }}" required class="geo-input w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
            </div>
            <div class="flex gap-3">
                <button type="submit" class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">{{ __('admin.button.save') }}</button>
                <a href="{{ route('admin.insight-templates.index') }}" class="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700">{{ __('admin.button.cancel') }}</a>
            </div>
        </form>
    </div>
@endsection
