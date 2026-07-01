<?php

namespace App\Services\GeoFlow;

use App\Models\Article;
use App\Models\ArticleDistribution;
use App\Models\DistributionChannel;
use App\Models\TechIpAsset;
use App\Support\GeoFlow\WikiTaskPolicy;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;
use RuntimeException;

class GwebWikiPublisher implements DistributionPublisherInterface
{
    public function __construct(
        private readonly WikiMdxAssembler $mdxAssembler,
        private readonly WikiArticleMetaBuilder $metaBuilder,
    ) {}

    public function health(DistributionChannel $channel): array
    {
        $config = $channel->resolvedGwebConfig();
        $baseUrl = rtrim((string) $config['base_url'], '/');
        if ($baseUrl === '') {
            throw new RuntimeException('Gweb base_url 未配置');
        }

        $response = Http::timeout(10)->get($baseUrl.'/api/pages.json');

        return [
            'ok' => $response->successful(),
            'channel_type' => 'gweb_wiki',
            'status_code' => $response->status(),
            'endpoint' => $baseUrl.'/api/pages.json',
        ];
    }

    public function publish(ArticleDistribution $distribution, array $payload): array
    {
        return $this->sync($distribution, 'upsert');
    }

    public function update(ArticleDistribution $distribution, array $payload): array
    {
        return $this->sync($distribution, 'upsert');
    }

    public function delete(ArticleDistribution $distribution): array
    {
        return $this->sync($distribution, 'delete');
    }

    public function syncSiteSettings(DistributionChannel $channel): array
    {
        return ['ok' => true, 'skipped' => true, 'reason' => 'gweb_wiki_no_site_settings'];
    }

    private function sync(ArticleDistribution $distribution, string $action): array
    {
        $distribution->loadMissing(['article', 'channel']);
        $article = $distribution->article;
        $channel = $distribution->channel;
        if (! $article || ! $channel) {
            throw new RuntimeException('分发记录缺少文章或渠道');
        }

        if (! WikiTaskPolicy::isWikiFormat((string) ($article->content_format ?? 'article'))) {
            throw new RuntimeException('仅 wiki_mdx 格式文章可同步至 Gweb');
        }

        $config = $channel->resolvedGwebConfig();
        $baseUrl = rtrim((string) $config['base_url'], '/');
        $secret = (string) $config['sync_secret'];
        if ($baseUrl === '' || $secret === '') {
            throw new RuntimeException('Gweb 同步配置不完整');
        }

        $wikiMeta = $this->metaBuilder->merge($article);
        $type = (string) ($wikiMeta['type'] ?? 'concept');
        $slug = (string) ($wikiMeta['slug'] ?? $article->slug);
        $routePrefix = $this->mdxAssembler->routePrefixForType($type);
        $body = $action === 'delete'
            ? ''
            : $this->mdxAssembler->assemble((string) $article->title, (string) $article->content, $wikiMeta);

        $syncPayload = [
            'action' => $action,
            'slug' => $slug,
            'type' => $type,
            'route_prefix' => $routePrefix,
            'frontmatter' => $wikiMeta,
            'body' => (string) $article->content,
            'mdx' => $body,
            'article_id' => (int) $article->id,
        ];

        Log::info('gweb_wiki.sync_start', [
            'distribution_id' => (int) $distribution->id,
            'article_id' => (int) $article->id,
            'action' => $action,
            'slug' => $slug,
            'route_prefix' => $routePrefix,
        ]);

        $response = Http::timeout((int) ($config['timeout_seconds'] ?? 30))
            ->withToken($secret)
            ->post($baseUrl.'/api/wiki/sync', $syncPayload);

        if (! $response->successful()) {
            Log::warning('gweb_wiki.sync_failed', [
                'distribution_id' => (int) $distribution->id,
                'status' => $response->status(),
                'body' => $response->body(),
            ]);
            throw new RuntimeException('Gweb 同步失败：HTTP '.$response->status());
        }

        $json = $response->json();
        $remoteUrl = is_array($json) ? (string) ($json['url'] ?? '') : '';
        if ($remoteUrl === '' && $action !== 'delete') {
            $remoteUrl = $baseUrl.'/'.$routePrefix.'/'.$slug;
        }

        $revalidatePaths = is_array($json['revalidate_paths'] ?? null)
            ? $json['revalidate_paths']
            : ['/'.$routePrefix.'/'.$slug, '/wiki', '/'.$routePrefix, '/sitemap.xml'];

        Http::timeout(10)
            ->withToken($secret)
            ->post($baseUrl.'/api/revalidate', ['paths' => $revalidatePaths]);

        Log::info('gweb_wiki.sync_ok', [
            'distribution_id' => (int) $distribution->id,
            'remote_url' => $remoteUrl,
        ]);

        return [
            'remote_id' => $slug,
            'remote_url' => $remoteUrl,
            'remote_meta' => [
                'gweb_wiki' => [
                    'status_code' => $response->status(),
                    'route_prefix' => $routePrefix,
                    'action' => $action,
                ],
            ],
        ];
    }
}
