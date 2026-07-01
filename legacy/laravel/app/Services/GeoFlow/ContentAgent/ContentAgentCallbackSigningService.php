<?php

namespace App\Services\GeoFlow\ContentAgent;

use Illuminate\Support\Str;
use RuntimeException;

final class ContentAgentCallbackSigningService
{
    public const CALLBACK_PATH = '/internal/content-agent/callback';

    /**
     * @return array<string, string>
     */
    public function signHeaders(string $method, string $body): array
    {
        $secret = trim((string) config('geoflow.content_agent.callback_secret', ''));
        if ($secret === '') {
            throw new RuntimeException('CONTENT_AGENT_CALLBACK_SECRET 未配置');
        }

        $method = mb_strtoupper($method, 'UTF-8');
        $timestamp = now()->toIso8601String();
        $nonce = (string) Str::uuid();
        $bodyHash = hash('sha256', $body);
        $signature = hash_hmac(
            'sha256',
            $method."\n".self::CALLBACK_PATH."\n".$timestamp."\n".$nonce."\n".$bodyHash,
            $secret
        );

        return [
            'X-Content-Agent-Timestamp' => $timestamp,
            'X-Content-Agent-Nonce' => $nonce,
            'X-Content-Agent-Signature' => $signature,
        ];
    }

    public function verify(string $method, string $body, string $timestamp, string $nonce, string $signature): bool
    {
        $secret = trim((string) config('geoflow.content_agent.callback_secret', ''));
        if ($secret === '') {
            return false;
        }

        $method = mb_strtoupper($method, 'UTF-8');
        $expected = hash_hmac(
            'sha256',
            $method."\n".self::CALLBACK_PATH."\n".$timestamp."\n".$nonce."\n".hash('sha256', $body),
            $secret
        );

        return hash_equals($expected, $signature);
    }
}
