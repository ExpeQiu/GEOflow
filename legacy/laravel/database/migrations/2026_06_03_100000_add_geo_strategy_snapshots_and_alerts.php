<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('geo_strategy_metric_snapshots')) {
            Schema::create('geo_strategy_metric_snapshots', function (Blueprint $table) {
                $table->id();
                $table->date('metric_date');
                $table->string('platform', 64)->default('');
                $table->decimal('adoption_rate', 8, 4)->default(0);
                $table->decimal('first_position_rate', 8, 4)->default(0);
                $table->unsignedInteger('sample_size')->default(0);
                $table->unsignedInteger('passed_count')->default(0);
                $table->json('meta')->nullable();
                $table->timestamps();
                $table->unique(['metric_date', 'platform']);
            });
        }

        if (! Schema::hasTable('geo_market_scan_runs')) {
            Schema::create('geo_market_scan_runs', function (Blueprint $table) {
                $table->id();
                $table->string('scan_type', 32)->default('weekly');
                $table->string('status', 32)->default('completed');
                $table->json('summary_json')->nullable();
                $table->timestamp('ran_at')->useCurrent();
                $table->timestamps();
            });
        }

        if (! Schema::hasTable('geo_admin_alerts')) {
            Schema::create('geo_admin_alerts', function (Blueprint $table) {
                $table->id();
                $table->string('alert_type', 64);
                $table->string('severity', 16)->default('warning');
                $table->decimal('threshold', 8, 4)->nullable();
                $table->decimal('current_value', 8, 4)->nullable();
                $table->string('message', 500)->nullable();
                $table->json('channels')->nullable();
                $table->boolean('notified_feishu')->default(false);
                $table->timestamp('created_at')->useCurrent();
            });
        }
    }

    public function down(): void
    {
        Schema::dropIfExists('geo_admin_alerts');
        Schema::dropIfExists('geo_market_scan_runs');
        Schema::dropIfExists('geo_strategy_metric_snapshots');
    }
};
