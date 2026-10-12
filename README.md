# Clef + Jev Decision Skill

以自架 Clef-Flash 建立具型別的 AI 決策流程：分類 `choice`、是非機率 `noul`、
等級評分 `score`，並依序使用兩組自架服務與最後的 Jev fallback。

| 順位 | Base URL | 請求模型 |
|---|---|---|
| 主要 | `https://clef.create360.ai` | `clef-flash` |
| 第二順位 | `https://clef.aiurl.tw` | `clef-flash` |
| 最後 fallback | `https://api.typesafe.ai` | `jev-latest` |

三組推論端點皆為 `POST /v1/systemone`。服務切換由呼叫程式執行；skill 提供
整合規則，附帶的 Python 工具已實作上述順序。

## OpenCode 安裝

這個 repo 由個人維護，也提供同事共用：
[tbdavid2019/clef-skill](https://github.com/tbdavid2019/clef-skill)。在 OpenCode
安裝為個人全域 skill：

```bash
npx skills add tbdavid2019/clef-skill --skill clef-jev -g -a opencode -y
```

在 OpenCode 使用 `@clef-jev` 載入 skill。若要跟某個專案一起版控，移除 `-g`、
加上 `--copy`，並提交產生的 `.agents/skills/clef-jev` 目錄。

## 其他支援的代理

Codex、Gemini CLI、Antigravity／agy、Cursor、Pi 與其他 Agent Skills 相容代理
都可以讀取同一份 `SKILL.md`。例如一次安裝到個人環境：

```bash
npx skills add tbdavid2019/clef-skill --skill clef-jev -g \
  -a codex -a gemini-cli -a antigravity -a antigravity-cli \
  -a cursor -a pi -a opencode -y
```

各代理使用自己的技能目錄與啟用方式；skills CLI 會安裝到指定代理的位置。
Cursor Cloud Agents 需同步個人 skill，或採用專案層級的 `.agents/skills`。
參見 [Codex](https://developers.openai.com/codex/skills)、
[Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/)、
[Antigravity](https://www.antigravity.google/docs/skills)、
[Cursor](https://cursor.com/docs/skills)、[Pi](https://pi.dev/docs/latest/skills)
及 [OpenCode](https://opencode.ai/docs/skills) 官方文件。

## 給 LLM 的 OpenCode 安裝 Prompt

把以下英文 prompt 和 repo URL 一起交給 OpenCode：

```text
Install the clef-jev Agent Skill from this repository:
https://github.com/tbdavid2019/clef-skill

This is an OpenCode environment. Use the native skill installer or run:
npx skills add tbdavid2019/clef-skill --skill clef-jev -g -a opencode -y

Install only clef-jev. Keep the complete skill directory, including scripts and
references. Confirm that OpenCode can discover it and tell me to invoke it as
@clef-jev.

The self-hosted Clef endpoints require no API keys. Do not request or set Clef
API keys. Leave TYPESAFE_API_KEY unset unless I explicitly ask to enable Jev as
the final fallback. Do not call the inference API or change service settings
during installation.
```

## 使用

向代理描述需求，例如：

> 使用 clef-jev，讓 Clef 對客服工單分類。create360 作為主要服務，
> aiurl 作為第二順位，Jev 作為最後 fallback，低信心結果交由人工處理。

也可直接使用 Python 3 標準函式庫工具：

```bash
python3 skills/clef-jev/scripts/systemone.py --timeout 15 <<'JSON'
{
  "state": "發票已付款。",
  "questions": {
    "paid": {"type": "noul", "instructions": "這張發票是否已付款？"}
  }
}
JSON
```

輸入可改成 JSON 檔案路徑。輸出含 `provider`、前面嘗試的 `failures`、原始
API `response`；決策位於 `response.answers`。每個服務最多嘗試一次，timeout
是每次 HTTP socket 的等待時間。全部失敗時退出碼為 1，錯誤寫入 stderr。

## 設定

| 環境變數 | 用途 | 預設 |
|---|---|---|
| `CLEF_PRIMARY_BASE_URL` | 主要服務 HTTPS origin | `https://clef.create360.ai` |
| `CLEF_SECONDARY_BASE_URL` | 第二順位 HTTPS origin | `https://clef.aiurl.tw` |
| `TYPESAFE_API_KEY` | 啟用最後 Jev fallback 的官方 key | 可省略 |

使用預設兩組 Clef 時不需設定任何 API key；Base URL 預設值也已內建。
只有希望兩組 Clef 都無法連線時再呼叫 Jev，才需要提供 `TYPESAFE_API_KEY`。

Base URL 使用主機 origin，工具會加入端點。例如：

```bash
export CLEF_PRIMARY_BASE_URL=https://my-clef.example.com
export CLEF_SECONDARY_BASE_URL=https://backup-clef.example.com
```

只有更換 Clef 主機時才覆寫 Base URL。若啟用 Jev fallback，以環境變數或
secret manager 提供 `TYPESAFE_API_KEY`。工具不會對 Clef 傳送 Authorization
header，並會拒絕 redirects，確保 Jev key 只傳給官方端點。

連線失敗、timeout、429、5xx 或無效回應會切換下一組；Clef 的 401／403
也會記錄後切換。400／422 停止並回報輸入或容量問題。
明確的實體 batch 超限即使回傳 500，也會停止並要求縮小輸入；第二組已將這類超限改為 400。
成功但低信心的結果交由應用程式另外決定處理方式。

兩組 Clef 都支援字串、物件或陣列 instructions 與 criteria 描述；Choice
描述亦可使用 null。主要 API `1.0.2` 已更新 Score legend 公開 schema；
第二組 API `1.2.0` 已放寬結構化輸入。兩組的完整 prompt 上限仍為 4096 tokens；分批保留所需情境，
Choice 的候選集合需維持完整。

## 文件與驗證

- [Skill](skills/clef-jev/SKILL.md)
- [API 相容性與 fallback 規則](skills/clef-jev/references/api-contract.md)
- [決策設計與 cookbooks](skills/clef-jev/references/decision-design.md)
- [第二組服務修訂與備份](skills/clef-jev/references/secondary-api-revision.md)
- [主要服務 Score legend 文件修訂](skills/clef-jev/references/primary-api-revision.md)
- 主要服務：[Swagger](https://clef.create360.ai/docs)、[OpenAPI](https://clef.create360.ai/openapi.json)
- 第二順位：[Swagger](https://clef.aiurl.tw/docs)、[OpenAPI](https://clef.aiurl.tw/openapi.json)

執行離線測試：

```bash
python3 -m unittest discover -s tests -v
```

## 來源與授權

改編自 [TypeSafe Agent Skills](https://github.com/typesafe-ai/skills)，保留其
決策設計指引與 MIT 授權。參見 [LICENSE](LICENSE)。
