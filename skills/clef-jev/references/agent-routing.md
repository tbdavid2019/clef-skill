# Runtime agent routing

Clef decides how to dispatch work; the current host supplies its model catalog,
subagent capabilities, constraints, and execution tools. This is session-specific
data. Never treat the Clef/Jev decision-provider list as the host's worker model list.

## Discover the host

| Environment | Read before routing |
| --- | --- |
| OpenCode | Native provider/model API or `opencode models`; `opencode agent list` and the selected agents' model/tool permissions |
| Pi | Native model selector/registry or `pi --list-models`; installed extensions determine whether delegation tools exist |
| Codex | Exposed model options, active model/effort, agent configuration, and actual spawn tool restrictions |
| Claude Code | Active model selector and configured subagent definitions; honor model inheritance and each subagent's allowed tools |
| Antigravity/agy, Gemini CLI, Cursor | Native model selector/API, active configuration, and exposed delegation tools; use CLI options only after checking the installed version's help |

Prefer native tool/API results over screen labels. The catalog must identify actual
model IDs, enabled access, target applicability, and provenance. Installed models
can be disabled, uncredentialed, quota-limited, or unsupported by a worker. Filter
these out using the host's known configuration without sending credentials to Clef.
Refresh when the host model settings change. If no native listing is accessible,
use a verified current configuration or the model options supplied by the harness.
Report an unavailable catalog rather than substituting a generic public model list.

Read the official docs for the current installed version before using an adapter:
[OpenCode CLI](https://opencode.ai/docs/cli/),
[Pi CLI](https://pi.dev/docs/latest/cli),
[Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[Claude Code subagents](https://code.claude.com/docs/en/sub-agents).

## Routing input

The agent constructs a JSON file and calls `scripts/route.py` relative to the skill.
This illustrative catalog contains placeholder model IDs. Replace them with IDs
and metadata obtained from the current environment before calling the helper:

```json
{
  "task": {
    "request": "Investigate API and UI regressions and propose a fix.",
    "context": "The failures can be investigated independently; parent owns integration.",
    "constraints": {"priority": "correctness", "latency": "moderate"}
  },
  "runtime": {
    "agent": "current-host",
    "catalog_source": "native model registry captured for this task",
    "current_model": "provider/model-a",
    "can_switch_model": false,
    "models": [
      {"id": "provider/model-a", "available": true,
       "targets": ["current", "subagent"], "level": "balanced",
       "description": "Host-verified general-purpose configuration", "cost": "unknown"},
      {"id": "provider/model-b", "available": true,
       "targets": ["current", "subagent"], "level": "deep",
       "description": "Host-verified reasoning configuration", "cost": "unknown"}
    ],
    "subagents": {"available": true, "free_slots": 2, "can_choose_model": true}
  }
}
```

- `task.request` and `runtime.catalog_source` are required.
- `models` must contain at least one available, authorized model. Only entries
  marked `available: true` become candidates; each declares `current`, `subagent`,
  or both targets. Supply actual context limits and capabilities where known.
- `level` is a host/user-defined model tier. Unknown levels stay null in the plan;
  the helper does not invent a fast/balanced/deep classification from a model name.
- `reasoning_levels` optionally lists each model's actual native effort options.
  Declare `can_set_reasoning_effort` on runtime/subagents and current/default
  effort where known. `task.requested_effort` is a hard constraint; models without
  that supported option are filtered out before inference.
- `task.requested_model` is an optional hard user constraint. An unavailable or
  target-incompatible requested model produces an error rather than a substitute.
- Delegation requires explicit `subagents.available: true`, at least one free slot,
  and an eligible worker model. Parallel mode requires at least two free slots.
- If worker models are inherited, set `can_choose_model: false` and declare the
  host's actual `default_model`. Only that worker model can be selected.
- Filter hard cost/context/modality restrictions in the host adapter. Then submit
  task-relevant candidates with concise known metadata. The full rendered request
  still has Clef's 4096-token limit; avoid dumping hundreds of model cards.

## Routing output and execution

`plan.execution` is `current`, `delegate`, or `parallel`. The plan contains the
selected real `model_id`, supplied `model_level`, complexity score, whether to
spawn a subagent, and a bounded `max_subagents`. Actual decisions and provider
provenance remain under `decisions` for inspection.

Execution mode is selected first. Model selection then uses only models eligible
for that mode, so current-agent and worker restrictions stay separate. If a model
is fixed by the user or by inheritance, a second inference is unnecessary.

`model_application: recommendation_only` means the host cannot apply a suggested
current-agent model switch. `host_supported` records declared host capability;
the parent still rechecks authorization and uses actual execution tool results.
The helper never launches processes, spawns subagents, or modifies agent settings.

Model tier and native reasoning/intelligence effort are separate settings. The
router selects effort in a third phase when the chosen model supplies multiple
`reasoning_levels`. It returns `reasoning_effort` and `effort_application`; unknown
options stay unspecified. Each phase uses the bounded provider chain. Allow for
the routing overhead and enforce an overall deadline in latency-sensitive hosts.
Apply effort only where the host supports and authorizes the override.

Use delegation when independent work, specialized tools, or context isolation
justifies its cost. The parent prepares work items, avoids conflicting writes,
sets completion criteria, waits for outcomes, and checks their combined result.
The decision engine is advisory about task strategy; tool policy remains authority.
