<?php

namespace App\Services\GeoEval\WebIntel;

use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

/**
 * 聚合 view_logs 中的 AI 爬虫访问信号。
 */
final class AdoptionSignalService
{
    /**
     * @return array{total_hits: int, ai_bot_hits: int, last_seen_at: string|null}
     */
    public function signalsForUrl(string $url, int $days = 30): array
    {
        if (! Schema::hasTable('view_logs')) {
            return ['total_hits' => 0, 'ai_bot_hits' => 0, 'last_seen_at' => null];
        }

        $path = parse_url($url, PHP_URL_PATH) ?: '';
        if ($path === '') {
            return ['total_hits' => 0, 'ai_bot_hits' => 0, 'last_seen_at' => null];
        }

        $since = now()->subDays($days);
        $query = DB::table('view_logs')
            ->where('created_at', '>=', $since)
            ->where('url', 'like', '%'.$path.'%');

        $total = (int) (clone $query)->count();
        $aiBotPatterns = ['GPTBot', 'ClaudeBot', 'PerplexityBot', 'Google-Extended', 'Bytespider', 'CCBot'];
        $aiQuery = clone $query;
        $aiQuery->where(function ($q) use ($aiBotPatterns): void {
            foreach ($aiBotPatterns as $pattern) {
                $q->orWhere('user_agent', 'like', '%'.$pattern.'%');
            }
        });
        $aiHits = (int) $aiQuery->count();
        $lastSeen = (clone $query)->orderByDesc('created_at')->value('created_at');

        return [
            'total_hits' => $total,
            'ai_bot_hits' => $aiHits,
            'last_seen_at' => $lastSeen ? (string) $lastSeen : null,
        ];
    }
}
