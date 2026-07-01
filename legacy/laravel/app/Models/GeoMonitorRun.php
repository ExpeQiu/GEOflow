<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class GeoMonitorRun extends Model
{
    protected $table = 'geo_monitor_runs';

    protected $fillable = [
        'run_type',
        'status',
        'question_count',
        'meta',
        'started_at',
        'finished_at',
    ];

    protected function casts(): array
    {
        return [
            'question_count' => 'integer',
            'meta' => 'array',
            'started_at' => 'datetime',
            'finished_at' => 'datetime',
        ];
    }

    public function results(): HasMany
    {
        return $this->hasMany(GeoMonitorResult::class, 'run_id');
    }
}
