%% P10 - Model System States and Transitions
% Guiding question:
% What inputs, observable effects, and failure modes matter when you model System States and Transitions?
%
% System goal:
% Explain every state change with a source state, event, legal edge, guard,
% priority rule, and observed destination instead of trusting a final label.

%% Read - turn P09's fixed sequence into explicit transition rules
disp('P09 showed one ordered startup/shutdown proof. P10 consumes its composite startup and safe-off proof facts as guards without executing P09.');
disp('A state label summarizes history; a transition record preserves the event, source, requested destination, guard, priority, and observed result.');
disp('OFF and SAFE-HOLD are modeled logical states, not physical equipment or personnel-safety evidence.');

%% Predict once, then run the baseline and controlled cases
% experiment.m owns the single pre-baseline prediction so this launch path
% and a direct experiment run behave identically.
experiment;

%% Open the bounded control panel
% Reset before moving a second lever. Confirmation and event steps are
% dimensionless observations; they do not measure elapsed time.
interactive;
