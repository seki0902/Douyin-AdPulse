# 整理包说明

这是本地推运营 Agent V1 的独立整理目录，来源于 `Juliang-benditui-Agent-MVP\agent`。

已包含：源码、技术文档、运行脚本、配置、状态库、原始导出和日报/跨天复盘产物。

未包含：
- `runtime\chrome-profile`：浏览器登录态与本地会话数据。
- `pushplus token.txt`：Clawbot 推送密钥。
- `.playwright-cli`、`__pycache__` 等可再生成缓存。

运行前需在本机补齐已登录的 Chrome Profile，并在需要日报推送时通过 `PUSHPLUS_TOKEN` 或项目根目录的 `pushplus token.txt` 配置密钥。V1 说明见 `docs\LOCAL_PUSH_AGENT_V1.md`。
