<?php

namespace Tests\Unit\GeoEval;

use App\Services\GeoEval\Simulation\AnswerAuditService;
use Tests\TestCase;

class AnswerAuditServiceTest extends TestCase
{
    public function test_audit_passes_with_sufficient_excerpt(): void
    {
        config(['geo_eval.brand_keywords' => ['领先']]);
        $service = new AnswerAuditService;
        $result = $service->audit(
            '电动汽车续航里程',
            str_repeat('电动汽车续航里程行业领先，配备800V高压平台与多项安全技术。', 5),
            ['领先']
        );

        $this->assertSame('pass', $result['status']);
    }
}
