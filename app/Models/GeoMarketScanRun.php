<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GeoMarketScanRun extends Model
{
    protected $table = 'geo_market_scan_runs';

    protected $fillable = [
        'scan_type',
        'status',
        'summary_json',
        'ran_at',
    ];

    protected function casts(): array
    {
        return [
            'summary_json' => 'array',
            'ran_at' => 'datetime',
        ];
    }
}
