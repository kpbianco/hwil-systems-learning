%% P02 - Write a CONOPS from an Operator Goal
close all; clc;
disp('Operator goal: request a test-article state and know by 80 ms whether it succeeded.');
disp('Failure response: cancellation or missing/late feedback commands safe hold.');

%% Baseline - read the event sequence before moving a lever
baseline = model(12,25,18,80,true,Inf);
eventLabels = {'Command sent','Command received','Effect reached', ...
    'Feedback arrives','Decision deadline','Terminal decision'};
criterionLabels = {'Physical effect','Feedback observed','Operator goal met','Safe hold'};

figure('Name','P02 baseline operator transaction');
subplot(2,1,1);
bar(1:numel(baseline.eventTimesMs),baseline.eventTimesMs);
xticks(1:numel(eventLabels)); xticklabels(eventLabels); xtickangle(18);
ylabel('Elapsed time from operator request (ms)'); grid on;
title(sprintf('Baseline event timeline: terminal state = %s',baseline.terminalState));
subplot(2,1,2);
bar(1:numel(baseline.criteria),double(baseline.criteria));
xticks(1:numel(criterionLabels)); xticklabels(criterionLabels); xtickangle(18);
ylabel('Observed state (0 = no, 1 = yes)'); ylim([0 1.2]); grid on;
title(sprintf('Operator decision criteria; planned margin = %.1f ms',baseline.plannedScheduleMarginMs));

fprintf('Baseline: effect %.1f ms, feedback %.1f ms, deadline %.1f ms, margin %.1f ms.\n', ...
    baseline.plannedEffectReachedMs,baseline.actualFeedbackArrivalMs, ...
    baseline.decisionDeadlineMs,baseline.plannedScheduleMarginMs);
assert(baseline.plannedEffectReachedMs == 12 + 25,'Independent effect-time calculation failed.');
assert(baseline.actualFeedbackArrivalMs == 12 + 25 + 18,'Independent feedback-time calculation failed.');

%% Sweep 1 - command-path latency moves the physical and observed events together
commandSweepMs = [0 12 35 55];
effectByCommandMs = zeros(size(commandSweepMs));
feedbackByCommandMs = zeros(size(commandSweepMs));
goalByCommand = false(size(commandSweepMs));
for k = 1:numel(commandSweepMs)
    trial = model(commandSweepMs(k),25,18,80,true,Inf);
    effectByCommandMs(k) = trial.plannedEffectReachedMs;
    feedbackByCommandMs(k) = trial.plannedFeedbackArrivalMs;
    goalByCommand(k) = trial.operatorGoalMet;
    fprintf('Command latency %.1f ms -> effect %.1f ms, feedback %.1f ms, goal met %d.\n', ...
        commandSweepMs(k),trial.plannedEffectReachedMs,trial.plannedFeedbackArrivalMs,trial.operatorGoalMet);
end
figure('Name','P02 command-latency sweep');
plot(commandSweepMs,effectByCommandMs,'o-','LineWidth',1.4,'DisplayName','Planned physical effect'); hold on;
plot(commandSweepMs,feedbackByCommandMs,'s-','LineWidth',1.4,'DisplayName','Planned feedback arrival');
yline(80,'--','Decision deadline'); hold off; grid on;
xlabel('Command-path latency (ms)'); ylabel('Event time from request (ms)');
title('Lever 1: command latency shifts effect and confirmation together'); legend('Location','best');

%% Read and explain lever 1 before advancing
disp('Mechanism after lever 1: command latency is upstream, so it shifts both the effect and feedback timestamps one-for-one.');

%% Sweep 2 - feedback latency changes observability without moving the physical effect
feedbackSweepMs = [0 18 40 55];
effectByFeedbackMs = zeros(size(feedbackSweepMs));
feedbackArrivalSweepMs = zeros(size(feedbackSweepMs));
goalByFeedback = false(size(feedbackSweepMs));
for k = 1:numel(feedbackSweepMs)
    trial = model(12,25,feedbackSweepMs(k),80,true,Inf);
    effectByFeedbackMs(k) = trial.plannedEffectReachedMs;
    feedbackArrivalSweepMs(k) = trial.plannedFeedbackArrivalMs;
    goalByFeedback(k) = trial.operatorGoalMet;
    fprintf('Feedback latency %.1f ms -> effect %.1f ms, feedback %.1f ms, goal met %d.\n', ...
        feedbackSweepMs(k),trial.plannedEffectReachedMs,trial.plannedFeedbackArrivalMs,trial.operatorGoalMet);
end
figure('Name','P02 feedback-latency sweep');
plot(feedbackSweepMs,effectByFeedbackMs,'o-','LineWidth',1.4,'DisplayName','Planned physical effect'); hold on;
plot(feedbackSweepMs,feedbackArrivalSweepMs,'s-','LineWidth',1.4,'DisplayName','Planned feedback arrival');
yline(80,'--','Decision deadline'); hold off; grid on;
xlabel('Feedback-path latency (ms)'); ylabel('Event time from request (ms)');
title('Lever 2: feedback latency moves confirmation, not the physical effect'); legend('Location','best');
assert(all(effectByFeedbackMs == effectByFeedbackMs(1)), ...
    'Feedback-only sweep must not move the physical effect.');

%% Read and explain lever 2 before breaking an assumption
disp('Mechanism after lever 2: feedback latency is downstream of the effect, so it changes operator knowledge without changing physical completion.');

%% Broken case - an end-state-only CONOPS omits the observable confirmation
broken = model(12,25,18,80,false,Inf);
figure('Name','P02 broken observability case');
bar(1:3,double([broken.physicalGoalReached broken.operatorGoalMet broken.safeHoldCommanded]));
xticks(1:3); xticklabels({'Physical effect','Operator-confirmed success','Safe hold'});
ylabel('Observed state (0 = no, 1 = yes)'); ylim([0 1.2]); grid on;
title('Broken assumption: physical completion is not observable to the operator');
fprintf('Broken case: effect reached = %d, operator goal met = %d, terminal = %s at %.1f ms.\n', ...
    broken.physicalGoalReached,broken.operatorGoalMet,broken.terminalState,broken.terminalTimeMs);
assert(broken.physicalGoalReached && ~broken.operatorGoalMet && broken.safeHoldCommanded, ...
    'Feedback loss must expose latent physical completion and command safe hold.');

%% Mechanism synthesis
disp('Synthesis: command latency moves both the effect and its confirmation.');
disp('Feedback latency moves only what the operator can observe. A CONOPS must name both paths, the deadline, and the safe response.');
