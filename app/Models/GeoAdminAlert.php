<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GeoAdminAlert extends Model
{
    public $timestamps = false;

    protected $table = 'geo_admin_alerts';

    protected $fillable = [
        'alert_type',
        'severity',
        'threshold',
        'current_value',
        'message',
        'channels',
        'notified_feishu',
        'created_at',
    ];

    protected function casts(): array
    {
        return [
            'threshold' => 'float',
            'current_value' => 'float',
            'channels' => 'array',
            'notified_feishu' => 'boolean',
            'created_at' => 'datetime',
        ];
    }
}
