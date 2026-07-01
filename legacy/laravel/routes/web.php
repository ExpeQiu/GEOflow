<?php

/**
 * Web 路由：前台与 Blade 管理后台（路径见 config/geoflow.admin_base_path，默认 geo_admin）。
 */

use App\Http\Controllers\Admin\AdminActivityLogController;
use App\Http\Controllers\Admin\AdminAuthController;
use App\Http\Controllers\Admin\AdminUserController;
use App\Http\Controllers\Admin\AdminWelcomeController;
use App\Http\Controllers\Admin\AiModelController;
use App\Http\Controllers\Admin\AiPromptController;
use App\Http\Controllers\Admin\AiSpecialPromptController;
use App\Http\Controllers\Admin\AnalyticsController;
use App\Http\Controllers\Admin\ApiTokenController;
use App\Http\Controllers\Admin\ArticleController;
use App\Http\Controllers\Admin\AuthorController;
use App\Http\Controllers\Admin\CategoryController;
use App\Http\Controllers\Admin\DashboardController;
use App\Http\Controllers\Admin\DistributionController;
use App\Http\Controllers\Admin\GeoEvalAlertsController;
use App\Http\Controllers\Admin\GeoEvalDiagnosticsController;
use App\Http\Controllers\Admin\MonitorQuestionController;
use App\Http\Controllers\Admin\StrategyHubController;
use App\Http\Controllers\Admin\StrategySimulatorController;
use App\Http\Controllers\Admin\StrategyWebIntelController;
use App\Http\Controllers\Admin\KnowledgeSettingsController;
use App\Http\Controllers\Admin\ImageLibraryController;
use App\Http\Controllers\Admin\InsightTemplateController;
use App\Http\Controllers\Admin\KeywordLibraryController;
use App\Http\Controllers\Admin\KnowledgeBaseController;
use App\Http\Controllers\Admin\KnowledgeRagSandboxController;
use App\Http\Controllers\Admin\LegacyController;
use App\Http\Controllers\Admin\MaterialsController;
use App\Http\Controllers\Admin\OperationsHubController;
use App\Http\Controllers\Admin\ProductionHubController;
use App\Http\Controllers\Admin\SecuritySettingsController;
use App\Http\Controllers\Admin\SiteSettingsController;
use App\Http\Controllers\Admin\TaskController;
use App\Http\Controllers\Admin\TechIpAssetController;
use App\Http\Controllers\Admin\TitleLibraryController;
use App\Http\Controllers\Admin\UrlImportController;
use App\Http\Controllers\Internal\ContentAgentCallbackController;
use App\Http\Controllers\Site\ArchiveController;
use App\Http\Controllers\Site\ArticleController as SiteArticleController;
use App\Http\Controllers\Site\CategoryController as SiteCategoryController;
use App\Http\Controllers\Site\HomeController;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Route;

Route::post('/internal/content-agent/callback', ContentAgentCallbackController::class)
    ->name('internal.content-agent.callback');

Route::middleware(['site.locale', 'site.public', 'site.view_log'])->group(function (): void {
    Route::get('/', [HomeController::class, 'index'])->name('site.home');
    Route::get('/archive', [ArchiveController::class, 'index'])->name('site.archive');
    Route::get('/archive/{year}/{month}', [ArchiveController::class, 'month'])
        ->name('site.archive.month')
        ->where(['year' => '[0-9]{4}', 'month' => '[0-9]{2}']);
    Route::get('/category/{slug}', [SiteCategoryController::class, 'show'])->name('site.category');
    Route::get('/article/{slug}', [SiteArticleController::class, 'show'])->name('site.article');
});

$adminPrefix = trim((string) config('geoflow.admin_base_path', '/geo_admin'), '/');

