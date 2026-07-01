<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GeoEvalEventLog extends Model
{
    public $timestamps = false;

    protected $table = 'geo_eval_event_logs';

    protected $fillable = [
        'request_id',
        'task_id',
        'article_id',
        'channel_id',
        'eval_status',
        'event',
        'level',
        'message',
        'context',
        'created_at',
    ];

    protected function casts(): array
    {
        return [
            'task_id' => 'integer',
            'article_id' => 'integer',
            'channel_id' => 'integer',
            'context' => 'array',
            'created_at' => 'datetime',
        ];
    }
}
