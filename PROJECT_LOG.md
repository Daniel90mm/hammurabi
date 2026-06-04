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

## 2026-06-04 - Quality-based decay added; σ still aggregate-inert (needs selection)

Type: Finding

Houses now inherit their builder's skill as "build quality" (AgentPool.house_quality), and the decay hazard scales as base*(1+factor*(0.5-quality)) -- shoddy houses wear out faster, expert-built ones slower (unit-tested). However, varying σ alone still barely moves aggregate stats (e.g. ~161/159/153 cum failures at σ=0.05/0.25/0.45). Reason: with skill symmetric around mean 0.5, the faster decay of low-skill houses is offset by the slower decay of high-skill ones, so population means cancel. σ lives in the distribution (house-lifetime spread, builder wealth inequality), not the mean. To make σ move aggregates we need a selection/nonlinear mechanism -- e.g. Hammurabi (P=0) removing low-skill builders so the surviving builder pool skews skilled, or skill-correlated pricing. Noted as the likely next place σ becomes load-bearing.

## 2026-06-04 - Added housing decay (out of README's numbered order, on purpose)

Type: Decision

Implemented constant-hazard housing decay (EconomyConfig.house_decay_rate, default 0.02/tick): each tick a housed agent's house may wear out, sending them back into the market. Decay is in the README tick-loop spec ("7. Houses age and decay") but was missing from the numbered build order; I pulled it in before step 5 (pricing) because pricing is near-pointless without ongoing demand to respond to, and because the sim froze at ~tick 13 otherwise. Verified the freeze is gone: failures/imprisonment/building continue indefinitely and the housed count reaches a churn rather than a one-shot. This unblocks meaningful pricing (step 5) and live charts. Age/condition-based decay deferred until data demands it. Next: step 5 (emergent pricing), then the matplotlib chart panel (user chose embedded matplotlib).

## 2026-06-04 - Sim freezes ~tick 13 without decay; ratio equilibrium explained

Type: Finding

Observed at pop=100k, σ=0.4, ρ=0.1, P=0.5: tick 1 houses 95.7% of residents at once, ~3000 build failures -> ~3000 imprisonments + ~900 occupant deaths; by ~tick 13 all buildable residents are housed, after which there are zero builds, failures, or imprisonments forever, and the role ratio sits at ~84.5% builders / 15.5% residents unchanging. Both are correct, not bugs: (1) houses never decay (step 7 absent), so construction is a one-time event and the justice system goes idle once it finishes; (2) the static ratio is the wealth gap closing -- residents convert to builders until each poor convert dilutes builder mean wealth enough to bring it within the switch threshold, then switching halts. Implication for visualization: live time-series charts will show a short transient then flatline. Housing decay (step 7) is the prerequisite for the sim to be interesting over time, and therefore for charts to be worth watching. Also: the simulation currently keeps no per-tick history (only current state + cumulative totals) -- live charts require adding a history buffer (the README's logger).

## 2026-06-04 - Step 4 (profession switching) wakes up ρ

Type: Finding

Agents now switch roles by comparing mean wealth of the two roles: if builders are richer, residents enter building gated by risk tolerance ρ; if residents are richer, builders flee gated by (1-ρ). Fled builders lose their house and re-enter the market. ρ now strongly drives the profession ratio: at fixed seed, ρ=0.1 -> ~637 builders/352 residents, ρ=0.9 -> ~934/55. Two caveats: (1) profitability proxy is cumulative mean wealth, which is dominated by the early one-time building windfall, so once everyone is housed there is no real income difference and switching chases a stale signal -- this will be much more meaningful once housing decay (step 7) sustains building demand and real per-tick income. (2) skill_variance is STILL ~inert; expect it to matter once selection + education let skill actually differentiate outcomes. Net so far: pop, P, and ρ all move outputs; σ does not yet.

## 2026-06-04 - Step 3 (failure + punishment) differentiates regimes

Type: Finding

Builds now fail on skill (fail_prob = (1-skill)*max_fail_rate) and P is mapped continuously to consequences via death_prob=max(0,1-2P), fine_prob=max(0,2P-1), prison_prob=remainder (anchors: P=0 death, P=0.5 prison, P=1 fine). 50-tick runs at fixed seed show clean separation: P=0 permanently removes failing builders (512->486), P=0.5 imprisons then releases them (~26 imprisoned at t=10, back to 512 by t=25), P=1 only fines them (512 stays). Two notable emergent properties: (1) occupant deaths (~10) are identical across regimes because punishment targets builders not victims, so harsher regimes raise the TOTAL death toll with no safety benefit yet -- there is no feedback making punishment improve build quality. That feedback is the project's central question and needs profession switching (step 4) + skill mobility/education (later). (2) skill_variance is still ~inert because the mean failure rate depends on mean skill (0.5), not its spread; expect it to matter once selection exists. Dynamics remain front-loaded (no decay until step 7).

## 2026-06-04 - Naive economy (step 2) produces no lasting inequality

Type: Finding

With flat income + fixed house price and nothing else, the economy is inert: builders (~512) outnumber residents (~488), so every resident is housed in the first tick or two, building then stops (no decay to renew demand), and mean wealth just climbs uniformly via the flat wage. The one-time build transfer creates a small static wealth gap (builders +price, residents -price) but no ongoing dynamics. This is expected and motivates later steps: failure + punishment (step 3) renews builder scarcity, housing decay (step 7) renews demand, supply/demand pricing (step 5) makes skill/scarcity matter. Do not "fix" the flat economy in isolation — the dynamics are meant to come from those mechanisms.

## 2026-06-04 - Map is cosmetic-first, not spatially causal

Type: Decision

Agents will get an (x, y) position so the city can be drawn growing (Civ-style overhead view), but position does NOT feed back into the model: builder/resident matching, pricing, and failure rolls stay global/non-spatial. The map faithfully shows state; it causes nothing. This honors the "complexity only when the data demands it" philosophy. Trigger to revisit (i.e. make position causal — nearest-neighbor matching, location price premiums, wealth clustering / segregation): if validation shows the non-spatial housing market cannot reproduce a real metric such as affordability spread or segregation. Open thread: at N=100,000 a per-agent pixel map is expensive to redraw each tick, so the displayed world size will be capped — implementation detail, deferred.
