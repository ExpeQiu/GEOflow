@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0 max-w-lg">
        <h1 class="mb-6 text-2xl font-bold text-gray-900">{{ __('admin.geo_eval.insight_edit_title') }}</h1>
        <form method="post" action="{{ route('admin.insight-templates.update', ['templateId' => $template->id]) }}">
            @csrf
            @method('PUT')
            <div class="mb-4">
                <label class="mb-1 block text-sm font-medium text-gray-700">{{ __('admin.geo_eval.template_name') }}</label>
                <input type="text" name="name" value="{{ old('name', $template->name) }}" required class="block w-full rounded-md border-gray-300 shadow-sm">
            </div>
            <p class="mb-4 text-sm text-gray-500">{{ __('admin.geo_eval.insight_url_readonly') }}: {{ $template->source_url }}</p>
            <button type="submit" class="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700">{{ __('admin.button.save') }}</button>
        </form>
    </div>
@endsection
