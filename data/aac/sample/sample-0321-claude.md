# 《Java 软件工程与 Agentic 开发》写作宪法

本文件是全书的**最高约束**。所有 subagents、skills、team mate 的输出都必须遵守。

## 目标与读者

| 项目 | 说明 |
|------|------|
| 读者 | 具备基础编程能力、正在从“会写代码”走向“会做工程”的学生 |
| 目标 | 用“软件工程化 + agentic 工作流”掌握 Java 后端工程基本功（从类设计到可验证交付） |
| 语言 | 中文；关键术语括注英文 |
| 课程结构 | 16 周，四阶段：思维奠基 → 系统化工程 → AI 时代工程 → 综合实战 |
| 技术栈 | Java 17 + Maven + JUnit 5 + Javalin + SQLite（极简） |
| 设计哲学 | 经典软件工程教学设计 + AI 时代工程素养（AI 是倍增器） |

---

## 全书叙事人格

本书的叙事声音是**一位有经验的编程老师坐在学生旁边**：亲切但不啰嗦，幽默但不油腻，严谨但不枯燥。

### 声音特征

| 维度 | 要 | 不要 |
|------|----|------|
| 语气 | 像朋友聊天：“你试试这样写” | 像领导讲话：“我们需要认识到” |
| 解释 | 用具体场景和故障案例讲清楚 | 抽象定义堆叠 |
| 鼓励 | 承认困难与学习曲线 | 过度鸡汤 |
| 幽默 | 轻量、贴近工程现场 | 强行抖机灵、emoji 堆砌 |

### 循环角色

全书使用 3 个循环角色增强代入感。角色设定见 `shared/characters.yml`。

| 角色 | 定位 | 典型出场方式 |
|------|------|-------------|
| **小北** | 学生视角，代表读者困惑 | “小北运行后直接报错了……” |
| **阿码** | 好奇心强，喜欢问“为什么” | “阿码举手：如果这么改会怎样？” |
| **老潘** | 工程老兵，提供真实团队视角 | “老潘说：线上系统不能这么干。” |

使用规则：
- 每章至少出现 2 次
- 用角色推动叙事和决策，不做装饰
- 角色性格必须前后一致

---

## 全书贯穿项目线（“超级线”）

除了每周独立实验，全书有一条跨 16 周的团队项目演进线：

### CampusFlow — 可交付的校园 Web 系统

学生从 Week 01 开始，逐周给 CampusFlow 增加能力：领域建模、异常策略、测试门禁、持久化、API、质量门禁、发布与复盘。

| 阶段 | 周次 | CampusFlow 进展 |
|------|------|----------------|
| 思维奠基 | 01-04 | 立项、领域模型、异常策略、协作流程与 ADR |
| 系统化工程 | 05-08 | 集合抽象、JUnit 门禁、SQLite 持久化、模式与重构 |
| AI 时代工程 | 09-12 | REST API、AI 审查训练、静态分析与覆盖率、架构演进 |
| 综合实战 | 13-16 | 集成与 Bug Bash、文档沉淀、发布准备、展示复盘 |

超级线规则：
- 每周 `CHAPTER.md` 在小结前必须有 `## CampusFlow 进度`
- 必须在上周代码基础上增量演进，禁止每周重写
- 详细设计见 `shared/book_project.md`

---

## 认知负荷预算

| 阶段 | 周次 | 新概念上限 | 回顾桥最低要求 |
|------|------|-----------|---------------|
| 思维奠基 | 01-04 | 6 个/周 | Week 01 豁免；其余至少引用前 1-2 周的 2 个概念 |
| 系统化工程 | 05-08 | 6 个/周 | 至少引用前 2-3 周的 2 个概念 |
| AI 时代工程 | 09-12 | 5 个/周 | 至少引用前 3-4 周的 2 个概念 |
| 综合实战 | 13-16 | 4 个/周 | 至少引用前 4-6 周的 3 个概念 |

概念管理：
- 新概念写入当周 `TERMS.yml`，并同步到 `shared/glossary.yml`
- 全书概念图谱维护在 `shared/concept_map.yml`
- `syllabus-planner` 规划时必须检查预算

---

## AI 辅助编程渐进融合

| 阶段 | 周次 | AI 融合程度 | 具体做法 |
|------|------|-----------|---------|
| 观察期 | 01-03 | 了解但不依赖 | 了解工具边界，先建立工程基本功 |
| 识别期 | 04-07 | 学会审视 AI 代码 | 加入 AI 生成代码审查练习 |
| 协作期 | 08-10 | 用 AI 辅助测试与调试 | 可选 AI 协作练习，必须有人类审查 |
| 主导期 | 11-16 | human-in-the-loop | AI 结对开发 + 强制门禁 + 可审计记录 |

规则：
- Week 01-03 作业禁止强制使用 AI
- Week 04+ 可在 `ASSIGNMENT.md` 增加 `### AI 协作练习（可选）`
- 每个 AI 协作练习必须附审查清单
- 详细路径见 `shared/ai_progression.md`

---

## 每周章包 Definition of Done（DoD）

对任意 `chapters/week_XX/`，发布前全部必须满足：

