# X 模块

[English](README.md) | [中文](README.zh-CN.md)

这里保存 `auto.x` 的用户可编辑配置。Python 代码位于 `src/auto/x/`。

## 目录内容

- `config/keywords.yaml` - 关键词规则、权重、静音作者和加权作者。

运行时状态保存在仓库外，并遵循 `XDG_DATA_HOME`：

```text
~/.local/share/auto/x/
  session/storage_state.json
  seen.sqlite
  raw/
```

Vault 摘要产物会写入：

```text
$VAULT_PATH/x/10_Daily/<YYYY-MM-DD>.md
```

## 调用示例

导入 Cookie-Editor 导出的 JSON cookies：

```bash
.venv/bin/python -m auto.x.cli.import_cookies /path/to/cookies.json
```

用 dry-run 验证 cookies：

```bash
mkdir -p /tmp/auto
.venv/bin/python -m auto.x.digest \
  --output /tmp/auto/x-cookies-test.json \
  --dry-run \
  --max-tweets 5
```

运行 digest：

```bash
.venv/bin/python -m auto.x.digest --output /tmp/auto/x-digest.json
```

查看 envelope：

```bash
cat /tmp/auto/x-digest.json
```

## Claude Code 调用方式

Claude Code 使用 `.claude/skills/` 下的细粒度 slash commands。

| 意图 | Claude Code command |
| --- | --- |
| 导入 X cookies | `/x-cookies` |
| 运行 X digest | `/x-digest` |

一次性设置：

1. 在 Chrome 中登录 `x.com`。
2. 使用 Cookie-Editor 导出 JSON cookies。
3. 运行 `/x-cookies` 并提供导出的 JSON 文件路径。
4. 运行 `/x-digest` 生成每日 Following 时间线摘要。

Cookie 通常有效 2-4 周。当 `/x-digest` 返回 `status: error` 且错误码与 auth 相关时，重新执行 cookie 导入流程。

## Codex 调用方式

Codex 使用聚合 skill `auto-x`，来源是 `codex/skills/auto-x`。

安装或刷新仓库内置 Codex skills：

```bash
bash codex/install-skills.sh
```

安装或修改 skill 后重启 Codex。之后可以显式调用 `$auto-x`，也可以直接描述任务，让 Codex 根据 skill description 自动匹配。

示例：

```text
$auto-x 导入 Cookie-Editor 导出的 X cookies，文件路径是 /path/to/cookies.json。
```

```text
$auto-x 跑一次 X digest dry-run，最多抓 5 条，检查 cookie 是否可用。
```

```text
$auto-x 执行 x-digest，把 envelope 写到 /tmp/auto/x-digest.json，并按 status 解释结果。
```

Codex 执行时应先读取 `codex/skills/auto-x/SKILL.md`，再根据具体旧工作流读取 `.claude/skills/x-cookies/SKILL.md` 或 `.claude/skills/x-digest/SKILL.md`。
