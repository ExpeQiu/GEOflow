<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (Schema::hasTable('content_agent_memories')) {
            return;
        }

        Schema::create('content_agent_memories', function (Blueprint $table) {
            $table->id();
            $table->unsignedBigInteger('task_id');
            $table->string('scope', 50)->default('task');
            $table->json('summary_json')->nullable();
            $table->timestamps();

            $table->unique(['task_id', 'scope']);
            $table->index('task_id');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('content_agent_memories');
    }
};
