# Changes

## The failure

On the committed demo fixture there are **143** active listings. Gemini's hard
pet gate mostly holds: all **31** `no_dogs` rows are `filtered`. What leaks
into the review band is softer:

| Residue | Count | What a reviewer sees without help |
| --- | --- | --- |
| `small_only` still ranked `concerns` | **9** | Mid-feed (#14–#24). Gemini already says “negotiate” — the sort still surfaces them. |
| `unknown` still in the review band | **4** of **52** unknowns | No dog badge on the card. On **Any**, easy to mistake for fine. |
| **`dog-gate` total** | **13** | Ranked like they’re still in play for a two-large-dog household. |

Nothing in the shipped UI asked, before a session: *which listings are still
“in play” even though pets probably don’t work for us?* Dog filtering had been
sketched in JS and then abandoned. The hard constraint lived in three systems
(`dog_policy`, Gemini severity/rank, heuristic `score()`) and the reviewer got
a badge plus a sorted feed.

## Why this, not something else

Large dogs are the invitation’s hard gate. Walk times, Marin drives, trails,
and bakeries are preferences. I wanted the place where the system is
*confidently soft* on a hard rule — not a documented rough edge from the docs
to-do list.

I considered tightening `score()` or the ranking prompt so `small_only` /
unknown drop out of the mid-pack. I left ranking alone for this change:

- On this fixture the prompt already refuses `ok` for hard pet failures.
- A heavier heuristic penalty would reshuffle rows I have not proven are
  wrong in the same direction — Bryce’s “show it, don’t score it” logic
  applies here too.
- Without a read-only audit, “I made pets stricter” is a vibe, not a
  before/after.

So the work is **make the gate operable** and **make softness measurable**.
Re-ranking can come later, against `dog-gate` as the meter.

## What shipped

### 1. Dog policy chips on the landing page

Same pattern as the existing “Added” date filter:

- Any · Large OK · Dogs OK · Small only · No dogs · Unknown
- Cards carry `data-dog` (`unknown` when policy is missing)
- Search, date, and dog filters share one client-side `apply()` so they compose
- URL hash restores `dog=…` with `q` and `since`

`large_ok` stays separate from `dogs_ok` on purpose. For this household those
are different calls: explicit large-dog welcome vs “dogs allowed, size unclear
— call and confirm.” Collapsing them would hide the signal enrichment works
hardest to extract.

Dead walk-oriented `_FILTER_JS` was removed rather than revived. It targeted
DOM the page never rendered, and a second script would have overwritten the
search filter’s visibility. Dog filtering belongs in the path that already
owns card show/hide.

### 2. `casita dog-gate` — read-only integrity report

Credentials-free. Lists active listings where ranking still looks usable but
the large-dog gate is weak or hostile:

| Flagged when | Meaning |
| --- | --- |
| `small_only` + `ok` / `concerns` | Still mid-feed; does not fit two large dogs cleanly |
| `no_dogs` + `ok` / `concerns` | Severity usable despite a hard no |
| unknown + `ok` | Optimistic without a classified policy |
| unknown + `concerns` + rank ≤ 50 | Still in the review band with no pet badge |

It does **not** re-rank, edit SQLite, or change the static site. Chips are how
you browse; the report is how you audit.

Fixture run (abridged):

```text
casita dog-gate  ·  fixtures/demo.sqlite
Large-dog gate vs ranking — read-only

#14  small_only  ·  concerns  ·  heuristic -15
     zumper:42244837 · Outer Richmond · $6,000
     Gemini: Small dogs only — would need to negotiate…
     Why:   still ranked with small_only — large dogs need negotiation

#37  unknown  ·  concerns
     zumper:64483664 · Parkside · $4,500
     Why:   ranked with unknown dog policy

13 flagged  ·  9 small_only · 4 unknown
```

That split is the point: the interesting failure mode is not “Gemini said pets
are fine on a no-dogs building.” It is **small_only kept mid-pack as
`concerns`**, plus **unknowns still sitting in the review band**.

### 3. Tests

- `tests/test_dogs.py` — `classify` restrictive-wins; gate flag / non-flag
  cases; conflict ordering by `llm_rank`
- `tests/test_demo.py` — render includes dog chips, `data-dog`, and filter JS

## Decisions

| Candidate | Decision | Reason |
| --- | --- | --- |
| Dog policy chips | **Built** | Hard gate was not operable in the review UI; abandoned filter JS was the hint. |
| Keep `large_ok` ≠ `dogs_ok` | **Kept split** | Different household decisions; collapsing hides enrichment’s work. |
| `casita dog-gate` | **Built** | Need a credentials-free way to list soft-ranking vs gate conflicts. |
| Penalize pets harder in `score()` / prompt | **Deferred** | Measure first; fixture shows prompt mostly holds — residue is `concerns` + unknown. |
| Auto-hide hostile pets from the index | **Rejected** | Hiding is a product call. Chips let you choose; the report shows leakage. |
| Extra banners on every card | **Rejected** | Badge + fit already speak; missing piece was filter + audit. |
| Revive dead walk-filter JS | **Deleted** | Wrong selectors; would fight search `display`. |

## When you'd use the report

| Situation | What you do |
| --- | --- |
| **Before a review session** | Run `dog-gate`, see if residue is mostly `small_only` or `unknown`, open that Dogs chip, work that set first |
| **After `enrich` / re-rank** | Before/after on the same DB: did Gemini get stricter, or are mid-pack `small_only` rows still there? |
| **Chasing unknowns** | Unknown has no dog badge — easy to miss on **Any**; chip or report on purpose |
| **Prompt / classify tweaks** | Change `_RANK_SYSTEM` or `dogs.classify`, then `dog-gate` as a cheap meter on the fixture |
| **Sharing the page** | Sanity check: are we still featuring places our dogs can’t have? |

You would **not** use it to pick a winner or replace browsing — chips do the
looking; the report is the checklist.

## How to use it

```bash
# Review UI
uv run casita demo
# → http://127.0.0.1:8765/  ·  Dogs chips

# Audit before / beside a session
CASITA_DB_PATH=fixtures/demo.sqlite CASITA_ROUTES_OFFLINE=1 \
  uv run casita dog-gate --local
```

Workflow: `dog-gate` → note `small_only` vs `unknown` → open that chip → review
that set on purpose. Report = homework list; chips = view.

## Why this choice

The invitation keeps large dogs, SF walkability, Marin drives, trails, and
bakeries as the product. I took the assumption that is both a hard gate and
under-instrumented in the review loop.

Two surfaces, one constraint:

1. **Chips** — make the gate operable while reviewing
2. **Report** — make ranking’s softness on that gate measurable
