<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class GeoMonitorPlatformConfig extends Model
{
    protected $table = 'geo_monitor_platform_configs';

    protected $fillable = [
        'ai_model_id',
        'label',
        'is_enabled',
        'sort_order',
    ];

    protected function casts(): array
    {
        return [
            'ai_model_id' => 'integer',
            'is_enabled' => 'boolean',
            'sort_order' => 'integer',
        ];
    }

    public function aiModel(): BelongsTo
    {
        return $this->belongsTo(AiModel::class, 'ai_model_id');
    }
}
