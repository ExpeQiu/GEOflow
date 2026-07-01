<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;

class AnalyticsController extends Controller
{
    public function index(Request $request): RedirectResponse
    {
        return redirect()->route('admin.strategy.index', array_merge(
            ['tab' => 'analytics'],
            $request->query()
        ));
    }
}
