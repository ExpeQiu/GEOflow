<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('geo_monitor_questions')) {
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
                $table->boolean('is_active')->default(true);
                $table->unsignedSmallInteger('priority')->default(50);
                $table->json('tags')->nullable();
                $table->unsignedBigInteger('created_by_admin_id')->nullable();
                $table->timestamps();
                $table->index(['is_active', 'priority']);
                $table->index('knowledge_base_id');
            });
        }

        if (! Schema::hasTable('geo_monitor_runs')) {
            Schema::create('geo_monitor_runs', function (Blueprint $table) {
                $table->id();
                $table->string('run_type', 32)->default('scheduled');
                $table->string('status', 32)->default('pending');
                $table->unsignedInteger('question_count')->default(0);
                $table->json('meta')->nullable();
                $table->timestamp('started_at')->nullable();
                $table->timestamp('finished_at')->nullable();
                $table->timestamps();
                $table->index(['status', 'created_at']);
            });
        }

        if (! Schema::hasTable('geo_monitor_results')) {
            Schema::create('geo_monitor_results', function (Blueprint $table) {
                $table->id();
                $table->foreignId('question_id')->constrained('geo_monitor_questions')->cascadeOnDelete();
                $table->foreignId('run_id')->constrained('geo_monitor_runs')->cascadeOnDelete();
                $table->unsignedBigInteger('article_id')->nullable();
                $table->unsignedSmallInteger('rank')->default(99);
                $table->boolean('found')->default(false);
                $table->decimal('target_score', 8, 4)->default(0);
                $table->unsignedSmallInteger('top_k')->default(5);
                $table->string('audit_status', 32)->nullable();
                $table->decimal('tech_accuracy', 5, 2)->nullable();
                $table->decimal('brand_consistency', 5, 2)->nullable();
                $table->json('snapshot_json')->nullable();
                $table->json('recommendations')->nullable();
                $table->timestamps();
                $table->index(['question_id', 'created_at']);
                $table->index('run_id');
            });
        }

        if (! Schema::hasTable('geo_web_sources')) {
            Schema::create('geo_web_sources', function (Blueprint $table) {
                $table->id();
                $table->string('url', 500);
                $table->string('domain', 255)->default('');
                $table->string('label', 32)->default('competitor');
                $table->unsignedBigInteger('question_id')->nullable();
                $table->timestamp('last_fetched_at')->nullable();
                $table->json('features_json')->nullable();
                $table->json('eeat_json')->nullable();
                $table->string('fetch_status', 32)->default('pending');
                $table->timestamps();
                $table->index(['question_id', 'label']);
                $table->index('domain');
            });
        }

        if (! Schema::hasTable('geo_web_insight_reports')) {
            Schema::create('geo_web_insight_reports', function (Blueprint $table) {
                $table->id();
                $table->unsignedBigInteger('question_id')->nullable();
                $table->unsignedBigInteger('self_source_id')->nullable();
                $table->json('competitor_source_ids')->nullable();
                $table->json('gap_analysis_json')->nullable();
                $table->json('recommendations_json')->nullable();
                $table->unsignedBigInteger('insight_template_id')->nullable();
                $table->timestamps();
                $table->index('question_id');
            });
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('geo_web_insight_reports');
        Schema::dropIfExists('geo_web_sources');
        Schema::dropIfExists('geo_monitor_results');
        Schema::dropIfExists('geo_monitor_runs');
        Schema::dropIfExists('geo_monitor_questions');
    }
};
