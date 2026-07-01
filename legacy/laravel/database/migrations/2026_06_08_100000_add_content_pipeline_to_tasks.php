<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('tasks')) {
            return;
        }

        if (! Schema::hasColumn('tasks', 'content_pipeline_mode')) {
            Schema::table('tasks', function (Blueprint $table) {
                $table->string('content_pipeline_mode', 20)->default('legacy')->after('model_selection_mode');
            });
        }
    }

    public function down(): void
    {
        if (Schema::hasTable('tasks') && Schema::hasColumn('tasks', 'content_pipeline_mode')) {
            Schema::table('tasks', function (Blueprint $table) {
                $table->dropColumn('content_pipeline_mode');
            });
        }
    }
};
