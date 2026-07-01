<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Symfony\Component\HttpFoundation\Response;

/** 技术品牌模式下可关闭 GEOFlow 公网前台，仅保留后台与 API。 */
class EnsurePublicSiteEnabled
{
    public function handle(Request $request, Closure $next): Response
    {
        if (filter_var(config('geoflow.public_site_enabled', true), FILTER_VALIDATE_BOOLEAN)) {
            return $next($request);
        }

        $adminPrefix = trim((string) config('geoflow.admin_base_path', '/geo_admin'), '/');

        if ($request->is($adminPrefix.'/*') || $request->is('api/*') || $request->is('internal/*') || $request->is('up')) {
            return $next($request);
        }

        abort(404);
    }
}
