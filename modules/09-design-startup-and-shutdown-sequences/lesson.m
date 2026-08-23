%% P09 - Design Startup and Shutdown Sequences
% Guiding question:
% What inputs, observable effects, and failure modes matter when you design Startup and Shutdown Sequences?
%
% System goal:
% Prove that every actuator-enable and power-removal action consumed its
% prerequisites before the system changed, instead of trusting final states.

%% Read - a sequence is an ordered contract
disp('P08 established conformance and input eligibility at one interface. P09 treats those as prerequisites before actuator enable and command release.');
disp('Each action exposes an evaluated flag, a guard result, a postcondition result, and the resulting logical state.');
disp('Modeled safe-off and hazard flags are instructional logic, not physical equipment or HIL safety evidence.');

%% Predict once before the baseline
disp('Prediction: if startup eventually reaches running and shutdown eventually reaches off, can those two snapshots prove that enable and power removal occurred safely?');

%% Baseline, two isolated levers, logical events, and broken assessment
experiment;

%% Open the bounded control panel
% Reset before moving a second lever. Action position is dimensionless;
% cancellation and timeout are asserted events without elapsed timing.
interactive;
