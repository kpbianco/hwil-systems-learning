%% P02 - Write a CONOPS from an Operator Goal
% Guiding question:
% What inputs, observable effects, and failure modes matter when you write a CONOPS from an Operator Goal?
%
% Operator goal:
% Request a test-article state and know by a response deadline whether the
% request succeeded. Cancellation or missing feedback must end in safe hold.

%% Read - connect the operator story to the P01 timing budget
disp('P01 assigned latency and deadline ownership. P02 turns those timing inputs into an operator-visible transaction.');
disp('A CONOPS needs an actor, trigger, precondition, action, physical effect, observable confirmation, deadline, failure response, and recovery.');

%% Predict once before the baseline
disp('Prediction: if the test article reaches the requested state but feedback is absent, should the operator declare success?');

%% Baseline, isolated levers, and deliberately broken observability
experiment;

%% Open the bounded control panel
% Move one control at a time. Use Reset baseline before moving a second lever.
interactive;
