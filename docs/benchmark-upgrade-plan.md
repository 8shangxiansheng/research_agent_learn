# 对标开源项目的改造方案

## 1. 目标

本文档用于指导当前 `Academic Q&A Agent` 项目，参考成熟开源学术智能体项目进行分阶段升级。

本方案的目标不是直接复制外部项目，而是提炼其中最成熟、最适合当前仓库的能力，逐步落到现有 `FastAPI + Vue` 架构中。

## 2. 参考项目选择

### 主参考项目：GPT Researcher

仓库：

- `assafelovic/gpt-researcher`
- <https://github.com/assafelovic/gpt-researcher>

选择原因：

- 项目成熟度高，活跃度高
- 已经形成完整产品形态，而不是单点 demo
- 覆盖研究任务拆解、检索、聚合、报告输出、多前端形态、MCP 集成等完整链路
- 更适合作为“产品能力与系统架构”的主参考

可借鉴重点：

- `planner -> researcher -> writer/publisher` 的研究流程编排
- 多源检索与来源整理
- 最终研究报告输出
- 将“聊天”升级为“研究任务”的交互模型

### 子参考项目：PaperQA2

仓库：

- `Future-House/paper-qa`
- <https://github.com/Future-House/paper-qa>

选择原因：

- 在“学术文献问答 + citation”这个子问题上更聚焦
- 强调 scientific documents、evidence gathering、citation accuracy
- 更适合作为“检索、证据组织、引用输出”的技术参考

可借鉴重点：

- 证据收集与筛选
- 回答中附带 citation
- 文献元数据增强
- 面向文档问答的质量导向设计

## 3. 当前项目与参考项目的差距

### 当前项目已经具备

- 多会话聊天
- WebSocket 流式回答
- arXiv 搜索工具
- 会话搜索
- Markdown 导出
- 最新回答 retry
- 基础测试与 CI

### 当前项目主要短板

- 仍以“单轮问答”思维为主，不是“研究任务”思维
- 只有单一 `arXiv` 检索入口，缺少证据聚合层
- 回答中的来源表达较弱，citation 语义不稳定
- 缺少结构化研究产物，例如 research report
- 缺少研究过程的中间状态，例如 plan、sources、evidence、draft

### 目标状态

把当前项目从“学术问答聊天工具”升级为“研究任务驱动的学术智能体”。

## 4. 总体改造方向

### 方向 A：从 Chat 升级到 Research Task

当前模式：

- 用户输入问题
- Agent 直接检索并回答

目标模式：

- 用户创建一个研究任务
- 系统先拆解子问题
- 针对子问题检索文献和证据
- 聚合结果并生成结构化研究报告

### 方向 B：从单工具调用升级到研究工作流

当前模式：

- `agent.py` 内单个 ReAct agent 调 `arxiv_search`

目标模式：

- Research Planner：生成研究计划与子问题
- Evidence Retriever：执行文献检索与证据收集
- Answer Synthesizer：根据证据生成回答
- Report Builder：输出结构化结果

### 方向 C：从“回答内容”升级到“回答 + 证据 + 产物”

当前输出：

- 一段回答文本

目标输出：

- 回答正文
- 证据列表
- 来源引用
- 报告摘要 / 完整报告

## 5. 模块级改造建议

下面按你当前仓库结构给出建议。

### 5.1 后端：`app/services/agent.py`

当前职责：

- 初始化单个 LangChain agent
- 处理历史消息
- 提供 `astream` 与 `ainvoke`

建议改造：

- 保留现有 `AcademicAgent` 作为基础聊天能力
- 新增 `ResearchOrchestrator`，作为研究任务总入口
- 将“规划、检索、综合、报告”拆成独立步骤，而不是全部塞进一个 agent prompt

建议新增文件：

- `app/services/research/orchestrator.py`
- `app/services/research/planner.py`
- `app/services/research/retriever.py`
- `app/services/research/synthesizer.py`
- `app/services/research/report_builder.py`

职责建议：

- `planner.py`：把研究问题拆成子问题和检索方向
- `retriever.py`：统一封装 arXiv 与后续扩展数据源
- `synthesizer.py`：根据证据生成研究回答
- `report_builder.py`：生成 Markdown 格式的研究报告
- `orchestrator.py`：协调执行顺序和中间状态

### 5.2 后端：`app/services/tools.py`

当前职责：

- 只提供 `arxiv_search`

建议改造：

- 把工具层从“单一工具函数”升级为“可扩展的 source provider”
- 先不引入新依赖，但要预留统一返回结构

建议返回结构统一为：

- `source_id`
- `title`
- `authors`
- `abstract`
- `published_at`
- `url`
- `pdf_url`
- `source_type`
- `score`

这样后续才能稳定做 citation、证据排序、前端展示。

### 5.3 后端：`app/models.py`

当前约束：

- 你之前要求尽量不改现有表结构

现在如果进入下一阶段，我建议开始允许有限扩表，否则研究任务能力会被强行塞进 message 文本，后续很难维护。

建议新增模型：

