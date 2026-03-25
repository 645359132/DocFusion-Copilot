# 后端

这里放置 DocFusion Copilot 的后端实现，当前已补全为一个可运行的 MVP 骨架，覆盖以下链路：

- FastAPI API 入口
- 文档上传与异步任务状态
- `docx / md / txt / xlsx` 四类文档解析
- 非结构化内容到 Fact 的轻量抽取
- `xlsx` 模板自动回填
- Fact 来源追溯
- 简单规则版 `agent/chat` 指令解析

## 目录说明

- `app/main.py`
  FastAPI 应用入口
- `app/api/v1`
  对外 REST 接口
- `app/core`
  配置、服务容器、字典规则
- `app/parsers`
  各类文档解析器
- `app/services`
  上传解析、抽取、回填、追溯等业务逻辑
- `app/repositories`
  内存仓储实现
- `app/tasks`
  线程池形式的轻量异步执行器
- `tests`
  本地基础单元测试

## 已实现接口

- `POST /api/v1/documents/upload`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/templates/fill`
- `GET /api/v1/templates/result/{task_id}`
- `POST /api/v1/agent/chat`
- `GET /api/v1/facts/{fact_id}/trace`

## 运行说明

1. 安装依赖：

```bash
pip install -r backend/requirements.txt
```

2. 启动服务：

```bash
uvicorn app.main:app --app-dir backend --reload
```

3. 运行测试：

```bash
python -m unittest discover backend/tests -v
```

## 当前取舍

- 为了先打通比赛 MVP，仓储层先用内存实现，后续可替换为 PostgreSQL / pgvector。
- 异步任务先用线程池模拟，后续可替换为 Celery + Redis。
- 模板回填当前优先支持 `xlsx`，`docx` 模板保留扩展位。
- `xlsx` 和 `docx` 解析尽量使用标准库，减少本地依赖门槛。
