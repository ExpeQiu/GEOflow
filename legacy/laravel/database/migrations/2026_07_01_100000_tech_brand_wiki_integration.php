<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('tech_ip_assets')) {
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
                $table->json('evidence')->nullable();
                $table->json('models')->nullable();
                $table->string('wiki_type', 40)->nullable();
                $table->string('wiki_slug', 120)->nullable();
                $table->string('status', 40)->default('待封装');
                $table->unsignedBigInteger('knowledge_base_id')->nullable();
                $table->timestamps();

                $table->index(['priority', 'status']);
                $table->index(['wiki_type', 'wiki_slug']);
            });
        }

        if (Schema::hasTable('tasks') && ! Schema::hasColumn('tasks', 'content_format')) {
            Schema::table('tasks', function (Blueprint $table) {
                $table->string('content_format', 20)->default('article')->after('content_pipeline_mode');
                $table->string('wiki_page_type', 40)->nullable()->after('content_format');
                $table->unsignedBigInteger('tech_ip_asset_id')->nullable()->after('wiki_page_type');
            });
        }

        if (Schema::hasTable('articles') && ! Schema::hasColumn('articles', 'content_format')) {
            Schema::table('articles', function (Blueprint $table) {
                $table->string('content_format', 20)->default('article')->after('content');
                $table->json('wiki_meta')->nullable()->after('content_format');
                $table->unsignedBigInteger('tech_ip_asset_id')->nullable()->after('wiki_meta');
            });
        }
    }

    public function down(): void
    {
        if (Schema::hasTable('articles') && Schema::hasColumn('articles', 'content_format')) {
            Schema::table('articles', function (Blueprint $table) {
                $table->dropColumn(['content_format', 'wiki_meta', 'tech_ip_asset_id']);
            });
        }

        if (Schema::hasTable('tasks') && Schema::hasColumn('tasks', 'content_format')) {
            Schema::table('tasks', function (Blueprint $table) {
                $table->dropColumn(['content_format', 'wiki_page_type', 'tech_ip_asset_id']);
            });
        }

        Schema::dropIfExists('tech_ip_assets');
    }
};
