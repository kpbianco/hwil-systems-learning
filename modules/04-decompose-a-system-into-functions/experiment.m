%% P04 - Decompose a System into Functions
close all; clc;
disp('System outcome: preserve a rotary-position request, produce the motion, confirm it, and report one trustworthy result.');
disp('A functional decomposition is complete only when every transformation has named inputs, outputs, and detectable failures.');

%% Baseline - inspect the system outcome before opening the functions
baseline = model(30,0.35,3,45,0.5,1000,Inf,'complete');
figure('Name','P04 baseline system outcome');
plot(baseline.timeMs,baseline.positionDeg,'LineWidth',1.5, ...
    'DisplayName','Observed position'); hold on;
yline(baseline.requestedTargetDeg,'--','Requested position');
yline(baseline.requestedTargetDeg + baseline.inputs.toleranceDeg,':','Tolerance');
yline(baseline.requestedTargetDeg - baseline.inputs.toleranceDeg,':');
xline(baseline.reportTimeMs,'--','Outcome reported'); hold off; grid on;
xlabel('Elapsed functional time (ms)'); ylabel('Rotary position (deg)');
xlim([0 600]);
title(sprintf('Baseline: trusted completion in %.0f ms with %.3f deg request error', ...
    baseline.reportTimeMs,baseline.requestErrorAtReportDeg));
legend('Location','best');

expectedFirstEntryMs = ceil(log(0.5/30)/log(1 - 0.35))*20;
expectedReportMs = expectedFirstEntryMs + (3 - 1)*20;
assert(baseline.firstWithinRequestToleranceMs == expectedFirstEntryMs && ...
    baseline.reportTimeMs == expectedReportMs && baseline.requirementsMet, ...
    'The baseline must agree with the independent geometric-error calculation.');
fprintf(['Baseline metrics: request %.1f deg, first in tolerance %.0f ms, ' ...
    'report %.0f ms, error at report %.3f deg, functions executed %d/%d.\n'], ...
    baseline.requestedTargetDeg,baseline.firstWithinRequestToleranceMs, ...
    baseline.reportTimeMs,baseline.requestErrorAtReportDeg, ...
    baseline.executedFunctionCount,baseline.functionCount);

