%% P06 - Trace a Command Path
% Guiding question:
% What inputs, observable effects, and failure modes matter when you trace a Command Path?
%
% System goal:
% Carry P04's function contracts and P05's owners into an explicit logical
% route, then distinguish local output from downstream endpoint receipt.

%% Read - turn allocated functions into observable handoffs
disp('P04 defined the functions and P05 allocated their owners. P06 traces which owner receives which unit-bearing value without reopening those decisions.');
disp('The hardware-side input latch is the endpoint: logical receipt is not physical motion, achieved safe hold, or a measurement path.');

%% Predict once before the baseline
disp('Prediction: if Generate correction produces a valid local value but the final boundary is open, has the actuator input latch received the command?');

%% Baseline, isolated levers, guarded terminals, and broken evidence
experiment;

%% Open the bounded control panel
% Reset before moving a second lever so each path consequence stays isolated.
interactive;
