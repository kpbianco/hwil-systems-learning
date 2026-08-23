%% P11 - Budget Latency and Jitter
% Guiding question:
% What inputs, observable effects, and failure modes matter when you budget Latency and Jitter?
%
% System goal:
% Allocate elapsed milliseconds to owned stages, retain bounded variation,
% and explain whether a P10-authorized repeated cycle can meet its deadline.

%% Read - add elapsed time to P10 transition evidence
disp('P10 proved logical source, edge, guard, priority, and observed destination facts without assigning them elapsed-time units.');
disp('P11 consumes one P10 activation-proof adapter, then budgets four timed stages on one ideal time base.');
disp('A timing interruption requests a P10 SAFE-HOLD handoff; it is not evidence that SAFE-HOLD or rollback occurred.');

%% Predict once, then run the baseline and controlled cases
% experiment.m owns the single pre-baseline prediction so a direct run and
% the public launch path ask the same one question.
experiment;

%% Open the bounded control panel
% Reset before moving a second lever. Every elapsed quantity is in ms;
% scheduled cycle is a dimensionless index, not a distributed clock.
interactive;

%% Complete checks and teach back
% Run run_checks, answer checks.md one prompt at a time, then give the
% mechanism-first two-sentence teach-back before recording completion.
