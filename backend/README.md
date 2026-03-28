# 后端说明

`DocFusion Copilot` 后端当前覆盖了赛题所要求的三条核心链路：

- 文档智能操作交互：自然语言查询事实、摘要、基础排版整理、文本替换
- 非结构化文档信息提取：上传 `docx / md / txt / xlsx` 后异步解析、抽取 facts、存入 PostgreSQL
- 表格自定义数据填写：上传 `xlsx / docx` 模板后，自动匹配相关文档并完成回填

当前版本额外补了几项对赛题评测很关键的能力：

- `document_set_id` 批次隔离，支持“先上传整批文档，再逐个上传模板”
- 模板到文档的自动匹配，优先规则匹配，配置 OpenAI-compatible 后可启用语义匹配
- 普通模板回填任务记录 `elapsed_seconds`
- `agent/execute` 同时支持 JSON 执行和 `multipart/form-data` 模板上传执行
- 事实评测与模板基准测试
- fact 追溯和人工复核

## 目录

- `app/main.py`
  FastAPI 入口
- `app/api/v1`
  REST API
- `app/core`
  配置、依赖容器、OpenAI-compatible 客户端模板
- `app/parsers`
  `docx / md / txt / xlsx` 解析器
- `app/services`
  文档处理、事实抽取、模板匹配与回填、自然语言执行、评测
- `app/repositories`
  PostgreSQL 仓储实现
- `tests`
  核心业务回归测试

## 主要接口

- `POST /api/v1/documents/upload`
- `POST /api/v1/documents/upload-batch`
- `GET /api/v1/documents`
- `GET /api/v1/documents/{doc_id}`
- `GET /api/v1/documents/{doc_id}/blocks`
- `GET /api/v1/documents/{doc_id}/facts`
- `GET /api/v1/tasks/{task_id}`
- `GET /api/v1/facts`
- `PATCH /api/v1/facts/{fact_id}/review`
- `GET /api/v1/facts/{fact_id}/trace`
- `POST /api/v1/templates/fill`
- `GET /api/v1/templates/result/{task_id}`
- `POST /api/v1/agent/chat`
- `POST /api/v1/agent/execute`
- `GET /api/v1/agent/artifacts/{file_name}`
- `POST /api/v1/benchmarks/facts/evaluate`
- `POST /api/v1/benchmarks/templates/fill`
- `GET /api/v1/benchmarks/reports/{task_id}`

## 运行

1. 安装依赖

```bash
pip install -r backend/requirements.txt
```

2. 配置 PostgreSQL

```bash
DOCFUSION_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/docfusion_copilot
DOCFUSION_DATABASE_ECHO=true
```

3. 可选配置 OpenAI-compatible

```bash
DOCFUSION_OPENAI_API_KEY=your_api_key
DOCFUSION_OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
DOCFUSION_OPENAI_MODEL=gpt-4o-mini
DOCFUSION_OPENAI_TIMEOUT_SECONDS=45
```

4. 可选配置 CORS

```bash
DOCFUSION_CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DOCFUSION_CORS_ALLOW_METHODS=*
DOCFUSION_CORS_ALLOW_HEADERS=*
DOCFUSION_CORS_ALLOW_CREDENTIALS=false
```

说明：

- 不配置也可运行，系统会使用本地规则完成解析、匹配和回填
- 配置后，`agent/chat`、文档摘要和模板文档匹配会优先尝试调用 OpenAI-compatible 接口
- 仓库只保留接口模板，不内置真实 `api_key` 和 `base_url`
- 后端已启用 `CORSMiddleware`，默认放行常见本地开发源：`3000 / 5173 / 8080`

5. 启动服务

```bash
uvicorn app.main:app --app-dir backend --reload
```

或

```bash
python backend/app/main.py
```

6. 运行测试

```bash
python -m unittest discover backend/tests -v
```

## 赛题相关建议用法

1. 用 `POST /api/v1/documents/upload-batch` 一次上传一批文档，并给这批文档分配 `document_set_id`
2. 轮询 `GET /api/v1/tasks/{task_id}`，确认文档解析完成
3. 对每个模板调用 `POST /api/v1/templates/fill`
4. 在模板请求中传同一个 `document_set_id`
5. 轮询模板任务状态，读取 `result.elapsed_seconds`、`result.matched_document_ids`
6. 用 `GET /api/v1/templates/result/{task_id}` 下载回填后的模板

## 当前边界

- 模板自动匹配已经可用，但仍以规则为主，OpenAI 语义匹配依赖你后续补充配置
- `agent/execute` 已支持编辑、格式整理、摘要、事实查询，也支持携带 `template_file` 的自然语言回填入口
- 目前异步执行是线程池，不是正式消息队列
- OCR 扫描件仍未接入
