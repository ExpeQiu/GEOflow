<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ArticleEvaluation extends Model
{
    protected $table = 'article_evaluations';

    protected $fillable = [
        'article_id',
        'task_run_id',
        'idempotency_key',
        'eval_type',
        'status',
        'request_id',
        'metrics',
        'failure_reason',
        'raw_response',
    ];

    protected function casts(): array
    {
        return [
            'article_id' => 'integer',
            'task_run_id' => 'integer',
            'metrics' => 'array',
            'raw_response' => 'array',
        ];
    }

    public function article(): BelongsTo
    {
        return $this->belongsTo(Article::class, 'article_id');
    }
}
