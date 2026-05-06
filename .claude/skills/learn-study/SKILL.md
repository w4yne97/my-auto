---
name: learn-study
description: 完整的交互式学习会话。综合 Web 搜索、vault 内容和 Claude 知识，对指定概念进行深入学习。
---

# learn-study — 交互式学习会话

## 触发

用户输入 `/learn-study <概念路径或关键词>`

## 工作流

### Phase 0: 根源溯源检查 (强制)

**这是最重要的一步，不可跳过。**

1. **定位概念**：在 `~/.local/share/auto/learning/knowledge-map.yaml` 中查找匹配的概念（支持模糊匹配中文名或路径）
2. **读取学习路线**：检查 `~/.local/share/auto/learning/learning-route.yaml` 中该概念的位置，但只作为展示/连续性信息
3. **构建溯源链**：
   - 从 `modules/learning/config/domain-tree.yaml` 读取该概念的 `prerequisites`
   - 递归追踪每个 prerequisite 的 prerequisites，直到找到根节点（无 prerequisites 的概念）
   - 构建完整的依赖链：`根节点 → ... → 前置概念 → 当前概念`
4. **检查前置完成度**：
   - 对链上每个概念，检查 knowledge-map.yaml 中的 depth 和 confidence
   - 默认前置完成标准：depth >= L1 且 confidence >= 0.5
   - 对高级概念，若 domain-tree 或学习目标暗示更高门槛，应说明需要更深掌握，不要机械放行
5. **处理未满足的前置**：
   - 如果有未满足的 prerequisite，**不能直接跳到目标概念**
   - 输出溯源链，标注每个节点的状态（✅ 已完成 / ❌ 未完成）
   - **自动切换到溯源链中第一个未完成的概念**作为本次学习目标
   - 告知用户："要学习 X，需要先掌握 Y。本次会话将从 Y 开始。"
6. **无前置问题时**：正常进入 Phase 1

### Phase 1: 准备素材 (自动)

1. **读取当前状态**：depth, target_depth, confidence, prerequisites
2. **收集本地素材**：
   - 读取 `$VAULT_PATH/30_Insights/` 中相关的洞察文件
   - 读取 `$VAULT_PATH/20_Papers/` 中相关的论文笔记
   - 读取 `$VAULT_PATH/` 中该概念已有的知识笔记（如果有）
3. **Web 搜索**：
   - 使用 WebSearch 搜索该概念的权威解释、经典论文、技术博客
   - 搜索关键词：概念英文名 + 相关技术术语
   - 优先搜索：arXiv 论文、知名 AI 博客（Lilian Weng, Jay Alammar, HuggingFace blog 等）、官方文档
4. **网页抓取**：
   - 使用 WebFetch 获取 top 3-5 搜索结果的页面内容
   - 提取关键信息和核心观点

### Phase 2: 生成学习内容并渲染 HTML (自动)

**输出方式：生成 HTML 文件并在浏览器中打开。**

使用 `modules/learning/lib/templates/study-session.html` 模板，填充以下内容：

#### 模板填充规则

1. **Header 区域**：
   - `{{TITLE}}`: 概念中文名 + 英文名
   - `{{DATE}}`: 当前日期
   - `{{DOMAIN}}`: 所属领域
   - `{{DEPTH_FROM}}` / `{{DEPTH_TO}}`: 当前深度 → 目标深度
   - `{{DEPTH_DOT_N}}`: 根据当前深度填充 `filled-0` 到 `filled-3`

2. **溯源链区域**：
   - `{{PREREQ_CHAIN}}`: 生成从根节点到当前概念的链路
   - 每个节点用 `<span class="node done|current|pending">名称</span>` 
   - 节点间用 `<span class="arrow">→</span>` 连接

