<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\AiModel;
use App\Models\Author;
use App\Models\Image;
use App\Models\ImageLibrary;
use App\Models\Keyword;
use App\Models\KeywordLibrary;
use App\Models\KnowledgeBase;
use App\Models\KnowledgeChunk;
use App\Models\Prompt;
use App\Models\SiteSetting;
use App\Models\Task;
use App\Models\Title;
use App\Models\TitleLibrary;
use App\Services\GeoFlow\ContentAgent\ContentAgentOrchestrationStatsService;
use App\Services\GeoFlow\ContentAgent\ContentAgentWorkflowCatalogService;
use App\Support\AdminWeb;
use Illuminate\Support\Carbon;
use Illuminate\Support\Facades\Schema;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\View\View;

class ProductionHubController extends Controller
{
    private const TABS = ['overview', 'materials', 'knowledge', 'ai_config'];

    public function __construct(
        private readonly ContentAgentOrchestrationStatsService $orchestrationStatsService,
        private readonly ContentAgentWorkflowCatalogService $workflowCatalogService,
    ) {}

    public function index(Request $request): View|RedirectResponse
    {
        $tab = trim((string) $request->query('tab', 'overview'));
        if ($tab === 'ai-config') {
            return redirect()->route('admin.production.index', array_merge(
                $request->except('tab'),
                ['tab' => 'ai_config']
            ));
        }
        if (! in_array($tab, self::TABS, true)) {
            $tab = 'overview';
        }

        $materialStats = $this->loadMaterialStats();
        $aiStats = $this->loadAiConfiguratorStats();
        $orchestrationStats = in_array($tab, ['knowledge', 'ai_config'], true)
            ? $this->orchestrationStatsService->load()
            : [];
        $workflowCatalog = $tab === 'ai_config'
            ? $this->workflowCatalogService->catalog()
            : ['default_workflow' => 'content_pipeline', 'workflows' => []];

        return view('admin.production.index', [
            'pageTitle' => __('admin.production.hub_title'),
            'activeMenu' => 'production_hub',
            'adminSiteName' => AdminWeb::siteName(),
            'tab' => $tab,
            'currentTab' => $tab,
            'stats' => $materialStats,
            'aiStats' => $aiStats,
            'orchestrationStats' => $orchestrationStats,
            'workflowCatalog' => $workflowCatalog,
        ]);
    }

    /**
     * @return array<string, int|string>
     */
    private function loadMaterialStats(): array
    {
        $knowledgeChunks = (int) KnowledgeChunk::query()->count();
        $vectorizedChunks = (int) KnowledgeChunk::query()
            ->whereNotNull('embedding_model_id')
            ->where('embedding_dimensions', '>', 0)
            ->count();
        $defaultEmbeddingModelId = (int) (SiteSetting::query()
            ->where('setting_key', 'default_embedding_model_id')
            ->value('setting_value') ?? 0);
        $defaultEmbeddingModel = $defaultEmbeddingModelId > 0
            ? (string) (AiModel::query()
                ->whereKey($defaultEmbeddingModelId)
                ->where('status', 'active')
                ->whereRaw("COALESCE(NULLIF(model_type, ''), 'chat') = 'embedding'")
                ->value('name') ?? '')
            : '';
        $chunkStrategy = (string) (SiteSetting::query()
            ->where('setting_key', 'knowledge_chunk_strategy')
            ->value('setting_value') ?? 'rule');

        return [
            'keyword_libraries' => KeywordLibrary::query()->count(),
            'total_keywords' => Keyword::query()->count(),
            'title_libraries' => TitleLibrary::query()->count(),
            'total_titles' => Title::query()->count(),
            'image_libraries' => ImageLibrary::query()->count(),
            'total_images' => Image::query()->count(),
            'knowledge_bases' => KnowledgeBase::query()->count(),
            'knowledge_chunks' => $knowledgeChunks,
            'vectorized_chunks' => $vectorizedChunks,
            'unvectorized_chunks' => max(0, $knowledgeChunks - $vectorizedChunks),
            'knowledge_usage_count' => Task::query()->whereNotNull('knowledge_base_id')->count(),
            'active_embedding_models' => AiModel::query()
                ->where('status', 'active')
                ->whereRaw("COALESCE(NULLIF(model_type, ''), 'chat') = 'embedding'")
                ->count(),
            'default_embedding_model' => $defaultEmbeddingModel,
            'chunk_strategy' => in_array($chunkStrategy, ['rule', 'auto', 'semantic_llm'], true) ? $chunkStrategy : 'rule',
            'latest_knowledge_updated_at' => $this->latestKnowledgeUpdatedAt(),
            'metadata_ready_count' => $this->knowledgeMetadataReadyCount(),
            'reviewed_knowledge_bases' => $this->reviewedKnowledgeBaseCount(),
            'high_risk_pending_count' => $this->highRiskPendingKnowledgeBaseCount(),
            'authors' => Author::query()->count(),
            'body_prompts' => Prompt::query()->where('type', 'body')->count(),
            'special_prompts' => Prompt::query()->where('type', 'special')->count(),
        ];
    }

    /**
     * @return array{model_count:int,prompt_count:int,total_usage:int,today_usage:int}
     */
    private function loadAiConfiguratorStats(): array
    {
        return [
            'model_count' => AiModel::query()->where('status', 'active')->count(),
            'prompt_count' => Prompt::query()->count(),
            'total_usage' => (int) (AiModel::query()->sum('total_used') ?? 0),
            'today_usage' => (int) (AiModel::query()->sum('used_today') ?? 0),
        ];
    }

    private function knowledgeMetadataReadyCount(): int
    {
        $columns = array_values(array_filter(
            ['source_name', 'source_url', 'business_line'],
            static fn (string $column): bool => Schema::hasColumn('knowledge_bases', $column)
        ));
        if ($columns === []) {
            return 0;
        }

        return KnowledgeBase::query()
            ->where(function ($query) use ($columns): void {
                foreach ($columns as $column) {
                    $query->orWhere(function ($inner) use ($column): void {
                        $inner->whereNotNull($column)->where($column, '<>', '');
                    });
                }
            })
            ->count();
    }

    private function reviewedKnowledgeBaseCount(): int
    {
        if (! Schema::hasColumn('knowledge_bases', 'review_status')) {
            return 0;
        }

        return KnowledgeBase::query()
            ->where('review_status', 'reviewed')
            ->count();
    }

    private function highRiskPendingKnowledgeBaseCount(): int
    {
        if (! Schema::hasColumn('knowledge_bases', 'risk_level') || ! Schema::hasColumn('knowledge_bases', 'review_status')) {
            return 0;
        }

        return KnowledgeBase::query()
            ->where('risk_level', 'high')
            ->where('review_status', '<>', 'reviewed')
            ->count();
    }

    private function latestKnowledgeUpdatedAt(): string
    {
        $timestamps = array_filter([
            KnowledgeBase::query()->max('updated_at'),
            KnowledgeChunk::query()->max('updated_at'),
        ]);

        if ($timestamps === []) {
            return '';
        }

        return Carbon::parse(max($timestamps))->format('Y-m-d H:i');
    }
}
