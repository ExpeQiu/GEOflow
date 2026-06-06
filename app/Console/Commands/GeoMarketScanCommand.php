<?php

namespace App\Console\Commands;

use App\Models\GeoMarketScanRun;
use App\Models\GeoWebSource;
use App\Services\GeoEval\Adoption\AdoptionMetricsAggregator;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Schema;

class GeoMarketScanCommand extends Command
{
    protected $signature = 'geo:market-scan {--type=weekly : daily|weekly}';

    protected $description = 'GEO 采纳指标周快照（写入 geo_market_scan_runs，非竞品爬虫）';

    public function handle(AdoptionMetricsAggregator $aggregator): int
    {
        if (! Schema::hasTable('geo_market_scan_runs')) {
            $this->warn('geo_market_scan_runs table missing');

            return self::FAILURE;
        }

        $type = (string) $this->option('type');
        $days = $type === 'daily' ? 7 : 30;
        $summary = $aggregator->summary($days, '');
        $trend = $aggregator->dailySeries($days, '');

        $webIntelSummary = [];
        if (Schema::hasTable('geo_web_sources')) {
            $webIntelSummary = [
                'sources_total' => GeoWebSource::query()->count(),
                'sources_stale' => GeoWebSource::query()
                    ->where(function ($q): void {
                        $q->whereNull('last_fetched_at')
                            ->orWhere('fetch_status', 'failed');
                    })
                    ->count(),
            ];
        }

        GeoMarketScanRun::query()->create([
            'scan_type' => $type,
            'status' => 'completed',
            'summary_json' => [
                'summary' => $summary,
                'trend_points' => count($trend),
                'web_intel' => $webIntelSummary,
            ],
            'ran_at' => now(),
        ]);

        $this->info('Market scan recorded.');

        return self::SUCCESS;
    }
}
