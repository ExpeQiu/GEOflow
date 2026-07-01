<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\GeoAdminAlert;
use App\Support\AdminWeb;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Schema;
use Illuminate\View\View;

class GeoEvalAlertsController extends Controller
{
    public function index(Request $request): View
    {
        $alertType = trim((string) $request->query('alert_type', ''));
        $severity = trim((string) $request->query('severity', ''));

        $alerts = collect();
        $alertTypes = [];
        $severities = [];

        if (Schema::hasTable('geo_admin_alerts')) {
            $alertTypes = GeoAdminAlert::query()
                ->select('alert_type')
                ->distinct()
                ->orderBy('alert_type')
                ->pluck('alert_type')
                ->map(fn ($v): string => (string) $v)
                ->all();

            $severities = GeoAdminAlert::query()
                ->select('severity')
                ->distinct()
                ->orderBy('severity')
                ->pluck('severity')
                ->map(fn ($v): string => (string) $v)
                ->all();

            $query = GeoAdminAlert::query()->orderByDesc('id');

            if ($alertType !== '') {
                $query->where('alert_type', $alertType);
            }

            if ($severity !== '') {
                $query->where('severity', $severity);
            }

            $alerts = $query->paginate(20)->withQueryString();
        }

        return view('admin.geo-eval.alerts', [
            'pageTitle' => __('admin.geo_eval.alerts_page_title'),
            'activeMenu' => 'geo_eval',
            'adminSiteName' => AdminWeb::siteName(),
            'alerts' => $alerts,
            'alertTypes' => $alertTypes,
            'severities' => $severities,
            'filters' => [
                'alert_type' => $alertType,
                'severity' => $severity,
            ],
        ]);
    }
}
