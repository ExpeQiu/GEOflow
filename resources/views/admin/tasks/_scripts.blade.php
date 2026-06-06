<script src="https://js.pusher.com/8.4.0/pusher.min.js"></script>
@php
    $taskInitialOverview = [
        'tasks' => $tasks,
        'queue_overview' => $queueStats,
        'worker_overview' => $workers,
        'recent_runs' => $recentJobs,
    ];
@endphp
<script>
const TASK_I18N = @json($taskI18n, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
const TASK_REALTIME = @json($taskRealtime, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
const TASK_HEALTH_URL = @js(route('admin.tasks.health', [], false));
const TASK_BATCH_URL = @js(route('admin.tasks.batch', [], false));
const TASK_INITIAL_OVERVIEW = @json($taskInitialOverview, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
const TASK_TEXT = {
    workerNone: @js(__('admin.tasks.worker.none')),
    workerCurrentJob: @js(__('admin.tasks.worker.current_job')),
    workerIdle: @js(__('admin.tasks.worker.idle')),
    workerLastSeen: @js(__('admin.tasks.worker.last_seen')),
    jobsNone: @js(__('admin.tasks.jobs.none')),
    jobsUnknownTask: @js(__('admin.tasks.jobs.unknown_task')),
    jobsTaskPrefix: @js(__('admin.tasks.jobs.task_prefix')),
    jobsUpdatedAt: @js(__('admin.tasks.jobs.updated_at')),
};

function renderIcons() { if (typeof lucide !== 'undefined') { lucide.createIcons(); } }

function showNotification(type, message) { if (window.AdminUtils && typeof window.AdminUtils.showToast === 'function') { window.AdminUtils.showToast(message, type); return; } alert(message); }

function setButtonLoading(btn, text, classes) { btn.disabled = true; btn.className = classes; btn.innerHTML = `<i data-lucide="loader-2" class="h-4 w-4 animate-spin"></i><span class="sr-only">${text}</span>`; renderIcons(); }

function updateBatchButton(btn, taskId, taskName, isActive) {
    if (!btn) return;
    btn.disabled = false;
    btn.dataset.batchAction = isActive ? 'stop' : 'start';
    btn.className = isActive ? 'inline-flex items-center justify-center w-8 h-8 text-red-600 hover:text-red-800 hover:bg-red-50 rounded-md transition-colors border border-red-200' : 'inline-flex items-center justify-center w-8 h-8 text-green-600 hover:text-green-800 hover:bg-green-50 rounded-md transition-colors border border-green-200';
    btn.innerHTML = isActive ? '<i data-lucide="square" class="w-4 h-4"></i>' : '<i data-lucide="play" class="w-4 h-4"></i>';
    btn.title = isActive ? TASK_I18N.stopBatch : TASK_I18N.startBatch;
    btn.setAttribute('aria-label', btn.title);
    btn.onclick = isActive ? () => stopBatchExecution(taskId, taskName) : () => startBatchExecution(taskId, taskName);
    renderIcons();
}

function formatEstimatedTime(seconds) { if (seconds < 60) return `${seconds}${TASK_I18N.secondsSuffix}`; if (seconds < 3600) return `${Math.round(seconds / 60)}${TASK_I18N.minutesSuffix}`; if (seconds < 86400) return `${Math.round(seconds / 3600)}${TASK_I18N.hoursSuffix}`; return `${Math.round(seconds / 86400)}${TASK_I18N.daysSuffix}`; }

function escapeHtml(value) { return String(value).replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#039;'); }
function truncateText(value, maxLength) { return value.length <= maxLength ? value : `${value.slice(0, maxLength - 1)}…`; }
function normalizeRuntimeError(message) { return String(message || '').trim(); }
function getFailureMeta() { return {label: TASK_I18N.recentFailed, chipClasses: 'bg-red-50 text-red-700 border-red-200', detailClasses: 'text-red-700'}; }

function publishScopeLabel(scope) {
    if (scope === 'distribution_only') return TASK_I18N.publishScopeDistributionOnly;
    if (scope === 'local_only') return TASK_I18N.publishScopeLocalOnly;
    return TASK_I18N.publishScopeLocalAndDistribution;
}

function publishScopeClasses(scope) {
    if (scope === 'distribution_only') return 'bg-violet-50 text-violet-700 ring-violet-100';
    if (scope === 'local_only') return 'bg-slate-50 text-slate-700 ring-slate-200';
    return 'bg-blue-50 text-blue-700 ring-blue-100';
}

function buildEvalHintHtml(task) {
    const pending = Number(task.eval_pending_count || 0);
    const failed = Number(task.eval_failed_count || 0);
    if (pending <= 0 && failed <= 0) return '';
    const parts = [];
    if (pending > 0) parts.push(`<span class="text-amber-700">${escapeHtml(TASK_I18N.evalPending.replace('__COUNT__', pending))}</span>`);
    if (failed > 0) parts.push(`<span class="text-red-700">${escapeHtml(TASK_I18N.evalFailed.replace('__COUNT__', failed))}</span>`);
    const diagnosticsUrl = TASK_I18N.geoEvalDiagnosticsUrl || '#';
    return `<div class="flex flex-col gap-1 text-xs">${parts.join(' · ')}<a href="${escapeHtml(diagnosticsUrl)}" class="font-medium text-cyan-700 hover:underline">${escapeHtml(TASK_I18N.openDiagnostics)}</a></div>`;
}

function updatePublishScopeBadge(task) {
    const badge = document.getElementById(`task-publish-scope-${task.id}`);
    if (!badge) return;
    const scope = String(task.publish_scope || 'local_and_distribution');
    badge.textContent = publishScopeLabel(scope);
    badge.className = `inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ${publishScopeClasses(scope)}`;
}

function updateEvalHint(task) {
    const hint = document.getElementById(`task-eval-hint-${task.id}`);
    if (!hint) return;
    const batchStatus = String(task.batch_status || '');
    const pending = Number(task.eval_pending_count || 0);
    const failed = Number(task.eval_failed_count || 0);
    const showHint = pending > 0 || failed > 0;
    if (!showHint || !['draft_pool_full', 'waiting_publish', 'waiting'].includes(batchStatus)) {
        hint.innerHTML = '';
        return;
    }
    hint.innerHTML = buildEvalHintHtml(task);
}

function formatTaskDateTime(value) {
    if (!value) return '';
    const date = new Date(String(value).replace(' ', 'T'));
    if (Number.isNaN(date.getTime())) return String(value);
    const pad = number => String(number).padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function updateBatchStatus(task) {
    const statusDiv = document.getElementById(`batch-status-${task.id}`);
    if (!statusDiv) return;
    const createdCount = Number(task.created_count || 0);
    const articleLimit = Number(task.article_limit || task.draft_limit || 0);
    const pendingJobs = Number(task.pending_jobs || 0);
    const runningJobs = Number(task.running_jobs || 0);
    const isRunning = task.batch_status === 'running' || task.batch_status === 'pending';
    const errorMessage = normalizeRuntimeError(task.batch_error_message || '');
    if (!isRunning) {
        if (task.batch_status === 'failed') {
            const failureMeta = getFailureMeta(errorMessage);
            statusDiv.innerHTML = `<div class="flex flex-col gap-1 text-xs"><span class="inline-flex items-center justify-center rounded-full border px-2 py-1 ${failureMeta.chipClasses}">${escapeHtml(failureMeta.label)}</span>${errorMessage ? `<div class="mx-auto max-w-[220px] break-words leading-5 ${failureMeta.detailClasses}">${escapeHtml(truncateText(errorMessage, 60))}</div>` : ''}</div>`;
        } else if (task.batch_status === 'completed') {
            statusDiv.innerHTML = `<span class="text-xs text-emerald-600 bg-emerald-50 px-2 py-1 rounded-full border border-emerald-200">${escapeHtml(TASK_I18N.completed)}</span>`;
        } else if (task.batch_status === 'waiting') {
            const nextRunAt = formatTaskDateTime(task.next_run_at || '');
            statusDiv.innerHTML = `<div class="flex flex-col gap-1 text-xs"><span class="inline-flex w-fit items-center rounded-full border px-2 py-1 bg-slate-50 text-slate-700 border-slate-200">${escapeHtml(TASK_I18N.waiting)}</span>${nextRunAt ? `<div class="text-gray-500">${escapeHtml(TASK_I18N.nextRunAt.replace('__TIME__', nextRunAt))}</div>` : ''}</div>`;
        } else if (task.batch_status === 'waiting_publish') {
            const nextPublishAt = formatTaskDateTime(task.next_publish_at || task.next_run_at || '');
            statusDiv.innerHTML = `<div class="flex flex-col gap-1 text-xs"><span class="inline-flex w-fit items-center rounded-full border px-2 py-1 bg-cyan-50 text-cyan-700 border-cyan-200">${escapeHtml(TASK_I18N.waitingPublish)}</span>${nextPublishAt ? `<div class="text-gray-500">${escapeHtml(TASK_I18N.nextRunAt.replace('__TIME__', nextPublishAt))}</div>` : ''}</div>`;
        } else if (task.batch_status === 'draft_pool_full') {
            const evalBlocked = Number(task.eval_blocked_drafts || 0) > 0;
            const poolLabel = evalBlocked ? TASK_I18N.draftPoolEvalBlocked : TASK_I18N.draftPoolFull;
            statusDiv.innerHTML = `<span class="text-xs text-orange-700 bg-orange-50 px-2 py-1 rounded-full border border-orange-200">${escapeHtml(poolLabel)}</span>`;
        } else if (task.batch_status === 'limit_reached') {
            statusDiv.innerHTML = `<span class="text-xs text-amber-700 bg-amber-50 px-2 py-1 rounded-full border border-amber-200">${escapeHtml(TASK_I18N.limitReached)}</span>`;
        } else { statusDiv.innerHTML = ''; }
        return;
    }
    const stateLabel = task.batch_status === 'pending' ? TASK_I18N.queued : TASK_I18N.running;
    const remainingArticles = Math.max(0, articleLimit - createdCount);
    const estimatedTime = formatEstimatedTime(remainingArticles * Number(task.publish_interval || 3600));
    statusDiv.innerHTML = `<div class="flex flex-col gap-1 text-xs"><div class="flex items-center gap-2"><span class="inline-flex items-center rounded-full border px-2 py-0.5 bg-blue-50 text-blue-700 border-blue-200"><i data-lucide="activity" class="h-3 w-3 mr-1"></i>${stateLabel}</span><span class="text-gray-600">${createdCount}/${articleLimit}</span></div><div class="text-gray-500">${TASK_I18N.pendingRunning.replace('__PENDING__', pendingJobs).replace('__RUNNING__', runningJobs)}${remainingArticles > 0 ? ` · ${TASK_I18N.estimated.replace('__TIME__', estimatedTime)}` : ''}</div></div>`;
    renderIcons();
}

function updateTaskUI(task) {
    const btn = document.getElementById(`batch-btn-${task.id}`);
    const isActive = task.status === 'active';
    updateBatchButton(btn, task.id, task.name, isActive);
    updateTaskStatusToggle(task.id, isActive);
    updatePublishScopeBadge(task);
    updateBatchStatus(task);
    updateEvalHint(task);
}

function updateTaskStatusToggle(taskId, isActive) {
    const form = document.getElementById(`status-form-${taskId}`);
    if (!form) return;
    const hidden = form.querySelector('input[name="status"]');
    const checkbox = form.querySelector('input[type="checkbox"]');
    const label = form.querySelector('span');
    if (hidden) hidden.value = isActive ? 'active' : 'paused';
    if (checkbox) checkbox.checked = isActive;
    if (label) {
        label.textContent = isActive ? TASK_I18N.enabledStatus : TASK_I18N.disabledStatus;
        label.className = `ml-2 text-sm ${isActive ? 'text-green-600' : 'text-gray-500'}`;
    }
}

function updateTaskCounters(task) {
    const createdEl = document.getElementById(`task-created-${task.id}`);
    const publishedEl = document.getElementById(`task-published-${task.id}`);
    const draftsEl = document.getElementById(`task-drafts-${task.id}`);
    const progressEl = document.getElementById(`task-progress-${task.id}`);
    const loopEl = document.getElementById(`task-loop-${task.id}`);
    const publishIntervalEl = document.getElementById(`task-publish-interval-${task.id}`);
    const createdCount = Number(task.created_count || task.total_articles || 0);
    const articleLimit = Math.max(1, Number(task.article_limit || task.draft_limit || 10));
    if (createdEl) {
        createdEl.textContent = TASK_I18N.createdOfLimitLabel.replace('__CREATED__', String(createdCount)).replace('__LIMIT__', String(articleLimit));
    }
    if (publishedEl) {
        publishedEl.textContent = TASK_I18N.publishedArticlesLabel.replace('__COUNT__', String(Number(task.published_articles || 0)));
    }
    if (draftsEl) {
        draftsEl.textContent = TASK_I18N.draftArticlesLabel.replace('__COUNT__', String(Number(task.draft_articles || 0)));
    }
    if (progressEl) {
        const percent = Math.max(0, Math.min(100, Math.floor((createdCount / articleLimit) * 100)));
        progressEl.style.width = `${percent}%`;
    }
    if (loopEl) {
        loopEl.textContent = TASK_I18N.loopTimesLabel.replace('__COUNT__', String(Number(task.loop_count || 0)));
    }
    if (publishIntervalEl) {
        const minutes = Math.max(1, Math.ceil(Number(task.publish_interval || 3600) / 60));
        publishIntervalEl.textContent = TASK_I18N.publishIntervalMinutes.replace('__COUNT__', String(minutes));
    }
}

function updateQueueOverview(queueOverview) {
    document.getElementById('queue-pending').textContent = String(Number(queueOverview.pending || 0));
    document.getElementById('queue-running').textContent = String(Number(queueOverview.running || 0));
    document.getElementById('queue-failed').textContent = String(Number(queueOverview.failed || 0));
    document.getElementById('queue-completed').textContent = String(Number(queueOverview.completed || 0));
}

function updateTopStats(tasks) {
    const totalTasks = Array.isArray(tasks) ? tasks.length : 0;
    const enabledTasks = (Array.isArray(tasks) ? tasks : []).filter(task => task.status === 'active').length;
    const totalArticles = (Array.isArray(tasks) ? tasks : []).reduce((sum, task) => sum + Number(task.total_articles || 0), 0);
    const totalPublished = (Array.isArray(tasks) ? tasks : []).reduce((sum, task) => sum + Number(task.published_articles || 0), 0);
    document.getElementById('stats-total-tasks').textContent = String(totalTasks);
    document.getElementById('stats-enabled-tasks').textContent = String(enabledTasks);
    document.getElementById('stats-total-articles').textContent = String(totalArticles);
    document.getElementById('stats-total-published').textContent = String(totalPublished);
}

function renderWorkerOverview(workers) {
    const container = document.getElementById('worker-overview-container');
    if (!container) return;
    if (!Array.isArray(workers) || workers.length === 0) {
        container.innerHTML = `<p class="text-sm text-gray-500">${escapeHtml(TASK_TEXT.workerNone)}</p>`;
        return;
    }
    const html = workers.map(worker => {
        const status = String(worker.status || 'idle');
        const statusClasses = status === 'running'
            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
            : 'bg-gray-50 text-gray-700 border border-gray-200';
        const currentJob = worker.current_job_id ? `#${Number(worker.current_job_id)}` : escapeHtml(TASK_TEXT.workerIdle);
        return `<div class="rounded-lg border border-gray-200 px-3 py-3">
            <div class="flex items-center justify-between gap-3">
                <span class="font-mono text-xs text-gray-700">${escapeHtml(String(worker.worker_id || ''))}</span>
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusClasses}">${escapeHtml(status)}</span>
            </div>
            <div class="mt-2 text-xs text-gray-500">
                <div>${escapeHtml(TASK_TEXT.workerCurrentJob)}: ${currentJob}</div>
                <div>${escapeHtml(TASK_TEXT.workerLastSeen)}: ${escapeHtml(String(worker.last_seen_at || ''))}</div>
            </div>
        </div>`;
    }).join('');
    container.innerHTML = `<div class="space-y-3">${html}</div>`;
}

function renderRecentRuns(recentRuns) {
    const container = document.getElementById('recent-runs-container');
    if (!container) return;
    if (!Array.isArray(recentRuns) || recentRuns.length === 0) {
        container.innerHTML = `<p class="text-sm text-gray-500">${escapeHtml(TASK_TEXT.jobsNone)}</p>`;
        return;
    }
    const html = recentRuns.map(job => {
        const status = String(job.status || 'idle');
        let badgeClass = 'bg-gray-50 text-gray-700 border-gray-200';
        if (status === 'running') {
            badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
        } else if (status === 'pending') {
            badgeClass = 'bg-blue-50 text-blue-700 border-blue-200';
        } else if (status === 'failed') {
            badgeClass = 'bg-red-50 text-red-700 border-red-200';
        }
        const taskName = String(job.task_name || '') || TASK_TEXT.jobsUnknownTask;
        return `<div class="rounded-lg border border-gray-200 px-3 py-3">
            <div class="flex items-center justify-between gap-3">
                <div class="min-w-0">
                    <div class="text-sm font-medium text-gray-900 truncate">${escapeHtml(taskName)}</div>
                    <div class="text-xs text-gray-500">Job #${Number(job.id || 0)} · ${escapeHtml(TASK_TEXT.jobsTaskPrefix)} #${Number(job.task_id || 0)}</div>
                </div>
                <span class="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border ${badgeClass}">${escapeHtml(status)}</span>
            </div>
            <div class="mt-2 text-xs text-gray-500">
                <div>${escapeHtml(TASK_TEXT.jobsUpdatedAt)}: ${escapeHtml(String(job.updated_at || ''))}</div>
            </div>
        </div>`;
    }).join('');
    container.innerHTML = `<div class="space-y-3">${html}</div>`;
}

function applyOverview(overview) {
    if (!overview || !Array.isArray(overview.tasks)) return;
    overview.tasks.forEach(task => {
        updateTaskUI(task);
        updateTaskCounters(task);
    });
    updateTopStats(overview.tasks);
    if (overview.queue_overview) {
        updateQueueOverview(overview.queue_overview);
    }
    renderWorkerOverview(overview.worker_overview || []);
    renderRecentRuns(overview.recent_runs || []);
}

function requestTaskSnapshot() {
    fetch(TASK_HEALTH_URL)
        .then(response => response.json())
        .then(data => {
            if (!data.success) return;
            applyOverview(data);
        })
        .catch(error => { console.error(TASK_I18N.syncFailed, error); });
}

function initTaskRealtime() {
    if (!TASK_REALTIME.enabled || !TASK_REALTIME.key || typeof window.Pusher === 'undefined') {
        return;
    }

    const pusher = new window.Pusher(TASK_REALTIME.key, {
        cluster: 'mt1',
        wsHost: TASK_REALTIME.host,
        wsPort: TASK_REALTIME.port || 80,
        wssPort: TASK_REALTIME.port || 443,
        forceTLS: TASK_REALTIME.scheme === 'https',
        enabledTransports: ['ws', 'wss'],
        authEndpoint: @js(url('/broadcasting/auth')),
        auth: {
            headers: {
                'X-CSRF-TOKEN': @js(csrf_token()),
            },
        },
    });

    const channel = pusher.subscribe('private-admin.tasks');
    channel.bind('tasks.overview.updated', (payload) => {
        applyOverview(payload);
    });
}

function startBatchExecution(taskId, taskName) {
    if (!confirm(TASK_I18N.confirmStart.replace('__NAME__', taskName))) return;
    const btn = document.getElementById(`batch-btn-${taskId}`);
    setButtonLoading(btn, TASK_I18N.starting, 'inline-flex items-center justify-center w-8 h-8 rounded-md border border-green-200 bg-green-50 text-green-600 cursor-wait');
    fetch(TASK_BATCH_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': @js(csrf_token()) }, body: JSON.stringify({ task_id: taskId, action: 'start' }) }).then(response => response.json()).then(data => { if (!data.success) { showNotification('error', TASK_I18N.startFailed.replace('__MESSAGE__', data.message)); updateBatchButton(btn, taskId, taskName, false); return; } showNotification('success', TASK_I18N.taskQueued.replace('__NAME__', taskName)); updateBatchButton(btn, taskId, taskName, true); requestTaskSnapshot(); }).catch(error => { showNotification('error', TASK_I18N.requestFailed.replace('__MESSAGE__', error.message)); updateBatchButton(btn, taskId, taskName, false); });
}

function stopBatchExecution(taskId, taskName) {
    if (!confirm(TASK_I18N.confirmStop.replace('__NAME__', taskName))) return;
    const btn = document.getElementById(`batch-btn-${taskId}`);
    setButtonLoading(btn, TASK_I18N.stopping, 'inline-flex items-center justify-center w-8 h-8 rounded-md border border-orange-200 bg-orange-50 text-orange-600 cursor-wait');
    fetch(TASK_BATCH_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': @js(csrf_token()) }, body: JSON.stringify({ task_id: taskId, action: 'stop' }) }).then(response => response.json()).then(data => { if (!data.success) { showNotification('error', TASK_I18N.stopFailed.replace('__MESSAGE__', data.message)); updateBatchButton(btn, taskId, taskName, true); return; } showNotification('success', TASK_I18N.taskStopped.replace('__NAME__', taskName)); updateBatchButton(btn, taskId, taskName, false); requestTaskSnapshot(); }).catch(error => { showNotification('error', TASK_I18N.requestFailed.replace('__MESSAGE__', error.message)); updateBatchButton(btn, taskId, taskName, true); });
}

function executeAllActiveTasks() {
    const buttons = Array.from(document.querySelectorAll('[id^="batch-btn-"]')).filter(btn => btn.dataset.batchAction === 'start');
    if (buttons.length === 0) { showNotification('info', TASK_I18N.noRunnable); return; }
    if (!confirm(TASK_I18N.confirmRunAll)) return;
    let completed = 0; let success = 0;
    buttons.forEach((btn, index) => {
        const taskId = Number(btn.id.replace('batch-btn-', ''));
        setTimeout(() => {
            fetch(TASK_BATCH_URL, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-TOKEN': @js(csrf_token()) }, body: JSON.stringify({ task_id: taskId, action: 'start' }) }).then(response => response.json()).then(data => { completed += 1; if (data.success) success += 1; if (completed === buttons.length) { showNotification('success', TASK_I18N.bulkSubmitted.replace('__SUCCESS__', success).replace('__TOTAL__', buttons.length)); requestTaskSnapshot(); } }).catch(() => { completed += 1; if (completed === buttons.length) { showNotification('warning', TASK_I18N.bulkSubmittedPartial.replace('__SUCCESS__', success).replace('__TOTAL__', buttons.length)); requestTaskSnapshot(); } });
        }, index * 150);
    });
}

function handleStatusToggle(taskId, checkbox) {
    const form = checkbox.closest('form');
    const currentStatus = form.querySelector('input[name="status"]').value;
    const nextLabel = checkbox.checked ? TASK_I18N.activating : TASK_I18N.pausing;
    const statusSpan = form.querySelector('label span');
    if (!confirm(checkbox.checked ? TASK_I18N.confirmActivate : TASK_I18N.confirmPause)) { checkbox.checked = currentStatus === 'active'; return; }
    checkbox.disabled = true;
    statusSpan.textContent = nextLabel;
    statusSpan.className = `ml-2 text-sm ${checkbox.checked ? 'text-blue-600' : 'text-orange-600'}`;
    form.submit();
}

document.addEventListener('DOMContentLoaded', () => {
    renderIcons();
    applyOverview(TASK_INITIAL_OVERVIEW);
    requestTaskSnapshot();
    initTaskRealtime();
});
</script>
