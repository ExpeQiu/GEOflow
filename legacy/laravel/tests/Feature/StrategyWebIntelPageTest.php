<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class StrategyWebIntelPageTest extends TestCase
{
    use RefreshDatabase;

    public function test_web_intel_tab_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'webintel_admin',
            'password' => 'secret',
            'email' => 'wi@example.com',
            'display_name' => 'WI',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/strategy?tab=web-intel')
            ->assertOk()
            ->assertSee(__('admin.strategy.web_intel.add_source'), false);
    }
}
