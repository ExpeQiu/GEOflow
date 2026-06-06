@php
    $currentAdmin = auth('admin')->user();
    $adminBrandName = $adminBrandName ?? \App\Support\AdminWeb::siteName();
    $isSuperAdmin = $currentAdmin && method_exists($currentAdmin, 'isSuperAdmin') && $currentAdmin->isSuperAdmin();
    $adminRoleLabel = $isSuperAdmin ? __('admin.header.super_admin') : __('admin.header.admin');
    $updateNotification = is_array($adminUpdateNotificationPayload ?? null) ? $adminUpdateNotificationPayload : [];
    $updateState = is_array($updateNotification['state'] ?? null) ? $updateNotification['state'] : [];
    $hasVersionUpdate = !empty($updateState['is_update_available']);
    $localeForChangelog = app()->getLocale() === 'en' ? 'en' : 'zh-CN';
    $updatePayload = is_array($updateState['payload'] ?? null) ? $updateState['payload'] : [];
    $updateSummary = (string) ($localeForChangelog === 'en'
        ? ($updatePayload['summary_en'] ?? '')
        : ($updatePayload['summary_zh'] ?? ''));
    $notificationStatus = (string) ($updateState['status'] ?? 'disabled');
    $menuGroups = [
        'l2' => ['label' => __('admin.nav.group_production'), 'items' => [
            'production_hub' => ['route' => 'admin.production.index', 'name' => __('admin.nav.production_hub')],
        ]],
        'l3' => ['label' => __('admin.nav.group_operations'), 'items' => [
            'operations_hub' => ['route' => 'admin.operations.index', 'name' => __('admin.nav.operations_hub')],
        ]],
        'l1' => ['label' => __('admin.nav.group_strategy'), 'items' => [
            'strategy_hub' => ['route' => 'admin.strategy.index', 'name' => __('admin.nav.strategy_hub')],
        ]],
    ];
    $menu = [
        'dashboard' => ['route' => 'admin.dashboard', 'name' => __('admin.nav.dashboard')],
        'production_hub' => ['route' => 'admin.production.index', 'name' => __('admin.nav.production_hub')],
        'operations_hub' => ['route' => 'admin.operations.index', 'name' => __('admin.nav.operations_hub')],
        'strategy_hub' => ['route' => 'admin.strategy.index', 'name' => __('admin.nav.strategy_hub')],
        'site_settings' => ['route' => 'admin.site-settings.index', 'name' => __('admin.nav.site_settings')],
    ];
    if ($isSuperAdmin) {
        $menu['admin_users'] = ['route' => 'admin.admin-users.index', 'name' => __('admin.nav.admin_users')];
    }
    $subMap = [
        'admin.analytics' => 'strategy_hub',
        'admin.strategy.index' => 'strategy_hub',
        'admin.strategy.monitor.store' => 'strategy_hub',
        'admin.strategy.monitor.update' => 'strategy_hub',
        'admin.strategy.monitor.destroy' => 'strategy_hub',
        'admin.strategy.monitor.import' => 'strategy_hub',
        'admin.strategy.monitor.import-batch' => 'strategy_hub',
        'admin.strategy.monitor.import-tech-keywords' => 'strategy_hub',
        'admin.strategy.monitor.config' => 'strategy_hub',
        'admin.strategy.monitor.scan' => 'strategy_hub',
        'admin.strategy.web-intel.sources.store' => 'strategy_hub',
        'admin.strategy.web-intel.sources.destroy' => 'strategy_hub',
        'admin.strategy.web-intel.sources.refresh' => 'strategy_hub',
        'admin.strategy.web-intel.reports.compose' => 'strategy_hub',
        'admin.strategy.simulator.reevaluate' => 'strategy_hub',
        'admin.strategy.simulator.batch-reevaluate' => 'strategy_hub',
        'admin.strategy.simulator.apply-recommendations' => 'strategy_hub',
        'admin.geo-eval.diagnostics' => 'strategy_hub',
        'admin.geo-eval.alerts' => 'strategy_hub',
        'admin.geo-eval.reevaluate' => 'strategy_hub',
        'admin.geo-eval.reevaluate-failed' => 'strategy_hub',
        'admin.insight-templates.index' => 'strategy_hub',
        'admin.insight-templates.create' => 'strategy_hub',
        'admin.insight-templates.store' => 'strategy_hub',
        'admin.insight-templates.show' => 'strategy_hub',
        'admin.insight-templates.edit' => 'strategy_hub',
        'admin.insight-templates.update' => 'strategy_hub',
        'admin.insight-templates.destroy' => 'strategy_hub',
        'admin.insight-templates.remine' => 'strategy_hub',
        'admin.production.index' => 'production_hub',
        'admin.knowledge-settings.index' => 'production_hub',
        'admin.knowledge-settings.update' => 'production_hub',
        'admin.knowledge-bases.rag-sandbox' => 'production_hub',
        'admin.operations.index' => 'operations_hub',
        'admin.tasks.index' => 'operations_hub',
        'admin.tasks.create' => 'operations_hub',
        'admin.tasks.edit' => 'operations_hub',
        'admin.articles.index' => 'operations_hub',
        'admin.distribution.index' => 'operations_hub',
        'admin.distribution.create' => 'operations_hub',
        'admin.distribution.store' => 'operations_hub',
        'admin.distribution.edit' => 'operations_hub',
        'admin.distribution.update' => 'operations_hub',
        'admin.distribution.show' => 'operations_hub',
        'admin.distribution.jobs' => 'operations_hub',
        'admin.distribution.retry' => 'operations_hub',
        'admin.distribution.health' => 'operations_hub',
        'admin.distribution.pause' => 'operations_hub',
        'admin.distribution.activate' => 'operations_hub',
        'admin.distribution.rotate-secret' => 'operations_hub',
        'admin.articles.create' => 'operations_hub',
        'admin.articles.edit' => 'operations_hub',
        'admin.materials.index' => 'production_hub',
        'admin.ai.configurator' => 'production_hub',
        'admin.categories.index' => 'production_hub',
        'admin.categories.create' => 'production_hub',
        'admin.categories.edit' => 'production_hub',
        'admin.authors.index' => 'production_hub',
        'admin.authors.create' => 'production_hub',
        'admin.authors.edit' => 'production_hub',
        'admin.authors.detail' => 'production_hub',
        'admin.keyword-libraries.index' => 'production_hub',
        'admin.keyword-libraries.create' => 'production_hub',
        'admin.keyword-libraries.edit' => 'production_hub',
        'admin.keyword-libraries.detail' => 'production_hub',
        'admin.keyword-libraries.detail.update' => 'production_hub',
        'admin.keyword-libraries.keywords.store' => 'production_hub',
        'admin.keyword-libraries.keywords.delete' => 'production_hub',
        'admin.keyword-libraries.import' => 'production_hub',
        'admin.title-libraries.index' => 'production_hub',
        'admin.title-libraries.create' => 'production_hub',
        'admin.title-libraries.edit' => 'production_hub',
        'admin.title-libraries.detail' => 'production_hub',
        'admin.title-libraries.titles.store' => 'production_hub',
        'admin.title-libraries.titles.delete' => 'production_hub',
        'admin.title-libraries.import' => 'production_hub',
        'admin.title-libraries.ai-generate' => 'production_hub',
        'admin.title-libraries.ai-generate.submit' => 'production_hub',
        'admin.image-libraries.index' => 'production_hub',
        'admin.image-libraries.create' => 'production_hub',
        'admin.image-libraries.edit' => 'production_hub',
        'admin.image-libraries.detail' => 'production_hub',
        'admin.image-libraries.images.upload' => 'production_hub',
        'admin.image-libraries.images.delete' => 'production_hub',
        'admin.image-libraries.detail.update' => 'production_hub',
        'admin.knowledge-bases.index' => 'production_hub',
        'admin.knowledge-bases.create' => 'production_hub',
        'admin.knowledge-bases.edit' => 'production_hub',
        'admin.knowledge-bases.detail' => 'production_hub',
        'admin.knowledge-bases.upload' => 'production_hub',
        'admin.knowledge-bases.detail.update' => 'production_hub',
        'admin.url-import' => 'production_hub',
        'admin.ai-models.index' => 'production_hub',
        'admin.ai-prompts' => 'production_hub',
        'admin.ai-special-prompts' => 'production_hub',
        'admin.site-settings.sensitive-words' => 'site_settings',
        'admin.site-settings.sensitive-words.store' => 'site_settings',
        'admin.site-settings.sensitive-words.delete' => 'site_settings',
        'admin.security-settings.index' => 'site_settings',
        'admin.security-settings.words.store' => 'site_settings',
        'admin.security-settings.words.delete' => 'site_settings',
        'admin.api-tokens.index' => 'admin_users',
        'admin.api-tokens.store' => 'admin_users',
        'admin.api-tokens.revoke' => 'admin_users',
        'admin.admin-activity-logs' => 'admin_users',
    ];
    $routeName = request()->route()?->getName();
    $resolvedActive = $activeMenu;
    if ($resolvedActive === '' && $routeName && isset($subMap[$routeName])) {
        $resolvedActive = $subMap[$routeName];
    }
