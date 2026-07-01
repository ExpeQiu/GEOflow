<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class GeoMonitorAiProbeResult extends Model
{
    protected $table = 'geo_monitor_ai_probe_results';

    protected $fillable = [
        'question_id',
        'run_id',
        'ai_model_id',
        'platform_label',
        'response_text',
        'brand_rank',
        'brand_mentioned',
        'brands_ordered',
        'metrics_json',
        'status',
        'error_message',
    ];

    protected function casts(): array
    {
        return [
            'question_id' => 'integer',
            'run_id' => 'integer',
            'ai_model_id' => 'integer',
            'brand_rank' => 'integer',
            'brand_mentioned' => 'boolean',
            'brands_ordered' => 'array',
            'metrics_json' => 'array',
        ];
    }

    public function question(): BelongsTo
    {
        return $this->belongsTo(GeoMonitorQuestion::class, 'question_id');
    }
}
