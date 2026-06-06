<?php

namespace Tests\Unit\GeoEval;

use App\Services\GeoEval\Insight\UrlInsightMinerService;
use App\Services\GeoEval\WebIntel\WebPageAnalyzer;
use Illuminate\Support\Facades\Http;
use Tests\TestCase;

class WebPageAnalyzerTest extends TestCase
{
    public function test_analyze_enriches_features_from_html(): void
    {
        Http::fake([
            'https://example.com/article' => Http::response(
                '<html><head><title>Test</title><meta name="author" content="Author A"></head>'
                .'<body><h2>Section</h2><p>Data 2024 and 100km range</p><table><tr><td>1</td></tr></table>'
                .'<a href="https://other.com">link</a></body></html>',
                200
            ),
        ]);

        $analyzer = new WebPageAnalyzer(new UrlInsightMinerService);
        $result = $analyzer->analyze('https://example.com/article');

        $this->assertSame('https://example.com/article', $result['url']);
        $this->assertGreaterThanOrEqual(1, (int) ($result['features']['tables'] ?? 0));
        $this->assertSame('Author A', $result['features']['author_meta'] ?? '');
    }
}