Route::prefix($adminPrefix)->name('admin.')->middleware(['admin.locale'])->group(function () {
    // 通用入口与语言切换
    Route::get('locale/{locale}', [AdminAuthController::class, 'switchLocale'])->name('locale.switch');

    Route::get('/', function () {
        return Auth::guard('admin')->check()
            ? redirect()->route('admin.dashboard')
            : redirect()->route('admin.login');
    })->name('entry');

    // 访客认证路由
    Route::middleware('guest:admin')->group(function () {
        Route::get('login', [AdminAuthController::class, 'showLoginForm'])->name('login');
        Route::post('login', [AdminAuthController::class, 'login'])->name('login.attempt');
    });

    // 后台受保护路由
    Route::middleware(['admin.auth', 'admin.activity'])->group(function () {
        // 会话与首页
        Route::post('logout', [AdminAuthController::class, 'logout'])->name('logout');
        Route::post('welcome/dismiss', [AdminWelcomeController::class, 'dismiss'])->name('welcome.dismiss');
        Route::get('dashboard', [DashboardController::class, 'index'])->name('dashboard');
        Route::get('analytics', [AnalyticsController::class, 'index'])->name('analytics');
        Route::prefix('production')->name('production.')->group(function () {
            Route::get('/', [ProductionHubController::class, 'index'])->name('index');
        });
        Route::prefix('operations')->name('operations.')->group(function () {
            Route::get('/', [OperationsHubController::class, 'index'])->name('index');
        });
        Route::prefix('strategy')->name('strategy.')->group(function () {
            Route::get('/', [StrategyHubController::class, 'index'])->name('index');
            Route::post('monitor', [MonitorQuestionController::class, 'store'])->name('monitor.store');
            Route::put('monitor/{questionId}', [MonitorQuestionController::class, 'update'])->name('monitor.update')->whereNumber('questionId');
            Route::delete('monitor/{questionId}', [MonitorQuestionController::class, 'destroy'])->name('monitor.destroy')->whereNumber('questionId');
            Route::post('monitor/import', [MonitorQuestionController::class, 'import'])->name('monitor.import');
            Route::post('monitor/import-batch', [MonitorQuestionController::class, 'importBatch'])->name('monitor.import-batch');
            Route::post('monitor/import-tech-keywords', [MonitorQuestionController::class, 'importTechKeywords'])->name('monitor.import-tech-keywords');
            Route::post('monitor/config', [MonitorQuestionController::class, 'saveConfig'])->name('monitor.config');
            Route::post('monitor/scan', [MonitorQuestionController::class, 'scan'])->name('monitor.scan');
            Route::post('web-intel/sources', [StrategyWebIntelController::class, 'storeSource'])->name('web-intel.sources.store');
            Route::delete('web-intel/sources/{sourceId}', [StrategyWebIntelController::class, 'destroySource'])->name('web-intel.sources.destroy')->whereNumber('sourceId');
            Route::post('web-intel/sources/{sourceId}/refresh', [StrategyWebIntelController::class, 'refreshSource'])->name('web-intel.sources.refresh')->whereNumber('sourceId');
            Route::post('web-intel/reports/compose', [StrategyWebIntelController::class, 'composeReport'])->name('web-intel.reports.compose');
            Route::post('simulator/articles/{articleId}/reevaluate', [StrategySimulatorController::class, 'reevaluate'])->name('simulator.reevaluate')->whereNumber('articleId');
            Route::post('simulator/batch-reevaluate', [StrategySimulatorController::class, 'batchReevaluate'])->name('simulator.batch-reevaluate');
            Route::post('simulator/articles/{articleId}/apply-recommendations', [StrategySimulatorController::class, 'applyRecommendations'])->name('simulator.apply-recommendations')->whereNumber('articleId');
        });
        Route::prefix('geo-eval')->name('geo-eval.')->group(function () {
            Route::get('diagnostics', [GeoEvalDiagnosticsController::class, 'index'])->name('diagnostics');
            Route::get('alerts', [GeoEvalAlertsController::class, 'index'])->name('alerts');
            Route::post('articles/{articleId}/reevaluate', [GeoEvalDiagnosticsController::class, 'reevaluate'])
                ->name('reevaluate')
                ->whereNumber('articleId');
            Route::post('reevaluate-failed', [GeoEvalDiagnosticsController::class, 'batchReevaluate'])->name('reevaluate-failed');
        });
        Route::prefix('knowledge-settings')->name('knowledge-settings.')->group(function () {
            Route::get('/', [KnowledgeSettingsController::class, 'index'])->name('index');
            Route::put('/', [KnowledgeSettingsController::class, 'update'])->name('update');
        });
        Route::prefix('tech-assets')->name('tech-assets.')->group(function () {
            Route::get('/', [TechIpAssetController::class, 'index'])->name('index');
            Route::get('create', [TechIpAssetController::class, 'create'])->name('create');
            Route::post('create', [TechIpAssetController::class, 'store'])->name('store');
            Route::post('import', [TechIpAssetController::class, 'import'])->name('import');
            Route::get('{assetId}/edit', [TechIpAssetController::class, 'edit'])->name('edit')->whereNumber('assetId');
            Route::put('{assetId}', [TechIpAssetController::class, 'update'])->name('update')->whereNumber('assetId');
        });
        Route::prefix('insight-templates')->name('insight-templates.')->group(function () {
            Route::get('/', [InsightTemplateController::class, 'index'])->name('index');
            Route::get('create', [InsightTemplateController::class, 'create'])->name('create');
            Route::post('create', [InsightTemplateController::class, 'store'])->name('store');
            Route::get('{templateId}', [InsightTemplateController::class, 'show'])->name('show')->whereNumber('templateId');
            Route::get('{templateId}/edit', [InsightTemplateController::class, 'edit'])->name('edit')->whereNumber('templateId');
            Route::put('{templateId}', [InsightTemplateController::class, 'update'])->name('update')->whereNumber('templateId');
            Route::post('{templateId}/delete', [InsightTemplateController::class, 'destroy'])->name('destroy')->whereNumber('templateId');
            Route::post('{templateId}/re-mine', [InsightTemplateController::class, 'remine'])->name('remine')->whereNumber('templateId');
        });

        // 任务管理（Blade 新路径）
        Route::prefix('tasks')->name('tasks.')->group(function () {
            Route::get('/', [TaskController::class, 'index'])->name('index');
            Route::post('{taskId}/toggle-status', [TaskController::class, 'toggleStatus'])->name('toggle-status');
            Route::post('{taskId}/delete', [TaskController::class, 'destroyTask'])->name('delete');
            Route::get('create', [TaskController::class, 'create'])->name('create');
            Route::post('create', [TaskController::class, 'store'])->name('store');
            Route::get('{taskId}/edit', [TaskController::class, 'edit'])->name('edit');
            Route::put('{taskId}', [TaskController::class, 'update'])->name('update');
            Route::get('health-check', [TaskController::class, 'healthCheck'])->name('health');
            Route::post('batch/start', [TaskController::class, 'batchAction'])->name('batch');
        });

        // 分发管理：集中管理外部站点 Agent 与文章分发队列
        Route::prefix('distribution')->name('distribution.')->group(function () {
            Route::get('/', [DistributionController::class, 'index'])->name('index');
            Route::get('create', [DistributionController::class, 'create'])->name('create');
            Route::post('create', [DistributionController::class, 'store'])->name('store');
            Route::get('jobs', [DistributionController::class, 'jobs'])->name('jobs');
            Route::get('jobs/{distributionId}/edit', [DistributionController::class, 'editArticle'])->name('article.edit')->whereNumber('distributionId');
            Route::put('jobs/{distributionId}', [DistributionController::class, 'updateArticle'])->name('article.update')->whereNumber('distributionId');
            Route::post('jobs/{distributionId}/delete', [DistributionController::class, 'deleteArticle'])->name('article.delete')->whereNumber('distributionId');
            Route::post('jobs/{distributionId}/retry', [DistributionController::class, 'retry'])->name('retry')->whereNumber('distributionId');
            Route::get('{channelId}/edit', [DistributionController::class, 'edit'])->name('edit')->whereNumber('channelId');
            Route::put('{channelId}', [DistributionController::class, 'update'])->name('update')->whereNumber('channelId');
            Route::post('{channelId}/pause', [DistributionController::class, 'pause'])->name('pause')->whereNumber('channelId');
            Route::post('{channelId}/activate', [DistributionController::class, 'activate'])->name('activate')->whereNumber('channelId');
            Route::post('{channelId}/rotate-secret', [DistributionController::class, 'rotateSecret'])->name('rotate-secret')->whereNumber('channelId');
            Route::post('{channelId}/reveal-secret', [DistributionController::class, 'revealSecret'])->name('reveal-secret')->whereNumber('channelId');
            Route::post('{channelId}/download-package', [DistributionController::class, 'downloadPackage'])->name('download-package')->whereNumber('channelId');
            Route::post('{channelId}/sync-settings', [DistributionController::class, 'syncSettings'])->name('sync-settings')->whereNumber('channelId');
            Route::get('{channelId}', [DistributionController::class, 'show'])->name('show')->whereNumber('channelId');
            Route::post('{channelId}/health', [DistributionController::class, 'health'])->name('health')->whereNumber('channelId');
        });

        // 文章管理（Blade 新路径）
        Route::prefix('articles')->name('articles.')->group(function () {
            Route::get('/', [ArticleController::class, 'index'])->name('index');
            Route::post('batch/update-status', [ArticleController::class, 'batchUpdateStatus'])->name('batch.update-status');
            Route::post('batch/update-review', [ArticleController::class, 'batchUpdateReview'])->name('batch.update-review');
            Route::post('batch/delete', [ArticleController::class, 'batchDelete'])->name('batch.delete');
            Route::post('batch/restore', [ArticleController::class, 'batchRestore'])->name('batch.restore');
            Route::post('batch/force-delete', [ArticleController::class, 'batchForceDelete'])->name('batch.force-delete');
            Route::post('trash/empty', [ArticleController::class, 'emptyTrash'])->name('trash.empty');
            Route::get('create', [ArticleController::class, 'create'])->name('create');
            Route::post('create', [ArticleController::class, 'store'])->name('store');
            Route::post('{articleId}/restore', [ArticleController::class, 'restore'])->name('restore')->whereNumber('articleId');
            Route::post('{articleId}/force-delete', [ArticleController::class, 'forceDelete'])->name('force-delete')->whereNumber('articleId');
            Route::get('{articleId}/edit', [ArticleController::class, 'edit'])->name('edit');
            Route::put('{articleId}', [ArticleController::class, 'update'])->name('update');
        });

        // 栏目管理（保持 geo_admin/categories 路径语义）
        Route::prefix('categories')->name('categories.')->group(function () {
            Route::get('/', [CategoryController::class, 'index'])->name('index');
            Route::get('create', [CategoryController::class, 'create'])->name('create');
            Route::post('create', [CategoryController::class, 'store'])->name('store');
            Route::get('{categoryId}/edit', [CategoryController::class, 'edit'])->name('edit');
            Route::put('{categoryId}', [CategoryController::class, 'update'])->name('update');
            Route::post('{categoryId}/delete', [CategoryController::class, 'destroy'])->name('delete');
        });

        // 素材管理：作者管理
        Route::prefix('authors')->name('authors.')->group(function () {
            Route::get('/', [AuthorController::class, 'index'])->name('index');
            Route::get('create', [AuthorController::class, 'create'])->name('create');
            Route::post('create', [AuthorController::class, 'store'])->name('store');
            Route::get('{authorId}/edit', [AuthorController::class, 'edit'])->name('edit');
            Route::get('{authorId}/detail', [AuthorController::class, 'detail'])->name('detail');
            Route::put('{authorId}', [AuthorController::class, 'update'])->name('update');
            Route::post('{authorId}/delete', [AuthorController::class, 'destroy'])->name('delete');
        });

        // 素材管理：关键词库管理
        Route::prefix('keyword-libraries')->name('keyword-libraries.')->group(function () {
            Route::get('/', [KeywordLibraryController::class, 'index'])->name('index');
            Route::get('create', [KeywordLibraryController::class, 'create'])->name('create');
            Route::post('create', [KeywordLibraryController::class, 'store'])->name('store');
            Route::get('{libraryId}/edit', [KeywordLibraryController::class, 'edit'])->name('edit');
            Route::get('{libraryId}/detail', [KeywordLibraryController::class, 'detail'])->name('detail');
            Route::post('{libraryId}/keywords', [KeywordLibraryController::class, 'storeKeyword'])->name('keywords.store');
            Route::post('{libraryId}/keywords/delete', [KeywordLibraryController::class, 'destroyKeywords'])->name('keywords.delete');
            Route::post('{libraryId}/import', [KeywordLibraryController::class, 'importKeywords'])->name('import');
            Route::put('{libraryId}/detail', [KeywordLibraryController::class, 'updateFromDetail'])->name('detail.update');
            Route::put('{libraryId}', [KeywordLibraryController::class, 'update'])->name('update');
            Route::post('{libraryId}/delete', [KeywordLibraryController::class, 'destroy'])->name('delete');
        });

        // 素材管理：标题库管理
        Route::prefix('title-libraries')->name('title-libraries.')->group(function () {
            Route::get('/', [TitleLibraryController::class, 'index'])->name('index');
            Route::get('create', [TitleLibraryController::class, 'create'])->name('create');
            Route::post('create', [TitleLibraryController::class, 'store'])->name('store');
            Route::get('{libraryId}/edit', [TitleLibraryController::class, 'edit'])->name('edit');
            Route::get('{libraryId}/detail', [TitleLibraryController::class, 'detail'])->name('detail');
            Route::post('{libraryId}/titles', [TitleLibraryController::class, 'storeTitle'])->name('titles.store');
            Route::post('{libraryId}/titles/delete', [TitleLibraryController::class, 'destroyTitles'])->name('titles.delete');
            Route::post('{libraryId}/import', [TitleLibraryController::class, 'importTitles'])->name('import');
            Route::get('{libraryId}/ai-generate', [TitleLibraryController::class, 'aiGenerate'])->name('ai-generate');
            Route::post('{libraryId}/ai-generate', [TitleLibraryController::class, 'generateWithAi'])->name('ai-generate.submit');
            Route::put('{libraryId}', [TitleLibraryController::class, 'update'])->name('update');
            Route::post('{libraryId}/delete', [TitleLibraryController::class, 'destroy'])->name('delete');
        });

        // 素材管理：图片库管理
        Route::prefix('image-libraries')->name('image-libraries.')->group(function () {
            Route::get('/', [ImageLibraryController::class, 'index'])->name('index');
            Route::get('create', [ImageLibraryController::class, 'create'])->name('create');
            Route::post('create', [ImageLibraryController::class, 'store'])->name('store');
            Route::get('{libraryId}/edit', [ImageLibraryController::class, 'edit'])->name('edit');
            Route::get('{libraryId}/detail', [ImageLibraryController::class, 'detail'])->name('detail');
            Route::post('{libraryId}/images/upload', [ImageLibraryController::class, 'uploadImages'])->name('images.upload');
            Route::post('{libraryId}/images/delete', [ImageLibraryController::class, 'destroyImages'])->name('images.delete');
            Route::put('{libraryId}/detail', [ImageLibraryController::class, 'updateFromDetail'])->name('detail.update');
            Route::put('{libraryId}', [ImageLibraryController::class, 'update'])->name('update');
            Route::post('{libraryId}/delete', [ImageLibraryController::class, 'destroy'])->name('delete');
        });

        // 素材管理：知识库管理
        Route::prefix('knowledge-bases')->name('knowledge-bases.')->group(function () {
            Route::get('rag-sandbox', [KnowledgeRagSandboxController::class, 'index'])->name('rag-sandbox');
            Route::get('/', [KnowledgeBaseController::class, 'index'])->name('index');
            Route::get('create', [KnowledgeBaseController::class, 'create'])->name('create');
            Route::post('create', [KnowledgeBaseController::class, 'store'])->name('store');
            Route::get('{knowledgeBaseId}/edit', [KnowledgeBaseController::class, 'edit'])->name('edit');
            Route::get('{knowledgeBaseId}/detail', [KnowledgeBaseController::class, 'detail'])->name('detail');
            Route::post('upload', [KnowledgeBaseController::class, 'uploadFile'])->name('upload');
            Route::post('{knowledgeBaseId}/chunks/refresh', [KnowledgeBaseController::class, 'refreshChunks'])->name('chunks.refresh');
            Route::put('{knowledgeBaseId}/detail', [KnowledgeBaseController::class, 'updateFromDetail'])->name('detail.update');
            Route::put('{knowledgeBaseId}', [KnowledgeBaseController::class, 'update'])->name('update');
            Route::post('{knowledgeBaseId}/delete', [KnowledgeBaseController::class, 'destroy'])->name('delete');
        });

        // 业务页面
        Route::get('materials', [MaterialsController::class, 'index'])->name('materials.index');
        Route::get('url-import', [UrlImportController::class, 'index'])->name('url-import');
        Route::post('url-import', [UrlImportController::class, 'store'])->name('url-import.store');
        Route::get('url-import/history', [UrlImportController::class, 'history'])->name('url-import.history');
        Route::post('url-import/{jobId}/run', [UrlImportController::class, 'run'])
            ->name('url-import.run')
            ->whereNumber('jobId');
        Route::get('url-import/{jobId}/status', [UrlImportController::class, 'status'])
            ->name('url-import.status')
            ->whereNumber('jobId');
        Route::post('url-import/{jobId}/commit', [UrlImportController::class, 'commit'])
            ->name('url-import.commit')
            ->whereNumber('jobId');
        Route::get('url-import/{jobId}', [UrlImportController::class, 'show'])
            ->name('url-import.show')
            ->whereNumber('jobId');

        // AI 配置模块（配置器 / 模型 / 提示词）
        Route::group([], function () {
            Route::get('ai-configurator', [LegacyController::class, 'aiConfigurator'])->name('ai.configurator');
            Route::prefix('ai-models')->name('ai-models.')->group(function () {
                Route::get('/', [AiModelController::class, 'index'])->name('index');
                Route::post('create', [AiModelController::class, 'store'])->name('store');
                Route::put('{modelId}', [AiModelController::class, 'update'])->name('update');
                Route::post('{modelId}/test', [AiModelController::class, 'testConnection'])->name('test');
                Route::post('{modelId}/delete', [AiModelController::class, 'destroy'])->name('delete');
                Route::post('default-embedding', [AiModelController::class, 'updateDefaultEmbedding'])->name('default-embedding');
                Route::post('chunking-config', [AiModelController::class, 'updateChunkingConfig'])->name('chunking-config');
            });
            Route::get('ai-prompts', [AiPromptController::class, 'index'])->name('ai-prompts');
            Route::post('ai-prompts/create', [AiPromptController::class, 'store'])->name('ai-prompts.store');
            Route::put('ai-prompts/{promptId}', [AiPromptController::class, 'update'])->name('ai-prompts.update');
            Route::post('ai-prompts/{promptId}/delete', [AiPromptController::class, 'destroy'])->name('ai-prompts.delete');
            Route::get('ai-special-prompts', [AiSpecialPromptController::class, 'index'])->name('ai-special-prompts');
            Route::post('ai-special-prompts/keyword', [AiSpecialPromptController::class, 'updateKeyword'])->name('ai-special-prompts.keyword');
            Route::post('ai-special-prompts/description', [AiSpecialPromptController::class, 'updateDescription'])->name('ai-special-prompts.description');
        });

        Route::prefix('site-settings')->name('site-settings.')->group(function () {
            Route::get('/', [SiteSettingsController::class, 'index'])->name('index');
            Route::post('/', [SiteSettingsController::class, 'update'])->name('update');
            Route::post('theme', [SiteSettingsController::class, 'updateTheme'])->name('theme');
            Route::post('article-detail-ads', [SiteSettingsController::class, 'updateArticleDetailAds'])->name('ads');
            Route::get('sensitive-words', [SecuritySettingsController::class, 'index'])->name('sensitive-words');
            Route::post('sensitive-words', [SecuritySettingsController::class, 'storeSensitiveWords'])->name('sensitive-words.store');
            Route::post('sensitive-words/{wordId}/delete', [SecuritySettingsController::class, 'destroySensitiveWord'])
                ->name('sensitive-words.delete')
                ->whereNumber('wordId');
        });
        Route::prefix('security-settings')->name('security-settings.')->group(function () {
            Route::get('/', fn () => redirect()->route('admin.site-settings.sensitive-words'))->name('index');
            Route::post('sensitive-words', [SecuritySettingsController::class, 'storeSensitiveWords'])->name('words.store');
            Route::post('sensitive-words/{wordId}/delete', [SecuritySettingsController::class, 'destroySensitiveWord'])->name('words.delete');
            Route::post('password', [SecuritySettingsController::class, 'updatePassword'])->name('password.update');
        });

        // 超级管理员功能
        Route::middleware('admin.super')->group(function () {
            Route::prefix('admin-users')->name('admin-users.')->group(function () {
                Route::get('/', [AdminUserController::class, 'index'])->name('index');
                Route::post('create', [AdminUserController::class, 'store'])->name('store');
                Route::post('{adminId}/update', [AdminUserController::class, 'update'])->name('update');
                Route::post('{adminId}/toggle-status', [AdminUserController::class, 'toggleStatus'])->name('toggle-status');
                Route::post('{adminId}/delete', [AdminUserController::class, 'destroy'])->name('delete');
            });
            Route::get('admin-activity-logs', [AdminActivityLogController::class, 'index'])->name('admin-activity-logs');
            Route::prefix('api-tokens')->name('api-tokens.')->group(function () {
                Route::get('/', [ApiTokenController::class, 'index'])->name('index');
                Route::post('/', [ApiTokenController::class, 'store'])->name('store');
                Route::post('{tokenId}/revoke', [ApiTokenController::class, 'revoke'])->name('revoke');
            });
        });
    });
});
