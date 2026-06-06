<?php

namespace App\Jobs;

use App\Services\GeoEval\Monitor\MonitorScanOrchestrator;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class RunMonitorScanJob implements ShouldQueue
{
    use Queueable;

    public function __construct(
        public string $runType = 'scheduled',
    ) {
        $this->onQueue('geo_eval');
    }

    public function handle(MonitorScanOrchestrator $orchestrator): void
    {
        $orchestrator->run($this->runType, false);
    }
}
