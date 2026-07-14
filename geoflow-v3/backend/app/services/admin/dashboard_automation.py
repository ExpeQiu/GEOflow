"""Dashboard 自动化流水线节点与建议动作。"""

from typing import Any


def build_automation(stats: dict[str, int]) -> dict[str, Any]:
    chat_models = stats.get("chat_models", 0)
    embedding_models = stats.get("embedding_models", 0)
    ai_used_today = stats.get("ai_used_today", 0)
    knowledge_bases = stats.get("knowledge_bases", 0)
    knowledge_chunks = stats.get("knowledge_chunks", 0)
    vectorized_chunks = stats.get("vectorized_chunks", 0)
    unvectorized_chunks = max(0, knowledge_chunks - vectorized_chunks)
    total_prompts = stats.get("total_prompts", 0)
    body_prompts = stats.get("body_prompts", 0)
    special_prompts = stats.get("special_prompts", 0)
    total_tasks = stats.get("total_tasks", 0)
    active_tasks = stats.get("active_tasks", 0)
    running_jobs = stats.get("running_jobs", 0)
    pending_jobs = stats.get("pending_jobs", 0)
    failed_jobs = stats.get("failed_jobs", 0)
    draft_articles = stats.get("draft_articles", 0)
    published_articles = stats.get("published_articles", 0)
    pending_review = stats.get("pending_review", 0)
    today_articles = stats.get("today_articles", 0)
    eval_pending = stats.get("eval_pending", 0)
    eval_failed = stats.get("eval_failed", 0)
    eval_passed = stats.get("eval_passed", 0)
    channels_total = stats.get("channels_total", 0)
    channels_active = stats.get("channels_active", 0)
    distribution_pending = stats.get("distribution_pending", 0)
    distribution_failed = stats.get("distribution_failed", 0)
    today_views = stats.get("today_views", 0)
    total_articles = stats.get("total_articles", 0)

    ai_status = "ready" if (chat_models + embedding_models) > 0 else "warning"
    materials_status = "warning" if unvectorized_chunks > 0 else ("ready" if knowledge_bases > 0 else "available")
    prompt_status = "ready" if total_prompts > 0 else "warning"
    task_status = (
        "error"
        if failed_jobs > 0
        else ("running" if (running_jobs + pending_jobs) > 0 else ("ready" if active_tasks > 0 else "available"))
    )
    content_status = (
        "running" if today_articles > 0 else ("ready" if (published_articles + draft_articles) > 0 else "available")
    )
    review_status = "warning" if pending_review > 0 else "ready"
    geo_eval_status = (
        "error" if eval_failed > 0 else ("running" if eval_pending > 0 else ("ready" if eval_passed > 0 else "available"))
    )
    distribution_status = (
        "error"
        if distribution_failed > 0
        else ("warning" if distribution_pending > 0 else ("ready" if channels_active > 0 else "available"))
    )
    feedback_status = "running" if today_views > 0 else "available"

    flow_nodes = [
        _node(
            "ai",
            "API 与模型",
            "聊天模型、Embedding 模型和代理配置",
            "cpu",
            "blue",
            ai_status,
            [f"Chat {chat_models}", f"Embed {embedding_models}", f"今日 {ai_used_today}"],
            [("/production/ai_config", "配置", True)],
        ),
        _node(
            "materials",
            "素材与知识库",
            "知识库、标题、关键词、图片和作者",
            "database",
            "green",
            materials_status,
            [f"知识库 {knowledge_bases}", f"向量化 {vectorized_chunks}/{knowledge_chunks}"],
            [("/production/knowledge", "查看", False, unvectorized_chunks > 0)],
        ),
        _node(
            "prompts",
            "提示词策略",
            "正文与特殊提示词",
            "message-square-text",
            "violet",
            prompt_status,
            [f"正文 {body_prompts}", f"特殊 {special_prompts}"],
            [("/production/ai_config", "提示词", False)],
        ),
        _node(
            "tasks",
            "任务编排",
            "生成数量、发布节奏与分发策略",
            "workflow",
            "blue",
            task_status,
            [f"启用 {active_tasks}", f"排队 {pending_jobs}", f"失败 {failed_jobs}"],
            [("/operations/tasks", "任务", True)],
        ),
        _node(
            "content",
            "内容生产",
            "草稿生成与发布节奏",
            "file-plus-2",
            "green",
            content_status,
            [f"草稿 {draft_articles}", f"今日 {today_articles}"],
            [("/operations/articles", "文章", False)],
        ),
        _node(
            "review",
            "审核发布",
            "待审与已发布内容",
            "badge-check",
            "amber",
            review_status,
            [f"待审 {pending_review}", f"已发布 {published_articles}"],
            [("/operations/articles", "审核", False, pending_review > 0)],
        ),
        _node(
            "geo_eval",
            "GEO 评估",
            "仿真门禁与 Wiki 合规",
            "shield-check",
            "cyan",
            geo_eval_status,
            [f"待评 {eval_pending}", f"失败 {eval_failed}", f"通过 {eval_passed}"],
            [("/production/geo-eval", "诊断", True, eval_failed > 0)],
        ),
        _node(
            "distribution",
            "多站点分发",
            "渠道与分发队列",
            "radio-tower",
            "red",
            distribution_status,
            [f"渠道 {channels_total}", f"待分发 {distribution_pending}", f"失败 {distribution_failed}"],
            [("/operations/distribution", "分发", False, distribution_failed > 0)],
        ),
        _node(
            "feedback",
            "数据反馈",
            "访问与采纳分析",
            "bar-chart-3",
            "violet",
            feedback_status,
            [f"今日访问 {today_views}"],
            [("/dashboard", "分析", True)],
        ),
    ]

    recommendations = [
        r
        for r in [
            _rec(eval_failed, "GEO 评估失败", "有文章未通过 GEO 门禁", "shield-alert", "cyan", "/production/geo-eval", "打开诊断"),
            _rec(distribution_failed, "分发失败", "远端同步存在失败项", "triangle-alert", "red", "/operations/distribution", "处理失败"),
            _rec(unvectorized_chunks, "切片未向量化", "知识片段尚未完成 embedding", "database-zap", "amber", "/production/knowledge", "同步切片"),
            _rec(pending_review, "待审核文章", "有内容等待人工审核", "badge-check", "blue", "/operations/articles", "进入审核"),
            _rec(failed_jobs, "任务失败", "队列中存在失败任务", "activity", "red", "/operations/tasks", "排查任务"),
        ]
        if r
    ]

    running_badge = int(running_jobs + pending_jobs > 0) + int(today_articles > 0) + int(distribution_pending > 0)
    attention_badge = failed_jobs + unvectorized_chunks + pending_review + distribution_failed + eval_failed

    lanes = [
        {
            "title_key": "single",
            "rows": [
                _lane("配置 AI", "模型与 Prompt", "/production/ai_config", "cpu", chat_models + embedding_models),
                _lane("素材库", "知识库与素材", "/production/materials", "database", knowledge_bases),
                _lane("创建任务", "启动生产", "/operations/tasks", "plus-circle", total_tasks),
                _lane("文章管理", "审核与发布", "/operations/articles", "file-text", total_articles),
            ],
        },
        {
            "title_key": "multi",
            "rows": [
                _lane("分发渠道", "目标站配置", "/operations/distribution", "radio-tower", channels_total),
                _lane("分发队列", "待同步任务", "/operations/distribution", "list-checks", distribution_pending),
            ],
        },
        {
            "title_key": "feedback",
            "rows": [
                _lane("数据分析", "访问与产出", "/dashboard", "chart-no-axes-combined", today_views),
                _lane("GEO 诊断", "评估失败项", "/production/geo-eval", "shield-check", eval_failed),
            ],
        },
    ]

    return {
        "running_badge_count": running_badge,
        "attention_badge_count": attention_badge,
        "flow_nodes": flow_nodes,
        "recommendations": recommendations,
        "lanes": lanes,
    }


