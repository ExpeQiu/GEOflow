<?php

namespace App\Console\Commands;

use App\Services\GeoEval\Monitor\MonitorScanOrchestrator;
use App\Services\GeoEval\Monitor\MonitorTrendAnalyzer;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Schema;

class GeoMonitorScanCommand extends Command
{
    protected $signature = 'geo:monitor-scan {--type=daily : daily|weekly} {--async : 入队异步执行}';

    protected $description = '监控问题库扫描：对 active 问题执行 RAG 仿真与审计';

    public function handle(
        MonitorScanOrchestrator $orchestrator,
        MonitorTrendAnalyzer $trendAnalyzer,
    ): int {
        if (! Schema::hasTable('geo_monitor_questions')) {
            $this->warn('geo_monitor_questions table missing');

            return self::FAILURE;
        }

        if (! config('geo_eval.enabled')) {
            $this->info('GEO eval disabled, skip.');

            return self::SUCCESS;
        }

        $type = (string) $this->option('type');
        $async = (bool) $this->option('async');
        $result = $orchestrator->run($type, $async);

        if ($async) {
            $this->info('Monitor scan queued.');

            return self::SUCCESS;
        }

        $alerts = $trendAnalyzer->checkAndRecordAlerts();
        $this->info(sprintf(
            'Scan run #%d: scanned=%d skipped=%d failed=%d alerts=%d',
            $result['run_id'],
            $result['scanned'],
            $result['skipped'],
            $result['failed'],
            $alerts
        ));

        return self::SUCCESS;
    }
}
