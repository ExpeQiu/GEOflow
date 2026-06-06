<?php

namespace App\Jobs;

use App\Models\GeoWebSource;
use App\Services\GeoEval\WebIntel\WebSourceRegistry;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;

class RefreshWebSourceJob implements ShouldQueue
{
    use Queueable;

    public function __construct(
        public int $sourceId,
    ) {
        $this->onQueue('geo_eval');
    }

    public function handle(WebSourceRegistry $registry): void
    {
        $source = GeoWebSource::query()->find($this->sourceId);
        if ($source) {
            $registry->refresh($source);
        }
    }
}
