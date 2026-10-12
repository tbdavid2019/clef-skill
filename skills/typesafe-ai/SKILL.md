---
name: typesafe-ai
license: MIT
description: >
  Build typed AI decisions with self-hosted Clef-Flash: clef.create360.ai first,
  clef.aiurl.tw second, and TypeSafe Jev last. Use for semantic routing, ranking,
  extraction, verification, and scoring with choice, noul, and score probabilities,
  or configuring System One base URLs and provider failover.
---

# Build decisions with Clef and Jev

Use System One models for focused semantic judgments over text or application
state. They return typed answers and probabilities. Keep exact rules, calculations,
permissions, and actions in application code.

This fork defaults to two self-hosted **Clef-Flash** services, with **Jev** as the
final fallback. Preserve the skill name `typesafe-ai` for invocation compatibility.

## Provider configuration

| Priority | Provider | Base URL | Request model |
| --- | --- | --- | --- |
| 1 | Clef primary | `https://clef.create360.ai` | `clef-flash` |
| 2 | Clef secondary | `https://clef.aiurl.tw` | `clef-flash` |
| 3 | TypeSafe Jev | `https://api.typesafe.ai` | `jev-latest` |

All use `POST /v1/systemone`. A base URL is an HTTPS origin without `/v1`;
append the endpoint once. Override Clef hosts independently with
`CLEF_PRIMARY_BASE_URL` and `CLEF_SECONDARY_BASE_URL`. Explicit user choices about
hosting and order take precedence over defaults.

Jev requires `TYPESAFE_API_KEY`. Self-hosted services can use their own optional
`CLEF_PRIMARY_API_KEY` and `CLEF_SECONDARY_API_KEY` for Bearer authentication.
Send each key only to its provider. Resolve keys server-side, outside source,
frontend bundles, and logs. The bundled client refuses redirects to keep
credentials on the configured host.

## Read the applicable source

Before integration, read [API contracts and failure rules](references/api-contract.md)
and each configured service's live OpenAPI specification:

