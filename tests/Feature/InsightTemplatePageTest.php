<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class InsightTemplatePageTest extends TestCase
{
    use RefreshDatabase;

    public function test_insight_templates_index_requires_auth(): void
    {
        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->get('/'.$prefix.'/insight-templates')->assertRedirect();
    }

    public function test_insight_templates_index_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'insight_admin',
            'password' => 'secret',
            'email' => 'insight@example.com',
            'display_name' => 'Insight',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/insight-templates')
            ->assertOk()
            ->assertSee(__('admin.geo_eval.insight_templates_title'), false);
    }
}