def _node(
    key: str,
    title: str,
    desc: str,
    icon: str,
    tone: str,
    status: str,
    metrics: list[str],
    actions: list[tuple],
) -> dict:
    parsed_actions = []
    for action in actions:
        href, label = action[0], action[1]
        parsed_actions.append(
            {
                "href": href,
                "label": label,
                "primary": action[2] if len(action) > 2 else False,
                "warning": action[3] if len(action) > 3 else False,
            }
        )
    return {
        "key": key,
        "title": title,
        "desc": desc,
        "icon": icon,
        "tone": tone,
        "status": status,
        "metrics": metrics,
        "actions": parsed_actions,
    }


def _rec(count: int, title: str, desc: str, icon: str, tone: str, href: str, button: str) -> dict | None:
    if count <= 0:
        return None
    styles = {
        "cyan": "border-cyan-200 bg-cyan-50",
        "red": "border-red-200 bg-red-50",
        "amber": "border-amber-200 bg-amber-50",
        "blue": "border-blue-200 bg-blue-50",
    }
    badges = {"cyan": "error", "red": "error", "amber": "warning", "blue": "running"}
    return {
        "count": count,
        "title": title,
        "desc": desc,
        "icon": icon,
        "style": styles.get(tone, "border-gray-200 bg-gray-50"),
        "badge": badges.get(tone, "warning"),
        "href": href,
        "button": button,
    }


def _lane(title: str, desc: str, href: str, icon: str, count: int | str) -> dict:
    return {"title": title, "desc": desc, "href": href, "icon": icon, "count": count}
