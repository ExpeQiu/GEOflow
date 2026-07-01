<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasColumn('articles', 'eval_status')) {
            Schema::table('articles', function (Blueprint $table) {
                $table->string('eval_status', 32)->default('skipped')->after('review_status');
                $table->json('eval_meta')->nullable()->after('eval_status');
            });
        }

        if (! Schema::hasColumn('tasks', 'insight_template_id')) {
            Schema::table('tasks', function (Blueprint $table) {
                $table->unsignedBigInteger('insight_template_id')->nullable()->after('knowledge_base_id');
            });
        }

        if (! Schema::hasTable('article_evaluations')) {
            Schema::create('article_evaluations', function (Blueprint $table) {
                $table->id();
                $table->foreignId('article_id')->constrained('articles')->cascadeOnDelete();
                $table->unsignedBigInteger('task_run_id')->nullable();
                $table->string('idempotency_key', 191);
                $table->string('eval_type', 32)->default('simulation');
                $table->string('status', 32)->default('pending_eval');
                $table->string('request_id', 64)->nullable();
                $table->json('metrics')->nullable();
                $table->string('failure_reason', 500)->nullable();
                $table->json('raw_response')->nullable();
                $table->timestamps();
                $table->unique(['article_id', 'idempotency_key']);
                $table->index(['status', 'created_at']);
            });
        }

        if (! Schema::hasTable('insight_templates')) {
            Schema::create('insight_templates', function (Blueprint $table) {
                $table->id();
                $table->string('name', 120);
                $table->string('source_url', 500)->nullable();
                $table->json('style_guide')->nullable();
                $table->json('features')->nullable();
                $table->decimal('eeat_score', 5, 2)->nullable();
                $table->unsignedBigInteger('created_by_admin_id')->nullable();
                $table->timestamps();
                $table->index('created_at');
            });
        }

        if (! Schema::hasTable('geo_eval_event_logs')) {
            Schema::create('geo_eval_event_logs', function (Blueprint $table) {
                $table->id();
                $table->string('request_id', 64)->index();
                $table->unsignedBigInteger('task_id')->nullable()->index();
                $table->unsignedBigInteger('article_id')->nullable()->index();
                $table->unsignedBigInteger('channel_id')->nullable();
                $table->string('eval_status', 32)->nullable();
                $table->string('event', 120);
                $table->string('level', 16)->default('info');
                $table->string('message', 500)->nullable();
                $table->json('context')->nullable();
                $table->timestamp('created_at')->useCurrent();
            });
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('geo_eval_event_logs');
        Schema::dropIfExists('insight_templates');
        Schema::dropIfExists('article_evaluations');

        if (Schema::hasColumn('tasks', 'insight_template_id')) {
            Schema::table('tasks', function (Blueprint $table) {
                $table->dropColumn('insight_template_id');
            });
        }

        if (Schema::hasColumn('articles', 'eval_status')) {
            Schema::table('articles', function (Blueprint $table) {
                $table->dropColumn(['eval_status', 'eval_meta']);
            });
        }
    }
};
