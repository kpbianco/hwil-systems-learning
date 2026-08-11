# Curriculum readiness audit

**Track:** HWIL Systems Architecture, Integration, and Verification

## Baseline conclusion

The repository has 24 uniquely identified modules in a six-phase, prerequisite-ordered sequence. P01 is the complete reference slice; P02-P24 are explicit non-runnable batch scaffolds. The learner flow is read → visualize → move one lever → visualize the delta → read/explain, followed by a broken case, checks, and teach-back.

Static structure and CLI behavior are verified in CI. MATLAB was not available during the 2026-08-11 baseline audit, so numerical execution, UI behavior, and instructional efficacy remain named validation gaps rather than implied evidence.

## Coverage and compounding order

### Phase 1: Mission and behavior

- **P01 — Build a Closed-Loop Timing Budget:** How do stage delay and jitter determine whether a closed loop meets its timing requirement?
- **P02 — Write a CONOPS from an Operator Goal:** What inputs, observable effects, and failure modes matter when you write a CONOPS from an Operator Goal?
- **P03 — Define Desired Physical Behavior:** What inputs, observable effects, and failure modes matter when you define Desired Physical Behavior?
- **P04 — Decompose a System into Functions:** What inputs, observable effects, and failure modes matter when you decompose a System into Functions?

### Phase 2: Allocation and interfaces

- **P05 — Allocate Functions Across Hardware and Software:** What inputs, observable effects, and failure modes matter when you allocate Functions Across Hardware and Software?
- **P06 — Trace a Command Path:** What inputs, observable effects, and failure modes matter when you trace a Command Path?
- **P07 — Trace a Measurement Data Path:** What inputs, observable effects, and failure modes matter when you trace a Measurement Data Path?
- **P08 — Write an Interface Control Contract:** What inputs, observable effects, and failure modes matter when you write an Interface Control Contract?

### Phase 3: Sequencing and synchronization

- **P09 — Design Startup and Shutdown Sequences:** What inputs, observable effects, and failure modes matter when you design Startup and Shutdown Sequences?
- **P10 — Model System States and Transitions:** What inputs, observable effects, and failure modes matter when you model System States and Transitions?
- **P11 — Budget Latency and Jitter:** What inputs, observable effects, and failure modes matter when you budget Latency and Jitter?
- **P12 — Synchronize Distributed Equipment:** What inputs, observable effects, and failure modes matter when you synchronize Distributed Equipment?

### Phase 4: Verification architecture

- **P13 — Turn Requirements into Verification Methods:** What inputs, observable effects, and failure modes matter when you turn Requirements into Verification Methods?
- **P14 — Build a Verification Cross-Reference Matrix:** What inputs, observable effects, and failure modes matter when you build a Verification Cross-Reference Matrix?
- **P15 — Choose Instrumentation and Observability Points:** What inputs, observable effects, and failure modes matter when you choose Instrumentation and Observability Points?
- **P16 — Define Acceptance Criteria:** What inputs, observable effects, and failure modes matter when you define Acceptance Criteria?

### Phase 5: Integration and faults

- **P17 — Plan an Incremental Integration Sequence:** What inputs, observable effects, and failure modes matter when you plan an Incremental Integration Sequence?
- **P18 — Contain and Propagate Faults Deliberately:** What inputs, observable effects, and failure modes matter when you contain and Propagate Faults Deliberately?
- **P19 — Perform Root-Cause Analysis from Evidence:** What inputs, observable effects, and failure modes matter when you perform Root-Cause Analysis from Evidence?
- **P20 — Control Configuration and Calibration State:** What inputs, observable effects, and failure modes matter when you control Configuration and Calibration State?

### Phase 6: Technical leadership

- **P21 — Run a Quantitative Trade Study:** What inputs, observable effects, and failure modes matter when you run a Quantitative Trade Study?
- **P22 — Build a Technical Review Package:** What inputs, observable effects, and failure modes matter when you build a Technical Review Package?
- **P23 — Manage Technical Risk:** What inputs, observable effects, and failure modes matter when you manage Technical Risk?
- **P24 — Design a Reusable Test Architecture:** What inputs, observable effects, and failure modes matter when you design a Reusable Test Architecture?

## Batch readiness gates

A scaffold may become `implemented` only when it has a deterministic model, a sectioned experiment, two independent parameter sweeps, one deliberately broken case, interactive controls, interpretation-focused tutor text, numerical checks, focused static tests, and evidence that says exactly what did and did not run.
