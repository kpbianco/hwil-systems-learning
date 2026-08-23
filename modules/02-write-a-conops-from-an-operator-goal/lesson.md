# Lesson: Write a CONOPS from an Operator Goal

## Guiding question

What inputs, observable effects, and failure modes matter when you write a CONOPS from an Operator Goal?

## Operator goal and prerequisite

The operator wants to request a test-article state and know by 80 ms whether it succeeded. P01
showed that command and feedback paths consume a timing budget. This lesson uses those owned delays
inside a CONOPS: who acts, what starts the transaction, what physically changes, what the operator
can observe, when a decision is due, and how failure returns the system to safe hold.

## Mechanism before MATLAB

For one transaction,

```text
effect time       = command-path latency + physical-action duration
confirmation time = effect time + feedback-path latency
```

Command latency shifts both the physical effect and its confirmation. Feedback latency shifts only
confirmation. That difference is the core observation: an effect can occur without becoming
operator knowledge. Success therefore means confirmed before the decision deadline, not merely
“the hardware moved.”

Cancellation has safety priority if it ties another event. Missing or late feedback causes a timeout
to safe hold. Recovery is a new transaction after feedback and readiness are re-established; hidden
state is not carried from the failed attempt.

## Inputs, observables, and failure modes

- Fixed preconditions outside the timing model: test-article readiness and a usable safe-hold response.
- Model inputs: operator command timing, command latency, action duration, feedback latency,
  feedback availability, response deadline, and cancellation time.
- Observable effects: command receipt, physical-effect time, feedback arrival, decision state,
  schedule margin, and whether safe hold was commanded.
- Failure modes: cancellation before completion, feedback arriving after the deadline, and feedback
  being absent even though the physical goal was reached.

## Common mistakes

- An end state is not an operator-observable success criterion.
- “The operator will notice” is not a feedback path, unit, threshold, or deadline.
- A timeout without a named safe response leaves the terminal behavior undefined.
- Recovery must recheck preconditions; it must not assume the failed transaction left trustworthy state.

## Completion standard

Write a short CONOPS that names the actor, trigger, readiness precondition, action, physical effect,
observable confirmation, response deadline, cancellation and timeout behavior, and recovery entry
condition. Explain why the broken feedback case cannot be declared successful, then pass
`run_checks.m`.
