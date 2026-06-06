<?php

namespace App\Services\GeoEval;

use App\Models\GeoEvalEventLog;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Str;

final class GeoEvalStructuredLogger
{
    public function newRequestId(): string
    {
        return (string) Str::uuid();
    }

    /**
     * @param  array<string, mixed>  $context
     */
    public function info(string $event, array $context = []): void
    {
        $this->write('info', $event, $context);
    }

    /**
     * @param  array<string, mixed>  $context
     */
    public function warning(string $event, array $context = []): void
    {
        $this->write('warning', $event, $context);
    }

    /**
     * @param  array<string, mixed>  $context
     */
    public function error(string $event, array $context = []): void
    {
        $this->write('error', $event, $context);
    }

    /**
     * @param  array<string, mixed>  $context
     */
    private function write(string $level, string $event, array $context): void
    {
        $requestId = (string) ($context['request_id'] ?? $this->newRequestId());
        $payload = array_merge([
            'event' => $event,
            'request_id' => $requestId,
            'task_id' => $context['task_id'] ?? null,
            'article_id' => $context['article_id'] ?? null,
            'channel_id' => $context['channel_id'] ?? null,
            'eval_status' => $context['eval_status'] ?? null,
            'retry_count' => $context['retry_count'] ?? null,
        ], $context);

        Log::channel('daily')->{$level}('[geo_eval] '.$event, $payload);

        try {
            if (! class_exists(GeoEvalEventLog::class)) {
                return;
            }
            GeoEvalEventLog::query()->create([
                'request_id' => $requestId,
                'task_id' => isset($context['task_id']) ? (int) $context['task_id'] : null,
                'article_id' => isset($context['article_id']) ? (int) $context['article_id'] : null,
                'channel_id' => isset($context['channel_id']) ? (int) $context['channel_id'] : null,
                'eval_status' => isset($context['eval_status']) ? (string) $context['eval_status'] : null,
                'event' => $event,
                'level' => $level,
                'message' => (string) ($context['message'] ?? $event),
                'context' => $context,
            ]);
        } catch (\Throwable) {
            // 日志表未迁移或测试库缺失时不阻塞主链路
        }
    }
}
