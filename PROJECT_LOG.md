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

## 2026-06-04 - Map is cosmetic-first, not spatially causal

Type: Decision

Agents will get an (x, y) position so the city can be drawn growing (Civ-style overhead view), but position does NOT feed back into the model: builder/resident matching, pricing, and failure rolls stay global/non-spatial. The map faithfully shows state; it causes nothing. This honors the "complexity only when the data demands it" philosophy. Trigger to revisit (i.e. make position causal — nearest-neighbor matching, location price premiums, wealth clustering / segregation): if validation shows the non-spatial housing market cannot reproduce a real metric such as affordability spread or segregation. Open thread: at N=100,000 a per-agent pixel map is expensive to redraw each tick, so the displayed world size will be capped — implementation detail, deferred.
