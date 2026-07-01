<?php

namespace Tests\Feature;

use App\Models\Admin;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class OperationsHubPageTest extends TestCase
{
    use RefreshDatabase;

    public function test_operations_hub_requires_auth(): void
    {
        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->get('/'.$prefix.'/operations')->assertRedirect();
    }

    public function test_operations_hub_renders_for_admin(): void
    {
        $admin = Admin::query()->create([
            'username' => 'operations_admin',
            'password' => 'secret',
            'email' => 'operations@example.com',
            'display_name' => 'Operations',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/operations')
            ->assertOk()
            ->assertSee(__('admin.operations.hub_title'), false)
            ->assertSee(__('admin.operations.tabs.overview'), false)
            ->assertSee(__('admin.operations.tabs.tasks'), false)
            ->assertSee(__('admin.operations.tabs.articles'), false)
            ->assertSee(__('admin.operations.tabs.distribution'), false);
    }

    public function test_tasks_index_redirects_to_operations_hub(): void
    {
        $admin = Admin::query()->create([
            'username' => 'tasks_redirect_admin',
            'password' => 'secret',
            'email' => 'tasks-redirect@example.com',
            'display_name' => 'Tasks Redirect',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.tasks.index'))
            ->assertRedirect(route('admin.operations.index', ['tab' => 'tasks']));
    }

    public function test_articles_index_redirects_to_operations_hub(): void
    {
        $admin = Admin::query()->create([
            'username' => 'articles_redirect_admin',
            'password' => 'secret',
            'email' => 'articles-redirect@example.com',
            'display_name' => 'Articles Redirect',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.articles.index'))
            ->assertRedirect(route('admin.operations.index', ['tab' => 'articles']));
    }

    public function test_operations_hub_tasks_tab_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'operations_tasks_admin',
            'password' => 'secret',
            'email' => 'operations-tasks@example.com',
            'display_name' => 'Operations Tasks',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.operations.index', ['tab' => 'tasks']))
            ->assertOk()
            ->assertSee(__('admin.tasks.list_title'), false);
    }

    public function test_operations_hub_articles_tab_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'operations_articles_admin',
            'password' => 'secret',
            'email' => 'operations-articles@example.com',
            'display_name' => 'Operations Articles',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.operations.index', ['tab' => 'articles']))
            ->assertOk()
            ->assertSee(__('admin.articles.page_title'), false);
    }

    public function test_dashboard_l3_card_links_to_operations_hub(): void
    {
        $admin = Admin::query()->create([
            'username' => 'dashboard_l3_admin',
            'password' => 'secret',
            'email' => 'dashboard-l3@example.com',
            'display_name' => 'Dashboard L3',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.dashboard'))
            ->assertOk()
            ->assertSee(route('admin.operations.index'), false)
            ->assertSee(route('admin.operations.index', ['tab' => 'tasks']), false);
    }
}
