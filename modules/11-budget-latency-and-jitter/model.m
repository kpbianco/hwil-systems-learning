function out = model(transportNominalMs,jitterScale,deadlineMs, ...
    p10ActivationProof,cancelAtMs,assessmentMode)
%MODEL Deterministic elapsed-time budget for a P10-authorized command cycle.
%   P10 supplies one caller-owned adapter fact from its nominal activation
%   transition (the 'activate-request' at step 6):
%   p10ActivationStep = 6;
%   p10ActivationProof = transitionTableAllowed(p10ActivationStep) && ...
%       strictGuardPass(p10ActivationStep) && ...
%       strictPostconditionPass(p10ActivationStep) && ...
%       ~priorityViolation(p10ActivationStep);
%   P11 does not invoke or reimplement the P10 state machine. A timing
%   interruption requests a P10 SAFE-HOLD handoff; P11 cannot prove that
%   SAFE-HOLD or rollback occurred.

if nargin < 1, transportNominalMs = 1.2; end
if nargin < 2, jitterScale = 1.0; end
if nargin < 3, deadlineMs = 4.2; end
if nargin < 4, p10ActivationProof = true; end
if nargin < 5, cancelAtMs = Inf; end
if nargin < 6, assessmentMode = 'bounded-sum'; end

minimumTransportNominalMs = 0.6;
maximumTransportNominalMs = 2.4;
minimumJitterScale = 0.0;
maximumJitterScale = 2.0;
minimumDeadlineMs = 0.5;
maximumDeadlineMs = 10.0;
cycleCount = 12;
stageCount = 4;
stageCellCount = cycleCount * stageCount;
cyclePeriodMs = 6.0;

transportNominalMs = normalizeBoundedScalar(transportNominalMs, ...
    minimumTransportNominalMs,maximumTransportNominalMs, ...
    'P11:InvalidTransportNominal','transportNominalMs');
jitterScale = normalizeBoundedScalar(jitterScale,minimumJitterScale, ...
    maximumJitterScale,'P11:InvalidJitterScale','jitterScale');
deadlineMs = normalizeBoundedScalar(deadlineMs,minimumDeadlineMs, ...
    maximumDeadlineMs,'P11:InvalidDeadline','deadlineMs');
p10ActivationProof = normalizeLogicalScalar(p10ActivationProof, ...
    'P11:InvalidP10ActivationProof','p10ActivationProof');
cancelAtMs = normalizeCancellationTime(cancelAtMs);
assessmentMode = normalizeChoice(assessmentMode, ...
    {'bounded-sum','rss-uncorrelated'}, ...
    'P11:InvalidAssessmentMode','assessmentMode');

stageNames = {'Input acquisition','Command calculation', ...
    'Command transport','Apply and observe'};
nominalStageLatencyMs = [0.6 0.5 transportNominalMs 1.0];
baseJitterAllocationMs = [0.1 0.1 0.3 0.2];
jitterAllocationMs = jitterScale .* baseJitterAllocationMs;

% Each column is balanced and every value is in {-1,0,1}. Row 4 aligns
% all positive allocations and row 8 aligns all negative allocations.
% This is a fixed deterministic fixture, not a probability distribution.
jitterPattern = [ ...
     0  0  0  0; ...
     1 -1  0  1; ...
    -1  1  1  0; ...
     1  1  1  1; ...
     0 -1 -1  1; ...
    -1  0  1 -1; ...
     1  0 -1  0; ...
    -1 -1 -1 -1; ...
     0  1  0 -1; ...
     1 -1  1 -1; ...
    -1  1 -1  1; ...
     0  0  0  0];

plannedStageVariationMs = jitterPattern .* jitterAllocationMs;
plannedStageLatencyMs = nominalStageLatencyMs + ...
    plannedStageVariationMs;
plannedStageCumulativeMs = cumsum(plannedStageLatencyMs,2);
plannedLatencyMs = sum(plannedStageLatencyMs,2)';
nominalLatencyMs = sum(nominalStageLatencyMs);
plannedLatencyDeviationMs = plannedLatencyMs - nominalLatencyMs;
strictJitterAllowanceMs = sum(jitterAllocationMs);
strictLowerBoundMs = nominalLatencyMs - strictJitterAllowanceMs;
strictUpperBoundMs = nominalLatencyMs + strictJitterAllowanceMs;
strictPeakToPeakJitterMs = 2 * strictJitterAllowanceMs;
rssJitterAllowanceMs = sqrt(sum(jitterAllocationMs .^ 2));
rssUpperBoundMs = nominalLatencyMs + rssJitterAllowanceMs;

