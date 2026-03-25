# DocFusion Copilot Backend API

本文档描述当前比赛版 MVP 后端已经实现的接口，基于代码中的实际行为整理，适合作为联调和演示参考。

## 基本信息

- 服务名称：`DocFusion Copilot Backend`
- 默认前缀：`/api/v1`
- 健康检查：`GET /health`
- 默认返回格式：`application/json`

## 状态约定

### 文档状态

- `uploaded`
- `parsing`
- `parsed`
- `failed`

### 任务状态

- `queued`
- `running`
- `succeeded`
- `failed`

### 任务类型

- `parse_document`
- `fill_template`

## 1. 上传文档

`POST /api/v1/documents/upload`

### 说明

上传一个源文档，并异步触发解析与事实抽取。

### 支持格式

- `.docx`
- `.md`
- `.txt`
- `.xlsx`

### 请求

- `Content-Type: multipart/form-data`
- 表单字段：`file`

### 响应示例

```json
{
  "task_id": "task_1234567890ab",
  "status": "queued",
  "document": {
    "doc_id": "doc_1234567890ab",
    "file_name": "city_report.txt",
    "stored_path": "D:/YOUR_CODE/DocFusion-Copilot/backend/storage/uploads/doc_xxx_city_report.txt",
    "doc_type": "txt",
    "upload_time": "2026-03-25T12:00:00Z",
    "status": "uploaded",
    "metadata": {}
  }
}
```

### 错误

- `400 Bad Request`
  文件名缺失或扩展名不被支持

## 2. 查询文档列表

`GET /api/v1/documents`

### 说明

返回当前后端内存仓储中的全部文档。

### 响应示例

```json
[
  {
    "doc_id": "doc_1234567890ab",
    "file_name": "city_report.txt",
    "stored_path": "D:/YOUR_CODE/DocFusion-Copilot/backend/storage/uploads/doc_xxx_city_report.txt",
    "doc_type": "txt",
    "upload_time": "2026-03-25T12:00:00Z",
    "status": "parsed",
    "metadata": {
      "block_count": 3,
      "fact_count": 4
    }
  }
]
```

## 3. 查询任务状态

`GET /api/v1/tasks/{task_id}`

### 说明

查询异步任务当前状态，适用于文档解析和模板回填两个流程。

### 响应示例

```json
{
  "task_id": "task_1234567890ab",
  "task_type": "parse_document",
  "status": "succeeded",
  "created_at": "2026-03-25T12:00:00Z",
  "updated_at": "2026-03-25T12:00:02Z",
  "progress": 1.0,
  "message": "Document parsed successfully.",
  "error": null,
  "result": {
    "document_id": "doc_1234567890ab",
    "block_count": 3,
    "fact_count": 4
  }
}
```

### 错误

- `404 Not Found`
  任务不存在

## 4. 上传模板并执行回填

`POST /api/v1/templates/fill`

### 说明

上传一个模板文件并异步触发回填。当前 MVP 优先支持 `xlsx` 模板。

### 支持格式

- `.xlsx`
- `.docx`

当前实现中：

- `.xlsx` 已支持实际回填
- `.docx` 会被接受为可支持类型，但当前填充逻辑尚未实现

### 请求

- `Content-Type: multipart/form-data`
- 表单字段：
  - `template_file`
  - `document_set_id`
  - `fill_mode`
  - `document_ids`

### 字段说明

- `document_set_id`
  用于选择文档集合
  默认值为 `default`
- `fill_mode`
  当前建议使用 `canonical`
- `document_ids`
  逗号分隔的文档 id 列表
  例如：`doc_a,doc_b`

### 响应示例

```json
{
  "task_id": "task_abcd1234ef56",
  "status": "queued",
  "template_name": "city_template.xlsx"
}
```

### 错误

- `400 Bad Request`
  模板文件名缺失或扩展名不支持

## 5. 下载回填结果

`GET /api/v1/templates/result/{task_id}`

### 说明

下载模板回填后的结果文件。

### 成功响应

- `200 OK`
- 文件类型：
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

### 错误

- `404 Not Found`
  对应任务尚未生成结果文件

## 6. 轻量 Agent 指令解析

`POST /api/v1/agent/chat`

### 说明

该接口不是完整大模型对话，而是一个规则版意图解析器，用于将自然语言请求转成结构化计划，并预览可命中的事实。

### 请求示例

```json
{
  "message": "提取所有城市的GDP并生成汇总表",
  "context_id": "proj_001"
}
```

### 响应示例

```json
{
  "intent": "query_facts",
  "entities": ["城市"],
  "fields": ["GDP总量"],
  "target": "fact_store",
  "need_db_store": false,
  "context_id": "proj_001",
  "preview": [
    {
      "fact_id": "fact_sh_gdp",
      "entity_name": "上海",
      "field_name": "GDP总量",
      "value_num": 56708.71,
      "value_text": "56,708.71",
      "unit": "亿元",
      "year": 2025,
      "confidence": 0.98
    }
  ]
}
```

## 7. Fact 来源追溯

`GET /api/v1/facts/{fact_id}/trace`

### 说明

返回某个事实的来源文档、来源块，以及它被哪些模板结果使用过。

### 响应示例

```json
{
  "fact": {
    "fact_id": "fact_sh_gdp",
    "entity_type": "city",
    "entity_name": "上海",
    "field_name": "GDP总量",
    "value_num": 56708.71,
    "value_text": "56,708.71",
    "unit": "亿元",
    "year": 2025,
    "source_doc_id": "doc_seed",
    "source_block_id": "blk_1",
    "source_span": "上海GDP总量56,708.71亿元",
    "confidence": 0.98,
    "conflict_group_id": "city::上海::GDP总量::2025::亿元",
    "is_canonical": true,
    "status": "confirmed",
    "metadata": {}
  },
  "document": {
    "doc_id": "doc_seed",
    "file_name": "seed.txt",
    "stored_path": "seed.txt",
    "doc_type": "txt",
    "upload_time": "2026-03-25T12:00:00Z",
    "status": "parsed",
    "metadata": {}
  },
  "block": null,
  "usages": [
    {
      "task_id": "task_abcd1234ef56",
      "output_file_name": "task_abcd1234ef56_city_template.xlsx",
      "sheet_name": "Sheet1",
      "cell_ref": "B2"
    }
  ]
}
```

### 错误

- `404 Not Found`
  事实不存在

## 8. 健康检查

`GET /health`

### 说明

用于确认服务进程是否成功启动。

### 响应示例

```json
{
  "status": "ok"
}
```

## 9. 当前实现说明

- 当前仓储层为内存实现，服务重启后数据不会保留。
- 当前异步机制使用线程池模拟，后续可替换为 `Celery + Redis`。
- 当前模板填充以 `xlsx` 为主，`docx` 模板填充尚未落地。
- 当前 `agent/chat` 为规则驱动，不依赖外部 LLM。
