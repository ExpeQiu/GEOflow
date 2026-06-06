<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GeoWebSource extends Model
{
    protected $table = 'geo_web_sources';

    protected $fillable = [
        'url',
        'domain',
        'label',
        'question_id',
        'last_fetched_at',
        'features_json',
        'eeat_json',
        'fetch_status',
    ];

    protected function casts(): array
    {
        return [
            'question_id' => 'integer',
            'last_fetched_at' => 'datetime',
            'features_json' => 'array',
            'eeat_json' => 'array',
        ];
    }
}
