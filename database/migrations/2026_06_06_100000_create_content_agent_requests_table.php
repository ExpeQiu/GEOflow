<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('content_agent_requests')) {
            return;
        }

        Schema::create('content_agent_requests', function (Blueprint $table): void {
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

            $table->index(['workflow_type', 'status']);
            $table->index(['correlation_type', 'correlation_id']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('content_agent_requests');
    }
};
