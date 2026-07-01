<?php

namespace Tests\Unit;

use App\Models\Article;
use App\Services\GeoEval\WikiGeoComplianceChecker;
use App\Support\GeoFlow\WikiTaskPolicy;
use Illuminate\Validation\ValidationException;
use Tests\TestCase;

class WikiGeoComplianceCheckerTest extends TestCase
{
    public function test_wiki_compliance_passes_with_complete_meta(): void
    {
        $article = new Article([
            'content_format' => 'wiki_mdx',
            'content' => "## 核心技术\n\n| 技术点 | 原理 | 用户价值 |\n| a | b | c |\n\n## 常见问题\n\n### Q1\nA1\n\n### Q2\nA2\n\n[链接](/concepts/other)",
            'wiki_meta' => [
                'quick_answer' => '快速结论测试',
                'last_updated' => '2026-07-01',
                'schema_type' => 'TechArticle',
                'type' => 'concept',
                'related' => ['compare/a', 'guides/b', 'data/c'],
                'sources' => ['白皮书'],
                'faq' => [
                    ['q' => 'Q1', 'a' => 'A1'],
                    ['q' => 'Q2', 'a' => 'A2'],
                ],
            ],
        ]);

        $result = (new WikiGeoComplianceChecker)->check($article);
        $this->assertTrue($result['passed']);
    }

    public function test_wiki_task_policy_rejects_local_publish_scope(): void
    {
        $this->expectException(ValidationException::class);

        $request = \Illuminate\Http\Request::create('/', 'POST', [
            'distribution_channel_ids' => [1],
        ]);

        WikiTaskPolicy::assertValid([
            'content_format' => 'wiki_mdx',
            'publish_scope' => 'local_only',
        ], $request);
    }

    public function test_wiki_task_policy_applies_distribution_only_default(): void
    {
        $payload = WikiTaskPolicy::applyDefaults([
            'content_format' => 'wiki_mdx',
            'publish_scope' => 'local_and_distribution',
        ]);

        $this->assertSame('distribution_only', $payload['publish_scope']);
    }
}