- Primary: [OpenAPI](https://clef.create360.ai/openapi.json),
  [Swagger](https://clef.create360.ai/docs), [ReDoc](https://clef.create360.ai/redoc),
  [health](https://clef.create360.ai/health).
- Secondary: [OpenAPI](https://clef.aiurl.tw/openapi.json),
  [Swagger](https://clef.aiurl.tw/docs), [ReDoc](https://clef.aiurl.tw/redoc),
  [health](https://clef.aiurl.tw/health).
- Jev: [HTTP API](https://docs.typesafe.ai/api.md). Discover prompting guidance,
  SDK references, and cookbooks through the [index](https://docs.typesafe.ai/llms.txt).
  Mintlify pages can be read with `.md` appended to page paths.

Clef's own live contract governs its capabilities. Reconcile TypeSafe examples
with that contract before using them on Clef. If live docs are unavailable, use
this reference baseline and state which capabilities remain unverified.

The secondary initially returned 403 to a default HTTP client and accepted an
explicit browser-style User-Agent. The helper includes one. Persistent 403 calls
for checking the host's access policy and recording that access failure.

Use health endpoints for monitoring or diagnosis. Interpret readiness fields per
host: primary currently reports `status: ok`, secondary `status: healthy`.
Successful inference verifies integration. Avoid adding a health round trip to
every inference or treating readiness as a decision answer.

## Portable request contract

Automatic failover uses the providers' shared subset:

- `state`: string, JSON object, or array.
- `questions`: non-empty map keyed by stable caller-chosen IDs.
- Each question has explicit `type` and non-empty `instructions`: a **string,
  JSON object, or array**.
  Put complete meaning in instructions; use IDs for application code.
- `choice`: 1–255 option IDs mapped to **string, object, array, or null** descriptions. Include a no-match
  outcome when the task needs one.
- `noul`: yes/no question with optional string, object, or array descriptions in `criteria.true`
  and `criteria.false`. Its result is the probability of true.
- `score`: 2–10 ordered **string, object, or array** descriptions, low to high. Its result is a
  probability-weighted level index starting at zero.

Set `clef-flash` for each Clef attempt and `jev-latest` for Jev. The secondary
may return `clef-flash-q4_k_m`; preserve the actual response model for provenance.
Both Clef services accept structured instructions and criteria, including null
Choice descriptions. The secondary's API wrapper was aligned with the primary on
2026-10-12 (version 1.2.0); its older string-only schema was an API-layer restriction.
Score legends may retain object or array descriptions; preserve these JSON values.
Images, null state, and streaming need a separate provider capability check before
using the full Jev fallback chain. The portable helper rejects unsupported fields
before sending requests rather than silently dropping them.

Clef's complete rendered prompt must fit within **4096 tokens**, counting state,
all instructions, criteria, model-template overhead, and supported image tokens.
Leave room for overhead. Character counts and fixed question counts are estimates.
Split independent question batches when needed and retain their required state.
Keep a Choice's candidate set intact: probabilities from separate candidate
subsets are not directly comparable. Long state needs deliberate evidence
selection or a task-specific decomposition.

## Bounded failover

Prefer direct HTTP for this chain. The bundled Python 3 standard-library helper
can be used directly or as a reference implementation:

```bash
python3 <skill-directory>/scripts/systemone.py request.json --timeout 15
```

Resolve `<skill-directory>` relative to this SKILL.md, including after installation.
The helper also accepts stdin. For example:

```json
{
  "state": "結帳出現 504，款項已扣除，訂單尚未建立。",
  "questions": {
    "department": {
      "type": "choice",
      "instructions": "哪個部門應處理這筆工單？",
      "criteria": {
        "billing": "扣款、退款、對帳問題",
        "technical": "系統錯誤、訂單建立失敗",
        "other": "其他問題"
      }
    }
  }
}
```

Each provider gets one attempt in priority order. The timeout is the underlying
HTTP socket timeout per attempt, not a hard wall-clock deadline for the entire
chain. Applications with strict latency budgets need an overall deadline too.

- Switch on connection failure, timeout, 429, 5xx, or invalid response structure.
- Clef 401/403 are host-specific access failures: record them and try the next
  provider. Jev authentication failure stops and surfaces configuration errors.
- Stop on 400/422 and other HTTP errors. Correct input or capacity before retrying;
  a known oversized request also exceeds the secondary's limit.
- Recognize a backend's explicit physical batch overflow even if it uses 500:
  reduce input or split independent questions instead of switching services.
  Secondary 1.2.0 maps this known overflow to 400; primary currently returns 500.
- If Jev's key is unset, the two Clef services remain usable. If both fail, report
  the missing key and exhausted providers instead of a synthetic decision.
- Keep state, IDs, instructions, and candidates identical across attempts;
  change only provider configuration, credentials, and model.
- Return successful provider identity, actual response model, usage, and concise
  previous failure reasons. Exclude state and credentials from diagnostic logs.

The CLI returns `provider`, `failures`, and the raw API `response` in an envelope.
Consume answers at `response.answers`; direct API answers are at root `answers`.
On exhaustion the CLI writes an error to stderr and exits with code 1.

An SDK's custom `baseURL` changes routing; it does not implement this chain.
Check the installed SDK's authentication requirements, model defaults, and retries.
Avoid an implicit `jev-latest` on Clef and layered retries that multiply latency.

## Design and verify decisions

Read [decision design and composition](references/decision-design.md) when
choosing primitives, decomposing workflows, or exploring application patterns.
It preserves upstream routing, extraction, ranking, scoring, and verification
patterns with links to TypeSafe cookbooks.

Service availability and uncertainty use separate policies. A valid answer with
low confidence remains a successful response. Design any Jev quality escalation
explicitly and evaluate thresholds on the user's data. A Noul near 0.5 expresses
uncertainty about yes/no. Choice/Score confidence describes distribution
concentration, not permission to act. Keep thresholds specific to each provider
and task until calibration is measured.

Validate representative application outcomes plus primary success, secondary
fallback, final Jev fallback, input errors, timeout, invalid responses, exhaustion,
and credential isolation. Use controlled failures for fallback testing and benign
examples for live checks. State whether Jev was simulated or tested with a real key.
