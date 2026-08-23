%% P03 - Define Desired Physical Behavior
close all; clc;
disp('Physical goal: command a rotary test article and state how position, motion, limits, and time define success.');
disp('The response is desired only when the request is inside its input envelope and settles inside both position and velocity bands by the deadline.');

%% Baseline - read the requested and observed position before moving a lever
baseline = model(30,1.5,0.7,45,0.5,2,1200);
figure('Name','P03 baseline position behavior');
plot(baseline.timeMs,baseline.positionDeg,'LineWidth',1.5,'DisplayName','Observed position'); hold on;
yline(baseline.requestedCommandDeg,'--','Requested position');
yline(baseline.requestedCommandDeg + baseline.inputs.positionToleranceDeg,':','Tolerance');
yline(baseline.requestedCommandDeg - baseline.inputs.positionToleranceDeg,':');
xline(baseline.inputs.deadlineMs,'--','Response deadline'); hold off; grid on;
xlabel('Time from accepted command (ms)'); ylabel('Rotary position (deg)');
xlim([0 3000]);
title(sprintf('Baseline position: overshoot %.2f%%, settling %.0f ms', ...
    baseline.overshootPercent,baseline.settlingTimeMs));
legend('Location','best');

%% Complementary baseline view - motion must also be quiet before success
figure('Name','P03 baseline velocity behavior');
plot(baseline.timeMs,baseline.velocityDegPerSec,'LineWidth',1.5); hold on;
yline(baseline.inputs.velocityToleranceDegPerSec,':','Velocity tolerance');
yline(-baseline.inputs.velocityToleranceDegPerSec,':');
xline(baseline.inputs.deadlineMs,'--','Response deadline'); hold off; grid on;
xlabel('Time from accepted command (ms)'); ylabel('Rotary velocity (deg/s)');
xlim([0 3000]);
title(sprintf('Complementary view: peak speed %.1f deg/s, behavior met = %d', ...
    baseline.peakVelocityMagnitudeDegPerSec,baseline.requirementsMet));

expectedOvershootPercent = 100*exp(-pi*0.7/sqrt(1 - 0.7^2));
assert(abs(baseline.overshootPercent - expectedOvershootPercent) < 0.02, ...
    'Sampled baseline overshoot must agree with the independent analytic limit.');
assert(baseline.requirementsMet,'The baseline must meet its complete behavior envelope.');
fprintf(['Baseline: command %.1f deg, peak %.2f deg, peak speed %.1f deg/s, ' ...
    'settling %.0f ms, deadline %.0f ms.\n'],baseline.requestedCommandDeg, ...
    baseline.peakPositionMagnitudeDeg,baseline.peakVelocityMagnitudeDegPerSec, ...
    baseline.settlingTimeMs,baseline.inputs.deadlineMs);

%% Sweep 1 - command magnitude scales physical position and speed
commandSweepDeg = [10 20 30 40];
peakPositionByCommandDeg = zeros(size(commandSweepDeg));
peakVelocityByCommandDegPerSec = zeros(size(commandSweepDeg));
overshootByCommandPercent = zeros(size(commandSweepDeg));
for k = 1:numel(commandSweepDeg)
    trial = model(commandSweepDeg(k),1.5,0.7,45,0.5,2,1200);
    peakPositionByCommandDeg(k) = trial.peakPositionMagnitudeDeg;
    peakVelocityByCommandDegPerSec(k) = trial.peakVelocityMagnitudeDegPerSec;
    overshootByCommandPercent(k) = trial.overshootPercent;
    fprintf('Command %.0f deg -> peak %.2f deg, peak speed %.1f deg/s, overshoot %.2f%%.\n', ...
        commandSweepDeg(k),trial.peakPositionMagnitudeDeg, ...
        trial.peakVelocityMagnitudeDegPerSec,trial.overshootPercent);
