<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

/**
 * 素材管理首页控制器。
 */
class MaterialsController extends Controller
{
    /**
     * 素材管理入口重定向至 L2 内容生产 Hub。
     */
    public function index(Request $request): RedirectResponse
    {
        return redirect()->route('admin.production.index', array_merge(
            ['tab' => 'materials'],
            $request->query()
        ));
    }
}
