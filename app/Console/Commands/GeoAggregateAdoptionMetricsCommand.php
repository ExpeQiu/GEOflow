<?php

namespace App\Console\Commands;

use App\Services\GeoEval\Adoption\AdoptionMetricsAggregator;
use Illuminate\Console\Command;

class GeoAggregateAdoptionMetricsCommand extends Command
{
    protected $signature = 'geo:aggregate-adoption-metrics {--days=30 : 回填最近 N 天}';

    protected $description = '聚合 GEO 采纳指标写入 geo_strategy_metric_snapshots';

    public function handle(AdoptionMetricsAggregator $aggregator): int
    {
        $days = max(1, (int) $this->option('days'));
        $stored = 0;
        for ($i = $days - 1; $i >= 0; $i--) {
            $stored += $aggregator->aggregateAndStore(now()->subDays($i));
        }

        $this->info("Stored {$stored} snapshot row(s).");

        return self::SUCCESS;
    }
}
