<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('geo_monitor_questions') && ! Schema::hasColumn('geo_monitor_questions', 'tech_keywords')) {
            Schema::table('geo_monitor_questions', function (Blueprint $table) {
                $table->json('tech_keywords')->nullable()->after('tags');
            });
        }

        if (! Schema::hasTable('geo_monitor_platform_configs')) {
            Schema::create('geo_monitor_platform_configs', function (Blueprint $table) {
                $table->id();
                $table->unsignedBigInteger('ai_model_id');
                $table->string('label', 120)->default('');
                $table->boolean('is_enabled')->default(true);
                $table->unsignedSmallInteger('sort_order')->default(50);
                $table->timestamps();
                $table->unique('ai_model_id');
            });
        }

        if (! Schema::hasTable('geo_monitor_ai_probe_results')) {
            Schema::create('geo_monitor_ai_probe_results', function (Blueprint $table) {
                $table->id();
                $table->foreignId('question_id')->constrained('geo_monitor_questions')->cascadeOnDelete();
                $table->unsignedBigInteger('run_id')->nullable();
                $table->unsignedBigInteger('ai_model_id');
                $table->string('platform_label', 120)->default('');
                $table->text('response_text')->nullable();
                $table->unsignedSmallInteger('brand_rank')->default(99);
                $table->boolean('brand_mentioned')->default(false);
                $table->json('brands_ordered')->nullable();
                $table->json('metrics_json')->nullable();
                $table->string('status', 32)->default('pending');
                $table->string('error_message', 500)->nullable();
                $table->timestamps();
                $table->index(['question_id', 'created_at']);
                $table->index(['ai_model_id', 'created_at']);
            });
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('geo_monitor_ai_probe_results');
        Schema::dropIfExists('geo_monitor_platform_configs');
        if (Schema::hasColumn('geo_monitor_questions', 'tech_keywords')) {
            Schema::table('geo_monitor_questions', function (Blueprint $table) {
                $table->dropColumn('tech_keywords');
            });
        }
    }
};
