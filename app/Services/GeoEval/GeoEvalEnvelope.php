<?php

namespace App\Services\GeoEval;

/**
 * 解析 GEO 策略模块统一数据信封（参考 GEO-OS api_response 字段约定，进程内使用）。
 */
final class GeoEvalEnvelope
{
    /**
     * @param  array<string, mixed>  $payload
     * @return array{ok:bool, data:mixed, request_id:?string, error:?array<string, mixed>}
     */
    public static function parse(array $payload): array
    {
        $requestId = isset($payload['request_id']) ? (string) $payload['request_id'] : null;

        if (($payload['success'] ?? null) === true) {
            return [
                'ok' => true,
                'data' => $payload['data'] ?? null,
                'request_id' => $requestId,
                'error' => null,
            ];
        }

        $error = is_array($payload['error'] ?? null) ? $payload['error'] : [
            'code' => 'unknown_error',
            'message' => 'GEO eval request failed',
        ];

        return [
            'ok' => false,
            'data' => null,
            'request_id' => $requestId,
            'error' => $error,
        ];
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    public static function unwrapData(array $payload): mixed
    {
        return self::parse($payload)['data'];
    }
}
