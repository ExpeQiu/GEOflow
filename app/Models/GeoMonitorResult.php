<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class GeoMonitorResult extends Model
{
    protected $table = 'geo_monitor_results';

    protected $fillable = [
        'question_id',
        'run_id',
        'article_id',
        'rank',
        'found',
        'target_score',
        'top_k',
        'audit_status',
        'tech_accuracy',
        'brand_consistency',
        'snapshot_json',
        'recommendations',
    ];

    protected function casts(): array
    {
        return [
            'question_id' => 'integer',
            'run_id' => 'integer',
            'article_id' => 'integer',
            'rank' => 'integer',
            'found' => 'boolean',
            'target_score' => 'float',
            'top_k' => 'integer',
            'tech_accuracy' => 'float',
            'brand_consistency' => 'float',
            'snapshot_json' => 'array',
            'recommendations' => 'array',
        ];
    }

    public function question(): BelongsTo
    {
        return $this->belongsTo(GeoMonitorQuestion::class, 'question_id');
    }

    public function run(): BelongsTo
    {
        return $this->belongsTo(GeoMonitorRun::class, 'run_id');
    }
}