@endphp
<nav class="bg-white shadow-sm border-b">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex h-16 items-center gap-3 lg:gap-4 min-w-0">
            <a href="{{ route('admin.dashboard') }}" class="shrink-0 text-lg sm:text-xl font-semibold text-gray-900">{{ $adminBrandName }}</a>
            <nav class="hidden flex-1 min-w-0 items-center">
                <div class="flex w-full min-w-0 items-center gap-3 lg:gap-5 overflow-x-auto overscroll-x-contain py-2 -my-2 [scrollbar-width:thin]">
                    @php
                        $orderedNavKeys = ['dashboard', 'production_hub', 'operations_hub', 'strategy_hub', 'site_settings'];
                    @endphp
                    @foreach ($orderedNavKeys as $navIndex => $key)
                        @if ($navIndex === 1 || $navIndex === 2 || $navIndex === 3)
                            <span class="hidden lg:inline shrink-0 text-gray-300" aria-hidden="true">|</span>
                        @endif
                        @if (isset($menu[$key]))
                            <a href="{{ route($menu[$key]['route']) }}"
                               class="@if($resolvedActive === $key) text-blue-600 font-medium @else text-gray-500 hover:text-gray-700 @endif shrink-0 whitespace-nowrap text-[15px] transition-colors duration-200"
                               title="{{ match ($navIndex) { 1 => $menuGroups['l2']['label'] ?? '', 2 => $menuGroups['l3']['label'] ?? '', 3 => $menuGroups['l1']['label'] ?? '', default => '' } }}">
                                {{ $menu[$key]['name'] }}
                            </a>
                        @endif
                    @endforeach
                </div>
            </nav>
            <div class="flex shrink-0 items-center gap-2 sm:gap-3 ml-auto">
                <div class="relative">
                    <button onclick="toggleAdminNotifications()" class="relative rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors duration-200" type="button" aria-label="{{ __('admin.header.notifications.label') }}" title="{{ __('admin.header.notifications.label') }}">
                        <i data-lucide="bell" class="w-5 h-5"></i>
                        @if($hasVersionUpdate)
                            <span data-update-indicator class="absolute right-1.5 top-1.5 h-2.5 w-2.5 rounded-full bg-red-500 ring-2 ring-white"></span>
                        @endif
                    </button>

                    <div id="admin-notification-menu" class="hidden absolute right-0 mt-3 w-80 overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-xl z-50">
                        <div class="border-b border-gray-100 px-4 py-3">
                            <div class="flex items-center justify-between gap-3">
                                <div class="text-sm font-semibold text-gray-900">{{ __('admin.header.notifications.title') }}</div>
                                @if($hasVersionUpdate)
                                    <span class="inline-flex items-center rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-600">{{ __('admin.header.notifications.badge_new') }}</span>
                                @endif
                            </div>
                        </div>
                        <div class="px-4 py-4">
                            @php $geoAlerts = $geoAlertNotificationPayload ?? ['count' => 0, 'items' => []]; @endphp
                            @if(($geoAlerts['count'] ?? 0) > 0)
                                <div class="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2">
                                    <div class="text-xs font-semibold text-amber-900">{{ __('admin.geo_eval.header_alerts_title') }}</div>
                                    @foreach (array_slice($geoAlerts['items'] ?? [], 0, 3) as $geoAlert)
                                        <p class="mt-1 text-xs text-amber-800">{{ \Illuminate\Support\Str::limit($geoAlert['message'] ?? '', 80) }}</p>
                                    @endforeach
                                    <div class="mt-2 flex flex-wrap gap-3 text-xs font-medium">
                                        <a href="{{ route('admin.strategy.index', ['tab' => 'simulator']) }}" class="text-amber-900 hover:underline">{{ __('admin.geo_eval.open_diagnostics') }}</a>
                                        <a href="{{ route('admin.geo-eval.alerts') }}" class="text-amber-900 hover:underline">{{ __('admin.geo_eval.view_all_alerts') }}</a>
                                    </div>
                                </div>
                            @endif
                            @if($hasVersionUpdate)
                                <div class="text-sm font-semibold text-gray-900">
                                    {{ __('admin.header.notifications.update_available', ['version' => (string) ($updateState['latest_version'] ?? '')]) }}
                                </div>
                                <p class="mt-2 text-sm leading-6 text-gray-600">{{ __('admin.header.notifications.update_desc') }}</p>
                                @if($updateSummary !== '')
                                    <p class="mt-2 text-sm leading-6 text-gray-600">{{ $updateSummary }}</p>
                                @endif
                            @elseif($notificationStatus === 'current')
                                <div class="text-sm font-semibold text-gray-900">{{ __('admin.header.notifications.up_to_date') }}</div>
                                <p class="mt-2 text-sm leading-6 text-gray-600">{{ __('admin.header.notifications.no_update_desc') }}</p>
                            @elseif($notificationStatus === 'disabled')
                                <div class="text-sm font-semibold text-gray-900">{{ __('admin.header.notifications.disabled') }}</div>
                                <p class="mt-2 text-sm leading-6 text-gray-600">{{ __('admin.header.notifications.disabled_desc') }}</p>
                            @else
                                <div class="text-sm font-semibold text-gray-900">{{ __('admin.header.notifications.unavailable') }}</div>
                                <p class="mt-2 text-sm leading-6 text-gray-600">{{ __('admin.header.notifications.unavailable_desc') }}</p>
                            @endif

                            <div class="mt-4 space-y-1 rounded-xl bg-gray-50 px-3 py-3 text-xs text-gray-500">
                                <div>{{ __('admin.header.notifications.current_version', ['version' => (string) ($updateState['current_version'] ?? config('geoflow.app_version', '2.0'))]) }}</div>
                                @if(!empty($updateState['latest_version']))
                                    <div>{{ __('admin.header.notifications.latest_version', ['version' => (string) $updateState['latest_version']]) }}</div>
                                @endif
                                <div>{{ __('admin.header.notifications.daily_check') }}</div>
                                @if(!empty($updateState['checked_at']))
                                    <div>{{ __('admin.header.notifications.checked_at', ['time' => (string) $updateState['checked_at']]) }}</div>
                                @endif
                            </div>
                        </div>
                    </div>
                </div>
                <div class="hidden md:flex items-center rounded-lg border border-gray-200 bg-white px-2 py-1 shadow-sm">
                    <i data-lucide="languages" class="w-4 h-4 text-gray-400 mr-1.5"></i>
                    <select
                        class="admin-locale-select appearance-none bg-transparent pr-5 text-sm font-medium text-gray-700 outline-none cursor-pointer"
                        aria-label="{{ __('admin.header.language') }}"
                        onchange="if (this.value) window.location.href = this.value"
                    >
                        @foreach (\App\Support\AdminWeb::supportedLocales() as $localeCode => $localeLabel)
                            <option value="{{ route('admin.locale.switch', ['locale' => $localeCode]) }}" @selected(app()->getLocale() === $localeCode)>
                                {{ $localeLabel }}
                            </option>
                        @endforeach
                    </select>
                </div>
                <div class="relative">
                    <button onclick="toggleUserMenu()" class="flex items-center space-x-1 text-sm text-gray-600 hover:text-gray-900 transition-colors duration-200" type="button">
                        <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                            <i data-lucide="user" class="w-4 h-4 text-blue-600"></i>
                        </div>
                        <i data-lucide="chevron-down" class="w-4 h-4"></i>
                    </button>

                    <div id="user-menu" class="hidden absolute right-0 mt-2 w-56 bg-white rounded-md shadow-lg py-1 z-50">
                        <div class="px-4 py-2 border-b border-gray-100">
                            <div class="text-sm text-gray-700">{{ __('admin.header.welcome', ['name' => $currentAdmin->username ?? '']) }}</div>
                            <div class="text-xs text-gray-400">{{ $adminRoleLabel }}</div>
                        </div>
                        <a href="{{ route('admin.dashboard') }}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                            <i data-lucide="home" class="w-4 h-4 inline mr-2"></i>
                            {{ __('admin.nav.back_home') }}
                        </a>
                        <a href="{{ route('admin.site-settings.index') }}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                            <i data-lucide="settings" class="w-4 h-4 inline mr-2"></i>
                            {{ __('admin.nav.system_settings') }}
                        </a>
                        @if ($isSuperAdmin)
                            <a href="{{ route('admin.admin-users.index') }}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                <i data-lucide="users" class="w-4 h-4 inline mr-2"></i>
                                {{ __('admin.nav.admin_management') }}
                            </a>
                            <a href="{{ route('admin.admin-activity-logs') }}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                <i data-lucide="clipboard-list" class="w-4 h-4 inline mr-2"></i>
                                {{ __('admin.nav.activity_logs') }}
                            </a>
                            <a href="{{ route('admin.api-tokens.index') }}" class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">
                                <i data-lucide="key-round" class="w-4 h-4 inline mr-2"></i>
                                {{ __('admin.nav.api_tokens') }}
                            </a>
                        @endif
                        <div class="border-t border-gray-100"></div>
                        <form method="POST" action="{{ route('admin.logout') }}">
                            @csrf
                            <button type="submit" class="w-full text-left block px-4 py-2 text-sm text-red-600 hover:bg-gray-100">
                                <i data-lucide="log-out" class="w-4 h-4 inline mr-2"></i>
                                {{ __('admin.button.logout') }}
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="mobile-menu" class="hidden md:hidden">
        <div class="px-2 pt-2 pb-3 space-y-3 sm:px-3 bg-gray-50 border-t">
            @if (isset($menu['dashboard']))
                <a href="{{ route($menu['dashboard']['route']) }}"
                   class="@if($resolvedActive === 'dashboard') bg-blue-100 text-blue-600 @else text-gray-600 hover:bg-gray-100 @endif block px-3 py-2 rounded-md text-base font-medium transition-colors duration-200">
                    {{ $menu['dashboard']['name'] }}
                </a>
            @endif
            @foreach ($menuGroups as $groupKey => $group)
                <div>
                    <div class="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-gray-400">{{ $group['label'] }}</div>
                    <div class="space-y-1">
                        @foreach ($group['items'] as $key => $item)
                            <a href="{{ route($item['route']) }}"
                               class="@if($resolvedActive === $key) bg-blue-100 text-blue-600 @else text-gray-600 hover:bg-gray-100 @endif block px-3 py-2 rounded-md text-base font-medium transition-colors duration-200">
                                {{ $item['name'] }}
                            </a>
                        @endforeach
                    </div>
                </div>
            @endforeach
            @if (isset($menu['site_settings']))
                <a href="{{ route($menu['site_settings']['route']) }}"
                   class="@if($resolvedActive === 'site_settings') bg-blue-100 text-blue-600 @else text-gray-600 hover:bg-gray-100 @endif block px-3 py-2 rounded-md text-base font-medium transition-colors duration-200">
                    {{ $menu['site_settings']['name'] }}
                </a>
            @endif
            @if ($isSuperAdmin && isset($menu['admin_users']))
                <a href="{{ route($menu['admin_users']['route']) }}"
                   class="@if($resolvedActive === 'admin_users') bg-blue-100 text-blue-600 @else text-gray-600 hover:bg-gray-100 @endif block px-3 py-2 rounded-md text-base font-medium transition-colors duration-200">
                    {{ $menu['admin_users']['name'] }}
                </a>
            @endif
        </div>
    </div>
