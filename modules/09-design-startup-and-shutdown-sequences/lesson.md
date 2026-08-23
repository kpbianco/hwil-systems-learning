# P09 lesson: Design Startup and Shutdown Sequences

## Guiding question

What inputs, observable effects, and failure modes matter when you design Startup and Shutdown Sequences?

## Compounds on P08

P08 showed that an interface record can be conformant while its data remains ineligible for use. P09 turns
those two facts into startup prerequisites: qualify the interface only after controller boot, and enable the
actuator or release commands only when input is eligible. The lesson consumes the facts without executing P08
or changing its record.

## Tutor opening

Use one prediction before the baseline:

> If the intermediate running snapshot and final off snapshot both look correct, do they prove the actions
> happened in a safe order?

Show the baseline startup guard plot first. Ask which fact makes actuator enable valid at position 5. Then show
the shutdown guard plot and ask which observation separates “disable requested” from “quiescence confirmed.”
Only after those answers should you show the full state trace.

## Mechanism before MATLAB

Treat each action as a small contract:

```text
guard facts ── action ── observable postcondition
```

An evaluated step passes only when both sides pass. A lifecycle passes only when every startup step passes,
the running configuration is reached, every shutdown step passes, and the safe-off configuration is reached.
The equation explains the bars; it is not an entrance requirement.

The state trace has seven Boolean facts: power, controller, P08 qualification, actuator enable, command
inhibit, safe command, and quiescence. “Safe” means only that these modeled facts meet this lesson's rule.

## Controlled transition 1 — startup enable

Reset to the baseline, move only `startupEnablePosition`, and show one changed plot. Positions 1–4 request
enable before at least one prerequisite. Position 5 is the limiting valid case. Later startup actions still make
the running snapshot look correct, which is exactly why the transient guard is retained.

Ask: “Which specific fact is missing at the position you chose?” Connect the answer to the visible prerequisite
bar, not to MATLAB indexing syntax.

## Controlled transition 2 — shutdown power removal

Reset startup to 5. Move only `shutdownPowerOffPosition`. Positions 1–5 omit, in order, one or more of command
inhibit, safe command, actuator disabled, quiescence confirmed, and interface closed. Position 6 is the limiting
valid case.

Ask: “Why is actuator disabled different from quiescence confirmed?” The direct answer is that one is a
commanded/postcondition state and the other is a separately observed release condition. Neither source code nor
a final off snapshot proves physical energy is gone.

## Cancellation, timeout, and rollback

Inject cancellation, then timeout, one at a time. Each is a logical event at a fixed checkpoint after action 3;
neither carries elapsed units. Remaining startup facts stay unevaluated, shutdown stays isolated, and, without
an injected fault, a fixed five-action compensation reaches modeled safe hold. In the injected tie,
cancellation has reporting precedence.

The nominal shutdown trace and final state stay unavailable (`NaN`) after an event. Read the separate rollback
trace for compensation state; never relabel a rollback result as completed shutdown evidence.

Then combine an event with a fault. If an early-enabled actuator cannot be disabled, or quiescence cannot be
confirmed, compensation still runs its bounded trace but safe hold remains false. Read the rollback guard,
postcondition, hazard, and failure output; do not infer success merely because rollback was attempted.

Ask: “Which facts are intentionally unavailable after the event?” Correct any claim that false means failed:
for skipped steps, the separate `evaluated` flag is false and the state rows are `NaN`, so no guard result is
being claimed.

## Broken case — snapshot-only approval

Put both positions at 1 and select `final-state-only`. The final running and safe-off snapshots become true, so
the broken assessor reports success. The strict result stays false because the factual traces retain early
enable and early power removal. This is a false approval, not a different simulated sequence.

Ask the learner to name the discarded evidence. The intended answer is the ordered precondition and
postcondition results, not “the code used the wrong if statement.”

## Negative cases

- Nonconformant P08 input prevents interface qualification.
- Conformant but ineligible P08 data prevents enable/release.
- `actuator-stuck-on` makes the disable postcondition fail.
- `quiescence-not-confirmed` keeps power-removal prerequisites incomplete.
- Cancellation and timeout lead to bounded rollback rather than nominal shutdown evaluation; an injected fault
  can make that rollback explicitly incomplete.
- Malformed or inconsistent inputs fail before any trace is returned.

## Common misconceptions

- **“The final off state proves shutdown was safe.”** No. Later actions can repair the final state after an
  unsafe transient.
- **“Disable commanded means quiescent.”** No. They are separate observable facts in the model.
- **“Timeout proves a timing budget failed.”** No. It is an asserted event with no milliseconds; P11 owns
  latency and jitter.
- **“The array order synchronizes equipment.”** No. P12 owns distributed time and synchronization.
- **“This is a reusable state machine.”** No. P10 owns general states/transitions; P09 uses one fixed trace.
- **“The safe flag proves hardware safety.”** No. No MATLAB runtime, UI review, protocol peer, bench, HIL, or
  field environment was exercised by static repository validation.

## Interpretation and teach-back

Use `checks.md` one question at a time after `run_checks.m`. A satisfactory two-sentence teach-back names the
ordered guard/postcondition mechanism first and then explains one consequence: early actuator enable, early
power removal, or false final-state approval.
