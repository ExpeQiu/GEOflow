@extends('admin.layouts.app')

@section('content')
    <div class="px-4 sm:px-0">
        <div class="flex items-center justify-between mb-6">
            <div>
                <h1 class="text-2xl font-bold text-gray-900">{{ __('admin.tech_assets.page_title') }}</h1>
                <p class="mt-1 text-sm text-gray-600">{{ __('admin.tech_assets.page_subtitle') }}</p>
            </div>
            <div class="flex gap-2">
                <a href="{{ route('admin.tech-assets.create') }}" class="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-md text-sm">{{ __('admin.tech_assets.add') }}</a>
            </div>
        </div>

        @if (session('message'))
            <div class="mb-4 rounded-md border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">{{ session('message') }}</div>
        @endif

        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div class="rounded-lg border bg-white p-4">
                <p class="text-xs text-gray-500">{{ __('admin.tech_assets.p0_coverage') }}</p>
                <p class="text-2xl font-semibold">{{ $p0Ready }}/{{ $p0Total }}</p>
            </div>
        </div>

        <form method="POST" action="{{ route('admin.tech-assets.import') }}" enctype="multipart/form-data" class="mb-6 flex flex-wrap items-end gap-3 rounded-lg border bg-white p-4">
            @csrf
            <div>
                <label class="block text-sm font-medium text-gray-700">{{ __('admin.tech_assets.import_yaml') }}</label>
                <input type="file" name="yaml_file" accept=".yaml,.yml,.txt" required class="mt-1 block text-sm">
            </div>
            <button type="submit" class="px-4 py-2 bg-gray-800 text-white rounded-md text-sm">{{ __('admin.tech_assets.import_btn') }}</button>
        </form>

        <div class="bg-white shadow rounded-lg overflow-hidden">
            <table class="min-w-full divide-y divide-gray-200 text-sm">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-4 py-3 text-left">{{ __('admin.tech_assets.col.name') }}</th>
                        <th class="px-4 py-3 text-left">{{ __('admin.tech_assets.col.mind_tag') }}</th>
                        <th class="px-4 py-3 text-left">{{ __('admin.tech_assets.col.priority') }}</th>
                        <th class="px-4 py-3 text-left">{{ __('admin.tech_assets.col.three_q') }}</th>
                        <th class="px-4 py-3 text-left">{{ __('admin.tech_assets.col.status') }}</th>
                        <th class="px-4 py-3 text-right">{{ __('admin.common.actions') }}</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    @forelse ($assets as $asset)
                        <tr>
                            <td class="px-4 py-3">
                                <div class="font-medium text-gray-900">{{ $asset->ip_name }}</div>
                                <div class="text-xs text-gray-500">{{ $asset->ip_id }}</div>
                            </td>
                            <td class="px-4 py-3 text-gray-600">{{ $asset->mind_tag ?: '—' }}</td>
                            <td class="px-4 py-3">{{ $asset->priority }}</td>
                            <td class="px-4 py-3">
                                {{ ($asset->can_name ? '✓' : '—') }}/{{ ($asset->can_visualize ? '✓' : '—') }}/{{ ($asset->can_translate ? '✓' : '—') }}
                            </td>
                            <td class="px-4 py-3">{{ $asset->status }}</td>
                            <td class="px-4 py-3 text-right space-x-3">
                                <a href="{{ route('admin.tasks.create', [
                                    'content_format' => 'wiki_mdx',
                                    'publish_scope' => 'distribution_only',
                                    'tech_ip_asset_id' => $asset->id,
                                    'wiki_page_type' => $asset->wiki_type ?: 'concept',
                                ]) }}" class="text-emerald-600 hover:underline">{{ __('admin.tech_assets.create_wiki_task') }}</a>
                                <a href="{{ route('admin.tech-assets.edit', ['assetId' => $asset->id]) }}" class="text-blue-600 hover:underline">{{ __('admin.common.edit') }}</a>
                            </td>
                        </tr>
                    @empty
                        <tr><td colspan="6" class="px-4 py-8 text-center text-gray-500">{{ __('admin.tech_assets.empty') }}</td></tr>
                    @endforelse
                </tbody>
            </table>
        </div>
        <div class="mt-4">{{ $assets->links() }}</div>
    </div>
@endsection
