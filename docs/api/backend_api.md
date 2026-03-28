# DocFusion Copilot Backend API

API 前缀：`/api/v1`

健康检查：`GET /health`

当前后端支持：

- 非结构化文档上传与异步解析
- facts 抽取、查询、复核、追溯
- 批次化文档管理
- `xlsx / docx` 模板自动回填
- 模板到文档的自动匹配
- 自然语言文档操作
- 准确率与耗时评测

## 1. 上传单个文档

`POST /api/v1/documents/upload`

表单字段：

- `file`
- `document_set_id`，可选

说明：

- 上传后立即返回任务 id
- 若提供 `document_set_id`，该文档会归入对应批次

## 2. 批量上传文档

`POST /api/v1/documents/upload-batch`

表单字段：

- `files`
- `document_set_id`，可选

说明：

- 不传 `document_set_id` 时，后端会自动生成一个批次 id
- 适合赛题中的“先上传整批文档”

## 3. 查询文档列表

`GET /api/v1/documents`

## 4. 查询单个文档

`GET /api/v1/documents/{doc_id}`

## 5. 查询解析块

`GET /api/v1/documents/{doc_id}/blocks`

## 6. 查询文档 facts

`GET /api/v1/documents/{doc_id}/facts`

查询参数：

- `canonical_only`
- `status`
- `min_confidence`

## 7. 查询任务状态

`GET /api/v1/tasks/{task_id}`

说明：

- 文档解析、模板回填、事实评测、模板基准测试都走异步任务
- 普通模板回填完成后，`result` 中会包含：
  - `matched_document_ids`
  - `match_mode`
  - `match_reason`
  - `elapsed_seconds`
  - `filled_cells`
  - `output_file_name`

## 8. 查询 facts

`GET /api/v1/facts`

查询参数：

- `entity_name`
- `field_name`
- `status`
- `min_confidence`
- `canonical_only`
- `document_ids`

## 9. 人工复核 fact

`PATCH /api/v1/facts/{fact_id}/review`

请求示例：

```json
{
  "status": "rejected",
  "reviewer": "tester",
  "note": "manual validation failed"
}
```

## 10. 查询 fact 追溯

`GET /api/v1/facts/{fact_id}/trace`

## 11. 提交模板回填任务

`POST /api/v1/templates/fill`

表单字段：

- `template_file`
- `document_set_id`，可选，默认 `default`
- `fill_mode`，默认 `canonical`
- `document_ids`，可选，逗号分隔
- `auto_match`，默认 `true`

说明：

- 若传 `document_ids`，后端只使用这些文档
- 若不传 `document_ids` 且传了 `document_set_id`，后端会先在该批次内选文档
- 若 `auto_match=true`，后端会读取模板名称、表头、实体列和内容提示，自动筛选最相关文档
- 若配置了 OpenAI-compatible，模板匹配会优先尝试语义匹配，否则走规则匹配

## 12. 下载回填结果

`GET /api/v1/templates/result/{task_id}`

返回文件类型：

- `.xlsx`
- `.docx`

## 13. 自然语言规划

`POST /api/v1/agent/chat`

作用：

- 将自然语言请求解析为结构化意图
- 已支持的意图包括事实查询、文档摘要、编辑、格式整理、模板回填规划等

## 14. 自然语言执行

`POST /api/v1/agent/execute`

支持两种请求方式：

- `application/json`
- `multipart/form-data`

当前支持：

- 事实查询
- 文档摘要
- 文本文档和 `docx` 的基础排版整理
- 文本文档和 `docx` 的文本替换编辑
- 通过 `multipart/form-data` 携带 `template_file` 直接提交模板回填任务

当使用 `multipart/form-data` 时，可传字段：

- `message`
- `context_id`
- `document_ids`
- `document_set_id`
- `fill_mode`
- `auto_match`
- `template_file`

当携带 `template_file` 时，返回体会额外包含：

- `task_id`
- `task_status`
- `template_name`

## 15. 下载自然语言执行产物

`GET /api/v1/agent/artifacts/{file_name}`

## 16. 事实评测

`POST /api/v1/benchmarks/facts/evaluate`

表单字段：

- `annotation_file`
- `document_ids`
- `canonical_only`
- `min_confidence`

返回指标：

- `accuracy`
- `precision`
- `recall`
- `f1`
- `per_field`
- `mismatches`
- `elapsed_seconds`

## 17. 模板基准测试

`POST /api/v1/benchmarks/templates/fill`

表单字段：

- `template_file`
- `expected_result_file`
- `document_set_id`
- `fill_mode`
- `document_ids`

返回指标：

- `accuracy`
- `matched_cells`
- `total_compared_cells`
- `elapsed_seconds`
- `mismatches`

## 18. 读取评测报告

`GET /api/v1/benchmarks/reports/{task_id}`

## OpenAI-compatible 环境变量模板

```bash
DOCFUSION_OPENAI_API_KEY=your_api_key
DOCFUSION_OPENAI_BASE_URL=https://your-openai-compatible-endpoint/v1
DOCFUSION_OPENAI_MODEL=gpt-4o-mini
DOCFUSION_OPENAI_TIMEOUT_SECONDS=45
```

## CORS 环境变量模板

```bash
DOCFUSION_CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
DOCFUSION_CORS_ALLOW_METHODS=*
DOCFUSION_CORS_ALLOW_HEADERS=*
DOCFUSION_CORS_ALLOW_CREDENTIALS=false
```

## 当前实现边界

- OCR 扫描件未接入
- 正式消息队列未接入
- 自然语言执行已支持模板文件上传，但回填结果仍通过异步任务下载链路获取
