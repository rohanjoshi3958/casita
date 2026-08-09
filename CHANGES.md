# Changes

## The failure

Casita’s hard product rule is two large dogs. That rule already lives in
`dog_policy`, Gemini severity/rank, and heuristic `score()` — but the review
loop never made it operable, and nothing audited when ranking stayed soft on
it.

On a fully enriched, ranked listing set the pet gate mostly holds where it is
explicit: `no_dogs` rows land as `filtered`. What leaked into the review band
was softer — Gemini correctly labeled `small_only` as `concerns` (“negotiate”)
but still left those rows mid-list, ahead of comparable `dogs_ok` listings.
The prompt already said they must not outrank `dogs_ok` / `large_ok`; the
model did not always hold that line.

| Residue (raw Gemini ranks) | Count | What a reviewer saw |
| --- | --- | --- |
| `small_only` still ranked `concerns` mid-pack | **9** | e.g. #14–#24 while `dogs_ok` + `concerns` sat later |
| `unknown` still in the review band | **4** of **52** | No dog badge; easy to mistake for fine on **Any** |
| **`dog-gate` (raw)** | **13** of **143** | Ranked like still in play for two large dogs |

Nothing in the shipped UI asked, before a session: *which listings are still
“in play” even though pets probably don’t work for us?* Dog filtering had been
sketched in JS and then abandoned.

## Why this, not something else

Large dogs are the hard gate. Walk times, drives, trails, and bakeries are
preferences. I wanted the place where the system is *confidently soft* on a
hard rule.

I measured first (`dog-gate` on raw ranks), then enforced the ordering rule the
prompt already stated — deterministically — instead of hoping a heavier
heuristic penalty or a prompt-only tweak would stick. Severity stays
`concerns` for negotiate / verify cases; **placement** is what was wrong.

## What shipped

### 1. Dog policy chips on the landing page

Same pattern as the existing “Added” date filter:

- Any · Large OK · Dogs OK · Small only · No dogs · Unknown
- Cards carry `data-dog` (`unknown` when policy is missing)
- Search, date, and dog filters share one client-side `apply()` so they compose
- URL hash restores `dog=…` with `q` and `since`

`large_ok` stays separate from `dogs_ok` on purpose. For this household those
are different calls: explicit large-dog welcome vs “dogs allowed, size unclear
— call and confirm.”

Dead walk-oriented `_FILTER_JS` was removed rather than revived.

### 2. Large-dog rank order (deterministic correction)

`dogs.apply_large_dog_rank_order` renumbers `llm_rank` among `ok` / `concerns`
listings:

**`dogs_ok` / `large_ok` → unknown → `small_only`**

Gemini’s relative order is preserved inside each tier. Wired into:

- `rank.rank()` — review site feed and card ranks
- live `enrich` after Gemini returns — persisted to SQLite
- ranking prompt — restates the same ordering rule for the model

Heuristic `score()` is unchanged (still a tie-break only).

### 3. `casita dog-gate` — integrity report

Applies the **same** rank order as the site, then lists residue still in the
review band (rank ≤ 50) with weak/hostile pets:

| Flagged when | Meaning |
| --- | --- |
| `small_only` + `ok` | Prompt violation |
| `small_only` + `concerns` + rank ≤ 50 | Still mid-band after correction |
| `no_dogs` + `ok` / `concerns` | Severity usable despite a hard no |
| unknown + `ok` | Optimistic without a classified policy |
| unknown + `concerns` + rank ≤ 50 | Still mid-band with no pet badge |

### Before / after (example DB)

| | Raw Gemini | After dog-policy rank order |
| --- | ---: | ---: |
| `dog-gate` flags | **13** | **3** |
| `small_only` in review band | **9** (e.g. #14–#24) | **0** (first `small_only` ≈ #100) |
| Remaining flags | — | **3** unknowns still at #48–#50 (verify band) |

`dogs_ok` now fills the top of the usable list; `small_only` no longer crowds
ahead of it. The leftover audit rows are unknowns still just inside the
review-band cutoff — real “call and confirm” work, not negotiate-over-rank
leakage. Chips remain for inspecting those sets on purpose.

### 4. Tests

- `tests/test_dogs.py` — classify; tier reorder + idempotence; gate flag /
  non-flag including past-band `small_only`; conflict ordering
- `tests/test_demo.py` — render includes dog chips, `data-dog`, and filter JS

## Decisions

| Candidate | Decision | Reason |
| --- | --- | --- |
| Dog policy chips | **Built** | Hard gate was not operable in the review UI. |
| Keep `large_ok` ≠ `dogs_ok` | **Kept split** | Different household decisions. |
| `casita dog-gate` | **Built** | Measure soft-ranking vs gate before/after. |
| Deterministic dog-policy rank order | **Built** | Prompt already required it; model left `small_only` mid-pack — enforce in code. |
| Auto-`filtered` every `small_only` | **Rejected** | Negotiate is real; wrong placement was the bug, not visibility. |
| Heavier heuristic pet penalty | **Rejected** | Heuristic only tie-breaks; wouldn’t move `#14` vs `#25`. |
| Extra banners on every card | **Rejected** | Badge + fit already speak. |
| Revive dead walk-filter JS | **Deleted** | Wrong selectors; would fight search `display`. |

## How to use it

```bash
# Audit (same order as the review site)
uv run casita dog-gate --local

# Optional: point at a specific SQLite file
CASITA_DB_PATH=/path/to/listings.sqlite CASITA_ROUTES_OFFLINE=1 \
  uv run casita dog-gate --local
```

On the static review site, use the Dogs chips when you want to inspect
`small_only` / unknown on purpose. After the rank-order fix they no longer
crowd the default mid-pack ahead of `dogs_ok`.

## Why this choice

The invitation keeps large dogs, walkability, drive times, trails, and
bakeries as the product. I took the assumption that is both a hard gate and
under-instrumented in the review loop.

Three surfaces, one constraint:

1. **Chips** — make the gate operable while reviewing
2. **Report** — make ranking’s softness on that gate measurable
3. **Rank order** — enforce the rule the prompt already stated, with the
   report as before/after proof
