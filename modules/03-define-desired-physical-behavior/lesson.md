# Lesson: Define Desired Physical Behavior

## Guiding question

What inputs, observable effects, and failure modes matter when you define Desired Physical Behavior?

## From the P02 transaction to a physical contract

P02 said that an operator requests a test-article state and needs observable confirmation by a deadline.
P03 opens the previously opaque physical action. Time zero here is the instant the accepted physical command
enters the response, so command-path and feedback-path delays remain owned by P02 rather than being counted twice.

The concrete system is a rotary test article starting at zero degrees. The desired behavior must name:

- the requested angle and valid command-authority envelope, in degrees;
- the observed position, in degrees, and velocity, in degrees per second;
- a position tolerance, velocity tolerance, and response deadline, in milliseconds;
- failure when the request is outside the envelope or motion does not remain in both bands by the deadline.

## Transparent physical model

The applied target is the requested command clipped to declared position-command authority. From zero
initial state, the response follows

```text
theta'' + 2*zeta*omega_n*theta' + omega_n^2*theta = omega_n^2*u_applied
omega_n = 2*pi*f_n
```

Here `theta` is position in degrees, `theta'` is velocity in degrees per second, `f_n` is natural
frequency in hertz, and damping ratio `zeta` is dimensionless. `model.m` evaluates the analytic
under-damped or critically damped response directly with base MATLAB; it does not call a controls toolbox.

Success is sustained entry, not first crossing:

```text
abs(request - position) <= position tolerance
abs(velocity)           <= velocity tolerance
```

Both statements must remain true for the rest of the modeled horizon, and their first sustained sample
must occur at or before the deadline. A ten-second fixed trace provides post-deadline observation, and an
analytic decay envelope must also prove that neither tolerance can be violated after the trace. An exact
deadline tie passes. Metrics at a non-grid deadline name the latest two-millisecond sample at or before it.

## What each lever means

Command magnitude is an operator input. In the linear valid envelope it scales position and velocity
while normalized overshoot stays constant. Damping ratio is a design lever: it changes how strongly
oscillatory motion is suppressed, so overshoot and sustained settling change without changing the request.
Natural frequency changes response rate; it is available in the interactive panel but held fixed during
the two required sweeps so each plotted cause remains isolated.

## Deliberately broken input envelope

The broken case requests 70 degrees with only 45 degrees of declared position-command authority. The
applied target is therefore 45 degrees. The article can settle around that effective target before the
deadline while retaining about 25 degrees of request error. “It moved and stopped” is not the specified
behavior: an out-of-envelope request must be rejected or reported, not silently called successful.

This is a position-command limit, not a torque-saturation or hard-stop model. Cancellation remains part
of the upstream P02 transaction and is intentionally not invented as a P03 plant-response input.

## Common mistakes

- “Move to position” omits direction, valid inputs, units, tolerances, and time.
- A first tolerance crossing is not settling if later oscillation leaves the band.
- Position alone can look acceptable while velocity shows the article is still moving.
- Smaller overshoot does not mean every response metric always improves monotonically.
- A clipped target is not the requested target, even when the resulting motion looks smooth.

## Completion standard

Explain how command magnitude and damping change different observables, diagnose the broken authority
case from requested versus effective target and steady-state error, pass `run_checks.m`, and give a
two-sentence teach-back: mechanism first, operational consequence second.
