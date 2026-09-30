## 使用方式

`<REDACTED_USER>.md <文件或目录路径>`

若未提供路径，默认检查当前项目根目录（`.`）。

## 上下文

- 目标文件或目录：$ARGUMENTS（默认 `.`）
- 使用 UV 运行相关命令
- 类型检查：执行 `uv run mypy`，可使用 `> .mypy/<输出文件名>.txt` 将结果写入文件
- Ruff 修复：执行 `uv run ruff check <file-or-folder-path> --fix` 修复代码
- Lint 检查：执行 `uv run ruff check <file-or-folder-path>`，并用 `> .ruff/<输出文件名>.txt` 保存结果
- 格式化：执行 `uv run black`

## 角色

你是一名资深 Python 开发者，熟练使用 Ruff、mypy 与 black 检查并格式化代码，能依据检查结果调整代码，确保遵循规范与最佳实践。若目标为目录，应逐个子文件完成检查。

## 流程

1. 分析目标文件或目录中的代码；若目标为目录，应逐个文件进行检查与修改
2. 使用 `uv run mypy` 执行类型检查，并根据结果修复问题
3. 使用 `uv run ruff fix <file-or-folder-path> --safe` 进行安全修复
4. 使用 `uv run ruff check <file-or-folder-path>` 执行 Lint 检查，并对应修改
5. 使用 `uv run black` 格式化代码
6. 修改完成后再次运行类型检查与 Ruff 检查，确认通过
7. 列出已检查的文件及其检查结果（通过/未通过）
8. 总结检查结果与所做修改