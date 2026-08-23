# Lesson: Allocate Functions Across Hardware and Software

## Guiding question

What inputs, observable effects, and failure modes matter when you allocate Functions Across Hardware and Software?

## From P04 functions to P05 owners

P04 decomposed one rotary-position transaction into ten verb-object functions. It deliberately stopped before
naming components. P05 keeps the same names, inputs, outputs, and failure observables, then assigns each
function to one of two instructional execution domains:

- **software** — application-processor work, counted in work units per update;
- **hardware** — independent logic or physical endpoints, counted in allocation units.

The model fixes `Observe position` and `Update physical state` in hardware because the physical sensor and
actuation boundaries cannot disappear. It fixes `Capture intent`, `Confirm requested behavior`, and `Report
outcome` in software for this lesson. Two allocation groups remain controllable:

1. `Compute error` and `Generate correction` move together as the control group.
2. `Validate authority`, `Handle cancellation`, and `Enforce deadline` move together as supervision.

Grouping is a visible design choice for this exercise, not a universal architecture or a claim about a
particular processor, FPGA, sensor, or actuator.

## Transparent resource and acceptance equations

For function owner `owner[i]`, declared costs are summed only in that owner's domain:

```text
D_sw = sum(c_sw[i]) for owner[i] = software
D_hw = sum(c_hw[i]) for owner[i] = hardware

margin_sw = capacity_sw - D_sw
margin_hw = capacity_hw - D_hw
```

The baseline has software-owned control and hardware-owned supervision:

```text
D_sw = 2 + 6 + 8 + 4 + 2 = 22 work units/update
D_hw = 3 + 5 + 8 + 3 + 3 = 22 allocation units
```

With capacities 30 and 40, both margins are positive. Moving the control pair to hardware changes the sums
to 8 and 38. This is a resource trade, not evidence that hardware is faster. The quantities are intentionally
unit-bearing design counters; no measured utilization, task schedule, clock rate, path time, or jitter is
hidden behind them.

The complete assessment asks four distinct questions:

```text
allocation contract met = resource fit
                          AND fixed bindings valid
                          AND supervision independent of application software
                          AND scenario requirement met
```

For a nominal no-event scenario, the scenario requirement is that every function is available. In this
conservative model, a function is available only when its owner domain has enough declared capacity and,
for software, the application is not stalled. For an injected cancellation or deadline event, the named
guard must meet that same availability rule before it can emit a logical safe-hold request. That
event-containment result is not transaction success and does not prove a physical hold command was delivered
or achieved.

## Two independent owner levers

### Lever 1 — control owner

Move only `Compute error` and `Generate correction`. Software demand falls from 22 to 8 work units per
update while hardware demand rises from 22 to 38 allocation units. The original function contracts and all
other owners remain unchanged. Offload can relieve one domain while exhausting another; it is never
automatically better.

### Lever 2 — supervision owner

Reset control ownership to software. Hold application software in `stalled` state and inject cancellation,
then move only the supervision group. At the baseline hardware capacity, hardware-owned supervision remains
available because its owner both fits and sits outside the stalled domain. Software-owned supervision still
fits nominal resources but disappears with the fault, so the cancellation guard and logical safe-hold request
are unavailable. Reducing the hardware capacity below demand also removes a hardware-owned guard; fault-domain
separation cannot compensate for an infeasible owner domain.

The same check applies to an injected deadline/timeout boundary. P05 does not decide which event wins a time
tie; P04 owns its transaction precedence, P06 will own command routing, and P11 will own timing and jitter.

## Deliberately broken evidence boundary

The `resource-only` assessment asks only whether the two resource sums fit and the fixed endpoints remain in
their required domains. With software-owned supervision, stalled software, and cancellation injected, that
shortcut reports an approval because 28/30 software work units and 13/40 hardware allocation units fit.

The complete facts disagree: `Handle cancellation` is unavailable, the event is unhandled, and the full
allocation contract fails. `falseFeasible` makes the mismatch visible. The broken assumption is not that the
arithmetic is wrong; it is that nominal resource fit is sufficient allocation evidence.

## Inputs, observables, and failure modes

- Inputs: control owner, supervision owner, both declared capacities, software availability, boundary event,
  and assessment evidence mode.
- Observable effects: one owner per function, domain contributions, demand, capacity margin, utilization,
  unavailable functions, event-guard availability, containment status, complete truth, and reported decision.
- Failure modes: software, hardware, or dual capacity overflow; fixed-binding violation; application-software
  common-mode loss; unavailable cancellation or deadline guard; common-mode supervision; and false approval.
- Recovery: `model.m` has no persistent or global state, so a fresh valid call after overload, malformed input,
  or the broken case reproduces the baseline exactly.

## Common mistakes and future boundaries

- “It fits” is not enough when the function owner disappears under the fault it must handle.
- Moving computation to hardware trades resources; it does not prove speed, determinism, or safety.
- A logical safe-hold request being available is not a commanded or verified physical hold.
- Zero declared cost marks an unsupported fixed binding, not a free implementation.
- The owner map is not a command or measurement path. P06 and P07 will trace those interfaces.
- Work and allocation units are not microseconds. P11 will establish latency, scheduling, and jitter evidence.
- This two-domain model is instructional; real allocation also needs measured platform, lifecycle, security,
  maintainability, certification, and integration evidence.

## Completion standard

Explain how each owner lever changes a different system consequence, diagnose the resource-only false
approval from the missing guard, pass `run_checks.m`, and give a two-sentence teach-back: allocation mechanism
first, system consequence second.
