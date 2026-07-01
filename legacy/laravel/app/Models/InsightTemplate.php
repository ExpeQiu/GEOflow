<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class InsightTemplate extends Model
{
    protected $table = 'insight_templates';

    protected $fillable = [
        'name',
        'source_url',
        'style_guide',
        'features',
        'eeat_score',
        'created_by_admin_id',
    ];

    protected function casts(): array
    {
        return [
            'style_guide' => 'array',
            'features' => 'array',
            'eeat_score' => 'float',
            'created_by_admin_id' => 'integer',
        ];
    }
}
