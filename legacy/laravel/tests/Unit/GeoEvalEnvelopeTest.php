<?php

namespace Tests\Unit;

use App\Services\GeoEval\GeoEvalEnvelope;
use PHPUnit\Framework\TestCase;

class GeoEvalEnvelopeTest extends TestCase
{
    public function test_parses_success_envelope(): void
    {
        $parsed = GeoEvalEnvelope::parse([
            'success' => true,
            'data' => ['metrics' => ['found' => true]],
            'request_id' => 'rid-1',
        ]);

        $this->assertTrue($parsed['ok']);
        $this->assertSame('rid-1', $parsed['request_id']);
        $this->assertTrue($parsed['data']['metrics']['found']);
    }

    public function test_parses_failure_envelope(): void
    {
        $parsed = GeoEvalEnvelope::parse([
            'success' => false,
            'error' => ['code' => 'timeout', 'message' => 'slow'],
        ]);

        $this->assertFalse($parsed['ok']);
        $this->assertSame('timeout', $parsed['error']['code']);
    }
}
