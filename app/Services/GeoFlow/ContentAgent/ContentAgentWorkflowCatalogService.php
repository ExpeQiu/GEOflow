<?php

namespace App\Services\GeoFlow\ContentAgent;

use Symfony\Component\Yaml\Yaml;

/** 从侧车 workflows.yml / agents.yml 构建编排可视化目录。 */
final class ContentAgentWorkflowCatalogService
{
    private const string WORKFLOWS_PATH = 'services/content-agent/config/workflows.yml';

    private const string AGENTS_PATH = 'services/content-agent/config/agents.yml';

    /**
     * @return array{
     *     default_workflow: string,
     *     workflows: array<string, array<string, mixed>>
     * }
     */
    public function catalog(): array
    {
        $workflows = $this->loadWorkflows();
        $agents = $this->loadAgents();
        $catalog = [];

        foreach ($workflows as $workflowId => $workflow) {
            if (! is_array($workflow)) {
                continue;
            }

            $nodes = $this->normalizeNodes($workflow, $agents);
            $edges = $this->normalizeEdges($workflow);
            $visual = $this->buildVisual($workflowId, $nodes, $edges);
            $catalog[$workflowId] = [
                'id' => $workflowId,
                'description' => (string) ($workflow['description'] ?? ''),
                'trace_key' => (string) ($workflow['trace_key'] ?? $workflowId),
                'nodes' => $nodes,
                'edges' => $edges,
                'visual_layout' => (string) ($visual['layout'] ?? 'linear'),
                'visual_steps' => is_array($visual['steps'] ?? null) ? $visual['steps'] : [],
                'visual_pipeline' => is_array($visual['pipeline'] ?? null) ? $visual['pipeline'] : null,
            ];
        }

        return [
            'default_workflow' => array_key_exists('content_pipeline', $catalog)
                ? 'content_pipeline'
                : (array_key_first($catalog) ?: 'content'),
            'workflows' => $catalog,
        ];
    }

    /**
     * @return array<string, mixed>
     */
    private function loadWorkflows(): array
    {
        $path = base_path(self::WORKFLOWS_PATH);
        if (! is_file($path)) {
            return [];
        }

        $parsed = Yaml::parseFile($path);

        return is_array($parsed['workflows'] ?? null) ? $parsed['workflows'] : [];
    }

    /**
     * @return array<string, array<string, mixed>>
     */
    private function loadAgents(): array
    {
        $path = base_path(self::AGENTS_PATH);
        if (! is_file($path)) {
            return [];
        }

        $parsed = Yaml::parseFile($path);
        $agents = $parsed['agents'] ?? [];

        return is_array($agents) ? $agents : [];
    }

    /**
     * @param  array<string, mixed>  $workflow
     * @param  array<string, array<string, mixed>>  $agents
     * @return array<string, array<string, mixed>>
     */
    private function normalizeNodes(array $workflow, array $agents): array
    {
        $nodes = [];
        foreach ($workflow['nodes'] ?? [] as $node) {
            if (! is_array($node) || ! isset($node['id'])) {
                continue;
            }
            $id = (string) $node['id'];
            $agentId = (string) ($node['agent'] ?? '');
            $agentMeta = is_array($agents[$agentId] ?? null) ? $agents[$agentId] : [];
            $nodes[$id] = [
                'id' => $id,
                'type' => (string) ($node['type'] ?? 'rule'),
                'agent' => $agentId,
                'agent_label' => (string) ($agentMeta['name'] ?? $agentId),
                'handler' => (string) ($node['handler'] ?? $id),
            ];
        }

        return $nodes;
    }

    /**
     * @param  array<string, mixed>  $workflow
     * @return list<array{from:string,to:string,when:?string}>
     */
    private function normalizeEdges(array $workflow): array
    {
        $edges = [];
        foreach ($workflow['edges'] ?? [] as $edge) {
            if (! is_array($edge)) {
                continue;
            }
            $from = (string) ($edge['from'] ?? '');
            $to = (string) ($edge['to'] ?? '');
            if ($from === '' || $to === '') {
                continue;
            }
            $edges[] = [
                'from' => $from,
                'to' => $to,
                'when' => isset($edge['when']) ? (string) $edge['when'] : null,
            ];
        }

        return $edges;
    }

