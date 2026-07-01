<?php

namespace App\Services\GeoFlow\ContentAgent\Dto;

/** Content Agent 同步执行或回调解析后的统一结果。 */
final readonly class ContentAgentResult
{
    /**
     * @param  array<string, mixed>  $data
     * @param  array<string, mixed>  $trace
     */
    public function __construct(
        public bool $success,
        public array $data = [],
        public ?string $error = null,
        public array $trace = [],
    ) {}

    public function string(string $key, string $default = ''): string
    {
        $value = $this->data[$key] ?? $default;

        return is_string($value) || is_numeric($value) ? trim((string) $value) : $default;
    }

    /**
     * @return list<string>
     */
    public function stringList(string $key): array
    {
        $value = $this->data[$key] ?? [];
        if (! is_array($value)) {
            return [];
        }

        return array_values(array_filter(array_map(
            static fn (mixed $item): string => trim(is_string($item) || is_numeric($item) ? (string) $item : ''),
            $value
        ), static fn (string $item): bool => $item !== ''));
    }
}