3. **主内容区域** `{{CONTENT}}`：根据深度级别生成
   
   **L0 → L1 (入门)**:
   - 概念定义与一句话总结
   - 为什么这个概念重要（在 SWE post-training 中的位置）
   - 核心机制的简化解释
   - 数学公式用 `<div class="math-block">$$...$$</div>` 包裹
   - Mermaid 图用 `<div class="mermaid">...</div>` 包裹
   - 重要洞察用 `<div class="insight-box"><div class="label">★ Insight</div><p>...</p></div>`
   - 来源引用用 `<p class="source">来源: <a href="URL">Title</a></p>`

   **L1 → L2 (进阶)**:
   - 技术细节深入
   - 关键论文的方法对比表（用 `<table>` 标签）
   - 优劣权衡分析
   - Mermaid 架构/流程图
   - 开放问题与最新进展
   - 代码/伪代码示例（用 `<pre><code>` 标签）

   **L2 → L3 (精通)**:
   - 研究前沿与争议
   - 未解决的问题和可能的研究方向
   - Mermaid 演化时间线
   - 跨领域连接与启发
   - 批判性分析

4. **复习问题区域** `{{QUESTIONS}}`：
   - 生成 3-5 个思考/复习问题
   - 每个问题用 `<div class="question-card">` 包裹
   - 问题按难度递增排列
   - 每个问题包含可折叠的提示/方向
   - 问题类型根据深度级别：
     - L0→L1: "用自己的话解释..."、"为什么...重要？"、"与X的区别是什么？"
     - L1→L2: "比较X和Y的优劣"、"如果...会怎样？"、"设计一个..."
     - L2→L3: "当前方法的主要局限是什么？"、"如何改进？"、"预测未来方向"

5. **导航区域** `{{NAV_PREV}}` / `{{NAV_NEXT}}`：
   - 根据 learning-route.yaml 填充前后步骤的链接

#### 渲染与打开

生成的 HTML 文件保存到 `$VAULT_PATH/learning/60_Study-Sessions/` 目录：
- 文件名: `{date}-{concept-id}.html`（如 `2026-04-09-ppo-for-llm.html`）
- 保存后使用 `open` 命令在浏览器中打开

```bash
open "$VAULT_PATH/learning/60_Study-Sessions/{date}-{concept-id}.html"
```

### Phase 3: 交互式学习 (对话)

HTML 打开后，在终端继续对话：

1. 告知用户 HTML 已打开，可以在浏览器中阅读完整内容
2. 在终端提供简短摘要（3-5 个关键要点）
3. 邀请用户提问、讨论、挑战
4. 用苏格拉底式方法引导深入思考
5. 中文对话，技术术语保留英文

### Phase 4: 总结

学习结束时：
1. 总结本次学习的关键收获
2. 建议用户运行 `/learn-note` 创建/更新知识笔记
3. 建议用户运行 `/learn-review` 进行测验
4. 给出建议的 depth 评估
   - L1 需要 explain 类 evidence
   - L2 需要 explain + compare + apply 类 evidence
   - L3 需要 explain + compare + apply + critique 类 evidence
   - 如果没有完成对应 evidence，不要建议提升到该 depth
5. 提示下一步：根据 planner 推荐展示下一个应学概念，并附带 cached route 位置（如果存在）

## 来源引用

在学习过程中，所有知识点都应标注来源：
- 论文：`[论文名] (arXiv:XXXX.XXXXX)`
- 博客：`[标题] (URL)`
- Vault：`来自 auto-reading-vault/30_Insights/...`
- Claude 知识：标注为 "基于通用知识"

## 注意事项

- **根源溯源不可跳过**：即使用户指定了目标概念，也必须先检查前置
- 优先使用具体的、有来源的知识，而非泛泛而谈
- 如果某个点在 vault 中已有详细笔记，引用而不重复
- 根据用户的反应调整讲解深度和速度
- 保持知识的准确性，不确定的地方明确标注
- HTML 中的数学公式使用 LaTeX 语法，MathJax 会自动渲染
- Mermaid 图表确保语法正确，避免使用不支持的特性