    /**
     * @param  array<string, array<string, mixed>>  $nodes
     * @param  list<array{from:string,to:string,when:?string}>  $edges
     * @return array{layout:string,steps?:list<array<string,mixed>>,pipeline?:array<string,mixed>}
     */
    private function buildVisual(string $workflowId, array $nodes, array $edges): array
    {
        if ($workflowId === 'content_pipeline') {
            return [
                'layout' => 'pipeline_fork',
                'pipeline' => $this->contentPipelineLayout($nodes),
            ];
        }

        $steps = match ($workflowId) {
            'content' => $this->linearVisualSteps($nodes, $edges, ['draft', 'cite_check', 'revise', 'finalize']),
            'url_import' => $this->linearVisualSteps($nodes, $edges, ['clean_page', 'build_knowledge', 'extract_keywords', 'extract_titles', 'finalize']),
            'semantic_chunk' => $this->linearVisualSteps($nodes, $edges, ['plan_blocks', 'build_chunks']),
            default => $this->linearVisualStepsFromEdges($nodes, $edges),
        };

        return ['layout' => 'linear', 'steps' => $steps];
    }

    /**
     * @param  array<string, array<string, mixed>>  $nodes
     * @return array<string, mixed>
     */
    private function contentPipelineLayout(array $nodes): array
    {
        return [
            'header' => [
                ['kind' => 'external', 'id' => 'laravel_rag', 'icon' => 'database'],
                $this->nodeStep($nodes, 'chief'),
                $this->nodeStep($nodes, 'deputy_route'),
            ],
            'paths' => [
                'fast' => [
                    'label_key' => 'path_fast_title',
                    'desc_key' => 'path_fast_desc',
                    'tone' => 'sky',
                    'nodes' => array_values(array_filter([
                        $this->nodeStep($nodes, 'writer'),
                        $this->nodeStep($nodes, 'xval_writer'),
                    ])),
                    'compliance' => 'skip',
                ],
                'deep' => [
                    'label_key' => 'path_deep_title',
                    'desc_key' => 'path_deep_desc',
                    'tone' => 'violet',
                    'nodes' => array_values(array_filter([
                        $this->nodeStep($nodes, 'parallel_probe'),
                        $this->nodeStep($nodes, 'writer'),
                        $this->nodeStep($nodes, 'xval_writer'),
                    ])),
                    'compliance' => 'required',
                ],
            ],
            'shared' => array_values(array_filter([
                $this->nodeStep($nodes, 'editor'),
                $this->nodeStep($nodes, 'xval_editor'),
            ])),
            'finalize' => [
                'fast' => array_values(array_filter([$this->nodeStep($nodes, 'deputy_finalize')])),
                'deep' => array_values(array_filter([
                    $this->nodeStep($nodes, 'compliance'),
                    $this->nodeStep($nodes, 'deputy_finalize'),
                ])),
            ],
            'footer' => [
                ['kind' => 'external', 'id' => 'laravel_callback', 'icon' => 'send'],
            ],
        ];
    }

    /**
     * @param  array<string, array<string, mixed>>  $nodes
     * @param  list<string>  $order
     * @return list<array<string, mixed>>
     */
    private function linearVisualSteps(array $nodes, array $edges, array $order): array
    {
        $steps = [];
        foreach ($order as $index => $nodeId) {
            if ($index > 0) {
                $steps[] = ['kind' => 'arrow'];
            }
            $step = $this->nodeStep($nodes, $nodeId);
            if ($step !== null) {
                $steps[] = $step;
            }
        }

        if ($steps === []) {
            return $this->linearVisualStepsFromEdges($nodes, $edges);
        }

        return $steps;
    }

    /**
     * @param  array<string, array<string, mixed>>  $nodes
     * @param  list<array{from:string,to:string,when:?string}>  $edges
     * @return list<array<string, mixed>>
     */
    private function linearVisualStepsFromEdges(array $nodes, array $edges): array
    {
        $start = null;
        foreach ($edges as $edge) {
            if ($edge['from'] === '__start__') {
                $start = $edge['to'];
                break;
            }
        }

        $steps = [];
        $current = $start;
        $guard = 0;
        while ($current !== null && $guard < 16) {
            $guard++;
            if ($guard > 1) {
                $steps[] = ['kind' => 'arrow'];
            }
            $step = $this->nodeStep($nodes, $current);
            if ($step !== null) {
                $steps[] = $step;
            }

            $next = null;
            foreach ($edges as $edge) {
                if ($edge['from'] === $current && $edge['when'] === null) {
                    $next = $edge['to'];
                    break;
                }
            }
            $current = $next;
        }

        return $steps;
    }

    /**
     * @param  array<string, array<string, mixed>>  $nodes
     * @return array<string, mixed>|null
     */
    private function nodeStep(array $nodes, string $nodeId, int $indent = 0): ?array
    {
        $node = $nodes[$nodeId] ?? null;
        if (! is_array($node)) {
            return null;
        }

        return [
            'kind' => 'node',
            'indent' => $indent,
            ...$node,
        ];
    }
}