if strcmp(assessmentMode,'bounded-sum')
    reportedJitterAllowanceMs = strictJitterAllowanceMs;
    reportedUpperBoundMs = strictUpperBoundMs;
else
    % Deliberately broken unless stage independence is separately proven.
    reportedJitterAllowanceMs = rssJitterAllowanceMs;
    reportedUpperBoundMs = rssUpperBoundMs;
end

strictMarginMs = deadlineMs - strictUpperBoundMs;
reportedMarginMs = deadlineMs - reportedUpperBoundMs;
strictBudgetPass = strictUpperBoundMs <= deadlineMs;
reportedBudgetPass = reportedUpperBoundMs <= deadlineMs;
strictBudgetAccepted = p10ActivationProof && strictBudgetPass;
reportedBudgetAccepted = p10ActivationProof && reportedBudgetPass;
falseApproval = reportedBudgetAccepted && ~strictBudgetAccepted;
assessmentDecisionCorrect = strictBudgetAccepted == ...
    reportedBudgetAccepted;

cycleIndex = 1:cycleCount;
plannedReleaseMs = (cycleIndex - 1) .* cyclePeriodMs;
plannedDeadlineMs = plannedReleaseMs + deadlineMs;
plannedCompletionMs = plannedReleaseMs + plannedLatencyMs;
plannedStageCompletionMs = plannedReleaseMs' + ...
    plannedStageCumulativeMs;
plannedDeadlineMiss = plannedCompletionMs > plannedDeadlineMs;
plannedBoundViolation = any(abs(plannedStageVariationMs) > ...
    jitterAllocationMs + 1e-12,2)';

cycleStarted = false(1,cycleCount);
cycleCompleted = false(1,cycleCount);
actualReleaseMs = nan(1,cycleCount);
actualCompletionMs = nan(1,cycleCount);
actualLatencyMs = nan(1,cycleCount);
actualStageLatencyMs = nan(cycleCount,stageCount);
actualStageCompletionMs = nan(cycleCount,stageCount);
cancellationRequested = isfinite(cancelAtMs);
cancellationObserved = false;
timeoutObserved = false;
tieResolvedToCancellation = false;
terminalTimeMs = NaN;
interruptedCycle = NaN;

if p10ActivationProof
    for k = 1:cycleCount
        releaseTimeMs = plannedReleaseMs(k);
        completionTimeMs = plannedCompletionMs(k);
        deadlineTimeMs = plannedDeadlineMs(k);

        % Cancellation wins a tie at release, so that cycle never starts.
        if cancelAtMs <= releaseTimeMs
            cancellationObserved = true;
            terminalTimeMs = cancelAtMs;
            interruptedCycle = k;
            break;
        end

        cycleStarted(k) = true;
        actualReleaseMs(k) = releaseTimeMs;
        timeoutCandidateMs = Inf;
        if completionTimeMs > deadlineTimeMs
            timeoutCandidateMs = deadlineTimeMs;
        end

        % Cancellation wins ties with completion and deadline. A tie with
        % the deadline records both observed causes but reports cancellation.
        if cancelAtMs <= completionTimeMs && ...
                cancelAtMs <= timeoutCandidateMs
            cancellationObserved = true;
            timeoutObserved = isfinite(timeoutCandidateMs) && ...
                abs(cancelAtMs - timeoutCandidateMs) <= 1e-12;
            tieResolvedToCancellation = timeoutObserved;
            terminalTimeMs = cancelAtMs;
            interruptedCycle = k;
            break;
        elseif timeoutCandidateMs < completionTimeMs && ...
                timeoutCandidateMs < cancelAtMs
            timeoutObserved = true;
            terminalTimeMs = timeoutCandidateMs;
            interruptedCycle = k;
            break;
        end

        cycleCompleted(k) = true;
        actualCompletionMs(k) = completionTimeMs;
        actualLatencyMs(k) = plannedLatencyMs(k);
        actualStageLatencyMs(k,:) = plannedStageLatencyMs(k,:);
        actualStageCompletionMs(k,:) = ...
            plannedStageCompletionMs(k,:);
    end
