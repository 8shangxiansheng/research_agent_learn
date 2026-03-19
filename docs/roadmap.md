# 开发路线图

## 当前优先清单

### P0：高投入产出比

1. PDF / 本地文档上传与解析
   - 支持本地 TXT、Markdown、PDF 作为 research 上下文输入。
   - 将上传文档纳入现有 `research task`、history、report、share-to-session 流程。

2. 更强 citation 约束
   - 让回答中的 `[S1]`、`[S2]` 与 source 列表稳定绑定。
   - 尽量减少模型自由发挥造成的 citation 漂移。

3. 研究阶段进度展示
   - 显式展示 `planning / retrieving / synthesizing / done`。
   - 提升用户对 research workflow 的理解和可预期性。

4. Research report 导出增强
   - 优化文件名、摘要区块、来源格式和导出可读性。

5. 前端 E2E 测试
   - 覆盖聊天、research、导出、retry、语言切换等核心链路。

### P1：研究质量增强

6. 多数据源扩展
   - 在 arXiv 之外接入更多论文元数据源。

7. research history 管理增强
   - 增加筛选、排序、批量删除等管理能力。

8. research 与聊天更深结合
   - 支持基于某个 research task 继续追问和引用。

9. 错误诊断与失败恢复
   - 对 research 失败原因做更明确的分层反馈。

### P2：工程与发布能力

10. 构建与性能优化
    - 处理当前前端大 chunk 告警，优化首屏加载体验。

## 当前执行状态

- 已完成：`1. PDF / 本地文档上传与解析`
- 已完成：`2. 更强 citation 约束`
- 已完成：`3. 研究阶段进度展示`
- 已完成：`4. Research report 导出增强`
- 已完成：`5. 前端 E2E 测试`
- 已完成：`6. 多数据源扩展`
- 已启动：`7. research history 管理增强`
