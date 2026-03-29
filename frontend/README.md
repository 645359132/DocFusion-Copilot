# 前端

当前前端采用以下技术栈：

- React
- Vite
- TypeScript
- Tailwind CSS
- Zustand

当前前端目标不是纯静态展示，而是围绕比赛 Demo 做一套可联调的操作台：上传文档、跟踪异步任务、提交模板回填、查看来源追溯，并逐步补齐事实复核与智能执行入口。

## 当前已完成

当前已经完成一套可继续联调的前端骨架，包含以下页面与模块：

- 上传页
- 任务状态页
- 结果预览页
- 事实复核页
- 文档详情页
- Agent 执行页
- Benchmark 内部页
- 来源追溯抽屉
- 基础布局
- 左侧导航
- 顶部概览区
- Zustand 本地 UI 状态管理
- 统一状态组件体系
- 统一按钮组件体系
- upload / tasks / templates / trace 四条核心请求封装
- facts 查询与 review 请求封装
- agent chat / execute / artifact 请求封装
- benchmark evaluate / report 请求封装
- 页面与真实接口的首轮接线
- document_set_id 批次链路接线
- 全局 toast 提示
- 移动端底部导航

当前静态页面主要文件：

- src/App.tsx
- src/layouts/AppLayout.tsx
- src/pages/uploadPage.tsx
- src/pages/TaskStatusPage.tsx
- src/pages/ResultPreviewPage.tsx
- src/pages/FactsReviewPage.tsx
- src/pages/DocumentDetailPage.tsx
- src/pages/AgentExecutePage.tsx
- src/pages/BenchmarkLabPage.tsx
- src/components/TraceabilityDrawer.tsx
- src/components/AppButton.tsx
- src/components/StateCardFrame.tsx
- src/components/LoadingStateCard.tsx
- src/components/ErrorStateCard.tsx
- src/components/EmptyStateCard.tsx
- src/components/ToastViewport.tsx
- src/components/MobileNavBar.tsx
- src/services/http.ts
- src/services/agent.ts
- src/services/benchmarks.ts
- src/services/documents.ts
- src/services/tasks.ts
- src/services/templates.ts
- src/services/trace.ts
- src/stores/uiStore.ts

说明：src/data/mockData.ts 仍保留为早期演示数据参考，但核心页面已优先走真实服务层，不再以 mock 数据作为主数据源。

## 目录说明

- src/pages：页面级组件
- src/components：可复用 UI 组件
- src/layouts：整体布局结构
- src/services：真实接口请求封装
- src/stores：Zustand 状态管理
- src/data：早期静态演示数据与占位内容
- src/styles：样式补充文件

## 统一组件规范

### 统一状态组件

当前已经统一为以下状态组件：

- LoadingStateCard：加载态
- ErrorStateCard：错误态
- EmptyStateCard：空状态
- StateCardFrame：状态组件统一外壳

使用原则：

- 页面级等待、查询中、提交中，优先使用 LoadingStateCard
- 页面级失败、请求失败、任务失败，优先使用 ErrorStateCard
- 无数据、无任务、无模板、无记录，优先使用 EmptyStateCard

### 统一按钮组件

当前按钮已经统一为 AppButton，支持以下能力：

- variant：primary / secondary / accent / ghost
- size：sm / md
- loading：按钮内部加载态
- loadingText：加载中显示文案
- disabled：禁用态

使用原则：

- 主操作按钮使用 primary
- 次操作按钮使用 secondary
- 强提示操作或强调按钮使用 accent
- 关闭、轻量操作使用 ghost
- 不再在页面里手写“上传中 / 刷新中 / 提交中 / 下载中”按钮样式，统一交给 AppButton

## 本地启动

在 frontend 目录下执行：

```bash
npm install
npm run dev
```

生产构建：

```bash
npm run build
```

如果需要联调后端，默认请求地址为：

```bash
VITE_API_BASE_URL=http://127.0.0.1:8000
```

注意：后端当前仍未配置跨域中间件，开发阶段前端通过浏览器直接访问后端时，可能出现 Failed to fetch。这不是当前前端页面逻辑错误，而是后端尚未放开跨域预检请求。

## 后续要做

### P0：优先级最高，先完成这些

以下内容当前已完成：

- 已接入批量文档上传与 document_set_id 串联流程
- 已在上传页保存并展示当前 document_set_id
- 模板回填页已支持 auto_match、fill_mode、document_ids 控制项
- 结果页已展示 matched_document_ids、elapsed_seconds、filled_cells
- 已新增 facts 列表与人工复核入口
- 已补任务页自动轮询，减少手动刷新操作

## 当前后端已实现接口

根据 [backend/README.md](../backend/README.md)，当前后端已经实现以下接口：