end

completedCycleCount = sum(cycleCompleted);
scheduleCompleted = all(cycleCompleted);
eventObserved = cancellationObserved || timeoutObserved;
safeHoldRequested = eventObserved;
rollbackRequired = safeHoldRequested;
rollbackEvidenceAvailable = false;
rollbackAuthority = 'P10';

if cancellationObserved && timeoutObserved
    handoffEvent = 'cancellation-timeout-tie';
elseif cancellationObserved
    handoffEvent = 'cancellation';
elseif timeoutObserved
    handoffEvent = 'timeout';
else
    handoffEvent = 'none';
end

if ~p10ActivationProof
    terminalStatus = 'blocked-p10-activation-proof';
    failureMode = 'p10-activation-proof-unavailable';
elseif cancellationObserved && timeoutObserved
    terminalStatus = 'cancelled-on-timeout-tie';
    failureMode = 'cycle-cancelled';
elseif cancellationObserved
    terminalStatus = 'cancelled-safe-hold-requested';
    failureMode = 'cycle-cancelled';
elseif timeoutObserved
    terminalStatus = 'timed-out-safe-hold-requested';
    failureMode = 'deadline-timeout';
elseif scheduleCompleted
    terminalStatus = 'completed-within-budget';
    failureMode = 'none';
else
    terminalStatus = 'unhandled-terminal';
    failureMode = 'unhandled-terminal';
end

if falseApproval
    reportingFailureMode = 'rss-independence-false-approval';
else
    reportingFailureMode = 'none';
end
terminalOutcomeHandled = ~strcmp(terminalStatus,'unhandled-terminal');

if any(cycleCompleted)
    observedMinimumLatencyMs = min(actualLatencyMs(cycleCompleted));
    observedMaximumLatencyMs = max(actualLatencyMs(cycleCompleted));
    observedPeakToPeakJitterMs = observedMaximumLatencyMs - ...
        observedMinimumLatencyMs;
else
    observedMinimumLatencyMs = NaN;
    observedMaximumLatencyMs = NaN;
    observedPeakToPeakJitterMs = NaN;
end

out = struct();
out.inputs = struct('transportNominalMs',transportNominalMs, ...
    'jitterScale',jitterScale,'deadlineMs',deadlineMs, ...
    'p10ActivationProof',p10ActivationProof, ...
    'cancelAtMs',cancelAtMs,'assessmentMode',assessmentMode);
