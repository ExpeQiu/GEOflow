<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GeoStrategyMetricSnapshot extends Model
{
    protected $table = 'geo_strategy_metric_snapshots';

    protected $fillable = [
        'metric_date',
        'platform',
        'adoption_rate',
        'first_position_rate',
        'sample_size',
        'passed_count',
        'meta',
    ];

    protected function casts(): array
    {
        return [
            'metric_date' => 'date',
            'adoption_rate' => 'float',
            'first_position_rate' => 'float',
            'sample_size' => 'integer',
            'passed_count' => 'integer',
            'meta' => 'array',
        ];
    }
}
