# Content Agent 侧车部署（Docker）

> Python LangGraph 编排侧车，Laravel 通过 `ContentAgentClientInterface` 调用。

## 环境变量

```env
GEOFLOW_CONTENT_AGENT_BACKEND=external
CONTENT_AGENT_SERVICE_URL=http://content-agent:8000
CONTENT_AGENT_CALLBACK_URL=http://app:8080/internal/content-agent/callback
CONTENT_AGENT_CALLBACK_SECRET=<与侧车一致>
CONTENT_AGENT_DRIVER=langgraph
```

- `internal`：进程内 Laravel AI SDK，无 LangGraph 多步编排，适合本地 Mock。
- `external`：走侧车 `run_async` + HMAC 回调，生产推荐。

## 启动顺序

```bash
docker compose up -d postgres redis init app content-agent queue
```

`app` / `queue` 会等待 `content-agent` healthcheck 通过。

## 健康检查

```bash
docker compose exec content-agent wget -q -O - http://127.0.0.1:8000/v1/health
./scripts/verify.sh content-agent
```

## 常见故障

| 现象 | 排查 |
|------|------|
| 提交失败 HTTP 连接拒绝 | `CONTENT_AGENT_SERVICE_URL` 是否容器内可达 `content-agent:8000` |
| 回调 401 | `CONTENT_AGENT_CALLBACK_SECRET` Laravel 与侧车不一致 |
| 回调超时 | `CONTENT_AGENT_CALLBACK_URL` 侧车能否访问 `app:8080`；检查 `geoflow:expire-content-agent-requests` |
| 请求一直 pending | 侧车日志；`content_agent_requests` 表 status |

## 相关文档

- [langgraph-orchestration.md](./langgraph-orchestration.md)
- `services/content-agent/config/workflows.yml`
