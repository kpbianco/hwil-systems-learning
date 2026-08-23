%% P04 - Decompose a System into Functions
% Guiding question:
% What inputs, observable effects, and failure modes matter when you decompose a System into Functions?
%
% System goal:
% Preserve the P03 rotary-position intent while turning one system outcome
% into functions with explicit inputs, outputs, and failure observables.

%% Read - move from desired behavior to functional ownership
disp('P03 defined valid rotary behavior. P04 asks which functions must transform the request into motion and trustworthy completion evidence.');
disp('Name what each function consumes and produces before deciding in P05 whether hardware or software performs it.');

%% Predict once before the baseline
disp('Prediction: if a local monitor reports success at 45 deg after a 70 deg request, which missing function could make that report untrustworthy?');

%% Baseline, isolated levers, and deliberately broken function chain
experiment;

%% Open the bounded control panel
% Reset before moving a second lever so each cause stays isolated.
interactive;
