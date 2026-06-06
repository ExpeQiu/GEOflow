<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class GeoEvalDiagnosticsPageTest extends TestCase
{
    use RefreshDatabase;

    public function test_diagnostics_page_requires_auth(): void
    {
        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->get('/'.$prefix.'/geo-eval/diagnostics')->assertRedirect();
    }

    public function test_diagnostics_page_renders_for_admin(): void
    {
        $admin = Admin::query()->create([
            'username' => 'eval_admin',
            'password' => 'secret',
            'email' => 'eval@example.com',
            'display_name' => 'Eval',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/geo-eval/diagnostics')
            ->assertOk()
            ->assertSee(__('admin.geo_eval.diagnostics_title'), false);
    }

    public function test_dashboard_shows_geo_eval_nav_only(): void
    {
        $admin = Admin::query()->create([
            'username' => 'nav_admin',
            'password' => 'secret',
            'email' => 'nav@example.com',
            'display_name' => 'Nav',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/dashboard')
            ->assertOk()
            ->assertSee(__('admin.nav.geo_eval'), false)
            ->assertSee('/'.$prefix.'/geo-eval/diagnostics', false);
    }

    public function test_diagnostics_shows_gate_status_banner(): void
    {
        $admin = Admin::query()->create([
            'username' => 'gate_admin',
            'password' => 'secret',
            'email' => 'gate@example.com',
            'display_name' => 'Gate',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/geo-eval/diagnostics')
            ->assertOk()
            ->assertSee(__('admin.geo_eval.gate_status_title'), false);
    }
}
