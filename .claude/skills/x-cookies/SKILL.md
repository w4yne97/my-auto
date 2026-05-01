---
name: x-cookies
description: 从 Chrome 导出的 cookies.json 重新导入 X (Twitter) session（用于 /x-digest cookie 失效时续期）
---

你是 auto-x 模块的 session 续期助手。用户敲 `/x-cookies` 通常因为 `/x-digest` 报 `auth` 错误（cookie 过期或缺失）。

# Step 1: 引导用户导出 cookies

提示用户按以下步骤操作：

```
1. 在已登录 X 的 Chrome 标签页打开 https://x.com
2. 安装 Cookie-Editor 扩展（Chrome Web Store）
3. 点击 Cookie-Editor → Export → Export as JSON
4. 将 JSON 内容保存到本地，例如 ~/Downloads/x-cookies.json
5. 把文件路径告诉我（默认使用 ~/Downloads/x-cookies.json）
```

等用户回复路径后进入 Step 2。

# Step 2: 导入 cookies

```bash
python -m auto.x.cli.import_cookies <用户提供的路径>
```

import_cookies 会：
- 校验 cookies 包含 auth_token + ct0（缺失则报错）
- 将 Cookie-Editor 格式转换为 Playwright storage_state 格式
- 写入 `~/.local/share/auto/x/session/storage_state.json`

若脚本报错（路径不存在 / JSON 格式错 / 缺关键 cookie），原样输出错误信息并提示用户重试。

# Step 3: dry-run 验证

```bash
python -m auto.x.digest --output /tmp/auto/x-cookies-test.json --dry-run --max-tweets 5
```

读取 `/tmp/auto/x-cookies-test.json`，确认 `status` 不为 `error` 且 errors 中无 `code == "auth"` 即视为通过。

# Step 4: 输出摘要

若验证通过：
```
✅ Cookies 导入成功
   📁 storage: ~/.local/share/auto/x/session/storage_state.json
   下次敲 /x-digest 即可正常工作
```

若 dry-run 仍报 auth 错误：提示用户 cookies 可能不完整，重新从已登录的 x.com 页面导出，确认 auth_token 和 ct0 都在列表中。
