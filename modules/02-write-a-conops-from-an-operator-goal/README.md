# P02 — Write a CONOPS from an Operator Goal

**Track:** HWIL Systems Architecture, Integration, and Verification  
**Phase 1:** Mission and behavior  
**Status:** implemented

## Guiding question

What inputs, observable effects, and failure modes matter when you write a CONOPS from an Operator Goal?

## Operational mental model

The operator goal is: request a test-article state and know by a response deadline whether the
request succeeded. A useful CONOPS makes the transaction observable from the operator's seat:

1. a ready test article receives the operator command;
2. the command path delivers it after a bounded latency;
3. the test article reaches the requested physical state;
4. feedback makes that effect observable;
5. confirmation before the deadline means success;
6. cancellation or missing/late feedback commands a safe hold;
7. recovery rechecks readiness and starts a fresh transaction.

The governing event times are visible rather than hidden in a simulation:

```text
t_effect  = t_command_latency + t_action
t_confirm = t_effect + t_feedback_latency
```

P01 established why path latency needs an owner and a deadline. P02 uses those timing inputs inside
an operational story and adds the trigger, physical effect, observable confirmation, failure
response, and recovery path that an operator needs.

Readiness and the availability of a safe-hold response are fixed CONOPS preconditions in this
bounded transaction model. They are rechecked before recovery but are not represented as timing levers.

## Required learning flow

1. Read the operator goal and predict whether physical completion alone is enough.
2. Run the deterministic baseline and inspect the event timeline and decision criteria.
3. Sweep command-path latency while holding feedback latency fixed.
4. Reset, then sweep feedback latency while holding the physical-effect time fixed.
5. Explain each changed view from the event equations.
6. Remove feedback deliberately and diagnose the violated observability assumption.
7. Run the executable checks and give a short CONOPS teach-back.

## Implementation and dependency boundary

The module separates deterministic calculations (`model.m`) from plotted experiments
(`experiment.m`), bounded controls (`interactive.m`), tutor text, and executable checks. It uses
base MATLAB only, performs no external I/O, and generates no random samples. P01 is the prerequisite;
P03 will develop the physical behavior itself rather than this operator transaction.

Static repository checks do not constitute MATLAB-runtime, UI, numerical-fidelity, bench, HIL, or
field validation.
