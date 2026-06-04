# Project log

Append-only record of decisions, pivots, risks, and open threads that future sessions should preserve.

This replaces the split between `IDEAS_TRAIL.md` and `RESEARCH_LOG.md`. Use one concise entry when a future agent would be materially worse off without the context.

## When to append

- A project direction changes or narrows.
- A mechanic, hypothesis, or experiment worth exploring arises.
- A simulation run produces an interesting finding.
- An idea is considered and explicitly rejected (with reason).
- An earlier assumption is corrected.
- A question or unresolved thread needs follow-up.
- A user preference is clarified well enough that future work depends on it.

Do not log routine Q&A, tool-use details, or ordinary implementation steps.

## Format

```markdown
## YYYY-MM-DD - Short title

Type: Idea | Decision | Finding | Rejected | Correction | Open thread

Brief context in 2-6 sentences. Include the caveat, rejected alternative, or uncertainty when relevant.
```

## Entries

## 2026-06-04 - Reverse "no GUI": simple GUI window with 2D map + stats

Type: Decision

The original README/DESIGN_PRINCIPLES mandated a terminal-only ASCII dashboard ("No GUI") as a hard rule. Reversed in favor of a single dead-simple GUI window (leaning Tkinter, stdlib, zero new deps): a 2D overhead "city Hammurabi" map on one side, the statistics dashboard on the other. Rationale: a terminal is character-cell, not pixel; the spatial map we want needs real pixels. The flat/sharp/dense aesthetic is retained — it just renders to a canvas. Statistics remain the main focus; the map is secondary. Map redraws once per tick, not per micro-action.

## 2026-06-04 - Step 3 (failure + punishment) differentiates regimes

Type: Finding

Builds now fail on skill (fail_prob = (1-skill)*max_fail_rate) and P is mapped continuously to consequences via death_prob=max(0,1-2P), fine_prob=max(0,2P-1), prison_prob=remainder (anchors: P=0 death, P=0.5 prison, P=1 fine). 50-tick runs at fixed seed show clean separation: P=0 permanently removes failing builders (512->486), P=0.5 imprisons then releases them (~26 imprisoned at t=10, back to 512 by t=25), P=1 only fines them (512 stays). Two notable emergent properties: (1) occupant deaths (~10) are identical across regimes because punishment targets builders not victims, so harsher regimes raise the TOTAL death toll with no safety benefit yet -- there is no feedback making punishment improve build quality. That feedback is the project's central question and needs profession switching (step 4) + skill mobility/education (later). (2) skill_variance is still ~inert because the mean failure rate depends on mean skill (0.5), not its spread; expect it to matter once selection exists. Dynamics remain front-loaded (no decay until step 7).

## 2026-06-04 - Naive economy (step 2) produces no lasting inequality

Type: Finding

With flat income + fixed house price and nothing else, the economy is inert: builders (~512) outnumber residents (~488), so every resident is housed in the first tick or two, building then stops (no decay to renew demand), and mean wealth just climbs uniformly via the flat wage. The one-time build transfer creates a small static wealth gap (builders +price, residents -price) but no ongoing dynamics. This is expected and motivates later steps: failure + punishment (step 3) renews builder scarcity, housing decay (step 7) renews demand, supply/demand pricing (step 5) makes skill/scarcity matter. Do not "fix" the flat economy in isolation — the dynamics are meant to come from those mechanisms.

## 2026-06-04 - Map is cosmetic-first, not spatially causal

Type: Decision

Agents will get an (x, y) position so the city can be drawn growing (Civ-style overhead view), but position does NOT feed back into the model: builder/resident matching, pricing, and failure rolls stay global/non-spatial. The map faithfully shows state; it causes nothing. This honors the "complexity only when the data demands it" philosophy. Trigger to revisit (i.e. make position causal — nearest-neighbor matching, location price premiums, wealth clustering / segregation): if validation shows the non-spatial housing market cannot reproduce a real metric such as affordability spread or segregation. Open thread: at N=100,000 a per-agent pixel map is expensive to redraw each tick, so the displayed world size will be capped — implementation detail, deferred.
