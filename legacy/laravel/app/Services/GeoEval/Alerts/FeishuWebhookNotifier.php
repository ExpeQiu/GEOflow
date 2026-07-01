<?php

namespace App\Services\GeoEval\Alerts;

use App\Services\GeoEval\GeoEvalStructuredLogger;
use Illuminate\Support\Facades\Http;

final class FeishuWebhookNotifier
{
    public function __construct(
        private readonly GeoEvalStructuredLogger $logger
    ) {}

    public function notify(string $title, string $text): bool
    {
        $url = trim((string) config('geo_eval.alerts.feishu_webhook_url', ''));
        if ($url === '') {
            return false;
        }

        try {
            $response = Http::timeout(10)->post($url, [
                'msg_type' => 'text',
                'content' => [
                    'text' => $title."\n".$text,
                ],
            ]);

            return $response->successful();
        } catch (\Throwable $e) {
            $this->logger->error('feishu_notify_failed', [
                'message' => $e->getMessage(),
            ]);

            return false;
        }
    }
}
