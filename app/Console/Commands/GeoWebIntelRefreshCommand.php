<?php

namespace App\Console\Commands;

use App\Jobs\RefreshWebSourceJob;
use App\Services\GeoEval\WebIntel\WebSourceRegistry;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Schema;

class GeoWebIntelRefreshCommand extends Command
{
    protected $signature = 'geo:web-intel-refresh {--async : 入队异步执行}';

    protected $description = '刷新过期外部信源页面特征';

    public function handle(WebSourceRegistry $registry): int
    {
        if (! Schema::hasTable('geo_web_sources')) {
            $this->warn('geo_web_sources table missing');

            return self::FAILURE;
        }

        $stale = $registry->staleSources();
        $async = (bool) $this->option('async');
        $count = 0;

        foreach ($stale as $source) {
            if ($async) {
                RefreshWebSourceJob::dispatch((int) $source->id);
            } else {
                $registry->refresh($source);
            }
            $count++;
        }

        $this->info("Refreshed {$count} source(s)".($async ? ' (queued)' : ''));

        return self::SUCCESS;
    }
}
