# Provider contract and failure policy

Baseline checked on 2026-10-12. Re-read configured services' live OpenAPI before
integration changes; the two deployments evolve independently.

Secondary was upgraded to 1.2.0 on this date. Its earlier string-only
`QuestionDef` schema rejected structured inputs at FastAPI validation (422), while
its llama.cpp backend accepted the identical request (200). Request schemas now
follow the primary's discriminated question types. Details and rollback location:
[secondary API revision](secondary-api-revision.md).

## Shared shape

Send JSON to `POST <base-url>/v1/systemone`:

```json
{
  "model": "clef-flash",
  "state": "The invoice is paid.",
  "questions": {
    "paid": {"type": "noul", "instructions": "Is the invoice paid?"}
  }
}
```

For Jev, change `model` to `jev-latest` and use the official Bearer key. Clef
accepts these requests without authentication.
Responses contain `model`, `answers`, and `usage.input_tokens` / `output_tokens`.
Answer IDs match question IDs. Preserve extra fields, including the secondary's
`latency_seconds`; consume only the fields required by the application.

| Type | Input criteria | Answer fields |
| --- | --- | --- |
| `noul` | Optional true/false descriptions | `type`, `noul` in [0, 1] |
| `choice` | Option ID → description | `type`, `choice`, `probabilities`, `confidence` |
| `score` | Ordered descriptions | `type`, `score`, `legend`, `probabilities`, `confidence` |

Validate complete question coverage, matching answer types, candidate keys, finite
probabilities in [0, 1], and a distribution summing to one within floating-point
tolerance. Confidence is in [0, 1]. A Score lies between zero and the final level
index. Typed output establishes interface shape, not decision accuracy.

## Differences affecting portability

| Capability | Clef primary | Clef secondary | Jev |
| --- | --- | --- | --- |
| Request model | `clef-flash` | `clef-flash` | `jev-latest` |
| Instructions | String/object/array/null | String/object/array/null | String/object/array |
| Choice criteria values | Broad values in schema | Broad values in schema | String/object/array/null |
| Rendered input limit | 4096 tokens | 4096 tokens | Check current model docs |
| Images | Data URLs in schema | Data URLs in schema | Check current model docs |
| Health status | `ok` | `healthy` plus backend fields | No shared Clef health contract |
| Observed response model | `clef-flash` | `clef-flash-q4_k_m` | Actual Jev version |

Use explicit types and meaningful string/object/array instructions. Choice
descriptions can be string/object/array/null; Score levels and Noul descriptions
can be string/object/array. Preserve structured values across attempts rather than
coercing them to strings. Both Clef services allow omitted or null instructions
with an ID fallback; explicit instructions remain portable and meaningful.

Both Clef schemas now constrain the request model to `clef-flash`.
Keep the request model separate from the returned model.
Both Clef hosts have 4096-token physical batches and perform joint inference
without automatic splitting. Split independent questions with required state.
Splitting candidates within one Choice changes the probability distribution and
needs a separately evaluated hierarchical strategy.

Secondary's confidence description was corrected to distribution concentration;
it is distinct from maximum probability. Cross-provider calibration still requires
evaluation on labeled data.

Structured Score levels are returned as structured `legend` values by both live
Clef services. Both OpenAPI schemas accept strings, objects, and arrays. Primary
was updated to version 1.0.2 on 2026-10-12; see the
[primary API revision](primary-api-revision.md). The helper preserves string,
object, and array legend values.

## Failure actions

| Event | Default action |
| --- | --- |
| Connection failure or socket timeout | Next provider |
| HTTP 429 | Next provider; bounded backoff if the caller later retries the chain |
| HTTP 5xx, including TypeSafe 529 | Next provider |
| Explicit physical batch overflow, even with HTTP 500 | Stop and reduce input or split independent questions |
| Clef HTTP 401/403 | Record host access failure, next provider |
| Jev HTTP 401/403 | Stop and correct credentials/access |
| HTTP 400/422 | Stop and correct input or prompt size |
| Redirect or other HTTP status | Stop and inspect configuration |
| Invalid JSON, missing answers, invalid distribution | Next provider |
| Valid answer with low confidence | Return; quality escalation uses separate policy |
| All providers fail | Error with attempted-provider diagnostics |

The helper makes at most three inference attempts, without same-provider retries.
It returns provenance outside the raw response. Add an overall deadline, circuit
breaker, or backoff for repeated traffic when the application needs it; keep retries
bounded. The two Clef origins receive no Authorization header. Jev's Bearer key
goes only to the fixed official origin. HTTPS origins are required and redirects
are refused.

## Sources

- [Primary OpenAPI](https://clef.create360.ai/openapi.json)
- [Secondary OpenAPI](https://clef.aiurl.tw/openapi.json)
- [TypeSafe HTTP API](https://docs.typesafe.ai/api.md)
- [JavaScript SDK client v0.6.0](https://github.com/typesafe-ai/typesafe-sdk-js/blob/v0.6.0/src/client.ts): `baseURL`, required key, default model, and retries. Re-check the installed version.
