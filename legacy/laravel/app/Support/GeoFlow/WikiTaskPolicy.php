<?php

namespace App\Support\GeoFlow;

use App\Models\DistributionChannel;
use App\Models\Task;
use Illuminate\Http\Request;
use Illuminate\Support\Collection;
use Illuminate\Validation\ValidationException;

/** Wiki 类 Task 的发布范围与渠道约束（阶段零减法）。 */
final class WikiTaskPolicy
{
    public static function isWikiFormat(?string $contentFormat): bool
    {
        return ($contentFormat ?? 'article') === 'wiki_mdx';
    }

    public static function isWikiTask(Task|array $task): bool
    {
        $format = $task instanceof Task
            ? (string) ($task->content_format ?? 'article')
            : (string) ($task['content_format'] ?? 'article');

        return self::isWikiFormat($format);
    }

    /**
     * @param  array<string, mixed>  $payload
     */
    public static function assertValid(array $payload, Request $request): void
    {
        if (! self::isWikiFormat((string) ($payload['content_format'] ?? 'article'))) {
            return;
        }

        $scope = (string) ($payload['publish_scope'] ?? 'distribution_only');
        if ($scope !== 'distribution_only') {
            throw ValidationException::withMessages([
                'publish_scope' => __('admin.wiki_task.error.scope_must_distribution_only'),
            ]);
        }

        $channelIds = collect($request->input('distribution_channel_ids', []))
            ->map(static fn ($id): int => (int) $id)
            ->filter(static fn (int $id): bool => $id > 0)
            ->unique()
            ->values();

        if ($channelIds->isEmpty()) {
            throw ValidationException::withMessages([
                'distribution_channel_ids' => __('admin.wiki_task.error.requires_gweb_channel'),
            ]);
        }

        $forbidden = DistributionChannel::query()
            ->whereIn('id', $channelIds->all())
            ->get()
            ->filter(static fn (DistributionChannel $channel): bool => in_array($channel->channelType(), ['geoflow_agent'], true));

        if ($forbidden->isNotEmpty()) {
            throw ValidationException::withMessages([
                'distribution_channel_ids' => __('admin.wiki_task.error.forbidden_agent_channel', [
                    'names' => $forbidden->pluck('name')->implode('、'),
                ]),
            ]);
        }

        $allowedTypes = ['gweb_wiki', 'generic_http_api'];
        $channels = DistributionChannel::query()->whereIn('id', $channelIds->all())->get();
        $invalid = $channels->filter(static fn (DistributionChannel $c): bool => ! in_array($c->channelType(), $allowedTypes, true));
        if ($invalid->isNotEmpty()) {
            throw ValidationException::withMessages([
                'distribution_channel_ids' => __('admin.wiki_task.error.invalid_wiki_channel', [
                    'names' => $invalid->pluck('name')->implode('、'),
                ]),
            ]);
        }
    }

    /**
     * @param  array<string, mixed>  $payload
     * @return array<string, mixed>
     */
    public static function applyDefaults(array $payload): array
    {
        if (! self::isWikiFormat((string) ($payload['content_format'] ?? 'article'))) {
            return $payload;
        }

        $payload['publish_scope'] = 'distribution_only';
        if (empty($payload['auto_keywords'])) {
            $payload['auto_keywords'] = 0;
        }
        if (empty($payload['auto_description'])) {
            $payload['auto_description'] = 0;
        }

        return $payload;
    }

    /**
     * @param  Collection<int, array<string, mixed>>|list<array<string, mixed>>  $channels
     * @return list<array<string, mixed>>
     */
    public static function filterChannelsForForm(Collection|array $channels, bool $isWiki): array
    {
        $items = $channels instanceof Collection ? $channels : collect($channels);

        if (! $isWiki) {
            return $items->values()->all();
        }

        return $items
            ->filter(static fn (array $channel): bool => in_array(
                (string) ($channel['channel_type'] ?? ''),
                ['gweb_wiki', 'generic_http_api'],
                true
            ))
            ->values()
            ->all();
    }
}
