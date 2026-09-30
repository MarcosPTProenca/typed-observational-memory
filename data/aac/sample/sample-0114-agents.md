<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# Repository Guidelines

## Project Structure & Module Organization
- `src/`：React + TypeScript 源码。主要模块：`components/`（UI 组件）、`hooks/`、`utils/`、`services/`、`contexts/`、`styles/`、`types/`。
- `docs/`：项目文档；`dist/`：构建产物；`index.html`：单页入口；`vite.config.ts`：Vite 配置。
- 命名与组织：组件单文件 `PascalCase.tsx`；子模块用 `index.ts` 聚合导出；跨模块通用工具置于 `src/utils/`。

## Build, Test, and Development Commands
- `npm run dev`：本地开发（Vite 热更新）。
- `npm run build`：`tsc` 编译 + `vite build`，输出到 `dist/`。
- `npm run preview`：本地预览构建产物。
- `npm run lint`：ESLint 全量检查（零警告策略）。

## Coding Style & Naming Conventions
- 语言：TypeScript + React 19；缩进 2 空格；使用单引号；尽量保持无多余分号与一致的导入顺序。
- 命名：组件/类型用 `PascalCase`；变量/函数用 `camelCase`；常量用 `SCREAMING_SNAKE_CASE`；Hook 以 `use` 前缀。
- 结构：UI 放 `src/components/...`；领域/跨域逻辑放 `src/utils/...`；副作用与数据访问放 `src/services/...`；上下文放 `src/contexts/...`。

## Testing Guidelines
- 当前未集成测试框架；如需新增，推荐 Vitest + React Testing Library。
- 测试命名：与被测文件同名，扩展名 `.test.ts`/`.test.tsx`，放同目录或 `__tests__/`。
- 覆盖重点：纯函数工具、关键 Hook 边界、核心交互（避免脆弱的快照）。

## Commit & Pull Request Guidelines
- 提交遵循 Conventional Commits：`feat|fix|chore|style|refactor|docs|test: 简要说明`。
- 例如：`feat: 新增任务固定功能`、`fix: 修复月视图高亮`。
- PR 要求：清晰描述与变更动机，关联 Issue；UI 变更附截图/录屏；本地通过 `npm run lint`；变更最小化，聚焦单一职责，说明影响范围与回滚方案。

## Security & Configuration Tips
- 本地配置放 `.env`，避免提交敏感信息；建议将 `.env` 列入 `.gitignore`。
- 不要提交 `dist/`；锁定依赖（`package-lock.json`）应随改动一并提交。
- 修改 `vite.config.ts` 时仅保留必要配置，避免与生产行为耦合。
