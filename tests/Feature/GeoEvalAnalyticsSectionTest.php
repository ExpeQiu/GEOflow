<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class GeoEvalAnalyticsSectionTest extends TestCase
{
    use RefreshDatabase;

    public function test_analytics_includes_geo_dashboard_section(): void
    {
        $admin = Admin::query()->create([
            'username' => 'analytics_admin',
            'password' => 'secret',
            'email' => 'analytics@example.com',
            'display_name' => 'Analytics',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/analytics')
            ->assertOk()
            ->assertSee('geo-eval-dashboard', false)
            ->assertSee(__('admin.geo_eval.adoption_rate'), false);
    }
}
