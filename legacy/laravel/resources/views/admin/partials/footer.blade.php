@php
    $appVersion = (string) config('geoflow.app_version', '2.0');
@endphp
<footer class="bg-white border-t border-gray-200 mt-12">
    <div class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div class="flex flex-col md:flex-row md:flex-wrap justify-center items-center gap-3 md:gap-4 text-sm text-gray-500 text-center">
            <span>{{ __('admin.footer.copyright') }}</span>
            <span>|</span>
            <span>{{ __('admin.footer.version', ['version' => $appVersion]) }}</span>
        </div>
    </div>
</footer>
<script>
    window.ADMIN_BASE_PATH = @json('/'.\App\Support\AdminWeb::basePath());
    window.adminUrl = function (path) {
        const base = window.ADMIN_BASE_PATH || '';
        if (!path) return base + '/';
        return base + '/' + String(path).replace(/^\/+/, '');
    };
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }
</script>
