<?php

namespace App\Console\Commands;

use App\Models\ContentAgentRequest;
use App\Models\TaskRun;
use App\Models\UrlImportJob;
use App\Services\GeoFlow\ContentAgent\ContentAgentRequestRepository;
use App\Services\GeoFlow\JobQueueService;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Log;

class ExpireContentAgentRequestsCommand extends Command
{
    protected $signature = 'geoflow:expire-content-agent-requests';

    protected $description = '将超时未回调的 Content Agent 请求标记过期并回写关联任务';

    public function handle(
        ContentAgentRequestRepository $repository,
        JobQueueService $jobQueueService,
    ): int {
        $ttl = max(60, (int) config('geoflow.content_agent.request_ttl_seconds', 600));
        $threshold = now()->subSeconds($ttl);

        $expired = ContentAgentRequest::query()
            ->whereIn('status', ['pending', 'running'])
            ->where('submitted_at', '<', $threshold)
            ->orderBy('id')
            ->get();

        $count = 0;
        foreach ($expired as $request) {
            $repository->markExpired((string) $request->request_id);

            if ($request->correlation_type === 'task_run' && (int) $request->correlation_id > 0) {
                $run = TaskRun::query()->whereKey((int) $request->correlation_id)->first(['id', 'task_id', 'status']);
                if ($run && ($run->status ?? '') === 'running') {
                    $jobQueueService->failJob((int) $run->id, (int) $run->task_id, 'Content Agent 回调超时', 0);
                }
            }

            if ($request->correlation_type === 'url_import_job' && (int) $request->correlation_id > 0) {
                UrlImportJob::query()->whereKey((int) $request->correlation_id)->update([
                    'status' => 'failed',
                    'current_step' => 'failed',
                    'error_message' => 'Content Agent 回调超时',
                    'finished_at' => now(),
                ]);
            }

            Log::channel('content_agent')->warning('content_agent.request_expired', [
                'request_id' => $request->request_id,
                'workflow_type' => $request->workflow_type,
            ]);
            $count++;
        }

        $this->info('Expired '.$count.' content agent request(s).');

        return self::SUCCESS;
    }
}
