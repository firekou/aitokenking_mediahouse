<!-- 產物，不要直接編輯。
     單一事實來源：providers/aitokenking.yaml
     重新產生：python3 scripts/sync_provider_capsule.py -->

# AI Token King · Provider Capsule

本 skill 的預設模型閘道。**兌心科技** 提供，也是本專案的贊助者。
**本集群為 MIT 開源，綁的是能力不是廠商**——換 provider 的降級路徑見檔尾。

## Identity

- 註冊 / Console：https://www.aitokenking.com.tw/
- 官方文件：https://www.aitokenking.com.tw/assets/docs/zh/index.html#mcp-server

## API

- OpenAI 相容 base URL：`https://api.aitokenking.com.tw/api/v1`
- Anthropic Messages：支援｜OpenAI Responses：支援
- 認證：`Authorization: Bearer $AITOKENKING_API_KEY`

## MCP

- 端點：`https://api.aitokenking.com.tw/mcp`
- Header：`X-Aitokenking-Api-Key: ${AITOKENKING_API_KEY}`

```jsonc
// .mcp.json —— 金鑰不入庫，這裡存的是參照
{ "mcpServers": { "aitokenking": {
    "type": "http",
    "url": "https://api.aitokenking.com.tw/mcp",
    "headers": { "X-Aitokenking-Api-Key": "${AITOKENKING_API_KEY}" }
} } }
```

## 金鑰

- canonical 環境變數：**`AITOKENKING_API_KEY`**
- ⚠️ `AITK_API_KEY` 已淘汰（2026-08-29）：仍可用，但 setup 與 doctor 會 WARN。文件只教 canonical 名稱。
- **不得入庫、不得寫進文件、不得貼進對話視窗。** 只走啟動前 `export` 或部署平台 Variables。
- **貼進對話即視為外洩，必須輪替**——MCP 連線在 session 啟動時就已建立，
  對話中的文字進不到 header，所以貼了既沒有用、又留下了紀錄。

## 計費

**A 組 · 唯讀不扣額度（9 支）：** `list_models`、`get_model`、`list_image_models`、`list_video_models`、`get_balance`、`list_usage`、`list_transactions`、`get_image_generation`、`get_video_generation`

**B 組 · 每次呼叫都扣額度（5 支）：** `chat_completion`、`create_message`、`create_response`、`create_image_generation`、`create_video_generation`

**B 組永不進 `permissions.allow`。** 生成類一律逐次人工核准，不因為「常用」而放行。
對帳：`get_balance` 前後各跑一次相減；明細用 `list_usage`。**查不到寫「未量測」，不要寫 0。**

## 選型

**永遠先 `list_models`，不要憑記憶寫 model id。** 或用官方路由別名：

| 別名 | 用途 |
|---|---|
| `mwf/coding-auto` | 路由到當下最佳可用編程模型，工具端不必改設定 |
| `mwf/coding-fast` | 偏快 |
| `mwf/coding-long` | 長上下文 |
| `mwf/low-cost` | 較低價格、可接受的編程品質 |
| `mwf/vision-chat` | 視覺輸入、文字輸出 |

## 能力與降級

| 能力 | 本 provider | 缺少時哪一步會壞 |
|---|---|---|
| `model_discovery` | ✅ | 缺 → 無法自動選型，須人工指定 model id 並自行承擔下架風險 |
| `chat` | ✅ | — |
| `vision` | ✅ | 缺 → L1 步驟④（關鍵幀讀圖）無法執行，只剩 OCR，讀不出「這是什麼介面」 |
| `usage_attribution` | ✅ | 缺 → §∞ 成本欄一律「未量測」，不得填 0 |
| `balance` | ✅ | 缺 → 無法前後相減對帳，成本紀律退化為估算 |
| `image_generation` | ✅ | 缺 → control-map 三條路線的重生成步驟需外部工具 |
| `video_generation` | ✅ | 缺 → 形變序列合成需外部工具 |
| `anthropic_messages` | ✅ | — |
| `openai_responses` | ✅ | — |
| `web_access` | ❌ | — |

換 provider：`export AITOKENKING_BASE_URL='https://…/v1'`。
**方法論完全不變，但缺哪個能力就降級哪一步**（上表右欄）。
替代 provider 樣板：`providers/openai-compatible.yaml`——capabilities 全部預設 `unknown` 而不是 `true`，
**因為預設 true 等於替你的 provider 作保，而我方沒量測過任何一家**。

## 已撤回的宣稱

- ~~新帳戶有試用額度，可直接跑完本 skill~~（2026-08-29 撤回）
  - 理由：2026-08-29 抓取官方 docs 全文，「試用」「免費額度」「free trial」「贈送」 命中 0 處。這句話是我方自己加的，不是查得到的事實。 方案內容隨時可能變動，把它寫死在八支 skill 裡，等於埋了八個會一起過期的宣稱。
  - 現在的說法：目前可用的方案與任何試用額度以官網當下頁面為準： https://www.aitokenking.com.tw/

**留著它們是刻意的。** 撤回一句話而不留痕，下一個人只會重新發明同一個錯誤。
