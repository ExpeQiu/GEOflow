<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class TechIpAsset extends Model
{
    protected $fillable = [
        'ip_id',
        'ip_name',
        'ip_layer',
        'mind_tag',
        'priority',
        'can_name',
        'can_visualize',
        'can_translate',
        'tech_term',
        'user_language',
        'evidence',
        'models',
        'wiki_type',
        'wiki_slug',
        'status',
        'knowledge_base_id',
    ];

    protected function casts(): array
    {
        return [
            'can_name' => 'boolean',
            'can_visualize' => 'boolean',
            'can_translate' => 'boolean',
            'evidence' => 'array',
            'models' => 'array',
            'knowledge_base_id' => 'integer',
        ];
    }

    public function knowledgeBase(): BelongsTo
    {
        return $this->belongsTo(KnowledgeBase::class, 'knowledge_base_id');
    }

    public function passesThreeQuestions(): bool
    {
        return $this->can_name && $this->can_visualize && $this->can_translate;
    }

    /**
     * @return list<string>
     */
    public static function ipLayers(): array
    {
        return ['架构层', '模块层', '参数层'];
    }

    /**
     * @return list<string>
     */
    public static function statuses(): array
    {
        return ['待封装', '已发布', '需更新'];
    }

    /**
     * @return list<string>
     */
    public static function wikiTypes(): array
    {
        return ['concept', 'compare', 'guide', 'glossary', 'data', 'thread', 'topic'];
    }
}
