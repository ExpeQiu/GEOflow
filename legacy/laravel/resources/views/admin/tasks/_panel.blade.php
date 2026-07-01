@php
    $formatTaskErrorSnippet = static function (?string $message, int $maxLength = 72): string {
        $message = trim((string) $message);
        if ($message === '') {
            return '';
        }
        if (str_contains($message, '任务已暂停') || str_contains($message, '管理员手动停止')) {
            return __('admin.tasks.failure.paused_detail');
        }
        if (str_contains($message, 'AI返回空正文')) {
            return __('admin.tasks.failure.empty_content_detail');
        }
        if (str_contains($message, '正文过短')) {
            return __('admin.tasks.failure.content_too_short_detail');
        }
        if (str_contains($message, '没有可用的标题')) {
            return __('admin.tasks.failure.title_exhausted_detail');
        }
        if (preg_match('/CURL错误:\s*Operation timed out after\s+(\d+)\s+milliseconds/i', $message, $matches)) {
            $seconds = max(1, (int) round(((int) $matches[1]) / 1000));
            return __('admin.tasks.failure.model_timeout_detail', ['seconds' => $seconds]);
        }
        if (mb_strlen($message, 'UTF-8') <= $maxLength) {
            return $message;
        }
        return mb_substr($message, 0, $maxLength - 1, 'UTF-8').'…';
    };
    $describeTaskFailure = static function (?string $message) use ($formatTaskErrorSnippet): array {
        $message = trim((string) $message);
        if ($message === '') {
            return ['label' => __('admin.tasks.failure.execution_failed'), 'detail' => '', 'tone' => 'red'];
        }
        if (str_contains($message, 'AI返回空正文')) {
            return ['label' => __('admin.tasks.failure.empty_content'), 'detail' => __('admin.tasks.failure.empty_content_detail'), 'tone' => 'red'];
        }
        if (str_contains($message, '正文过短')) {
            return ['label' => __('admin.tasks.failure.content_too_short'), 'detail' => __('admin.tasks.failure.content_too_short_detail'), 'tone' => 'amber'];
        }
        if (str_contains($message, '没有可用的标题')) {
            return ['label' => __('admin.tasks.failure.title_exhausted'), 'detail' => __('admin.tasks.failure.title_exhausted_detail'), 'tone' => 'amber'];
        }
        if (str_contains($message, '任务已暂停') || str_contains($message, '管理员手动停止')) {
            return ['label' => __('admin.tasks.failure.paused'), 'detail' => __('admin.tasks.failure.paused_detail'), 'tone' => 'slate'];
        }
        return ['label' => __('admin.tasks.failure.execution_failed'), 'detail' => $formatTaskErrorSnippet($message, 110), 'tone' => 'red'];
    };
    $getFailureToneClasses = static function (string $tone): array {
        return match ($tone) {
            'amber' => ['chip' => 'bg-amber-50 text-amber-700 border-amber-200', 'card' => 'border-amber-200 bg-amber-50 text-amber-800', 'detail' => 'text-amber-700'],
            'slate' => ['chip' => 'bg-slate-50 text-slate-700 border-slate-200', 'card' => 'border-slate-200 bg-slate-50 text-slate-800', 'detail' => 'text-slate-600'],
            default => ['chip' => 'bg-red-50 text-red-700 border-red-200', 'card' => 'border-red-200 bg-red-50 text-red-800', 'detail' => 'text-red-700'],
        };
    };
    $standalone = (bool) ($standalone ?? false);
@endphp
@if ($standalone)
    <div class="mb-8 flex items-center justify-between">
        <div>
            <h1 class="text-2xl font-bold text-gray-900">{{ __('admin.tasks.page_title') }}</h1>
            <p class="mt-1 text-sm text-gray-600">{{ __('admin.tasks.page_subtitle') }}</p>
        </div>
        <div class="flex space-x-3">
            <a href="{{ route('admin.tasks.create') }}" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
                <i data-lucide="plus" class="w-4 h-4 mr-2"></i>
                {{ __('admin.button.create_task') }}
            </a>
            <button onclick="executeAllActiveTasks()" class="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50">
                <i data-lucide="play" class="w-4 h-4 mr-2"></i>
                {{ __('admin.button.run_all_tasks') }}
            </button>
        </div>
    </div>
