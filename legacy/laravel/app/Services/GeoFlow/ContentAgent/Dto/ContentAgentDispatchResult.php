<?php

namespace App\Services\GeoFlow\ContentAgent\Dto;

/** dispatch* façade 返回值：同步直接带 result，异步带 request_id。 */
final readonly class ContentAgentDispatchResult
{
    public function __construct(
        public string $mode,
        public ?string $requestId = null,
        public ?ContentAgentResult $result = null,
    ) {}

    public function isAsync(): bool
    {
        return $this->mode === 'async';
    }

    public function isSync(): bool
    {
        return $this->mode === 'sync';
    }
}
