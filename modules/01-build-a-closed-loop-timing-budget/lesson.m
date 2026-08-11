%% P01 - Build a Closed-Loop Timing Budget
% Guiding question:
% How do stage delay and jitter determine whether a closed loop meets its timing requirement?
%
% Mental model:
% A closed-loop HWIL path is a chain of physical and computational delays. The total latency matters, but its distribution and where uncertainty enters determine whether the loop is trustworthy.

%% Read the baseline lesson
disp('How do stage delay and jitter determine whether a closed loop meets its timing requirement?');
disp('A closed-loop HWIL path is a chain of physical and computational delays. The total latency matters, but its distribution and where uncertainty enters determine whether the loop is trustworthy.');

%% Run the deterministic experiment
experiment;

%% Open the live lever panel
% Move one control at a time and connect the visible change to the model.
interactive;
