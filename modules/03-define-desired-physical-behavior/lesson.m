%% P03 - Define Desired Physical Behavior
% Guiding question:
% What inputs, observable effects, and failure modes matter when you define Desired Physical Behavior?
%
% Physical goal:
% Turn the P02 requested test-article state into a quantitative rotary
% behavior envelope: valid input, observable motion, tolerance, and time.

%% Read - replace an opaque action with measurable physical behavior
disp('P02 named the actor, transaction, physical effect, confirmation, deadline, and safe response.');
disp('P03 opens the physical effect: a position request is successful only inside its command envelope and after position and velocity stay in band by the deadline.');

%% Predict once before the baseline
disp('Prediction: if the article stops at 45 deg after a 70 deg request, did it achieve the desired behavior?');

%% Baseline, isolated levers, and deliberately broken input envelope
experiment;

%% Open the bounded control panel
% Move one control at a time. Use Reset baseline before moving a second lever.
interactive;
