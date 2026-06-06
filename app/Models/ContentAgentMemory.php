<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ContentAgentMemory extends Model
{
    protected $table = 'content_agent_memories';

    protected $fillable = [
        'task_id',
        'scope',
        'summary_json',
    ];

    protected function casts(): array
    {
        return [
            'task_id' => 'integer',
            'summary_json' => 'array',
        ];
    }

    public function task(): BelongsTo
    {
        return $this->belongsTo(Task::class);
    }
}
