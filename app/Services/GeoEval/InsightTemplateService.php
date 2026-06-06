<?php

namespace App\Services\GeoEval;

use App\Models\InsightTemplate;
use App\Services\GeoEval\Contracts\GeoEvalClientInterface;

final class InsightTemplateService
{
    public function __construct(
        private readonly GeoEvalClientInterface $client,
        private readonly GeoEvalStructuredLogger $logger
    ) {}

    /**
     * @return array<string, mixed>
     */
    public function createFromUrl(string $name, string $url, ?int $adminId = null): array
    {
        $requestId = $this->logger->newRequestId();
        $response = $this->client->mineUrlInsight(['url' => $url], $requestId);
        $data = is_array($response['data'] ?? null) ? $response['data'] : [];

        $template = InsightTemplate::query()->create([
            'name' => $name,
            'source_url' => $url,
            'style_guide' => $data['style_guide'] ?? [],
            'features' => $data['features'] ?? [],
            'eeat_score' => isset($data['eeat']['overall']) ? (float) $data['eeat']['overall'] : null,
            'created_by_admin_id' => $adminId,
        ]);

        $this->logger->info('insight_template_created', [
            'request_id' => $response['request_id'] ?? $requestId,
            'message' => $name,
        ]);

        return $template->toArray();
    }

    /**
     * @return array<string, mixed>
     */
    public function refreshFromUrl(InsightTemplate $template): array
    {
        $url = (string) ($template->source_url ?? '');
        if ($url === '') {
            throw new \InvalidArgumentException('missing_source_url');
        }

        $requestId = $this->logger->newRequestId();
        $response = $this->client->mineUrlInsight(['url' => $url], $requestId);
        $data = is_array($response['data'] ?? null) ? $response['data'] : [];

        $template->style_guide = $data['style_guide'] ?? [];
        $template->features = $data['features'] ?? [];
        $template->eeat_score = isset($data['eeat']['overall']) ? (float) $data['eeat']['overall'] : null;
        $template->touch();
        $template->save();

        return $template->toArray();
    }

    public function buildPromptAppendix(?int $templateId): string
    {
        if ($templateId === null || $templateId <= 0) {
            return '';
        }

        $template = InsightTemplate::query()->find($templateId);
        if (! $template) {
            return '';
        }

        $guide = $template->style_guide;
        if (! is_array($guide) || $guide === []) {
            return '';
        }

        $lines = ['【洞察风格约束】'];
        foreach ($guide as $key => $value) {
            if (is_array($value)) {
                $lines[] = (string) $key.': '.json_encode($value, JSON_UNESCAPED_UNICODE);
            } else {
                $lines[] = (string) $key.': '.(string) $value;
            }
        }

        return implode("\n", $lines);
    }
}
