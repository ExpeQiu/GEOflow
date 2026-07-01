<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\KnowledgeBase;
use App\Services\GeoFlow\KnowledgeRetrievalService;
use App\Support\AdminWeb;
use Illuminate\Http\Request;
use Illuminate\View\View;

class KnowledgeRagSandboxController extends Controller
{
    public function __construct(
        private readonly KnowledgeRetrievalService $knowledgeRetrievalService,
    ) {}

    public function index(Request $request): View
    {
        $knowledgeBaseId = (int) $request->input('knowledge_base_id', 0);
        $query = trim((string) $request->input('query', ''));
        $evidence = [];

        if ($knowledgeBaseId > 0 && $query !== '') {
            $evidence = $this->knowledgeRetrievalService->retrieveEvidence($knowledgeBaseId, $query, 12);
        }

        return view('admin.knowledge-bases.rag-sandbox', [
            'pageTitle' => __('admin.knowledge_bases.rag_sandbox_title'),
            'activeMenu' => 'materials',
            'adminSiteName' => AdminWeb::siteName(),
            'knowledgeBases' => KnowledgeBase::query()->orderBy('name')->get(['id', 'name']),
            'selectedKnowledgeBaseId' => $knowledgeBaseId,
            'query' => $query,
            'evidence' => $evidence,
        ]);
    }
}
