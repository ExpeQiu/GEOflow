<?php

namespace App\Services\GeoEval\Contracts;

/** GEOworkflow 内置策略引擎端口（进程内实现，非 HTTP 客户端）。 */
interface GeoEvalClientInterface
{
    /**
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>
     */
    public function runSimulation(array $payload, ?string $requestId = null): array;

    /**
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>
     */
    public function auditAnswer(array $payload, ?string $requestId = null): array;

    /**
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>
     */
    public function mineUrlInsight(array $payload, ?string $requestId = null): array;

    /**
     * @return array<string, mixed>
     */
    public function getAdoptionStats(int $days = 30, string $platform = '', ?string $requestId = null): array;

    /**
     * @return array<string, mixed>
     */
    public function getStrategyTrends(int $days = 30, ?string $requestId = null): array;

    public function healthCheck(): bool;
}
