<?php

namespace Tests\Feature;

use App\Models\Admin;
use App\Models\ContentAgentRequest;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ProductionHubPageTest extends TestCase
{
    use RefreshDatabase;

    public function test_production_hub_requires_auth(): void
    {
        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->get('/'.$prefix.'/production')->assertRedirect();
    }

    public function test_production_hub_renders_for_admin(): void
    {
        $admin = Admin::query()->create([
            'username' => 'production_admin',
            'password' => 'secret',
            'email' => 'production@example.com',
            'display_name' => 'Production',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/production')
            ->assertOk()
            ->assertSee(__('admin.production.hub_title'), false)
            ->assertSee(__('admin.production.tabs.overview'), false)
            ->assertSee(__('admin.production.tabs.materials'), false)
            ->assertSee(__('admin.production.tabs.knowledge'), false)
            ->assertSee(__('admin.production.tabs.ai_config'), false);
    }

    public function test_production_hub_knowledge_tab_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'production_kb_admin',
            'password' => 'secret',
            'email' => 'production-kb@example.com',
            'display_name' => 'Production KB',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/production?tab=knowledge')
            ->assertOk()
            ->assertSee(__('admin.materials.knowledge_hub_title'), false);
    }

    public function test_materials_index_redirects_to_production_hub(): void
    {
        $admin = Admin::query()->create([
            'username' => 'materials_redirect_admin',
            'password' => 'secret',
            'email' => 'materials-redirect@example.com',
            'display_name' => 'Materials Redirect',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.materials.index'))
            ->assertRedirect(route('admin.production.index', ['tab' => 'materials']));
    }

    public function test_ai_configurator_redirects_to_production_hub(): void
    {
        $admin = Admin::query()->create([
            'username' => 'ai_redirect_admin',
            'password' => 'secret',
            'email' => 'ai-redirect@example.com',
            'display_name' => 'AI Redirect',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.ai.configurator'))
            ->assertRedirect(route('admin.production.index', ['tab' => 'ai_config']));
    }

    public function test_production_hub_ai_config_tab_renders(): void
    {
        $admin = Admin::query()->create([
            'username' => 'production_ai_admin',
            'password' => 'secret',
            'email' => 'production-ai@example.com',
            'display_name' => 'Production AI',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/production?tab=ai_config')
            ->assertOk()
            ->assertSee(__('admin.ai_configurator.heading'), false)
            ->assertSee(__('admin.ai_configurator.models_action'), false)
            ->assertSee(__('admin.ai_configurator.orchestration_title'), false)
            ->assertSee(__('admin.production.orchestration.title'), false)
            ->assertSee(__('admin.production.orchestration.graph_title'), false)
            ->assertSee(__('admin.production.orchestration.workflow_content_pipeline'), false)
            ->assertSee(__('admin.production.orchestration.path_fast_title'), false)
            ->assertSee(__('admin.production.orchestration.path_deep_title'), false)
            ->assertSee(__('admin.production.orchestration.phase_fork'), false)
            ->assertDontSee(__('admin.materials.foundation_title'), false);

        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/production?tab=ai-config')
            ->assertRedirect(route('admin.production.index', ['tab' => 'ai_config']));
    }

    public function test_production_hub_overview_does_not_render_orchestration_panel(): void
    {
        $admin = Admin::query()->create([
            'username' => 'production_orch_admin',
            'password' => 'secret',
            'email' => 'production-orch@example.com',
            'display_name' => 'Production Orch',
            'role' => 'admin',
            'status' => 'active',
        ]);

        ContentAgentRequest::query()->create([
            'request_id' => '11111111-1111-1111-1111-111111111111',
            'workflow_type' => 'semantic_chunk',
            'backend' => 'external',
            'status' => 'running',
            'correlation_type' => 'knowledge_base',
            'correlation_id' => 9,
            'contract_version' => '1.0',
            'submitted_at' => now(),
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/production?tab=overview')
            ->assertOk()
            ->assertDontSee('id="content-agent-orchestration"', false)
            ->assertDontSee(__('admin.production.orchestration.graph_title'), false)
            ->assertSee(__('admin.production.tabs.knowledge'), false);
    }

    public function test_production_hub_knowledge_tab_shows_pending_orchestration(): void
    {
        $admin = Admin::query()->create([
            'username' => 'production_kb_pending_admin',
            'password' => 'secret',
            'email' => 'production-kb-pending@example.com',
            'display_name' => 'Production KB Pending',
            'role' => 'admin',
            'status' => 'active',
        ]);

        ContentAgentRequest::query()->create([
            'request_id' => '22222222-2222-2222-2222-222222222222',
            'workflow_type' => 'semantic_chunk',
            'backend' => 'external',
            'status' => 'pending',
            'correlation_type' => 'knowledge_base',
            'correlation_id' => 3,
            'contract_version' => '1.0',
            'submitted_at' => now(),
        ]);

        $prefix = trim((string) config('geoflow.admin_base_path', 'geo_admin'), '/');
        $this->actingAs($admin, 'admin')
            ->get('/'.$prefix.'/production?tab=knowledge')
            ->assertOk()
            ->assertSee(__('admin.production.orchestration.knowledge_chunking_active', ['count' => 1]), false);
    }

    public function test_dashboard_l2_card_links_to_production_hub(): void
    {
        $admin = Admin::query()->create([
            'username' => 'dashboard_l2_admin',
            'password' => 'secret',
            'email' => 'dashboard-l2@example.com',
            'display_name' => 'Dashboard L2',
            'role' => 'admin',
            'status' => 'active',
        ]);

        $this->actingAs($admin, 'admin')
            ->get(route('admin.dashboard'))
            ->assertOk()
            ->assertSee(route('admin.production.index'), false)
            ->assertSee(route('admin.production.index', ['tab' => 'knowledge']), false);
    }
}
