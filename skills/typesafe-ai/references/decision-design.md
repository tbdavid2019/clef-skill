# Decision design and composition

Adapted from the upstream TypeSafe skill. These patterns apply to Clef and Jev;
use the provider contract in [api-contract.md](api-contract.md) for integration.

## Find the useful shape

Start from the behavior the user wants: what will the application show, select,
change, or hand off? Work backward to the judgments it needs. Keep known rules,
calculations, exact lookups, and execution in code. Preserve the user's chosen stack
and scope; add System One decisions where semantic understanding helps.

When brainstorming or choosing an architecture, consider more than classification.
The patterns below are starting points: combine primitives around the user's goal,
including ideas that do not fit an established recipe.

- **Route and fill known arguments.** A request can select a handler and its typed
  parameters. Ask useful branch-specific questions up front and consume only the
  relevant answers. Explore [function calling](https://docs.typesafe.ai/cookbooks/function_calling.md)
  and [speculative fan-out](https://docs.typesafe.ai/patterns/fan-out.md).
- **Select instead of generate.** Find candidate values or source spans in code,
  use a judgment to select the intended one, then copy or normalize it. Code can
  also assemble source text into a formatted document or reading guide. Explore
  [value extraction](https://docs.typesafe.ai/cookbooks/pre_parsed_value_extraction_cookbook.md)
  and [structure recovery](https://docs.typesafe.ai/cookbooks/autoformat.md).
- **Find and judge evidence.** Retrieve candidates, compare their relevance to a
  query, and select useful context. Explore [reranking](https://docs.typesafe.ai/cookbooks/rerank_typesafe.md)
  and [hierarchical classification](https://docs.typesafe.ai/cookbooks/hierarchical_classification.md).
- **Turn judgments into reusable data.** Score dimensions once, then let code or
  user controls change weights, thresholds, rankings, and views. With labeled
  outcomes, those signals can become classical ML features. Explore
  [composite scoring](https://docs.typesafe.ai/patterns/composite-scoring.md) and
  [feature discovery](https://docs.typesafe.ai/cookbooks/autoresearch_feature_discovery.md).
- **Verify and escalate.** Check specific claims or fields against their evidence;
  send uncertain or failing cases to a person or reasoning model. Explore
  [citation checks](https://docs.typesafe.ai/cookbooks/citation_check.md) and
  [extraction cascades](https://docs.typesafe.ai/cookbooks/sde_cascade.md).
- **Respond to changing state.** Code can retain goals and observations while fresh
  judgments guide the next bounded step. Keep inferred state distinct from observed
  facts, and check freshness before applying a result to a changed situation.

For open-ended requests, offer the few directions that best serve the user's goal
and recommend a starting point. For a concrete request, choose the relevant pattern
and build; a brainstorm is not a mandatory detour.

## Design the judgments

Choose by what the answer means, then read the relevant primitive page:

| Need | Primitive | Important distinction |
| --- | --- | --- |
| One of a defined set | [Choice](https://docs.typesafe.ai/primitives/choice.md) | Picks one option; its distribution compares competing options |
| Whether a condition holds | [Noul](https://docs.typesafe.ai/primitives/noul.md) | Probability of yes; no separate confidence; use one per label when several may apply |
| Degree along a described dimension | [Score](https://docs.typesafe.ai/primitives/score.md) | Probability-weighted position on ordered levels; use comparable per-item Scores for graded ranking |

Give each question enough relevant **state** to answer: source text, identities,
relationships, policies, and current facts. Prefer named JSON fields when context
has several parts. Put the judgment in **instructions** and define its possible
answers in **criteria**. Question IDs are for code; include complete meaning in
explicit instructions instead of depending on provider-specific ID defaults. Reference nested state with backticked
paths such as `ticket.messages[0].text`.

Ask one narrow, coherent judgment per question. Split independently useful dimensions,
without destroying the relationship being judged. A bounded action selection or
contextual interpretation is valid; atomic does not mean literal fact extraction
or a one-sentence limit. Use strings for simple instructions and criteria, or
structured objects and arrays when definitions or examples clarify the question.
Both Clef deployments now accept these shapes; check the configured live contract
when replacing a provider. Put shared context into named state fields.
Score levels must describe concrete situations and stand on their own.

Keep the needed answers available. Include a no-match outcome when nothing may fit;
use a separate presence judgment when it is independently useful. For source-value
selection, check candidate coverage: the model cannot choose an omitted value.

## Compose and verify

**Ask independent questions over the same state together**, including useful
speculative questions, within the provider's prompt limit. Clef evaluates the batch
jointly; structure each question so it does not require another answer as input.
State each speculative premise explicitly; code consumes the applicable answers.
A second request is warranted when an earlier answer is needed to fetch evidence,
construct new state, or determine the next options. Extra questions still use tokens;
measure actual request budgets, cost, and end-to-end latency.

Use probabilities and confidence to guide behavior, with thresholds evaluated on
the user's data and consequences. Choice/Score confidence summarizes distribution
concentration, not overall workflow correctness or permission to act. A Noul near
0.5 means similar probability for yes and no, not medium intensity. Several
acceptable alternatives can also spread probability; low confidence need not
invalidate a harmless preference choice. Ignore uncertainty on unused branches.

Keep policy explicit and raw judgments reusable. Weighted scores suit compensating
preferences; an “any serious violation” rule needs separate conditions. Changing a
weight or display filter need not rerun inference when evidence and question meanings
are unchanged. Typed output guarantees the interface, not truth. Validate decision
accuracy and probability calibration separately for each provider in the target domain.

Test representative cases and the resulting application behavior. For failures,
inspect the exact state, questions, candidates, answers, composition, and observed
outcome. Separate missing evidence, model errors, code errors, and service failures.
Treat cookbook thresholds and demo results as examples to evaluate, not universal
rules or permanent model limitations. Keep API credentials server-side in web apps.
