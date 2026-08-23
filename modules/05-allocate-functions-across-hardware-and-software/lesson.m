%% P05 - Allocate Functions Across Hardware and Software
% Guiding question:
% What inputs, observable effects, and failure modes matter when you allocate Functions Across Hardware and Software?
%
% System goal:
% Preserve P04's ten function contracts while assigning one owner to each,
% budgeting both domains, and containing an application-software stall.

%% Read - move from functional contracts to execution-domain ownership
disp('P04 established what every function consumes, produces, and can get wrong. P05 decides which domain owns each function without changing those contracts.');
disp('A resource-feasible allocation is incomplete when cancellation and deadline supervision share the application-software fault they must contain.');

%% Predict once before the baseline
disp('Prediction: if both resource totals fit but application software stalls, does software-owned cancellation supervision remain available?');

%% Baseline, isolated levers, and deliberately broken assessment
experiment;

%% Open the bounded control panel
% Reset before moving a second owner lever so each cause stays isolated.
interactive;
