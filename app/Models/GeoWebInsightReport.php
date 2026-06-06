<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;

class GeoWebInsightReport extends Model
{
    protected $table = 'geo_web_insight_reports';

    protected $fillable = [
        'question_id',
        'self_source_id',
        'competitor_source_ids',
        'gap_analysis_json',
        'recommendations_json',
        'insight_template_id',
    ];

    protected function casts(): array
    {
        return [
            'question_id' => 'integer',
            'self_source_id' => 'integer',
            'competitor_source_ids' => 'array',
            'gap_analysis_json' => 'array',
            'recommendations_json' => 'array',
            'insight_template_id' => 'integer',
        ];
    }
}
