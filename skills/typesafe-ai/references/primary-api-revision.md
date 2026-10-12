# Primary Clef Score legend schema — 2026-10-12

The primary API returned structured Score criteria in `answers.*.legend`, while
its OpenAPI described every legend value as a string. The live endpoint returned
objects and arrays intact, leaving Swagger clients with an incorrect response type.

Version 1.0.2 changes `ScoreAnswer.legend` to accept string, object, or array
values, matching the criteria accepted by Clef and observed in live responses. The
endpoint also documents HTTP 500 for inference errors, including the backend's
physical batch overflow. The API continues to use the deployed 1.0.1 telemetry
runtime as its image base.

Primary source: `/home/human/clef-flash-api/main.py`. OpenAPI snapshot:
`/home/human/clef-flash-api/openapi.json`. Operations guide:
`/home/human/clef-flash-api/README.md`.

The live public OpenAPI, Swagger UI, ReDoc, and health endpoint all returned 200
after deployment. The public OpenAPI reports version 1.0.2, documents legend
values as strings/objects/arrays, and includes the inference HTTP 500 response.
The pre-deployment source, Dockerfile, README, and OpenAPI snapshot are backed up
at `/home/human/clef-flash-api/backups/openapi-legend-20261012T024111Z/`.

The active container uses `local/clef-flash-api:1.0.2-legend`. Its previous
container remains available as `clef-flash-api-backup-20261012T024148Z` until a
later deployment replaces it.
