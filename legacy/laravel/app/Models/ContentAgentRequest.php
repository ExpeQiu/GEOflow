<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class ContentAgentRequest extends Model
{
    protected $table = 'content_agent_requests';

    protected $fillable = [
        'request_id',
        'workflow_type',
        'backend',
        'engine_hint',
        'status',
        'correlation_type',
        'correlation_id',
        'contract_version',
        'payload_json',
        'result_json',
        'error_message',
        'submitted_at',
        'completed_at',
    ];

    protected function casts(): array
    {
        return [
            'correlation_id' => 'integer',
            'submitted_at' => 'datetime',
            'completed_at' => 'datetime',
        ];
    }
}
