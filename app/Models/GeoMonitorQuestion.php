<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class GeoMonitorQuestion extends Model
{
    protected $table = 'geo_monitor_questions';

    protected $fillable = [
        'question_text',
        'category',
        'intent_type',
        'source',
        'knowledge_base_id',
        'task_id',
        'target_article_id',
        'target_content_snapshot',
        'is_active',
        'priority',
        'tags',
        'tech_keywords',
        'created_by_admin_id',
    ];

    protected function casts(): array
    {
        return [
            'knowledge_base_id' => 'integer',
            'task_id' => 'integer',
            'target_article_id' => 'integer',
            'is_active' => 'boolean',
            'priority' => 'integer',
            'tags' => 'array',
            'tech_keywords' => 'array',
            'created_by_admin_id' => 'integer',
        ];
    }

    public function results(): HasMany
    {
        return $this->hasMany(GeoMonitorResult::class, 'question_id');
    }
}
