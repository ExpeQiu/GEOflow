<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class StrategyMonitorPageTest extends TestCase
{
    use RefreshDatabase;

    public function test_strategy_hub_requires_auth(): void
    {
        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->get('/'.$prefix.'/strategy')->assertRedirect();
    }

    public function test_strategy_hub_renders_for_admin(): void
    {
        $admin = Admin::query()->create([
            'username' => 'strategy_admin',
            'password' => 'secret',
            'email' => 'strategy@example.com',
            'display_name' => 'Strategy',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/strategy')
            ->assertOk()
            ->assertSee(__('admin.strategy.hub_title'), false);
    }

    public function test_dashboard_shows_strategy_hub_nav(): void
    {
        $admin = Admin::query()->create([
            'username' => 'nav_strategy',
            'password' => 'secret',
            'email' => 'navs@example.com',
            'display_name' => 'Nav',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/dashboard')
            ->assertOk()
            ->assertSee(__('admin.nav.strategy_hub'), false)
            ->assertSee('/'.$prefix.'/strategy', false);
    }

    public function test_monitor_tab_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'monitor_tab',
            'password' => 'secret',
            'email' => 'mon@example.com',
            'display_name' => 'Mon',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/strategy?tab=monitor')
            ->assertOk()
            ->assertSee(__('admin.strategy.monitor.dashboard_title'), false)
            ->assertSee(__('admin.strategy.monitor.add_title'), false);
    }
}
