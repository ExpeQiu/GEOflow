<?php

namespace App\Console\Commands;

use App\Models\GeoAdminAlert;
use App\Services\GeoEval\Adoption\AdoptionMetricsAggregator;
use App\Services\GeoEval\Alerts\FeishuWebhookNotifier;
use App\Services\GeoEval\Monitor\MonitorTrendAnalyzer;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Schema;

class GeoCheckAdoptionAlertsCommand extends Command
{
    protected $signature = 'geo:check-adoption-alerts';

    protected $description = '检查采纳率阈值并写入站内告警 / 可选飞书通知';

    public function handle(
        AdoptionMetricsAggregator $aggregator,
        FeishuWebhookNotifier $feishu,
        MonitorTrendAnalyzer $monitorTrendAnalyzer,
    ): int {
        if (! config('geo_eval.enabled')) {
            $this->info('GEO eval disabled, skip.');

            return self::SUCCESS;
        }

        $stats = $aggregator->summary(7, '');
        $adoption = (float) ($stats['adoption_rate'] ?? 0);
        $firstPos = (float) ($stats['first_position_rate'] ?? 0);
        $adoptionFloor = (float) config('geo_eval.alerts.adoption_rate_floor', 0.5);
        $firstFloor = (float) config('geo_eval.alerts.first_position_rate_floor', 0.4);

        $alerts = 0;
        if ($stats['sample_size'] > 0 && $adoption < $adoptionFloor) {
            $alerts += $this->recordAlert('low_adoption_rate', $adoptionFloor, $adoption, $feishu);
        }
        if ($stats['sample_size'] > 0 && $firstPos < $firstFloor) {
            $alerts += $this->recordAlert('low_first_position_rate', $firstFloor, $firstPos, $feishu);
        }

        $alerts += $monitorTrendAnalyzer->checkAndRecordAlerts();

        $this->info("Recorded {$alerts} alert(s).");

        return self::SUCCESS;
    }

    private function recordAlert(string $type, float $threshold, float $current, FeishuWebhookNotifier $feishu): int
    {
        if (! Schema::hasTable('geo_admin_alerts')) {
            return 0;
        }

        $recent = GeoAdminAlert::query()
            ->where('alert_type', $type)
            ->where('created_at', '>=', now()->subDay())
            ->exists();
        if ($recent) {
            return 0;
        }

        $message = "{$type}: current={$current}, threshold={$threshold}";
        $notified = $feishu->notify('GEOworkflow 策略告警', $message);

        GeoAdminAlert::query()->create([
            'alert_type' => $type,
            'severity' => 'warning',
            'threshold' => $threshold,
            'current_value' => $current,
            'message' => $message,
            'channels' => ['feishu' => $notified, 'admin' => true],
            'notified_feishu' => $notified,
            'created_at' => now(),
        ]);

        return 1;
    }
}
