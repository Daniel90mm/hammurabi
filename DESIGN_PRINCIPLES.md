# Design principles — hammurabi

These are **hard rules**, not preferences. An agent proposing UI that violates them has misread this file.

## Visual language

- **Flat. No exceptions.** No soft shadows, no glassmorphism, no neumorphism, no gradients used as ambient decoration.
- **Sharp corners, or near-sharp.** Max border-radius is 2–4px (hairline). **No pill shapes, no rounded buttons, no rounded cards.** The default "friendly modern SaaS" look is rejected.
- **Real contrast.** High contrast between foreground and background. No faint grey-on-grey text. No low-contrast borders pretending to be structure.
- **Clear hierarchy through type and spacing**, not through drop-shadows and colored boxes.
- **Dense where data is dense.** Do not waste vertical space on oversized padding "for breathing room".
- **Simple GUI window is the primary visualization.** A single dead-simple window: a 2D overhead map of the city ("Hammurabi"), the statistics panel, and live charts. The **statistics/charts are the main focus**; the map is a faithful but cosmetic view of state (agent positions do not feed back into the model — see PROJECT_LOG). Keep it terminal-*like* in spirit — flat, sharp, monospace, dense — but use real pixels.
- **Batch-first, not live-first.** The default interaction is **run → results**: set seeds + run length, run to completion instantly, then read the summary, charts, and the country-comparison verdict. Watching a run tick-by-tick is an *optional* toggle. The science is comparing many runs, not watching one.

## Interaction

- **Primary actions are obvious.** Destructive actions are visually distinct, not just red text.
- **No animated transitions over ~150ms.** Instant feels better than smooth.
- **Keyboard-first where reasonable.** If the user can complete a task without reaching for the mouse, they should be able to.
- **The simulation window is the interface.** A canvas-rendered dashboard — dense, flat, keyboard-controlled where reasonable, exits cleanly. Not chrome-heavy.

## Two-persona test

Every UI decision should pass both:

- **Surface user** — can run a simulation with default params and read the dashboard in ~10 seconds without documentation.
- **Depth user** — can tweak founding parameters, run auto-calibration against a target country, and inspect raw per-tick logs without being forced through a simplified wrapper.

If a design serves only one persona, it is wrong.

## Anti-patterns (do not propose)

- Rounded pill buttons.
- Cards with drop-shadows floating on a neutral background.
- Material Design's aggressive rounding.
- Loading skeletons that animate for longer than the content takes to load.
- Modals for actions that should be inline edits.
- Tooltips carrying load-bearing information.
- Fancy animations on the map or dashboard. It should just update, once per tick.

## When you're about to deviate

Do not. Ask first. Reference the specific rule you want to break and the specific reason. "It looks nicer" is not a reason.
