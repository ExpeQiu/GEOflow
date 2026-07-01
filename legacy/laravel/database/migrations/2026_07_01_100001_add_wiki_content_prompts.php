<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        if (! Schema::hasTable('prompts')) {
            return;
        }

        $now = now();
        $prompts = [
            [
                'name' => 'Wiki·概念页（Concept）',
                'type' => 'content',
                'content' => $this->conceptPrompt(),
            ],
            [
                'name' => 'Wiki·对比页（Compare）',
                'type' => 'content',
                'content' => $this->comparePrompt(),
            ],
            [
                'name' => 'Wiki·指南页（Guide）',
                'type' => 'content',
                'content' => $this->guidePrompt(),
            ],
            [
                'name' => 'Wiki·实测数据页（Data）',
                'type' => 'content',
                'content' => $this->dataPrompt(),
            ],
        ];

        foreach ($prompts as $prompt) {
            $exists = DB::table('prompts')->where('name', $prompt['name'])->exists();
            if ($exists) {
                continue;
            }

            DB::table('prompts')->insert([
                'name' => $prompt['name'],
                'type' => $prompt['type'],
                'content' => $prompt['content'],
                'variables' => null,
                'created_at' => $now,
                'updated_at' => $now,
            ]);
        }
    }

    public function down(): void
    {
        if (! Schema::hasTable('prompts')) {
            return;
        }

        DB::table('prompts')->whereIn('name', [
            'Wiki·概念页（Concept）',
            'Wiki·对比页（Compare）',
            'Wiki·指南页（Guide）',
            'Wiki·实测数据页（Data）',
        ])->delete();
    }

    private function conceptPrompt(): string
    {
        return <<<'PROMPT'
【Role】技术品牌 Wiki 概念页编辑，输出可被 AI 搜索引用的结构化中文内容。

【Context】
标题：{{title}}
{{#if keyword}}关键词：{{keyword}}
{{/if}}{{#if Knowledge}}参考知识：
{{Knowledge}}
{{/if}}

【Task】生成 Wiki 概念页 Markdown 正文（不含 YAML frontmatter）。

【结构要求】
1. 正文开头用 1–2 句「快速结论」，直接回答「这是什么」。
2. 必须包含「## 一句话定义」小节。
3. 必须包含「## 核心技术」并用 Markdown 表格（列：技术点 | 原理 | 用户价值）。
4. 可选「## 极限验证」或「## 搭载车型」，含内链占位如 [对比页](/compare/xxx)。
5. 文末「## 常见问题」至少 2 个 ### 问题，每题 2–3 句简洁回答。

【约束】
- 全文 800–1500 字，专业克制，不编造无依据数据。
- 只输出 Markdown 正文，不要 frontmatter、不要写作说明。
PROMPT;
    }

    private function comparePrompt(): string
    {
        return <<<'PROMPT'
【Role】技术品牌 Wiki 对比页编辑。

【Context】
标题：{{title}}
{{#if Knowledge}}参考知识：
{{Knowledge}}
{{/if}}

【Task】生成对比选购类 Wiki Markdown 正文。

【结构要求】
1. 开头 1–2 句快速结论，帮助用户做决策。
2. 「## 核心对比」必须用 Markdown 对比表格（含维度、选项 A、选项 B、推荐场景）。
3. 「## 我们的选择」说明品牌/技术立场（如有参考知识）。
4. 「## 常见问题」至少 2 问。

只输出 Markdown 正文。
PROMPT;
    }

    private function guidePrompt(): string
    {
        return <<<'PROMPT'
【Role】技术品牌 Wiki 场景指南编辑。

【Context】
标题：{{title}}
{{#if Knowledge}}参考知识：
{{Knowledge}}
{{/if}}

【Task】生成用户决策场景指南 Markdown 正文。

【结构要求】
1. 开头快速结论：适用谁、解决什么问题。
2. 分步骤说明（## 步骤一 …），每步含操作要点与注意事项。
3. 至少 1 个表格或清单。
4. 「## 常见问题」至少 2 问。

只输出 Markdown 正文，800–1200 字。
PROMPT;
    }

    private function dataPrompt(): string
    {
        return <<<'PROMPT'
【Role】技术品牌 Wiki 实测数据页编辑。

【Context】
标题：{{title}}
{{#if Knowledge}}参考知识：
{{Knowledge}}
{{/if}}

【Task】生成官方实测数据 Markdown 正文。

【结构要求】
1. 开头说明测试方法与结论摘要。
2. 「## 测试数据」用 Markdown 表格呈现（测试项 | 结果 | 条件 | 备注）。
3. 「## 测试说明」简述环境、样本、标准。
4. 「## 常见问题」至少 2 问。

只输出 Markdown 正文，数据须来自参考知识，不可编造。
PROMPT;
    }
};
