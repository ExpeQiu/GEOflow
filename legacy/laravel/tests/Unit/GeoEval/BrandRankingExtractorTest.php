<?php

namespace Tests\Unit\GeoEval;

use App\Services\GeoEval\Monitor\BrandRankingExtractor;
use Tests\TestCase;

class BrandRankingExtractorTest extends TestCase
{
    public function test_extracts_rank_from_numbered_list(): void
    {
        $extractor = new BrandRankingExtractor;
        $result = $extractor->extract(
            "1. 竞品A\n2. 目标品牌 Pro\n3. 竞品B",
            ['目标品牌']
        );

        $this->assertSame(2, $result['brand_rank']);
        $this->assertTrue($result['brand_mentioned']);
        $this->assertCount(3, $result['brands_ordered']);
    }

    public function test_returns_not_mentioned_when_brand_absent(): void
    {
        $extractor = new BrandRankingExtractor;
        $result = $extractor->extract("1. Alpha\n2. Beta", ['Gamma']);

        $this->assertFalse($result['brand_mentioned']);
        $this->assertSame(99, $result['brand_rank']);
    }
}