@endif

        @if (!empty($legacyError))
            <div class="admin-flash-alert mb-4 bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
                <span class="block sm:inline">{{ $legacyError }}</span>
            </div>
        @endif

        <div class="bg-white shadow rounded-lg">
            <div class="px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-medium text-gray-900">{{ __('admin.tasks.list_title') }}</h3>
            </div>

            @if (empty($tasks))
                <div class="px-6 py-8 text-center">
                    <i data-lucide="inbox" class="w-12 h-12 mx-auto text-gray-400 mb-4"></i>
                    <h3 class="text-lg font-medium text-gray-900 mb-2">{{ __('admin.tasks.empty_title') }}</h3>
                    <p class="text-gray-500 mb-4">{{ __('admin.tasks.empty_desc') }}</p>
                    <a href="{{ route('admin.tasks.create') }}" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700">
                        <i data-lucide="plus" class="w-4 h-4 mr-2"></i>
                        {{ __('admin.button.new_task') }}
                    </a>
                </div>
            @else
                <div class="overflow-x-auto">
                    <table class="w-full min-w-[1110px] table-fixed divide-y divide-gray-200">
                        <thead class="bg-gray-50">
                        <tr>
                            <th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.name') }}</th>
                            <th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.created_at') }}</th>
                            <th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.model') }}</th>
                            <th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.article_stats') }}</th>
                            <th class="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.loop_count') }}</th>
                            <th class="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.status') }}</th>
                            <th class="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ __('admin.tasks.column.actions') }}</th>
                        </tr>
                        </thead>
                        <tbody class="bg-white divide-y divide-gray-200">
                        @foreach ($tasks as $task)
                            @php
                                $failureInfo = $describeTaskFailure($task['batch_error_message'] ?? '');
                                $failureClasses = $getFailureToneClasses($failureInfo['tone']);
                                $hasVisibleFailure = !empty($task['batch_error_message']) && in_array($task['batch_status'], ['failed', 'cancelled'], true);
                                $publishScope = (string) ($task['publish_scope'] ?? 'local_and_distribution');
                                $publishScopeClass = match ($publishScope) {
                                    'distribution_only' => 'bg-violet-50 text-violet-700 ring-violet-100',
                                    'local_only' => 'bg-slate-50 text-slate-700 ring-slate-200',
                                    default => 'bg-blue-50 text-blue-700 ring-blue-100',
                                };
                                $publishScopeLabel = match ($publishScope) {
                                    'distribution_only' => __('admin.tasks.publish_scope.distribution_only'),
                                    'local_only' => __('admin.tasks.publish_scope.local_only'),
                                    default => __('admin.tasks.publish_scope.local_and_distribution'),
                                };
                            @endphp
                            <tr class="hover:bg-gray-50">
                                <td class="px-5 py-4 align-top">
                                    <div class="text-sm font-medium leading-6 text-gray-900 break-words">{{ $task['name'] ?? '' }}</div>
                                    <div class="mt-1 flex flex-wrap items-center gap-2">
                                        <span id="task-publish-scope-{{ (int) $task['id'] }}" class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 {{ $publishScopeClass }}">{{ $publishScopeLabel }}</span>
                                    </div>
                                    <div class="mt-1 text-sm text-gray-500 break-words">{{ __('admin.tasks.label.title_library') }}: {{ $task['title_library_name'] ?? '' }}</div>
                                    <div id="task-eval-hint-{{ (int) $task['id'] }}" class="mt-2"></div>
                                    @if ($hasVisibleFailure)
                                        <div class="mt-2 rounded-md border px-3 py-2 text-xs {{ $failureClasses['card'] }}">
                                            <span class="inline-flex items-center rounded-full border px-2 py-0.5 font-medium {{ $failureClasses['chip'] }}">{{ $failureInfo['label'] }}</span>
                                            @if (!empty($failureInfo['detail']))
                                                <div class="mt-1 {{ $failureClasses['detail'] }}">{{ $failureInfo['detail'] }}</div>
                                            @endif
                                        </div>
                                    @endif
                                </td>
                                <td class="px-5 py-4 align-top whitespace-nowrap text-sm text-gray-500">{{ !empty($task['created_at']) ? \Illuminate\Support\Carbon::parse($task['created_at'])->format('Y-m-d H:i') : '' }}</td>
                                <td class="px-5 py-4 align-top text-sm text-gray-500">
                                    <div class="break-words leading-6">{{ $task['ai_model_name'] ?? '' }}</div>
                                    <div class="mt-1">
                                        <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {{ (($task['model_selection_mode'] ?? 'fixed') === 'smart_failover') ? 'bg-violet-100 text-violet-800' : 'bg-slate-100 text-slate-700' }}">
                                            {{ (($task['model_selection_mode'] ?? 'fixed') === 'smart_failover') ? __('admin.tasks.mode.smart_failover') : __('admin.tasks.mode.fixed') }}
                                        </span>
                                    </div>
                                </td>
                                <td class="px-5 py-4 align-top whitespace-nowrap text-sm text-gray-500">
                                    @php
                                        $articleLimit = max(1, (int) ($task['article_limit'] ?? $task['draft_limit'] ?? 10));
                                        $createdForProgress = min($articleLimit, (int) ($task['created_count'] ?? $task['total_articles'] ?? 0));
                                        $progressPercent = (int) floor(($createdForProgress / $articleLimit) * 100);
                                        $distributionTotal = (int) ($task['distribution_total_count'] ?? 0);
                                        $distributionSynced = (int) ($task['distribution_synced_count'] ?? 0);
                                        $distributionFailed = (int) ($task['distribution_failed_count'] ?? 0);
                                        $distributionPending = max(0, $distributionTotal - $distributionSynced - $distributionFailed);
                                        $taskDistributionBadge = null;
                                        if ($distributionTotal > 0) {
                                            if ($distributionFailed > 0) {
                                                $taskDistributionBadge = [
                                                    'label' => __('admin.distribution.task_status.failed', ['count' => $distributionFailed]),
                                                    'class' => 'bg-red-50 text-red-700 ring-red-100',
                                                ];
                                            } elseif ($distributionSynced >= $distributionTotal) {
                                                $taskDistributionBadge = [
                                                    'label' => __('admin.distribution.task_status.synced', ['count' => $distributionTotal]),
                                                    'class' => 'bg-emerald-50 text-emerald-700 ring-emerald-100',
                                                ];
                                            } else {
                                                $taskDistributionBadge = [
                                                    'label' => __('admin.distribution.task_status.queued', ['count' => $distributionPending]),
                                                    'class' => 'bg-sky-50 text-sky-700 ring-sky-100',
                                                ];
                                            }
                                        }
                                    @endphp
                                    <div id="task-created-{{ (int) $task['id'] }}">{{ __('admin.tasks.label.created_of_limit', ['created' => (int) ($task['created_count'] ?? $task['total_articles'] ?? 0), 'limit' => $articleLimit]) }}</div>
                                    <div id="task-published-{{ (int) $task['id'] }}">{{ __('admin.tasks.label.published_articles', ['count' => (int) ($task['published_articles'] ?? 0)]) }}</div>
                                    <div id="task-drafts-{{ (int) $task['id'] }}">{{ __('admin.tasks.label.draft_articles', ['count' => (int) ($task['draft_articles'] ?? 0)]) }}</div>
                                    <div class="mt-2 h-1.5 w-28 overflow-hidden rounded-full bg-gray-200">
                                        <div id="task-progress-{{ (int) $task['id'] }}" class="h-full rounded-full bg-blue-600" style="width: {{ $progressPercent }}%"></div>
                                    </div>
                                    @if($taskDistributionBadge !== null)
                                        <div class="mt-2">
                                            <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 {{ $taskDistributionBadge['class'] }}">
                                                <i data-lucide="send" class="mr-1 h-3 w-3"></i>
                                                {{ $taskDistributionBadge['label'] }}
                                            </span>
                                        </div>
                                    @endif
                                </td>
                                <td class="px-5 py-4 align-top whitespace-nowrap text-sm text-gray-500">
                                    <span id="task-loop-{{ (int) $task['id'] }}">{{ __('admin.tasks.label.loop_times', ['count' => (int) ($task['loop_count'] ?? 0)]) }}</span>
                                    <div id="task-publish-interval-{{ (int) $task['id'] }}" class="mt-1 text-xs text-gray-400">
                                        {{ __('admin.tasks.label.publish_interval_minutes', ['count' => max(1, (int) ceil(((int) ($task['publish_interval'] ?? 3600)) / 60))]) }}
                                    </div>
                                </td>
                                <td class="px-4 py-4 align-top">
                                    <form method="POST" action="{{ route('admin.tasks.toggle-status', ['taskId' => (int) $task['id']]) }}" class="inline" id="status-form-{{ (int) $task['id'] }}">
                                        @csrf
                                        <input type="hidden" name="status" value="{{ $task['status'] }}">
                                        <label class="inline-flex items-center">
                                            <input type="checkbox" @checked(($task['status'] ?? '') === 'active') onchange="handleStatusToggle({{ (int) $task['id'] }}, this)" class="rounded border-gray-300 text-blue-600 shadow-sm">
                                            <span class="ml-2 text-sm {{ ($task['status'] ?? '') === 'active' ? 'text-green-600' : 'text-gray-500' }}">
                                                {{ ($task['status'] ?? '') === 'active' ? __('admin.tasks.status.enabled') : __('admin.tasks.status.disabled') }}
                                            </span>
                                        </label>
                                    </form>
                                </td>
                                <td class="px-3 py-4 align-top">
                                    <div class="flex w-fit items-center gap-1.5">
                                        @if (($task['status'] ?? '') === 'active')
                                            <button onclick="stopBatchExecution({{ (int) $task['id'] }}, '{{ addslashes((string) ($task['name'] ?? '')) }}')" data-batch-action="stop" class="inline-flex items-center justify-center w-8 h-8 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors border border-red-200" title="{{ __('admin.tasks.action.stop_batch') }}" aria-label="{{ __('admin.tasks.action.stop_batch') }}" id="batch-btn-{{ (int) $task['id'] }}">
                                                <i data-lucide="square" class="w-4 h-4"></i>
                                            </button>
                                        @else
                                            <button onclick="startBatchExecution({{ (int) $task['id'] }}, '{{ addslashes((string) ($task['name'] ?? '')) }}')" data-batch-action="start" class="inline-flex items-center justify-center w-8 h-8 text-green-600 hover:text-green-800 hover:bg-green-50 rounded-md transition-colors border border-green-200" title="{{ __('admin.tasks.action.start_batch') }}" aria-label="{{ __('admin.tasks.action.start_batch') }}" id="batch-btn-{{ (int) $task['id'] }}">
                                                <i data-lucide="play" class="w-4 h-4"></i>
                                            </button>
                                        @endif

                                        <a href="{{ route('admin.tasks.edit', ['taskId' => (int) $task['id']]) }}" class="inline-flex items-center justify-center w-8 h-8 text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-md transition-colors border border-blue-200" title="{{ __('admin.tasks.action.settings') }}">
                                            <i data-lucide="settings" class="w-4 h-4"></i>
                                        </a>

                                        <a href="{{ route('admin.articles.index', ['task_id' => (int) $task['id']]) }}" class="inline-flex items-center justify-center w-8 h-8 text-green-600 hover:text-green-800 hover:bg-green-50 rounded-md transition-colors border border-green-200" title="{{ __('admin.tasks.action.articles') }}">
                                            <i data-lucide="file-text" class="w-4 h-4"></i>
                                        </a>

                                        <form method="POST" action="{{ route('admin.tasks.delete', ['taskId' => (int) $task['id']]) }}" class="inline" onsubmit="return confirm(@js(__('admin.tasks.confirm.delete')))">
                                            @csrf
                                            <button type="submit" class="inline-flex items-center justify-center w-8 h-8 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors border border-red-200" title="{{ __('admin.tasks.action.delete') }}">
                                                <i data-lucide="trash-2" class="w-4 h-4"></i>
                                            </button>
                                        </form>
                                    </div>
                                    <div class="mt-2 max-w-[165px]" id="batch-status-{{ (int) $task['id'] }}"></div>
                                </td>
                            </tr>
                        @endforeach
                        </tbody>
                    </table>
                </div>
            @endif
        </div>

        <div class="mt-8 grid grid-cols-1 md:grid-cols-4 gap-6">
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i data-lucide="zap" class="h-6 w-6 text-blue-600"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <div class="text-sm text-gray-500">{{ __('admin.tasks.stats.total_tasks') }}</div>
                            <div id="stats-total-tasks" class="text-2xl font-semibold text-gray-900">{{ count($tasks) }}</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i data-lucide="play" class="h-6 w-6 text-green-600"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <div class="text-sm text-gray-500">{{ __('admin.tasks.stats.enabled') }}</div>
                            <div id="stats-enabled-tasks" class="text-2xl font-semibold text-gray-900">{{ count(array_filter($tasks, static fn (array $row): bool => ($row['status'] ?? '') === 'active')) }}</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i data-lucide="file-text" class="h-6 w-6 text-purple-600"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <div class="text-sm text-gray-500">{{ __('admin.tasks.stats.total_articles') }}</div>
                            <div id="stats-total-articles" class="text-2xl font-semibold text-gray-900">{{ array_sum(array_map(static fn (array $row): int => (int) ($row['total_articles'] ?? 0), $tasks)) }}</div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="p-5">
                    <div class="flex items-center">
                        <div class="flex-shrink-0">
                            <i data-lucide="globe" class="h-6 w-6 text-orange-600"></i>
                        </div>
                        <div class="ml-5 w-0 flex-1">
                            <div class="text-sm text-gray-500">{{ __('admin.tasks.stats.total_published') }}</div>
                            <div id="stats-total-published" class="text-2xl font-semibold text-gray-900">{{ array_sum(array_map(static fn (array $row): int => (int) ($row['published_articles'] ?? 0), $tasks)) }}</div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <div class="mt-8 grid grid-cols-1 xl:grid-cols-3 gap-6">
            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="px-5 py-4 border-b border-gray-200">
                    <h3 class="text-base font-medium text-gray-900">{{ __('admin.tasks.worker.title') }}</h3>
                </div>
                <div class="p-5">
                    <div id="worker-overview-container">
                        @if (empty($workers))
                            <p class="text-sm text-gray-500">{{ __('admin.tasks.worker.none') }}</p>
                        @else
                            <div class="space-y-3">
                                @foreach ($workers as $worker)
                                    <div class="rounded-lg border border-gray-200 px-3 py-3">
                                        <div class="flex items-center justify-between gap-3">
                                            <span class="font-mono text-xs text-gray-700">{{ $worker['worker_id'] ?? '' }}</span>
                                            <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium {{ ($worker['status'] ?? '') === 'running' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-gray-50 text-gray-700 border border-gray-200' }}">
                                                {{ $worker['status'] ?? 'idle' }}
                                            </span>
                                        </div>
                                        <div class="mt-2 text-xs text-gray-500">
                                            <div>{{ __('admin.tasks.worker.current_job') }}: {{ !empty($worker['current_job_id']) ? '#'.(int) $worker['current_job_id'] : __('admin.tasks.worker.idle') }}</div>
                                            <div>{{ __('admin.tasks.worker.last_seen') }}: {{ (string) ($worker['last_seen_at'] ?? '') }}</div>
                                        </div>
                                    </div>
                                @endforeach
                            </div>
                        @endif
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="px-5 py-4 border-b border-gray-200">
                    <h3 class="text-base font-medium text-gray-900">{{ __('admin.tasks.queue.title') }}</h3>
                </div>
                <div class="p-5">
                    <div class="grid grid-cols-2 gap-3">
                        <div class="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
                            <div class="text-xs text-blue-700">{{ __('admin.tasks.queue.pending') }}</div>
                            <div class="mt-1 text-2xl font-semibold text-blue-900" id="queue-pending">{{ (int) ($queueStats['pending'] ?? 0) }}</div>
                        </div>
                        <div class="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3">
                            <div class="text-xs text-emerald-700">{{ __('admin.tasks.queue.running') }}</div>
                            <div class="mt-1 text-2xl font-semibold text-emerald-900" id="queue-running">{{ (int) ($queueStats['running'] ?? 0) }}</div>
                        </div>
                        <div class="rounded-lg border border-red-200 bg-red-50 px-4 py-3">
                            <div class="text-xs text-red-700">{{ __('admin.tasks.queue.failed') }}</div>
                            <div class="mt-1 text-2xl font-semibold text-red-900" id="queue-failed">{{ (int) ($queueStats['failed'] ?? 0) }}</div>
                        </div>
                        <div class="rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
                            <div class="text-xs text-gray-700">{{ __('admin.tasks.queue.completed') }}</div>
                            <div class="mt-1 text-2xl font-semibold text-gray-900" id="queue-completed">{{ (int) ($queueStats['completed'] ?? 0) }}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div class="bg-white overflow-hidden shadow rounded-lg">
                <div class="px-5 py-4 border-b border-gray-200">
                    <h3 class="text-base font-medium text-gray-900">{{ __('admin.tasks.jobs.recent') }}</h3>
                </div>
                <div class="p-5">
                    <div id="recent-runs-container">
                        @if (empty($recentJobs))
                            <p class="text-sm text-gray-500">{{ __('admin.tasks.jobs.none') }}</p>
                        @else
                            <div class="space-y-3">
                                @foreach ($recentJobs as $job)
                                    <div class="rounded-lg border border-gray-200 px-3 py-3">
                                        <div class="flex items-center justify-between gap-3">
                                            <div class="min-w-0">
                                                <div class="text-sm font-medium text-gray-900 truncate">{{ $job['task_name'] ?: __('admin.tasks.jobs.unknown_task') }}</div>
                                                <div class="text-xs text-gray-500">Job #{{ (int) $job['id'] }} · {{ __('admin.tasks.jobs.task_prefix') }} #{{ (int) $job['task_id'] }}</div>
                                            </div>
                                            <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border
                                                @if (($job['status'] ?? '') === 'running') bg-emerald-50 text-emerald-700 border-emerald-200
                                                @elseif (($job['status'] ?? '') === 'pending') bg-blue-50 text-blue-700 border-blue-200
                                                @elseif (($job['status'] ?? '') === 'failed') bg-red-50 text-red-700 border-red-200
                                                @else bg-gray-50 text-gray-700 border-gray-200 @endif">
                                                {{ $job['status'] ?? 'idle' }}
                                            </span>
                                        </div>
                                        <div class="mt-2 text-xs text-gray-500">
                                            <div>{{ __('admin.tasks.jobs.updated_at') }}: {{ (string) ($job['updated_at'] ?? '') }}</div>
                                        </div>
                                    </div>
                                @endforeach
                            </div>
                        @endif
                    </div>
                </div>
            </div>
        </div>