</nav>
<div class="md:hidden fixed top-4 right-4 z-50">
    <button onclick="toggleMobileMenu()" class="bg-white p-2 rounded-md shadow-md" type="button">
        <i data-lucide="menu" class="w-5 h-5 text-gray-600"></i>
    </button>
</div>

<style>
    .admin-locale-select {
        background-image: linear-gradient(45deg, transparent 50%, #6b7280 50%), linear-gradient(135deg, #6b7280 50%, transparent 50%);
        background-position: calc(100% - 8px) 52%, calc(100% - 4px) 52%;
        background-size: 4px 4px, 4px 4px;
        background-repeat: no-repeat;
    }
</style>

<script>
    function toggleUserMenu() {
        const menu = document.getElementById('user-menu');
        if (menu) {
            menu.classList.toggle('hidden');
        }
    }

    function toggleAdminNotifications() {
        const menu = document.getElementById('admin-notification-menu');
        if (menu) {
            menu.classList.toggle('hidden');
        }
    }

    function toggleMobileMenu() {
        const menu = document.getElementById('mobile-menu');
        if (menu) {
            menu.classList.toggle('hidden');
        }
    }

    document.addEventListener('click', function (event) {
        const userMenu = document.getElementById('user-menu');
        const mobileMenu = document.getElementById('mobile-menu');
        const notificationMenu = document.getElementById('admin-notification-menu');
        if (userMenu && !event.target.closest('[onclick="toggleUserMenu()"]') && !userMenu.contains(event.target)) {
            userMenu.classList.add('hidden');
        }
        if (notificationMenu && !event.target.closest('[onclick="toggleAdminNotifications()"]') && !notificationMenu.contains(event.target)) {
            notificationMenu.classList.add('hidden');
        }
        if (mobileMenu && !event.target.closest('[onclick="toggleMobileMenu()"]') && !mobileMenu.contains(event.target)) {
            mobileMenu.classList.add('hidden');
        }
    });
</script>
