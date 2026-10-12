# Secondary Clef API revision — 2026-10-12

Read this when diagnosing secondary schema differences or maintaining its API wrapper.

## Cause and change

- Primary: `10.9.0.32`, public host `clef.create360.ai`.
- Secondary: `10.9.0.99`, public host `clef.aiurl.tw`.
- Secondary API source: `/home/david/clef-flash-service/api_server.py`.
- Service: `clef-flash.service`; API port `8099`; model backend `127.0.0.1:18080`.

The former secondary `QuestionDef` used `Optional[str]` instructions and
`Union[Dict[str, str], List[str]]` criteria. The API returned 422 for structured
input that its underlying llama.cpp backend handled successfully with 200.

API version 1.2.0 adopts the primary's discriminated Choice/Noul/Score request
schemas, structured instructions/criteria, nullable Choice descriptions, constant
model identifier, explicit state types, image data URLs, and question bounds.
Structured Score legends remain structured through response validation. Request
serialization preserves explicit null state, nested null criteria, and extra
fields. Existing telemetry, actual model identifier, latency field, and deployment
method remain in use.

Both model servers use a 16384-token context and a 4096-token batch/ubatch.
The current joint-inference limit stays at 4096 rendered tokens. This revision
changes API compatibility rather than model capacity.

## Verification and rollback

Ten regression tests reproduced old-schema failures and passed with the revised
API, including structured round trips, bounds, string requests, field forwarding,
invalid-input rejection, and batch overflow classification. Tests are installed beside the secondary API source:

```bash
cd /home/david/clef-flash-service
.venv/bin/python -m unittest test_api_contract -v
```

Pre-revision source backup:
`/home/david/clef-flash-service/backups/compat-20261012T021627Z/api_server.py`.
The deployment checked the original source hash before replacement and had an
automatic rollback if readiness failed. Restart readiness passed.

Public structured three-question inference and an image Noul request returned
200 on both hosts; Swagger and ReDoc returned 200. A 5143-token test exceeded
the 4096-token physical batch on both backends. Secondary now maps this known
backend 500 to an API 400, so callers can distinguish input capacity from outages.
Primary documents its backend 500; the bundled client recognizes its explicit
overflow message and stops without fallback. The capacity-error revision also has
a backup at `backups/capacity-20261012T022124Z/api_server.py` on the secondary host.

If a future regression requires rollback, restore that backup to `api_server.py`,
preserve the service user's read access, restart `clef-flash.service`, then verify
local `/health`, inference, and the public endpoint. Update the skill's compatibility
baseline if the service returns to the narrower contract.
