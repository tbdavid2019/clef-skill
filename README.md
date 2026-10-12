# Clef Decision Skill

以自架 Clef-Flash 建立具型別的 AI 決策流程：分類 `choice`、是非機率 `noul`、
等級評分 `score`，並依序使用兩組自架服務與最後的 TypeSafe Jev fallback。

| 順位 | Base URL | 請求模型 |
|---|---|---|
| 主要 | `https://clef.create360.ai` | `clef-flash` |
| 第二順位 | `https://clef.aiurl.tw` | `clef-flash` |
| 最後 fallback | `https://api.typesafe.ai` | `jev-latest` |

三組推論端點皆為 `POST /v1/systemone`。服務切換由呼叫程式執行；skill 提供
整合規則，附帶的 Python 工具已實作上述順序。

## 安裝

本 skill 由個人 repo 維護，並可提供同事安裝：
[tbdavid2019/clef-skill](https://github.com/tbdavid2019/clef-skill)。沿用
`typesafe-ai` skill 與 `typesafe` plugin 名稱。

### skills.sh

執行：

```bash
npx skills add tbdavid2019/clef-skill --skill typesafe-ai
```

依提示選擇代理；加上 `-g` 可安裝到全域。

### Claude Code plugin

執行：

```bash
claude plugin marketplace add tbdavid2019/clef-skill
claude plugin install typesafe@typesafe-ai
```

用 `/typesafe:typesafe-ai` 呼叫。團隊成員可以使用同一 repo 安裝並取得更新。

## 使用

向代理描述需求，例如：

> 使用 typesafe-ai，讓 Clef 對客服工單分類。create360 作為主要服務，
> aiurl 作為第二順位，Jev 作為最後 fallback，低信心結果交由人工處理。

也可直接使用 Python 3 標準函式庫工具：

```bash
python3 skills/typesafe-ai/scripts/systemone.py --timeout 15 <<'JSON'
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
| `CLEF_PRIMARY_API_KEY` | 主要服務專用 Bearer key | 省略 |
| `CLEF_SECONDARY_API_KEY` | 第二順位專用 Bearer key | 省略 |
| `TYPESAFE_API_KEY` | 最後 Jev fallback 的官方 key | Jev 呼叫時必須設定 |

Base URL 使用主機 origin，工具會加入端點。例如：

```bash
export CLEF_PRIMARY_BASE_URL=https://my-clef.example.com
export CLEF_SECONDARY_BASE_URL=https://backup-clef.example.com
```

以環境變數或 secret manager 提供金鑰。工具把各服務的金鑰限定傳給對應主機，
並拒絕 HTTP redirects。Jev key 尚未設定時，兩組 Clef 仍可正常呼叫。

連線失敗、timeout、429、5xx 或無效回應會切換下一組；Clef 的 401／403
也會記錄後切換。400／422 停止並回報輸入或容量問題。
明確的實體 batch 超限即使回傳 500，也會停止並要求縮小輸入；第二組已將這類超限改為 400。
成功但低信心的結果交由應用程式另外決定處理方式。

兩組 Clef 都支援字串、物件或陣列 instructions 與 criteria 描述；Choice
描述亦可使用 null。主要 API `1.0.2` 已更新 Score legend 公開 schema；
第二組 API `1.2.0` 已放寬結構化輸入。兩組的完整 prompt 上限仍為 4096 tokens；分批保留所需情境，
Choice 的候選集合需維持完整。

## 文件與驗證

- [Skill](skills/typesafe-ai/SKILL.md)
- [API 相容性與 fallback 規則](skills/typesafe-ai/references/api-contract.md)
- [決策設計與 cookbooks](skills/typesafe-ai/references/decision-design.md)
- [第二組服務修訂與備份](skills/typesafe-ai/references/secondary-api-revision.md)
- [主要服務 Score legend 文件修訂](skills/typesafe-ai/references/primary-api-revision.md)
- 主要服務：[Swagger](https://clef.create360.ai/docs)、[OpenAPI](https://clef.create360.ai/openapi.json)
- 第二順位：[Swagger](https://clef.aiurl.tw/docs)、[OpenAPI](https://clef.aiurl.tw/openapi.json)

執行離線測試：

```bash
python3 -m unittest discover -s tests -v
```

## 來源與授權

改編自 [TypeSafe Agent Skills](https://github.com/typesafe-ai/skills)，保留其
決策設計指引與 MIT 授權。參見 [LICENSE](LICENSE)。
