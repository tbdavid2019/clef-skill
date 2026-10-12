# Clef + Jev Decision Skill

用 Clef-Flash 與 Jev 判斷代理任務的執行方式：讀取目前環境的 model list，
選擇主代理處理、單一 subagent 或平行 subagents，並選擇可用模型與模型層級。
也支援應用程式的分類 `choice`、是非機率 `noul` 與等級評分 `score`。

| 順位 | Base URL | 請求模型 |
|---|---|---|
| 主要 | `https://clef.create360.ai` | `clef-flash` |
| 第二順位 | `https://clef.aiurl.tw` | `clef-flash` |
| 最後 fallback | `https://api.typesafe.ai` | `jev-latest` |

三組推論端點皆為 `POST /v1/systemone`。服務切換由呼叫程式執行；skill 提供
整合規則，附帶的 Python 工具已實作上述順序。

同一份 `clef-jev` skill 可安裝到 **Codex、Claude Code、OpenCode、Pi、
Antigravity／agy、Gemini CLI、Cursor**。skill 使用通用 Agent Skills 格式；
執行決策呼叫工具需有 Python 3、shell 執行權限與 HTTPS 網路存取。

## 安裝到目前的代理

這個 repo 由個人維護，也提供同事共用：
[tbdavid2019/clef-skill](https://github.com/tbdavid2019/clef-skill)。執行以下命令，
依提示選擇目前使用的代理，安裝為個人全域 skill：

```bash
npx skills add tbdavid2019/clef-skill --skill clef-jev -g
```

也可用 `-a` 明確指定目標代理：

| 代理 | skills CLI 的 `-a` 值 |
|---|---|
| Codex | `codex` |
| Claude Code | `claude-code` |
| OpenCode | `opencode` |
| Pi | `pi` |
| Antigravity IDE | `antigravity` |
| Antigravity CLI／agy | `antigravity-cli` |
| Gemini CLI | `gemini-cli` |
| Cursor | `cursor` |

例如 OpenCode 可加 `-a opencode -y`，Claude Code 可加 `-a claude-code -y`。
各代理使用自己的 skill 呼叫介面，也可以直接要求「使用 clef-jev」。
若要與專案一起版控，移除 `-g` 並加上 `--copy`，提交安裝器產生的 skill 目錄。

## 同時安裝到多個代理

同一個 skill 目錄包含 `SKILL.md`、scripts 與 references。一次安裝到多個
個人代理環境：

```bash
npx skills add tbdavid2019/clef-skill --skill clef-jev -g \
  -a codex -a claude-code -a gemini-cli -a antigravity -a antigravity-cli \
  -a cursor -a pi -a opencode -y
```

各代理使用自己的技能目錄與啟用方式；skills CLI 會安裝到指定代理的位置。
Cursor Cloud Agents 需同步個人 skill，或採用專案層級的 `.agents/skills`。
參見 [Codex](https://developers.openai.com/codex/skills)、
[Gemini CLI](https://geminicli.com/docs/cli/using-agent-skills/)、
[Antigravity](https://www.antigravity.google/docs/skills)、
[Cursor](https://cursor.com/docs/skills)、[Pi](https://pi.dev/docs/latest/skills)
及 [OpenCode](https://opencode.ai/docs/skills) 官方文件。

## 給 LLM 的通用安裝 Prompt

將以下英文 prompt 交給任何目標代理。LLM 應依目前環境選擇安裝方式：

目前 skill 的實際路徑為
[`skills/clef-jev/SKILL.md`](https://github.com/tbdavid2019/clef-skill/blob/main/skills/clef-jev/SKILL.md)。
安裝時以最新 `main` 的 Git checkout 為準，避免沿用先前抓取的 GitHub 頁面。

```text
Install the clef-jev Agent Skill from this repository:
https://github.com/tbdavid2019/clef-skill

First fetch a fresh checkout of the current main branch using Git. Do not rely
on an earlier WebFetch response, a search snippet, or a previously cached clone.
Choose a new temporary directory for CHECKOUT_DIR and run:
git clone --depth 1 --branch main https://github.com/tbdavid2019/clef-skill.git CHECKOUT_DIR

Read CHECKOUT_DIR/skills/clef-jev/SKILL.md and confirm its name is clef-jev.
The current repository contains skills/clef-jev/, not skills/typesafe-ai/ or a
Claude plugin marketplace. If the checkout has the old layout, check its remote
and commit against the current main branch before proceeding.

Determine which agent environment you are running in, then install clef-jev for
that agent at user/global scope using its native Agent Skills installer or the
skills CLI. This skill supports Codex, Claude Code, OpenCode, Pi, Antigravity
(IDE and agy CLI), Gemini CLI, and Cursor. Use the matching skills CLI agent ID:
codex, claude-code, opencode, pi, antigravity, antigravity-cli, gemini-cli, or cursor.

For the skills CLI, install from that fresh checkout. Replace CHECKOUT_DIR with
its actual path and AGENT_ID with the current agent's ID:
npx skills add CHECKOUT_DIR --skill clef-jev -g -a AGENT_ID -y

Install only clef-jev for the current agent. Keep the complete skills/clef-jev/
directory, including scripts and references. If the installer is unavailable,
copy that complete directory into the current agent's supported skills location.
Verify discovery using that agent's own skill interface and report the installed
path, the checkout commit SHA, and how to invoke it. Do not assume any particular agent or invoke another
agent's CLI. Check whether Python 3 and HTTPS access are available for the helper.

The self-hosted Clef endpoints require no API keys. Do not request or set Clef
API keys. Leave TYPESAFE_API_KEY unset unless I explicitly ask to enable Jev as
the final fallback. Do not call the inference API or change service settings
during installation.
```

## 使用

遇到需要規劃、委派或選模型的任務時，代理依 skill 讀取目前環境的模型清單、
代理工具與權限，再呼叫 Clef 做路由。路由工具會輸出計畫；實際開 subagent、
切模型與設定 reasoning level 由該環境支援的工具執行。
安裝 skill 提供按任務選用的觸發指引；每則訊息自動攔截需由 host hook 另外整合。

可以這樣要求：

> 使用 clef-jev，先讀取目前可用的 model list，判斷這個任務需要主代理、
> 一個 subagent 或平行 subagents，並選擇符合成本與品質需求的模型。
> 使用目前環境允許的工具執行計畫，回報實際採用的模型。

代理會準備 runtime/task JSON，再執行：

```bash
python3 <skill-directory>/scripts/route.py routing-context.json
```

完整輸入與模型清單取得方式見[代理路由規格](skills/clef-jev/references/agent-routing.md)。
模型清單來自目前 host；Clef 與 Jev 是做路由判斷的服務。模型清單或切換功能
尚未提供時，skill 會指出限制，並採用目前支援的執行方式。

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
- [代理路由與動態模型清單](skills/clef-jev/references/agent-routing.md)
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