%% Complementary baseline view - open the functional execution sequence
figure('Name','P04 baseline function activation');
imagesc(baseline.timeMs,1:baseline.functionCount,double(baseline.functionActivation'));
colormap([1 1 1; 0.10 0.45 0.75]); caxis([0 1]);
set(gca,'YTick',1:baseline.functionCount,'YTickLabel',baseline.functionNames);
xlabel('Elapsed functional time (ms)'); ylabel('Named system function');
xlim([0 300]);
title('Complementary view: functions transform intent into evidence');

%% Sweep 1 - response fraction changes the correction function only
responseSweep = [0.20 0.35 0.50 0.70];
reportByResponseMs = zeros(size(responseSweep));
firstEntryByResponseMs = zeros(size(responseSweep));
for k = 1:numel(responseSweep)
    trial = model(30,responseSweep(k),3,45,0.5,1000,Inf,'complete');
    reportByResponseMs(k) = trial.reportTimeMs;
    firstEntryByResponseMs(k) = trial.firstWithinRequestToleranceMs;
    fprintf('Response fraction %.2f -> first entry %.0f ms, trusted report %.0f ms.\n', ...
        responseSweep(k),trial.firstWithinRequestToleranceMs,trial.reportTimeMs);
end
figure('Name','P04 correction-response sweep');
plot(responseSweep,firstEntryByResponseMs,'o-','LineWidth',1.4, ...
    'DisplayName','First position in tolerance'); hold on;
plot(responseSweep,reportByResponseMs,'s-','LineWidth',1.4, ...
    'DisplayName','Trusted outcome report'); hold off; grid on;
xlabel('Correction response fraction per update (-)'); ylabel('Elapsed time (ms)');
title('Lever 1: stronger bounded correction closes error in fewer updates');
legend('Location','best');
assert(all(diff(reportByResponseMs) < 0), ...
    'The selected response sweep must reduce completion time monotonically.');

%% Read and explain lever 1 before advancing
disp('Mechanism after lever 1: Generate correction converts signed error into a larger fraction of remaining motion, so the same tolerance is reached in fewer 20 ms updates.');

%% Sweep 2 - confirmation depth changes evidence, not the correction law
confirmationSweep = [1 3 5 8];
reportByConfirmationMs = zeros(size(confirmationSweep));
firstEntryByConfirmationMs = zeros(size(confirmationSweep));
for k = 1:numel(confirmationSweep)
    trial = model(30,0.35,confirmationSweep(k),45,0.5,1000,Inf,'complete');
    reportByConfirmationMs(k) = trial.reportTimeMs;
    firstEntryByConfirmationMs(k) = trial.firstWithinRequestToleranceMs;
    fprintf('Confirmation depth %.0f samples -> first entry %.0f ms, report %.0f ms.\n', ...
        confirmationSweep(k),trial.firstWithinRequestToleranceMs,trial.reportTimeMs);
end
figure('Name','P04 confirmation-depth sweep');
plot(confirmationSweep,reportByConfirmationMs,'o-','LineWidth',1.4); grid on;
xlabel('Required consecutive observations (samples)'); ylabel('Outcome report time (ms)');
title('Lever 2: deeper evidence delays the report by one update per added sample');
assert(all(firstEntryByConfirmationMs == firstEntryByConfirmationMs(1)) && ...
    all(diff(reportByConfirmationMs) == baseline.sampleTimeMs*diff(confirmationSweep)), ...
    'Confirmation depth must change evidence latency without moving first tolerance entry.');

%% Read and explain lever 2 before breaking an assumption
disp('Mechanism after lever 2: Confirm requested behavior waits for consecutive observations; it does not change the target, correction fraction, or first tolerance entry.');

%% Broken case - validation is omitted and local success loses operator intent
rejected = model(70,0.35,3,45,0.5,1000,Inf,'complete');
broken = model(70,0.35,3,45,0.5,1000,Inf,'bypass-validation');
figure('Name','P04 broken functional decomposition');
plot(rejected.timeMs,rejected.positionDeg,'LineWidth',1.5, ...
    'DisplayName','Complete architecture: reject'); hold on;
plot(broken.timeMs,broken.positionDeg,'LineWidth',1.5, ...
    'DisplayName','Broken architecture: move to clipped target');
yline(broken.requestedTargetDeg,'--','Requested 70 deg');
yline(broken.effectiveTargetDeg,':','Local target 45 deg');
xline(broken.reportTimeMs,'--','False success reported'); hold off; grid on;
xlabel('Elapsed functional time (ms)'); ylabel('Rotary position (deg)');
xlim([0 600]);
title('Broken assumption: every request is validated and intent stays end to end');
legend('Location','best');
fprintf(['Broken metrics: report %s at %.0f ms, local error %.3f deg, ' ...
    'request error %.3f deg, failure %s.\n'],broken.status,broken.reportTimeMs, ...
    broken.monitorErrorAtReportDeg,broken.requestErrorAtReportDeg,broken.failureMode);
assert(strcmp(rejected.status,'rejected') && ~rejected.physicalMotionOccurred && ...
    broken.reportedSuccess && broken.falseSuccess && ~broken.requirementsMet && ...
    ~any(broken.functionActivation(:,2)), ...
    'Omitting validation must create a recognizable false-success symptom.');

%% Recovery and mechanism synthesis
recovered = model(30,0.35,3,45,0.5,1000,Inf,'complete');
assert(isequaln(recovered,baseline), ...
    'A fresh complete decomposition must recover without hidden state.');
disp('Synthesis: decompose by preserving intent across named transformations, assigning observable contracts, and giving rejection, cancellation, timeout, and reporting explicit owners.');
disp('The function list is independent of later hardware/software allocation; a plausible local result is not trustworthy when a required function or end-to-end input is missing.');