end
figure('Name','P03 command-magnitude sweep');
subplot(2,1,1);
plot(commandSweepDeg,peakPositionByCommandDeg,'o-','LineWidth',1.4); grid on;
xlabel('Requested command magnitude (deg)'); ylabel('Peak position magnitude (deg)');
title('Lever 1: a larger requested motion scales the position response');
subplot(2,1,2);
plot(commandSweepDeg,peakVelocityByCommandDegPerSec,'s-','LineWidth',1.4); grid on;
xlabel('Requested command magnitude (deg)'); ylabel('Peak velocity magnitude (deg/s)');
title('The same response shape demands proportionally more speed');
assert(max(abs(overshootByCommandPercent - overshootByCommandPercent(1))) < 1e-10, ...
    'A linear command sweep must preserve normalized overshoot.');

%% Read and explain lever 1 before advancing
disp('Mechanism after lever 1: the linear response shape is unchanged, so angle and speed scale with command while overshoot percentage stays fixed.');

%% Sweep 2 - damping changes overshoot and settling without changing the request
dampingSweep = [0.25 0.45 0.7 1.0];
overshootByDampingPercent = zeros(size(dampingSweep));
settlingByDampingMs = zeros(size(dampingSweep));
deadlineMetByDamping = false(size(dampingSweep));
for k = 1:numel(dampingSweep)
    trial = model(30,1.5,dampingSweep(k),45,0.5,2,1200);
    overshootByDampingPercent(k) = trial.overshootPercent;
    settlingByDampingMs(k) = trial.settlingTimeMs;
    deadlineMetByDamping(k) = trial.settledByDeadline;
    fprintf('Damping %.2f -> overshoot %.2f%%, settling %.0f ms, deadline met %d.\n', ...
        dampingSweep(k),trial.overshootPercent,trial.settlingTimeMs,trial.settledByDeadline);
end
figure('Name','P03 damping-ratio sweep');
subplot(2,1,1);
plot(dampingSweep,overshootByDampingPercent,'o-','LineWidth',1.4); grid on;
xlabel('Damping ratio (-)'); ylabel('Overshoot (%)');
title('Lever 2: damping removes excess motion');
subplot(2,1,2);
plot(dampingSweep,settlingByDampingMs,'s-','LineWidth',1.4); hold on;
yline(1200,'--','Response deadline'); hold off; grid on;
xlabel('Damping ratio (-)'); ylabel('Sustained settling time (ms)');
title('Both position and velocity bands determine completion');
assert(all(diff(overshootByDampingPercent) < 0), ...
    'The selected damping sweep must reduce overshoot monotonically.');

%% Read and explain lever 2 before breaking an assumption
disp('Mechanism after lever 2: damping dissipates oscillatory motion, reducing overshoot and changing when both position and velocity remain in band.');

%% Broken case - the requested command violates the declared input envelope
broken = model(70,1.5,0.7,45,0.5,2,1200);
figure('Name','P03 broken command-authority case');
plot(broken.timeMs,broken.positionDeg,'LineWidth',1.5,'DisplayName','Observed position'); hold on;
yline(broken.requestedCommandDeg,'--','Requested 70 deg');
yline(broken.effectiveCommandDeg,':','Effective 45 deg target');
xline(broken.inputs.deadlineMs,'--','Response deadline'); hold off; grid on;
xlabel('Time from accepted command (ms)'); ylabel('Rotary position (deg)');
xlim([0 3000]);
title('Broken assumption: the requested input is inside command authority');
legend('Location','best');
fprintf(['Broken case: requested %.1f deg, effective target %.1f deg, final error %.1f deg, ' ...
    'failure = %s.\n'],broken.requestedCommandDeg,broken.effectiveCommandDeg, ...
    broken.finalRequestErrorDeg,broken.failureMode);
assert(broken.commandWasLimited && broken.effectiveTargetSettledByDeadline && ...
    ~broken.requirementsMet && isinf(broken.settlingTimeMs), ...
    'A limited request may settle physically while failing the requested behavior.');

%% Mechanism synthesis
disp('Synthesis: desired physical behavior names the valid input envelope, measurable position and velocity effects, quantitative bands, and a deadline.');
disp('A plausible motion trace is not success when the request is clipped, motion remains outside a band, or completion is late.');
