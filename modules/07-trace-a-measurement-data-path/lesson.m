%% P07 - Trace a Measurement Data Path
% Guiding question:
% What inputs, observable effects, and failure modes matter when you trace a Measurement Data Path?
%
% System goal:
% Turn P05's hardware-owned observation into a quality-gated scalar that is
% eligible for P06's unchanged observedAngleDeg input.

%% Read - follow value and validity without confusing them
disp('P05 fixed Observe position in hardware. P07 traces voltage, ADC count, calibrated degrees, and quality to a P07-local qualified-control intake.');
disp('P06 accepts only the scalar observedAngleDeg. P07 uses p06InputEligible to gate that unchanged input and does not add a validity input to P06.');
disp('Model truth is a comparison reference, not a signal available to the path; local receipt is neither P06 consumption nor physical sensing, electrical delivery, or control response.');

%% Predict once before the baseline
disp('Prediction: if a finite stale value reaches the P07 qualified intake, should it become eligible for P06''s scalar input?');

%% Baseline, isolated levers, acquisition guards, and broken evidence
experiment;

%% Open the bounded control panel
% Reset before moving a second lever so value, reachability, and quality
% consequences remain attributable to one changed input.
interactive;
