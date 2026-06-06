@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        @include('admin.strategy._hub-header')

        @if (session('status'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ session('status') }}</div>
        @endif

        @include('admin.strategy._hub-nav', ['strategyHubCurrentTab' => 'insight-templates'])

        <div class="mb-6 flex items-center justify-between">
            <div>
                <h2 class="text-lg font-semibold text-gray-900">{{ __('admin.geo_eval.insight_templates_title') }}</h2>
                <p class="mt-1 text-sm text-gray-500">{{ __('admin.geo_eval.insight_templates_subtitle') }}</p>
            </div>
            <a href="{{ route('admin.insight-templates.create') }}" class="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
                {{ __('admin.geo_eval.insight_create') }}
            </a>
        </div>

        <div class="overflow-hidden rounded-lg border border-gray-200 bg-white">
            <table class="min-w-full text-sm">
                <thead class="bg-gray-50 text-left text-xs text-gray-500">
                    <tr>
                        <th class="px-4 py-3">ID</th>
                        <th class="px-4 py-3">{{ __('admin.geo_eval.template_name') }}</th>
                        <th class="px-4 py-3">URL</th>
                        <th class="px-4 py-3">E-E-A-T</th>
                        <th class="px-4 py-3">{{ __('admin.geo_eval.created_at') }}</th>
                        <th class="px-4 py-3">{{ __('admin.geo_eval.actions') }}</th>
                    </tr>
                </thead>
                <tbody>
                    @forelse ($templates as $template)
                        <tr class="border-t border-gray-100">
                            <td class="px-4 py-3">{{ $template->id }}</td>
                            <td class="px-4 py-3 font-medium text-gray-900">
                                <a href="{{ route('admin.insight-templates.show', ['templateId' => $template->id]) }}" class="text-blue-600 hover:underline">{{ $template->name }}</a>
                            </td>
                            <td class="px-4 py-3 text-blue-600"><a href="{{ $template->source_url }}" target="_blank" rel="noopener">{{ \Illuminate\Support\Str::limit($template->source_url, 48) }}</a></td>
                            <td class="px-4 py-3">{{ $template->eeat_score ?? '-' }}</td>
                            <td class="px-4 py-3">{{ optional($template->updated_at ?? $template->created_at)->format('Y-m-d H:i') }}</td>
                            <td class="px-4 py-3 space-x-2">
                                <a href="{{ route('admin.insight-templates.show', ['templateId' => $template->id]) }}" class="text-blue-600 hover:underline">{{ __('admin.geo_eval.insight_preview') }}</a>
                                <a href="{{ route('admin.insight-templates.edit', ['templateId' => $template->id]) }}" class="text-blue-600 hover:underline">{{ __('admin.geo_eval.insight_edit') }}</a>
                                <form class="inline" method="post" action="{{ route('admin.insight-templates.destroy', ['templateId' => $template->id]) }}" onsubmit="return confirm('{{ __('admin.geo_eval.delete_confirm') }}')">
                                    @csrf
                                    <button type="submit" class="text-red-600 hover:underline">{{ __('admin.button.delete') }}</button>
                                </form>
                            </td>
                        </tr>
                    @empty
                        <tr><td colspan="6" class="px-4 py-8 text-center text-gray-400">{{ __('admin.geo_eval.no_templates') }}</td></tr>
                    @endforelse
                </tbody>
            </table>
        </div>
    </div>
@endsection
