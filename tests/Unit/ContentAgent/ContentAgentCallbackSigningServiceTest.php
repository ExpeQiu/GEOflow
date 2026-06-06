<?php

namespace Tests\Unit\ContentAgent;

use App\Services\GeoFlow\ContentAgent\ContentAgentCallbackSigningService;
use Tests\TestCase;

class ContentAgentCallbackSigningServiceTest extends TestCase
{
    public function test_sign_and_verify_round_trip(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $service = new ContentAgentCallbackSigningService;
        $body = '{"contract_version":"1.0","request_id":"rid-1","status":"success"}';
        $headers = $service->signHeaders('POST', $body);

        $this->assertArrayHasKey('X-Content-Agent-Signature', $headers);
        $this->assertTrue($service->verify(
            'POST',
            $body,
            $headers['X-Content-Agent-Timestamp'],
            $headers['X-Content-Agent-Nonce'],
            $headers['X-Content-Agent-Signature'],
        ));
    }

    public function test_verify_rejects_tampered_body(): void
    {
        config(['geoflow.content_agent.callback_secret' => 'test-secret']);

        $service = new ContentAgentCallbackSigningService;
        $body = '{"request_id":"rid-1"}';
        $headers = $service->signHeaders('POST', $body);

        $this->assertFalse($service->verify(
            'POST',
            '{"request_id":"rid-2"}',
            $headers['X-Content-Agent-Timestamp'],
            $headers['X-Content-Agent-Nonce'],
            $headers['X-Content-Agent-Signature'],
        ));
    }
}
