---
icon: lucide/list-ordered
---

# Ranking

Ranking has two layers.

`src/casita/rank.py` is the deterministic sorter. It handles explicit pipeline
state, votes, filtered listings, and heuristic score. Human engagement beats a
fresh LLM rank because an active conversation is real work.

`src/casita/llm.py` is the preference ranker. `rank_listings` builds a compact
brief for each listing, adds route summaries, attaches current feedback, and
asks Gemini to return every listing with:

- a rank
- a one-sentence reason
- a severity: `ok`, `concerns`, or `filtered`

The ranking policy keeps the personal assumptions: large dogs, SF walkability,
Marin drive context, trail or beach access, and practical livability.

After Gemini returns (and again when sorting for the review site),
`dogs.apply_large_dog_rank_order` renumbers ranks among `ok` / `concerns`
listings so `dogs_ok` / `large_ok` always sit above unknown, which sits above
`small_only`. Relative model order is kept inside each tier. That makes the
prompt’s “small_only must not outrank dogs_ok” rule hold even when the model
leaves negotiate-rows mid-pack. `casita dog-gate` audits residue after the
same correction.

## Ways This Could Go Further

Ranking is deliberately still prompt-centric and Vertex-only. A future version
could make policy changes easier to evaluate more broadly, compare
deterministic and LLM rank movement beyond the dog gate, or support another
model backend.