1. 文件齐全：
   - `CHAPTER.md` / `ASSIGNMENT.md` / `RUBRIC.md` / `QA_REPORT.md`
   - `ANCHORS.yml` / `TERMS.yml` / `.research_cache.md`
   - `examples/` / `starter_code/`（含 `pom.xml` + `src/main/java` + `src/test/java`）
2. 测试通过：`mvn -q -f chapters/week_XX/starter_code/pom.xml test`
3. QA 阻塞项清零：`QA_REPORT.md` 阻塞项无未勾选 `- [ ]`
4. 术语同步：`TERMS.yml` 的 `term_zh` 已进入 `shared/glossary.yml`
5. 锚点完整：`ANCHORS.yml` 的 `id` 周内唯一，`claim/evidence/verification` 齐全
6. 叙事质量：`student-qa` 四维评分总分 >= 18/20
7. 认知负荷：新概念与回顾桥达标
8. 贯穿项目推进：`CHAPTER.md` 包含 `## CampusFlow 进度`

上述规则由 `scripts/validate_week.py` 强制执行；`.claude/hooks/` 默认只做提示（非阻塞）。

如需 hooks 作为硬闸门，可设置环境变量：
- `TEXTBOOK_HOOK_STRICT=1`

### student-qa 四维评分

| 维度 | 分值 | 评估点 |
|------|------|--------|
| 叙事流畅度 | 1-5 | 结构变化、过渡自然、无模板感 |
| 趣味性 | 1-5 | 有继续阅读动力，有意外与共鸣 |
| 知识覆盖 | 1-5 | 概念准确、覆盖完整、代码可运行 |
| 认知负荷 | 1-5 | 难度可承受、回顾桥有效 |

总分 >= 18 才能 release；任一维度 <= 2 视为阻塞项。

修订回路（最多 3 轮）：
- >= 18：轻量修订（prose-polisher）
- < 18：结构性重写（chapter-writer）

---

## Git/Gitea 建议项（非硬闸门）

- `/release-week` 前建议工作区干净（`git status --porcelain` 为空）
- 至少 2 次提交（draft + verify）
- PR 描述引用本周 DoD 与验证输出
- 参考：`shared/gitea_workflow.md`

---

## 时效性约束（防止年份过时）

1. `shared/current_date.txt` 由 lead agent 每次流水线启动时生成（`date '+%Y-%m-%d'`）
2. 时代脉搏/AI 小专栏中的数据与事件需基于当前年份回溯近 1-2 年
3. 参考访问日期必须使用 `shared/current_date.txt` 的日期
4. 联网查证关键词必须包含当前年份
5. `syllabus-planner` 规划搜索词时必须包含当前年份

---

## ⚠️ 参考链接真实性（全局铁律）

绝对禁止编造链接和统计数据。

禁止行为：
- 凭记忆拼 URL
- 伪造论文/新闻链接
- 伪造精确统计数字

正确做法：
1. 优先使用：
   - `chapters/week_XX/.research_cache.md`
   - `WebSearch`
   - Exa MCP
   - `perplexity` MCP
   - `WebFetch`
   - Context7 MCP（技术文档）
2. 只使用搜索工具返回的 URL 原文，不要改写拼接
3. 搜索失败时使用模糊表达，并写 `<!-- TODO: 需联网搜索 ... -->`

适用范围：
- `CHAPTER.md` 的时代脉搏
- `CHAPTER.md` 的 AI 小专栏
- `ASSIGNMENT.md` 外部资源链接
- 任意正文 `https://...`

---

## 行文风格

详见 `shared/style_guide.md` + `shared/writing_exemplars.md`。

三条铁律：
1. 场景驱动：先让读者感受到问题，再引出概念
2. 贯穿案例：每章要推动一个渐进式小项目
3. 去模板化：避免每节固定骨架、避免清单堆砌

质量闸门：
- `student-qa` >= 18/20
- 代码块可运行（否则注明伪代码/节选）
- 重要结论必须落到 `ANCHORS.yml`

### 章首导入（每章必须）

每章标题后、学习目标前必须包含：
1. 引言格言（blockquote）
2. 时代脉搏段落（200-300 字，不加标题）

### 写作元数据必须注释

Bloom 标注、概念预算、AI 专栏规划、角色出场规划、章节骨架等元数据必须用 `<!-- ... -->` 包裹，不得出现在渲染正文中。

### Context7 技术查证（写作前必做）

Java 及其生态持续演进。所有写正文的 agent 在动笔前必须：
1. 用 `resolve-library-id` 定位相关库
2. 用 `query-docs` 获取最佳实践/API 用法
3. 将查证结论落实到代码示例（版本、依赖、API 用法一致）

---

## 术语与一致性

- 新术语先写入当周 `TERMS.yml`，再合入 `shared/glossary.yml`
- 概念图谱统一维护在 `shared/concept_map.yml`
- 中文为主，英文可选；定义要短、准、可复述
- 循环角色必须与 `shared/characters.yml` 一致

## Team 协作约定（强制）

- 所有 task subject 必须以 `[week_XX]` 开头（hooks 依赖）
- Lead 建议只拆任务与收敛，不直接写正文
- 所有写正文的 agent 必须先读：
  - `shared/writing_exemplars.md`
  - `shared/characters.yml`
- 规划阶段（syllabus-planner）不要求跑全量校验
- 产出阶段（writer/example/assignment/polisher/error-fixer）完成前应确保本周校验通过