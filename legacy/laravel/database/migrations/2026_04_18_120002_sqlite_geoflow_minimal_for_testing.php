<?php

/**
 * 仅在 PHPUnit（APP_ENV=testing）且 SQLite 内存库下创建 GEOworkflow 最小表结构，
 * 供 API 契约测试使用。生产/开发 PostgreSQL 仍以 120000 全量 SQL 为准，勿依赖本迁移。
 */

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (DB::getDriverName() !== 'sqlite' || ! app()->environment('testing')) {
            return;
        }

        Schema::create('api_idempotency_keys', function (Blueprint $table) {
            $table->id();
            $table->string('idempotency_key', 120);
            $table->string('route_key', 120);
            $table->string('request_hash', 64);
            $table->text('response_body');
            $table->integer('response_status');
            $table->timestamps();
            $table->unique(['idempotency_key', 'route_key']);
        });

        Schema::create('ai_models', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->string('version', 50)->default('');
            $table->string('api_key', 500)->default('');
            $table->string('model_id', 100);
            $table->string('model_type', 20)->nullable();
            $table->string('api_url', 500)->default('');
            $table->integer('failover_priority')->default(100);
            $table->integer('daily_limit')->default(0);
            $table->integer('used_today')->default(0);
            $table->integer('total_used')->default(0);
            $table->string('status', 20)->default('active');
            $table->timestamps();
        });

        Schema::create('prompts', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->string('type', 50);
            $table->text('content');
            $table->text('variables')->nullable();
            $table->timestamps();
        });

        Schema::create('sensitive_words', function (Blueprint $table) {
            $table->id();
            $table->string('word', 100)->unique();
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('keyword_libraries', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->text('description')->nullable();
            $table->integer('keyword_count')->default(0);
            $table->timestamps();
        });

        Schema::create('keywords', function (Blueprint $table) {
            $table->id();
            $table->foreignId('library_id')->constrained('keyword_libraries')->cascadeOnDelete();
            $table->string('keyword', 200);
            $table->integer('used_count')->default(0);
            $table->integer('usage_count')->default(0);
            $table->timestamp('created_at')->nullable();
            $table->unique(['library_id', 'keyword']);
        });

        Schema::create('title_libraries', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->text('description')->nullable();
            $table->integer('title_count')->default(0);
            $table->string('generation_type', 20)->default('manual');
            $table->foreignId('keyword_library_id')->nullable()->constrained('keyword_libraries');
            $table->foreignId('ai_model_id')->nullable()->constrained('ai_models');
            $table->foreignId('prompt_id')->nullable()->constrained('prompts');
            $table->integer('generation_rounds')->default(1);
            $table->integer('is_ai_generated')->default(0);
            $table->timestamps();
        });

        Schema::create('titles', function (Blueprint $table) {
            $table->id();
            $table->foreignId('library_id')->constrained('title_libraries')->cascadeOnDelete();
            $table->string('title', 500);
            $table->string('keyword', 200)->default('');
            $table->boolean('is_ai_generated')->default(false);
            $table->integer('used_count')->default(0);
            $table->integer('usage_count')->default(0);
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('knowledge_bases', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->text('description')->nullable();
            $table->text('content')->default('');
            $table->integer('character_count')->default(0);
            $table->integer('used_task_count')->default(0);
            $table->string('file_type', 20)->default('markdown');
            $table->string('file_path', 500)->default('');
            $table->integer('word_count')->default(0);
            $table->integer('usage_count')->default(0);
            $table->timestamps();
        });

        Schema::create('knowledge_chunks', function (Blueprint $table) {
            $table->id();
            $table->foreignId('knowledge_base_id')->constrained('knowledge_bases')->cascadeOnDelete();
            $table->integer('chunk_index');
            $table->text('content');
            $table->string('content_hash', 64)->default('');
            $table->integer('token_count')->default(0);
            $table->text('embedding_json')->nullable();
            $table->integer('embedding_model_id')->nullable();
            $table->integer('embedding_dimensions')->default(0);
            $table->string('embedding_provider', 255)->default('');
            $table->text('embedding_vector')->nullable();
            $table->timestamps();
            $table->unique(['knowledge_base_id', 'chunk_index']);
        });

        Schema::create('image_libraries', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->text('description')->nullable();
            $table->integer('image_count')->default(0);
            $table->integer('used_task_count')->default(0);
            $table->timestamps();
        });

        Schema::create('images', function (Blueprint $table) {
            $table->id();
            $table->foreignId('library_id')->constrained('image_libraries')->cascadeOnDelete();
            $table->string('filename', 255);
            $table->string('original_name', 255);
            $table->string('file_name', 255)->default('');
            $table->string('file_path', 500);
            $table->integer('file_size')->default(0);
            $table->string('mime_type', 100)->default('');
            $table->integer('width')->default(0);
            $table->integer('height')->default(0);
            $table->text('tags')->nullable();
            $table->integer('used_count')->default(0);
            $table->integer('usage_count')->default(0);
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('tech_ip_assets', function (Blueprint $table) {
            $table->id();
            $table->string('ip_id', 120)->unique();
            $table->string('ip_name', 200);
            $table->string('ip_layer', 40)->default('模块层');
            $table->string('mind_tag', 500)->nullable();
            $table->string('priority', 10)->default('P1');
            $table->boolean('can_name')->default(false);
            $table->boolean('can_visualize')->default(false);
            $table->boolean('can_translate')->default(false);
            $table->text('tech_term')->nullable();
            $table->text('user_language')->nullable();
            $table->text('evidence')->nullable();
            $table->text('models')->nullable();
            $table->string('wiki_type', 40)->nullable();
            $table->string('wiki_slug', 120)->nullable();
            $table->string('status', 40)->default('待封装');
            $table->unsignedBigInteger('knowledge_base_id')->nullable();
            $table->timestamps();
        });

        Schema::create('tasks', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->foreignId('title_library_id')->nullable()->constrained('title_libraries');
            $table->foreignId('image_library_id')->nullable()->constrained('image_libraries');
            $table->foreignId('knowledge_base_id')->nullable()->constrained('knowledge_bases');
            $table->unsignedBigInteger('insight_template_id')->nullable();
            $table->foreignId('prompt_id')->nullable()->constrained('prompts');
            $table->foreignId('ai_model_id')->nullable()->constrained('ai_models');
            $table->integer('image_count')->default(0);
            $table->unsignedBigInteger('author_id')->nullable();
            $table->integer('need_review')->default(1);
            $table->integer('publish_interval')->default(3600);
            $table->integer('auto_keywords')->default(1);
            $table->integer('auto_description')->default(1);
            $table->integer('draft_limit')->default(10);
            $table->integer('article_limit')->default(10);
            $table->integer('is_loop')->default(0);
            $table->string('model_selection_mode', 20)->default('fixed');
            $table->string('content_pipeline_mode', 20)->default('legacy');
            $table->string('content_format', 20)->default('article');
            $table->string('wiki_page_type', 40)->nullable();
            $table->unsignedBigInteger('tech_ip_asset_id')->nullable();
            $table->string('publish_scope', 40)->default('local_and_distribution');
            $table->integer('created_count')->default(0);
            $table->integer('published_count')->default(0);
            $table->integer('loop_count')->default(0);
            $table->string('category_mode', 20)->default('smart');
            $table->unsignedBigInteger('fixed_category_id')->nullable();
            $table->timestamp('last_run_at')->nullable();
            $table->timestamp('next_run_at')->nullable();
            $table->timestamp('next_publish_at')->nullable();
            $table->timestamp('last_success_at')->nullable();
            $table->timestamp('last_error_at')->nullable();
            $table->text('last_error_message')->nullable();
            $table->integer('schedule_enabled')->default(1);
            $table->integer('max_retry_count')->default(3);
            $table->string('status', 20)->default('active');
            $table->timestamps();
        });

        Schema::create('authors', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->text('bio')->nullable();
            $table->string('email', 100)->default('');
            $table->string('avatar', 200)->default('');
            $table->string('website', 200)->default('');
            $table->text('social_links')->nullable();
            $table->timestamps();
        });

        Schema::create('categories', function (Blueprint $table) {
            $table->id();
            $table->string('name', 100);
            $table->string('slug', 100)->unique();
            $table->text('description')->nullable();
            $table->integer('sort_order')->default(0);
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('articles', function (Blueprint $table) {
            $table->id();
            $table->string('title', 500);
            $table->string('slug', 500)->unique();
            $table->text('excerpt')->nullable();
            $table->text('content');
            $table->string('content_format', 20)->default('article');
            $table->text('wiki_meta')->nullable();
            $table->unsignedBigInteger('tech_ip_asset_id')->nullable();
            $table->foreignId('category_id')->constrained('categories');
            $table->foreignId('author_id')->constrained('authors');
            $table->foreignId('task_id')->nullable()->constrained('tasks')->nullOnDelete();
            $table->string('original_keyword', 200)->default('');
            $table->text('keywords')->nullable();
            $table->text('meta_description')->nullable();
            $table->string('status', 20)->default('draft');
            $table->string('review_status', 20)->default('pending');
            $table->string('eval_status', 32)->default('skipped');
            $table->text('eval_meta')->nullable();
            $table->integer('view_count')->default(0);
            $table->integer('is_ai_generated')->default(0);
            $table->timestamps();
            $table->timestamp('published_at')->nullable();
            $table->softDeletes();
        });

        Schema::create('article_evaluations', function (Blueprint $table) {
            $table->id();
            $table->foreignId('article_id')->constrained('articles')->cascadeOnDelete();
            $table->unsignedBigInteger('task_run_id')->nullable();
            $table->string('idempotency_key', 191);
            $table->string('eval_type', 32)->default('simulation');
            $table->string('status', 32)->default('pending_eval');
            $table->string('request_id', 64)->nullable();
            $table->text('metrics')->nullable();
            $table->string('failure_reason', 500)->nullable();
            $table->text('raw_response')->nullable();
            $table->timestamps();
            $table->unique(['article_id', 'idempotency_key']);
        });

        Schema::create('insight_templates', function (Blueprint $table) {
            $table->id();
            $table->string('name', 120);
            $table->string('source_url', 500)->nullable();
            $table->text('style_guide')->nullable();
            $table->text('features')->nullable();
            $table->decimal('eeat_score', 5, 2)->nullable();
            $table->unsignedBigInteger('created_by_admin_id')->nullable();
            $table->timestamps();
        });

        Schema::create('geo_eval_event_logs', function (Blueprint $table) {
            $table->id();
            $table->string('request_id', 64);
            $table->unsignedBigInteger('task_id')->nullable();
            $table->unsignedBigInteger('article_id')->nullable();
            $table->unsignedBigInteger('channel_id')->nullable();
            $table->string('eval_status', 32)->nullable();
            $table->string('event', 120);
            $table->string('level', 16)->default('info');
            $table->string('message', 500)->nullable();
            $table->text('context')->nullable();
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('geo_strategy_metric_snapshots', function (Blueprint $table) {
            $table->id();
            $table->date('metric_date');
            $table->string('platform', 64)->default('');
            $table->decimal('adoption_rate', 8, 4)->default(0);
            $table->decimal('first_position_rate', 8, 4)->default(0);
            $table->unsignedInteger('sample_size')->default(0);
            $table->unsignedInteger('passed_count')->default(0);
            $table->text('meta')->nullable();
            $table->timestamps();
            $table->unique(['metric_date', 'platform']);
        });

        Schema::create('geo_market_scan_runs', function (Blueprint $table) {
            $table->id();
            $table->string('scan_type', 32)->default('weekly');
            $table->string('status', 32)->default('completed');
            $table->text('summary_json')->nullable();
            $table->timestamp('ran_at')->nullable();
            $table->timestamps();
        });

        Schema::create('geo_admin_alerts', function (Blueprint $table) {
            $table->id();
            $table->string('alert_type', 64);
            $table->string('severity', 16)->default('warning');
            $table->decimal('threshold', 8, 4)->nullable();
            $table->decimal('current_value', 8, 4)->nullable();
            $table->string('message', 500)->nullable();
            $table->text('channels')->nullable();
            $table->integer('notified_feishu')->default(0);
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('geo_monitor_questions', function (Blueprint $table) {
            $table->id();
            $table->text('question_text');
            $table->string('category', 120)->default('');
            $table->string('intent_type', 32)->default('factual');
            $table->string('source', 32)->default('manual');
            $table->unsignedBigInteger('knowledge_base_id')->nullable();
            $table->unsignedBigInteger('task_id')->nullable();
            $table->unsignedBigInteger('target_article_id')->nullable();
            $table->text('target_content_snapshot')->nullable();
            $table->integer('is_active')->default(1);
            $table->unsignedSmallInteger('priority')->default(50);
            $table->text('tags')->nullable();
            $table->text('tech_keywords')->nullable();
            $table->unsignedBigInteger('created_by_admin_id')->nullable();
            $table->timestamps();
        });

        Schema::create('geo_monitor_runs', function (Blueprint $table) {
            $table->id();
            $table->string('run_type', 32)->default('scheduled');
            $table->string('status', 32)->default('pending');
            $table->unsignedInteger('question_count')->default(0);
            $table->text('meta')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('finished_at')->nullable();
            $table->timestamps();
        });

        Schema::create('geo_monitor_results', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('question_id');
            $table->unsignedBigInteger('run_id');
            $table->unsignedBigInteger('article_id')->nullable();
            $table->unsignedSmallInteger('rank')->default(99);
            $table->integer('found')->default(0);
            $table->decimal('target_score', 8, 4)->default(0);
            $table->unsignedSmallInteger('top_k')->default(5);
            $table->string('audit_status', 32)->nullable();
            $table->decimal('tech_accuracy', 5, 2)->nullable();
            $table->decimal('brand_consistency', 5, 2)->nullable();
            $table->text('snapshot_json')->nullable();
            $table->text('recommendations')->nullable();
            $table->timestamps();
        });

        Schema::create('geo_monitor_platform_configs', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('ai_model_id');
            $table->string('label', 120)->default('');
            $table->integer('is_enabled')->default(1);
            $table->unsignedSmallInteger('sort_order')->default(50);
            $table->timestamps();
        });

        Schema::create('geo_monitor_ai_probe_results', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('question_id');
            $table->unsignedBigInteger('run_id')->nullable();
            $table->unsignedBigInteger('ai_model_id');
            $table->string('platform_label', 120)->default('');
            $table->text('response_text')->nullable();
            $table->unsignedSmallInteger('brand_rank')->default(99);
            $table->integer('brand_mentioned')->default(0);
            $table->text('brands_ordered')->nullable();
            $table->text('metrics_json')->nullable();
            $table->string('status', 32)->default('pending');
            $table->string('error_message', 500)->nullable();
            $table->timestamps();
        });

        Schema::create('geo_web_sources', function (Blueprint $table) {
            $table->id();
            $table->string('url', 500);
            $table->string('domain', 255)->default('');
            $table->string('label', 32)->default('competitor');
            $table->unsignedBigInteger('question_id')->nullable();
            $table->timestamp('last_fetched_at')->nullable();
            $table->text('features_json')->nullable();
            $table->text('eeat_json')->nullable();
            $table->string('fetch_status', 32)->default('pending');
            $table->timestamps();
        });

        Schema::create('geo_web_insight_reports', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('question_id')->nullable();
            $table->unsignedBigInteger('self_source_id')->nullable();
            $table->text('competitor_source_ids')->nullable();
            $table->text('gap_analysis_json')->nullable();
            $table->text('recommendations_json')->nullable();
            $table->unsignedBigInteger('insight_template_id')->nullable();
            $table->timestamps();
        });

        Schema::create('task_runs', function (Blueprint $table) {
            $table->id();
            $table->foreignId('task_id')->constrained('tasks')->cascadeOnDelete();
            $table->string('status', 20);
            $table->foreignId('article_id')->nullable()->constrained('articles')->nullOnDelete();
            $table->text('error_message')->nullable();
            $table->integer('duration_ms')->default(0);
            $table->text('meta')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('finished_at')->nullable();
            $table->timestamp('created_at')->nullable();
        });

        Schema::create('content_agent_requests', function (Blueprint $table) {
            $table->id();
            $table->uuid('request_id')->unique();
            $table->string('workflow_type', 32);
            $table->string('backend', 16)->default('external');
            $table->string('engine_hint', 64)->nullable();
            $table->string('status', 20)->default('pending');
            $table->string('correlation_type', 32)->nullable();
            $table->unsignedBigInteger('correlation_id')->nullable();
            $table->string('contract_version', 16)->default('1.0');
            $table->longText('payload_json')->nullable();
            $table->longText('result_json')->nullable();
            $table->text('error_message')->nullable();
            $table->timestamp('submitted_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();
        });

        Schema::create('content_agent_memories', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('task_id');
            $table->string('scope', 50)->default('task');
            $table->json('summary_json')->nullable();
            $table->timestamps();
            $table->unique(['task_id', 'scope']);
        });
    }

    public function down(): void
    {
        if (DB::getDriverName() !== 'sqlite' || ! app()->environment('testing')) {
            return;
        }

        Schema::dropIfExists('task_runs');
        Schema::dropIfExists('content_agent_memories');
        Schema::dropIfExists('content_agent_requests');
        Schema::dropIfExists('geo_web_insight_reports');
        Schema::dropIfExists('geo_web_sources');
        Schema::dropIfExists('geo_monitor_ai_probe_results');
        Schema::dropIfExists('geo_monitor_platform_configs');
        Schema::dropIfExists('geo_monitor_results');
        Schema::dropIfExists('geo_monitor_runs');
        Schema::dropIfExists('geo_monitor_questions');
        Schema::dropIfExists('geo_admin_alerts');
        Schema::dropIfExists('geo_market_scan_runs');
        Schema::dropIfExists('geo_strategy_metric_snapshots');
        Schema::dropIfExists('geo_eval_event_logs');
        Schema::dropIfExists('insight_templates');
        Schema::dropIfExists('article_evaluations');
        Schema::dropIfExists('articles');
        Schema::dropIfExists('tasks');
        Schema::dropIfExists('tech_ip_assets');
        Schema::dropIfExists('images');
        Schema::dropIfExists('image_libraries');
        Schema::dropIfExists('knowledge_chunks');
        Schema::dropIfExists('titles');
        Schema::dropIfExists('title_libraries');
        Schema::dropIfExists('keywords');
        Schema::dropIfExists('keyword_libraries');
        Schema::dropIfExists('knowledge_bases');
        Schema::dropIfExists('authors');
        Schema::dropIfExists('categories');
        Schema::dropIfExists('sensitive_words');
        Schema::dropIfExists('prompts');
        Schema::dropIfExists('ai_models');
        Schema::dropIfExists('api_idempotency_keys');
    }
};
