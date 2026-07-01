<?php

namespace App\Services\GeoFlow\ContentAgent;

use RuntimeException;

/** 外部 Content Agent 已接单，当前 Job 应等待回调。 */
final class ContentAgentAsyncSubmittedException extends RuntimeException
{
    public function __construct(public readonly string $requestId)
    {
        parent::__construct('content_agent_async_submitted:'.$requestId);
    }
}