out.stageNames = stageNames;
out.nominalStageLatencyMs = nominalStageLatencyMs;
out.baseJitterAllocationMs = baseJitterAllocationMs;
out.jitterAllocationMs = jitterAllocationMs;
out.jitterPattern = jitterPattern;
out.plannedStageVariationMs = plannedStageVariationMs;
out.plannedStageLatencyMs = plannedStageLatencyMs;
out.plannedStageCumulativeMs = plannedStageCumulativeMs;
out.plannedStageCompletionMs = plannedStageCompletionMs;
out.plannedLatencyMs = plannedLatencyMs;
out.plannedLatencyDeviationMs = plannedLatencyDeviationMs;
out.plannedReleaseMs = plannedReleaseMs;
out.plannedDeadlineMs = plannedDeadlineMs;
out.plannedCompletionMs = plannedCompletionMs;
out.plannedDeadlineMiss = plannedDeadlineMiss;
out.plannedBoundViolation = plannedBoundViolation;
out.cycleIndex = cycleIndex;
out.cycleStarted = cycleStarted;
out.cycleCompleted = cycleCompleted;
out.actualReleaseMs = actualReleaseMs;
out.actualCompletionMs = actualCompletionMs;
out.actualLatencyMs = actualLatencyMs;
out.actualStageLatencyMs = actualStageLatencyMs;
out.actualStageCompletionMs = actualStageCompletionMs;
out.nominalLatencyMs = nominalLatencyMs;
out.strictJitterAllowanceMs = strictJitterAllowanceMs;
out.strictLowerBoundMs = strictLowerBoundMs;
out.strictUpperBoundMs = strictUpperBoundMs;
out.strictPeakToPeakJitterMs = strictPeakToPeakJitterMs;
out.rssJitterAllowanceMs = rssJitterAllowanceMs;
out.rssUpperBoundMs = rssUpperBoundMs;
out.reportedJitterAllowanceMs = reportedJitterAllowanceMs;
out.reportedUpperBoundMs = reportedUpperBoundMs;
out.strictMarginMs = strictMarginMs;
out.reportedMarginMs = reportedMarginMs;
out.strictBudgetPass = strictBudgetPass;
out.reportedBudgetPass = reportedBudgetPass;
out.strictBudgetAccepted = strictBudgetAccepted;
out.reportedBudgetAccepted = reportedBudgetAccepted;
out.falseApproval = falseApproval;
out.assessmentDecisionCorrect = assessmentDecisionCorrect;
out.observedMinimumLatencyMs = observedMinimumLatencyMs;
out.observedMaximumLatencyMs = observedMaximumLatencyMs;
out.observedPeakToPeakJitterMs = observedPeakToPeakJitterMs;
out.cancellationRequested = cancellationRequested;
out.cancellationObserved = cancellationObserved;
out.timeoutObserved = timeoutObserved;
out.eventObserved = eventObserved;
out.tieResolvedToCancellation = tieResolvedToCancellation;
out.terminalTimeMs = terminalTimeMs;
out.interruptedCycle = interruptedCycle;
out.safeHoldRequested = safeHoldRequested;
out.handoffEvent = handoffEvent;
out.rollbackRequired = rollbackRequired;
out.rollbackEvidenceAvailable = rollbackEvidenceAvailable;
out.rollbackAuthority = rollbackAuthority;
out.completedCycleCount = completedCycleCount;
out.scheduleCompleted = scheduleCompleted;
out.terminalStatus = terminalStatus;
out.failureMode = failureMode;
out.reportingFailureMode = reportingFailureMode;
out.terminalOutcomeHandled = terminalOutcomeHandled;
out.cycleCount = cycleCount;
out.stageCount = stageCount;
out.stageCellCount = stageCellCount;
out.cyclePeriodMs = cyclePeriodMs;
out.minimumTransportNominalMs = minimumTransportNominalMs;
out.maximumTransportNominalMs = maximumTransportNominalMs;
out.minimumJitterScale = minimumJitterScale;
out.maximumJitterScale = maximumJitterScale;
out.minimumDeadlineMs = minimumDeadlineMs;
out.maximumDeadlineMs = maximumDeadlineMs;
end

function normalized = normalizeBoundedScalar(value,lowerBound,upperBound, ...
    errorId,inputName)
if ~(isnumeric(value) && ~islogical(value) && isscalar(value) && ...
        isreal(value) && isfinite(value))
    error(errorId,'%s must be one finite real numeric scalar.',inputName);
end
normalized = double(value);
if normalized < lowerBound || normalized > upperBound
    error(errorId,'%s is outside its bounded range.',inputName);
end
end

function normalized = normalizeLogicalScalar(value,errorId,inputName)
if islogical(value) && isscalar(value)
    normalized = logical(value);
elseif isnumeric(value) && ~islogical(value) && isscalar(value) && ...
        isreal(value) && isfinite(value) && (value == 0 || value == 1)
    normalized = logical(value);
else
    error(errorId,'%s must be one logical scalar or numeric zero/one.', ...
        inputName);
end
end

function normalized = normalizeCancellationTime(value)
if ~(isnumeric(value) && ~islogical(value) && isscalar(value) && ...
        isreal(value) && ~isnan(value) && value >= 0 && ...
        (isfinite(value) || (isinf(value) && value > 0)))
    error('P11:InvalidCancellationTime', ...
        'cancelAtMs must be one nonnegative finite scalar or positive Inf.');
end
normalized = double(value);
end

function normalized = normalizeChoice(value,allowed,errorId,inputName)
if isstring(value)
    if ~isscalar(value)
        error(errorId,'%s must be scalar text.',inputName);
    end
elseif ~(ischar(value) && isrow(value) && ~isempty(value))
    error(errorId,'%s must be scalar text.',inputName);
end
normalized = lower(strtrim(char(value)));
if ~any(strcmp(normalized,allowed))
    error(errorId,'%s has an unsupported value.',inputName);
end
end