- `ResearchTask`
- `ResearchSource`
- `ResearchArtifact`

最小字段建议：

- `ResearchTask`：`id`、`session_id`、`query`、`status`、`plan`、`summary`
- `ResearchSource`：`task_id`、`title`、`authors`、`url`、`abstract`、`score`
- `ResearchArtifact`：`task_id`、`artifact_type`、`content`

如果你暂时不想扩表，短期替代方案是：

- 先把 plan、sources、report 挂在新 API 的内存 / 临时文件结果中
- 等 Phase 2 稳定后再正式建模

### 5.4 后端：`app/api.py`

当前职责：

- Session / Message CRUD
- Export
- Retry
- WebSocket chat

建议新增 REST API：

- `POST /api/research/tasks`
- `GET /api/research/tasks/{task_id}`
- `POST /api/research/tasks/{task_id}/run`
- `GET /api/research/tasks/{task_id}/sources`
- `GET /api/research/tasks/{task_id}/report`

建议新增 WebSocket 或流式事件：

- 研究任务执行状态流
- 当前阶段提示，例如 `planning`、`retrieving`、`synthesizing`、`done`

短期可以直接复用你现有的 WebSocket 模式，只是事件类型更丰富。

### 5.5 前端：`frontend/src/stores/chat.ts`

当前职责：

- Session / Message 状态中心
- WebSocket 聊天状态

建议改造：

- 保留 `chat` store，不要硬改成“万能 store”
- 新增 `research` store，专门负责研究任务状态

建议新增文件：

- `frontend/src/stores/research.ts`

建议状态：

- `currentTask`
- `tasks`
- `sources`
- `report`
- `plan`
- `isRunning`
- `phase`
- `error`

### 5.6 前端：组件层

当前核心组件：

- `SessionList.vue`
- `ChatInterface.vue`
- `MessageItem.vue`

建议不要继续把研究能力堆到 `ChatInterface.vue`。

建议新增组件：

- `ResearchTaskPanel.vue`
- `ResearchPlanView.vue`
- `ResearchSourceList.vue`
- `ResearchReportView.vue`

交互建议：

- 左侧仍保留会话列表
- 右侧由“纯聊天”升级为“聊天 + 研究结果”双区布局
- 用户可在会话中发起“Deep Research”
- 研究完成后显示来源列表和最终报告

## 6. 推荐的 3 个落地阶段

### 阶段 1：把研究流程跑通

目标：

- 在不大改 UI 和数据库的前提下，先做出一个最小研究流程

本阶段只做：

- 研究问题拆解
- 多轮 arXiv 检索
- 结构化 Markdown 报告输出

建议落地：

- 新增 `ResearchOrchestrator`
- 新增 `/api/research/tasks` 与 `/report`
- 前端新增最小 research 面板

本阶段不做：

- 多数据源
- 正式 citation 格式化
- 扩表后的复杂任务管理

### 阶段 2：把证据与 citation 做扎实

目标：

- 向 PaperQA2 靠拢，提升“基于文献回答”的可信度

重点：

- 检索结果标准化
- evidence 选择与排序
- 回答中引用来源
- 前端展示来源卡片

本阶段核心收益：

- 回答更像研究助手，而不是普通聊天机器人

### 阶段 3：把研究任务产品化

目标：

- 让研究任务成为完整工作流，而不是临时功能

重点：

- 任务状态持久化
- 历史研究结果查看
- 报告导出
- 更稳定的评估与日志

## 7. 最优先的首批任务

如果现在马上开始，我建议优先做下面 5 项：

1. 为检索结果定义统一 schema，并改造 `tools.py` 输出。
2. 新增 `ResearchOrchestrator`，先串起 `plan -> retrieve -> synthesize -> report`。
3. 新增研究任务 API，而不是继续挤在现有 chat API 里。
4. 新增 `research` store 和最小研究结果面板。
5. 为研究结果增加基础测试，至少覆盖计划生成、来源列表、报告导出。

## 8. 对你项目最有价值的“借鉴清单”

### 应直接借鉴 GPT Researcher 的部分

- 研究任务编排
- 阶段化执行状态
- 报告产物思维
- 多步骤而不是单 prompt

### 应直接借鉴 PaperQA2 的部分

- evidence gathering
- citation 输出
- 文献元数据增强
- 用证据驱动回答，而不是只靠模型自由发挥

### 不建议直接照搬的部分

- 整套前端重做
- 直接把外部项目的工程结构搬进来
- 一上来就引入过多数据源或复杂 agent 框架

## 9. 建议结论

对当前仓库最合适的路径不是“重写成 GPT Researcher”，而是：

以 `GPT Researcher` 为产品和流程蓝本，  
以 `PaperQA2` 为检索与 citation 子系统蓝本，  
在你现有 `FastAPI + Vue` 项目里增量式演进。

这样做的优点是：

- 保留当前已经完成的会话、导出、retry、CI 基础
- 让下一阶段开发有明确方向
- 风险小于整体重构
- 更适合持续迭代和对外展示
