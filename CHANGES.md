# Changes

## The failure

Casita’s hard product rule is two large dogs. That rule already lives in
`dog_policy`, Gemini severity/rank, and heuristic `score()` — but the review
loop never made it operable, and nothing audited when ranking stayed soft on
it.

On a fully enriched, ranked listing set the pet gate mostly holds where it is
explicit: `no_dogs` rows land as `filtered`. What still leaks into the review
band is softer:

| Residue | Count (example DB) | What a reviewer sees without help |
| --- | --- | --- |
| `small_only` still ranked `concerns` | **9** | Mid-feed. Gemini already says “negotiate” — the sort still surfaces them. |
| `unknown` still in the review band | **4** of **52** unknowns | No dog badge on the card. On **Any**, easy to mistake for fine. |
| **`dog-gate` total** | **13** of **143** active | Ranked like they’re still in play for a two-large-dog household. |

Nothing in the shipped UI asked, before a session: *which listings are still
“in play” even though pets probably don’t work for us?* Dog filtering had been
sketched in JS and then abandoned. The reviewer got a badge plus a sorted feed.

## Why this, not something else

Large dogs are the hard gate. Walk times, drives, trails, and bakeries are
preferences. I wanted the place where the system is *confidently soft* on a
hard rule — not a documented rough edge from a docs to-do list.

I considered tightening `score()` or the ranking prompt so `small_only` /
unknown drop out of the mid-pack. I left ranking alone for this change:

- Where policy is a hard no, the prompt already tends to refuse severity `ok`.
- A heavier heuristic penalty would reshuffle rows without a measured
  before/after — show the conflict first, don’t hardcode a bias.
- Without a read-only audit, “I made pets stricter” is a vibe, not evidence.

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

Lists active listings where ranking still looks usable but the large-dog gate
is weak or hostile:

| Flagged when | Meaning |
| --- | --- |
| `small_only` + `ok` / `concerns` | Still mid-feed; does not fit two large dogs cleanly |
| `no_dogs` + `ok` / `concerns` | Severity usable despite a hard no |
| unknown + `ok` | Optimistic without a classified policy |
| unknown + `concerns` + rank ≤ 50 | Still in the review band with no pet badge |

It does **not** re-rank, edit SQLite, or change the static site. Chips are how
you browse; the report is how you audit. Works against whatever DB the CLI is
pointed at (local or synced).

Example run (abridged):

```text
casita dog-gate
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

That split is the point: the interesting failure mode is not “severity said
pets are fine on a no-dogs building.” It is **small_only kept mid-pack as
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
| `casita dog-gate` | **Built** | Need a way to list soft-ranking vs gate conflicts before or beside a review pass. |
| Penalize pets harder in `score()` / prompt | **Deferred** | Measure first; residue is mid-pack `concerns` + unknown, not failed hard filters. |
| Auto-hide hostile pets from the index | **Rejected** | Hiding is a product call. Chips let you choose; the report shows leakage. |
| Extra banners on every card | **Rejected** | Badge + fit already speak; missing piece was filter + audit. |
| Revive dead walk-filter JS | **Deleted** | Wrong selectors; would fight search `display`. |

## When you'd use the report

| Situation | What you do |
| --- | --- |
| **Before a review session** | Run `dog-gate`, see if residue is mostly `small_only` or `unknown`, open that Dogs chip, work that set first |
| **After `enrich` / re-rank** | Before/after on the same DB: did severity get stricter, or are mid-pack `small_only` rows still there? |
| **Chasing unknowns** | Unknown has no dog badge — easy to miss on **Any**; chip or report on purpose |
| **Prompt / classify tweaks** | Change `_RANK_SYSTEM` or `dogs.classify`, then `dog-gate` as a cheap meter |
| **Sharing the page** | Sanity check: are we still featuring places our dogs can’t have? |

You would **not** use it to pick a winner or replace browsing — chips do the
looking; the report is the checklist.

## How to use it

```bash
# Audit the active DB (add --local to skip cloud sync)
uv run casita dog-gate --local

# Optional: point at a specific SQLite file
CASITA_DB_PATH=/path/to/listings.sqlite CASITA_ROUTES_OFFLINE=1 \
  uv run casita dog-gate --local
```

On the static review site, use the Dogs chips the same way as the date filter.
Workflow: `dog-gate` → note `small_only` vs `unknown` → open that chip → review
that set on purpose. Report = homework list; chips = view.

## Why this choice

The invitation keeps large dogs, walkability, drive times, trails, and
bakeries as the product. I took the assumption that is both a hard gate and
under-instrumented in the review loop.

Two surfaces, one constraint:

1. **Chips** — make the gate operable while reviewing
2. **Report** — make ranking’s softness on that gate measurable