- POST /api/v1/documents/upload
- POST /api/v1/documents/upload-batch
- GET /api/v1/documents
- GET /api/v1/documents/{doc_id}
- GET /api/v1/documents/{doc_id}/blocks
- GET /api/v1/documents/{doc_id}/facts
- GET /api/v1/tasks/{task_id}
- GET /api/v1/facts
- PATCH /api/v1/facts/{fact_id}/review
- GET /api/v1/facts/{fact_id}/trace
- POST /api/v1/templates/fill
- GET /api/v1/templates/result/{task_id}
- POST /api/v1/agent/chat
- POST /api/v1/agent/execute
- GET /api/v1/agent/artifacts/{file_name}
- POST /api/v1/benchmarks/facts/evaluate
- POST /api/v1/benchmarks/templates/fill
- GET /api/v1/benchmarks/reports/{task_id}

当前前端已经首轮对接了以下核心链路：

- POST /api/v1/documents/upload
- POST /api/v1/documents/upload-batch
- GET /api/v1/documents
- GET /api/v1/documents/{doc_id}
- GET /api/v1/documents/{doc_id}/blocks
- GET /api/v1/documents/{doc_id}/facts
- GET /api/v1/tasks/{task_id}
- GET /api/v1/facts
- PATCH /api/v1/facts/{fact_id}/review
- POST /api/v1/templates/fill
- GET /api/v1/templates/result/{task_id}
- GET /api/v1/facts/{fact_id}/trace
- POST /api/v1/agent/chat
- POST /api/v1/agent/execute
- GET /api/v1/agent/artifacts/{file_name}
- POST /api/v1/benchmarks/facts/evaluate
- POST /api/v1/benchmarks/templates/fill
- GET /api/v1/benchmarks/reports/{task_id}

后续新增需求优先围绕 agent 结果解释、benchmark 报告可视化和页面联动继续扩展。

### P1：联调前必须补齐

- 批量上传后的任务汇总展示
- document_set_id 在页面、store、服务层三处统一透传
- facts 列表筛选条件与查询态处理
- 人工复核后的事实状态刷新
- 任务页自动轮询与完成态收口
- agent 执行结果与任务页/追溯抽屉联动
- benchmark 报告字段的结构化展示

### P2：演示效果增强

- 做 facts 管理台，支持筛选、追溯、复核
- 补低置信度高亮展示
- 补待确认字段区域
- 补模板信息卡片
- 补任务筛选与搜索

### P3：时间允许再做

- 做更完整的 Excel / Word 结果预览交互
- 做批次级 document set 管理视图
- 做更细的动效与过渡
- 做演示专用首页或封面页

## 建议的联调顺序

建议按下面顺序联调，不要同时开太多口子：

1. 上传页补 POST /api/v1/documents/upload-batch，并保存 document_set_id
2. 任务状态页继续接 GET /api/v1/tasks/{task_id}，补自动轮询
3. 结果页补 document_set_id、auto_match、fill_mode、document_ids 控制
4. 来源追溯抽屉继续用 GET /api/v1/facts/{fact_id}/trace，并把入口接到 filled_cells / facts 列表
5. 新增 facts 页，对接 GET /api/v1/facts 和 PATCH /api/v1/facts/{fact_id}/review
6. 最后再接 POST /api/v1/agent/execute 与 benchmark 系列接口

## 前端对接建议

当前 backend README 已经补全了主要接口列表，但前端仍应以后端 schema 和实际返回字段为准。联调前建议和 A 再确认每个接口的：

- 请求参数
- 返回字段
- 错误码
- 空结果场景
- 任务状态枚举值
- 是否允许跨域预检请求

推荐优先确认这些接口的响应样例：

- documents/upload
- documents/upload-batch
- tasks/{task_id}
- templates/fill
- templates/result/{task_id}
- facts
- facts/{fact_id}/review

## 建议确认的字段

### 文档上传

- task_id
- document_set_id
- status
- document

### 任务状态

- task_id
- task_type
- status
- progress
- updated_at
- message
- error
- result

### 回填结果

- task_id
- template_name
- output_file_name
- fill_mode
- document_ids
- filled_cells
- elapsed_seconds
- matched_document_ids

### 来源追溯

- fact_id
- field_name
- document
- block
- usages
- confidence

### 事实复核

- fact_id
- status
- reviewer
- note
- reviewed_at

## 前端负责人当前工作重点

你作为 B，建议持续按下面顺序推进：

1. 先补 document_set_id 这条主链路
2. 再做 facts 查询和人工复核
3. 再增强结果页的数据解释能力
4. 最后补 agent 执行和 benchmark 展示

## 当前原则

- 先保证演示链路清晰
- 先保证页面结构稳定
- 先保证接口联调顺畅
- 不优先做花哨功能
- 对比赛评委可见的结果说明、证据链、复核能力优先于纯视觉优化