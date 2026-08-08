# Changes

## Why this

Casita’s product assumption is blunt: **two large dogs**. That rule already
shows up as badges, Gemini severity, and heuristic penalties — but the review
loop never made it operable, and nothing audited when ranking stayed soft on
it.

I looked for the place where the most interesting failure lives with the least
visibility: the hard constraint is encoded in three systems (classified
`dog_policy`, Gemini severity/rank, heuristic `score()`), yet a reviewer only
got a badge and a sorted feed. Filter JS for dogs had been sketched and then
abandoned. There was no way to ask, before a review session: *which listings
are still “in play” even though pets probably don’t work for us?*


## What shipped

### 1. Dog policy chips on the landing page

The static index now filters by `dog_policy` the same way it already filters by
“Added” date:

- Any · Large OK · Dogs OK · Small only · No dogs · Unknown
- Cards carry `data-dog` (`unknown` when policy is missing)
- Search, date filter, and dog filter share one client-side `apply()` so they
  compose instead of fighting over `display`
- URL hash can restore `dog=…` alongside `q` and `since`

`large_ok` stays separate from `dogs_ok` on purpose. For this household those
are different decisions: explicit large-dog welcome vs “dogs allowed, size
unclear — call and confirm.” Collapsing them would hide the signal Casita
works hardest to extract.

Dead walk-oriented `_FILTER_JS` was removed rather than revived. It targeted
selectors and DOM that the page never rendered, and a second script would have
overwritten the search filter’s visibility. Dog filtering belongs in the same
path that already owns card show/hide.

### 2. `casita dog-gate` — read-only integrity report

A credentials-free CLI that lists active listings where ranking still looks
usable but the large-dog gate is weak or hostile:

| Flagged when | Meaning |
| --- | --- |
| `small_only` + `concerns` / `ok` | Still mid-feed; does not fit two large dogs cleanly |
| `no_dogs` + `ok` / `concerns` | Severity usable despite a hard no |
| unknown + `ok` | Optimistic without a classified policy |
| unknown + `concerns` + mid rank | Still in the review band with no pet badge |

It does **not** re-rank, edit SQLite, or change the static site. Chips are how
you browse; the report is how you audit.

Demo fixture example (abridged):

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
```

On this fixture, Gemini rarely marks a hard pet failure as `ok` — the prompt
mostly holds. The report still surfaces the interesting residue: **small_only
kept mid-pack as `concerns`**, and **unknown policies still sitting in the
review band**. That is exactly the soft-constraint failure mode worth
measuring.

### 3. Tests

- `tests/test_dogs.py` — `classify` restrictive-wins; gate flag / non-flag
  cases; conflict ordering by `llm_rank`
- `tests/test_demo.py` — render includes dog chips, `data-dog`, and filter JS


## How to use it

```bash
# Review UI
UV_PROJECT_ENVIRONMENT=venv uv run casita demo
# → http://127.0.0.1:8765/  ·  use the Dogs chips

# Audit before / beside a session
CASITA_DB_PATH=fixtures/demo.sqlite CASITA_ROUTES_OFFLINE=1 \
  UV_PROJECT_ENVIRONMENT=venv uv run casita dog-gate --local
```

Workflow: run `dog-gate` → note whether the residue is mostly `small_only` or
`unknown` → on the site open that Dogs chip and review that set on purpose.
The report is the homework list; the chips are the view.

## Why this choice

The invitation keeps large dogs, SF walkability, Marin drives, trails, and
bakeries as the product. I took the assumption that is both a hard gate and
under-instrumented in the review loop.

Two surfaces, one constraint:

1. **Chips** — make the gate operable while reviewing  
2. **Report** — make ranking’s softness on that gate measurable  

That is the same shape as evaluating a coach that can be too optimistic about a
hard rule: you need a control for the human loop, and an eval for when the
system ignored the constraint. Keeping banners off the cards is part of the
judgment — the existing badge + fit already speak; the missing piece was
filter + audit, not more labels.
