%% P08 - Write an Interface Control Contract
% Guiding question:
% What inputs, observable effects, and failure modes matter when you write an Interface Control Contract?
%
% System goal:
% Make independently owned producer and receiver assumptions explicit before
% a plausible number can be treated as a valid P06 scalar input.

%% Read - replace an unnamed handoff with an executable promise
disp('P06 traced command ownership; P07 traced measurement value plus quality. P08 specifies what a producer and receiver must agree on without changing either prerequisite interface.');
disp('The contract names identity, version, length, units, range, sequence, quality encoding, integrity, and rejection behavior.');
disp('Logical acceptance is not wire transfer, protocol execution, P06 consumption, physical motion, or safety evidence.');

%% Predict once before the baseline
disp('Prediction: if 0.524 arrives where degrees are required, is the value safe to accept merely because it lies inside +/-180?');

%% Baseline, isolated levers, guarded terminals, and broken validation
experiment;

%% Open the bounded control panel
% Reset before moving a second lever so the visible consequence belongs to
% one changed contract input.
interactive;
