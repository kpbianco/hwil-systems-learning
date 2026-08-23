function out = model(readinessConfirmations,recoveryConfirmations, ...
    p09StartupProof,p09SafeOffProof,scenarioMode,eventMode, ...
    arbitrationMode)
%MODEL Evaluate one bounded finite-state transition proposal.
%   P10 separates state, event, guard, priority, and observed destination.
%   P09 facts enter through two explicit adapters:
%     p09StartupProof = startupOrderValid && startupFinalRunning
%     p09SafeOffProof = shutdownOrderValid && shutdownFinalSafeOff
%   This function does not execute or alter the P09 lifecycle model.
%
%   Confirmation counts are consecutive logical evidence observations.
%   Transition step is a dimensionless sequence index, not elapsed time. Cancellation and
%   timeout are injected logical events at a fixed checkpoint and carry no
%   deadline, latency, or clock meaning.

if nargin < 1, readinessConfirmations = 2; end
if nargin < 2, recoveryConfirmations = 2; end
if nargin < 3, p09StartupProof = true; end
if nargin < 4, p09SafeOffProof = true; end
if nargin < 5, scenarioMode = 'nominal'; end
if nargin < 6, eventMode = 'none'; end
if nargin < 7, arbitrationMode = 'guarded-priority'; end

minimumReadinessConfirmations = 1;
maximumReadinessConfirmations = 4;
minimumRecoveryConfirmations = 1;
maximumRecoveryConfirmations = 4;
transitionCount = 13;
stateCount = 6;
rollbackTransitionCount = 3;
eventCheckpointTransition = 6;

readinessConfirmations = normalizeIntegerScalar( ...
    readinessConfirmations,'readinessConfirmations', ...
    minimumReadinessConfirmations,maximumReadinessConfirmations, ...
    'P10:InvalidReadinessConfirmations');
recoveryConfirmations = normalizeIntegerScalar( ...
    recoveryConfirmations,'recoveryConfirmations', ...
    minimumRecoveryConfirmations,maximumRecoveryConfirmations, ...
    'P10:InvalidRecoveryConfirmations');
p09StartupProof = normalizeLogicalScalar(p09StartupProof, ...
    'p09StartupProof','P10:InvalidP09StartupProof');
p09SafeOffProof = normalizeLogicalScalar(p09SafeOffProof, ...
    'p09SafeOffProof','P10:InvalidP09SafeOffProof');
scenarioMode = normalizeChoice(scenarioMode, ...
    {'nominal','recoverable-feedback-loss','fault-reset-conflict', ...
    'state-stuck-active','premature-activation'}, ...
    'P10:InvalidScenarioMode','scenarioMode');
eventMode = normalizeChoice(eventMode, ...
    {'none','cancellation','timeout','cancellation-timeout-tie'}, ...
    'P10:InvalidEventMode','eventMode');
arbitrationMode = normalizeChoice(arbitrationMode, ...
    {'guarded-priority','last-request-wins'}, ...
    'P10:InvalidArbitrationMode','arbitrationMode');

offState = 1;
standbyState = 2;
readyState = 3;
activeState = 4;
faultState = 5;
safeHoldState = 6;
stateNames = {'OFF','STANDBY','READY','ACTIVE','FAULT','SAFE-HOLD'};

% Row is source and column is destination. Self-transitions retain an
% observation without inventing a state change.
transitionTable = false(stateCount,stateCount);
transitionTable(offState,[offState standbyState]) = true;
transitionTable(standbyState, ...
    [standbyState readyState safeHoldState]) = true;
transitionTable(readyState, ...
    [readyState activeState safeHoldState]) = true;
transitionTable(activeState, ...
    [activeState faultState safeHoldState]) = true;
transitionTable(faultState, ...
    [readyState faultState safeHoldState]) = true;
transitionTable(safeHoldState,[offState safeHoldState]) = true;

eventNames = {'enter-standby-request','readiness-evidence', ...
    'readiness-evidence','readiness-evidence','readiness-evidence', ...
    'activate-request','operate','operate','operate','operate','operate', ...
    'stop-request','off-request'};
if strcmp(scenarioMode,'premature-activation')
    eventNames{2} = 'activate-request';
elseif strcmp(scenarioMode,'recoverable-feedback-loss')
    eventNames{7} = 'feedback-loss';
    eventNames(8:11) = {'recovery-evidence','recovery-evidence', ...
        'recovery-evidence','recovery-evidence'};
elseif strcmp(scenarioMode,'fault-reset-conflict')
    eventNames{7} = 'feedback-loss+reset';
    eventNames(8:11) = {'recovery-evidence','recovery-evidence', ...
        'recovery-evidence','recovery-evidence'};
elseif strcmp(scenarioMode,'state-stuck-active')
    eventNames{7} = 'feedback-loss';
end
rollbackEventNames = {'enter-safe-hold','clear-transition-requests', ...
    'return-off-after-p09-proof'};
transitionInputNames = {'enter-standby-request','readiness-evidence', ...
    'activate-request','operate','feedback-loss','reset-request', ...
    'recovery-evidence','stop-request','off-request'};
transitionInputMatrix = false(transitionCount,numel(transitionInputNames));
for k = 1:transitionCount
    switch eventNames{k}
        case 'enter-standby-request'
            transitionInputMatrix(k,1) = true;
        case 'readiness-evidence'
            transitionInputMatrix(k,2) = true;
        case 'activate-request'
            transitionInputMatrix(k,3) = true;
        case 'operate'
            transitionInputMatrix(k,4) = true;
        case 'feedback-loss'
            transitionInputMatrix(k,5) = true;
        case 'feedback-loss+reset'
            transitionInputMatrix(k,[5 6]) = true;
        case 'recovery-evidence'
            transitionInputMatrix(k,7) = true;
        case 'stop-request'
            transitionInputMatrix(k,8) = true;
        case 'off-request'
            transitionInputMatrix(k,9) = true;
    end
end
transitionInputCount = sum(transitionInputMatrix,2)';
transitionInputConflict = transitionInputCount > 1;
maximumSimultaneousTransitionInputs = 2;

cancellationRequested = any(strcmp(eventMode, ...
    {'cancellation','cancellation-timeout-tie'}));
timeoutRequested = any(strcmp(eventMode, ...
    {'timeout','cancellation-timeout-tie'}));
eventRequested = cancellationRequested || timeoutRequested;
observedInterruptionName = 'none';
preemptedTransitionInput = 'none';
cancellationObserved = false;
timeoutObserved = false;
eventObserved = false;
tieResolvedToCancellation = false;

transitionEvaluated = false(1,transitionCount);
sourceStateId = NaN(1,transitionCount);
strictRequestedStateId = NaN(1,transitionCount);
reportedRequestedStateId = NaN(1,transitionCount);
observedStateId = NaN(1,transitionCount);
transitionTableAllowed = false(1,transitionCount);
reportedTransitionTableAllowed = false(1,transitionCount);
strictGuardPass = false(1,transitionCount);
reportedGuardPass = false(1,transitionCount);
strictPostconditionPass = false(1,transitionCount);
reportedPostconditionPass = false(1,transitionCount);
strictTransitionPass = false(1,transitionCount);
reportedTransitionPass = false(1,transitionCount);
policyStepAccepted = false(1,transitionCount);
transitionHazard = false(1,transitionCount);
priorityViolation = false(1,transitionCount);
guardBypassed = false(1,transitionCount);
strictSelectedInput = repmat({''},1,transitionCount);
reportedSelectedInput = repmat({''},1,transitionCount);
stateIdTrace = NaN(1,transitionCount);
stateOccupancyTrace = NaN(transitionCount,stateCount);
readinessEvidenceCountTrace = NaN(1,transitionCount);
recoveryEvidenceCountTrace = NaN(1,transitionCount);

stateId = offState;
readinessEvidenceCount = 0;
recoveryEvidenceCount = 0;
readinessQualifiedStep = NaN;
recoveryQualifiedStep = NaN;
sequenceHalted = false;

for k = 1:transitionCount
    if sequenceHalted
        break;
    end
    if eventRequested && k == eventCheckpointTransition
        eventObserved = true;
        cancellationObserved = cancellationRequested;
        timeoutObserved = timeoutRequested;
        tieResolvedToCancellation = cancellationObserved && ...
            timeoutObserved;
        observedInterruptionName = eventMode;
        preemptedTransitionInput = eventNames{k};
        break;
    end

    transitionEvaluated(k) = true;
    source = stateId;
    strictTarget = source;
    reportedTarget = source;
    eventName = eventNames{k};
    strictSelection = eventName;
    reportedSelection = eventName;
    strictGuard = false;
    brokenConflictAccepted = false;

    switch eventName
        case 'enter-standby-request'
            strictTarget = standbyState;
            reportedTarget = strictTarget;
            strictGuard = source == offState && p09StartupProof;
        case 'readiness-evidence'
            if source == standbyState
                readinessEvidenceCount = readinessEvidenceCount + 1;
                if readinessEvidenceCount >= readinessConfirmations
                    strictTarget = readyState;
                    if isnan(readinessQualifiedStep)
                        readinessQualifiedStep = k;
                    end
                else
                    strictTarget = standbyState;
                end
                reportedTarget = strictTarget;
                strictGuard = true;
            elseif source == readyState
                strictTarget = readyState;
                reportedTarget = strictTarget;
                strictGuard = true;
            else
                strictTarget = source;
                reportedTarget = strictTarget;
                strictGuard = false;
            end
        case 'activate-request'
            strictTarget = activeState;
            reportedTarget = strictTarget;
            strictGuard = source == readyState;
        case 'operate'
            strictTarget = activeState;
            reportedTarget = strictTarget;
            strictGuard = source == activeState;
        case 'feedback-loss'
            strictTarget = faultState;
            reportedTarget = strictTarget;
            strictGuard = source == activeState;
        case 'feedback-loss+reset'
            strictTarget = faultState;
            strictGuard = source == activeState;
            strictSelection = 'feedback-loss';
            if strcmp(arbitrationMode,'guarded-priority')
                reportedTarget = strictTarget;
                reportedSelection = strictSelection;
            else
                % Deliberately broken: textual request order selects reset,
                % bypassing both source-state legality and fault priority.
                reportedTarget = readyState;
                reportedSelection = 'reset-request';
                brokenConflictAccepted = source == activeState;
            end
        case 'recovery-evidence'
            if source == faultState
                recoveryEvidenceCount = recoveryEvidenceCount + 1;
                if recoveryEvidenceCount >= recoveryConfirmations
                    strictTarget = readyState;
                    if isnan(recoveryQualifiedStep)
                        recoveryQualifiedStep = k;
                    end
                else
                    strictTarget = faultState;
                end
                reportedTarget = strictTarget;
                strictGuard = true;
            elseif source == readyState
                strictTarget = readyState;
                reportedTarget = strictTarget;
                strictGuard = true;
            else
                strictTarget = source;
                reportedTarget = strictTarget;
                strictGuard = false;
            end
        case 'stop-request'
            strictTarget = safeHoldState;
            reportedTarget = strictTarget;
            strictGuard = source == activeState || source == readyState;
        case 'off-request'
            strictTarget = offState;
            reportedTarget = strictTarget;
            strictGuard = source == safeHoldState && p09SafeOffProof;
    end

    tableAllowed = transitionTable(source,strictTarget);
    reportedTableAllowed = transitionTable(source,reportedTarget);
    if brokenConflictAccepted
        reportedGuard = false;
        policyAllowsTransition = true;
        priorityWasViolated = true;
    else
        reportedGuard = strictGuard;
        policyAllowsTransition = tableAllowed && strictGuard;
        priorityWasViolated = false;
    end

    nextState = source;
    if policyAllowsTransition
        nextState = reportedTarget;
    end
    if strcmp(scenarioMode,'state-stuck-active') && ...
            strcmp(eventName,'feedback-loss') && source == activeState
        nextState = activeState;
    end
    stateId = nextState;
    strictPostcondition = stateId == strictTarget;
    reportedPostcondition = stateId == reportedTarget;

    sourceStateId(k) = source;
    strictRequestedStateId(k) = strictTarget;
    reportedRequestedStateId(k) = reportedTarget;
    observedStateId(k) = stateId;
    transitionTableAllowed(k) = tableAllowed;
    reportedTransitionTableAllowed(k) = reportedTableAllowed;
    strictGuardPass(k) = strictGuard;
    reportedGuardPass(k) = reportedGuard;
    strictPostconditionPass(k) = strictPostcondition;
    reportedPostconditionPass(k) = reportedPostcondition;
    strictTransitionPass(k) = tableAllowed && strictGuard && ...
        strictPostcondition;
    reportedTransitionPass(k) = reportedTableAllowed && ...
        reportedGuard && reportedPostcondition;
    policyStepAccepted(k) = policyAllowsTransition && ...
        reportedPostcondition;
    transitionHazard(k) = ~strictTransitionPass(k);
    priorityViolation(k) = priorityWasViolated;
    guardBypassed(k) = policyAllowsTransition && ...
        (~reportedTableAllowed || ~reportedGuard);
    strictSelectedInput{k} = strictSelection;
    reportedSelectedInput{k} = reportedSelection;
    stateIdTrace(k) = stateId;
    stateOccupancyTrace(k,:) = stateOneHot(stateId,stateCount);
    readinessEvidenceCountTrace(k) = readinessEvidenceCount;
    recoveryEvidenceCountTrace(k) = recoveryEvidenceCount;

    if ~policyStepAccepted(k)
        sequenceHalted = true;
    end
end

sequenceCompleted = all(transitionEvaluated);
if sequenceCompleted
    sequenceFinalStateId = stateId;
else
    sequenceFinalStateId = NaN;
end
strictStateMachineAccepted = sequenceCompleted && ...
    all(strictTransitionPass) && stateId == offState;
reportedStateMachineAccepted = sequenceCompleted && ...
    all(policyStepAccepted) && stateId == offState;
falseApproval = sequenceCompleted && reportedStateMachineAccepted && ...
    ~strictStateMachineAccepted;
assessmentDecisionCorrect = sequenceCompleted && ...
    (reportedStateMachineAccepted == strictStateMachineAccepted);

rollbackTransitionExecuted = false(1,rollbackTransitionCount);
rollbackSourceStateId = NaN(1,rollbackTransitionCount);
rollbackRequestedStateId = NaN(1,rollbackTransitionCount);
rollbackObservedStateId = NaN(1,rollbackTransitionCount);
rollbackTransitionTableAllowed = false(1,rollbackTransitionCount);
rollbackGuardPass = false(1,rollbackTransitionCount);
rollbackPostconditionPass = false(1,rollbackTransitionCount);
rollbackTransitionPass = false(1,rollbackTransitionCount);
rollbackHazard = false(1,rollbackTransitionCount);
rollbackStateTrace = NaN(rollbackTransitionCount,stateCount);
rollbackPerformed = false;
rollbackComplete = false;
rollbackFinalStateId = NaN;

if eventObserved
    rollbackPerformed = true;
    rollbackStateId = stateId;
    for k = 1:rollbackTransitionCount
        rollbackTransitionExecuted(k) = true;
        source = rollbackStateId;
        switch rollbackEventNames{k}
            case 'enter-safe-hold'
                target = safeHoldState;
                guard = any(source == ...
                    [standbyState readyState activeState faultState]);
            case 'clear-transition-requests'
                target = safeHoldState;
                guard = source == safeHoldState;
            case 'return-off-after-p09-proof'
                target = offState;
                guard = source == safeHoldState && p09SafeOffProof;
        end
        tableAllowed = transitionTable(source,target);
        if tableAllowed && guard
            rollbackStateId = target;
        end
        postcondition = rollbackStateId == target;
        rollbackSourceStateId(k) = source;
        rollbackRequestedStateId(k) = target;
        rollbackObservedStateId(k) = rollbackStateId;
        rollbackTransitionTableAllowed(k) = tableAllowed;
        rollbackGuardPass(k) = guard;
        rollbackPostconditionPass(k) = postcondition;
        rollbackTransitionPass(k) = tableAllowed && guard && ...
            postcondition;
        rollbackHazard(k) = ~rollbackTransitionPass(k);
        rollbackStateTrace(k,:) = stateOneHot(rollbackStateId,stateCount);
    end
    rollbackComplete = all(rollbackTransitionPass) && ...
        rollbackStateId == offState;
    rollbackFinalStateId = rollbackStateId;
end

stateObservationCount = zeros(1,stateCount);
for state = 1:stateCount
    stateObservationCount(state) = sum(transitionEvaluated & ...
        stateIdTrace == state);
end
stateChangeCount = sum(transitionEvaluated & ...
    sourceStateId ~= observedStateId);
transitionViolationCount = sum(transitionEvaluated & ...
    ~strictTransitionPass);
reportedViolationCount = sum(transitionEvaluated & ...
    ~reportedTransitionPass);
policyViolationCount = sum(transitionEvaluated & ...
    ~policyStepAccepted);
rollbackViolationCount = sum(rollbackTransitionExecuted & ...
    ~rollbackTransitionPass);
priorityViolationCount = sum(transitionEvaluated & priorityViolation);
totalViolationCount = transitionViolationCount + rollbackViolationCount;
firstViolationStep = find(transitionEvaluated & ...
    ~strictTransitionPass,1,'first');
if isempty(firstViolationStep)
    firstViolationStep = NaN;
end

if cancellationObserved && rollbackComplete
    terminalStatus = 'cancelled-rollback-complete';
elseif cancellationObserved
    terminalStatus = 'cancelled-rollback-incomplete';
elseif timeoutObserved && rollbackComplete
    terminalStatus = 'timed-out-rollback-complete';
elseif timeoutObserved
    terminalStatus = 'timed-out-rollback-incomplete';
elseif strictStateMachineAccepted
    terminalStatus = 'completed-off';
elseif falseApproval
    terminalStatus = 'completed-false-approval';
else
    terminalStatus = 'rejected-transition';
end

if cancellationObserved
    failureMode = 'state-transition-cancelled';
elseif timeoutObserved
    failureMode = 'state-transition-timeout';
elseif ~p09StartupProof
    failureMode = 'p09-startup-proof-unavailable';
elseif strcmp(scenarioMode,'premature-activation') && ...
        ~isnan(firstViolationStep)
    failureMode = 'activation-before-ready';
elseif strcmp(scenarioMode,'state-stuck-active') && ...
        ~isnan(firstViolationStep)
    failureMode = 'state-postcondition-failed';
elseif priorityViolationCount > 0
    failureMode = 'fault-priority-bypassed';
elseif ~p09SafeOffProof
    failureMode = 'p09-safe-off-proof-unavailable';
elseif transitionViolationCount > 0
    failureMode = 'transition-guard-rejected';
else
    failureMode = 'none';
end
if falseApproval
    reportingFailureMode = 'last-request-wins-false-approval';
else
    reportingFailureMode = 'none';
end
if ~eventObserved || rollbackComplete
    rollbackFailureMode = 'none';
else
    rollbackFailureMode = 'p09-safe-off-proof-unavailable';
end
terminalOutcomeHandled = sequenceCompleted || sequenceHalted || ...
    eventObserved;

out = struct();
out.inputs = struct('readinessConfirmations',readinessConfirmations, ...
    'recoveryConfirmations',recoveryConfirmations, ...
    'p09StartupProof',p09StartupProof, ...
    'p09SafeOffProof',p09SafeOffProof, ...
    'scenarioMode',scenarioMode,'eventMode',eventMode, ...
    'arbitrationMode',arbitrationMode);
out.stateNames = stateNames;
out.eventNames = eventNames;
out.rollbackEventNames = rollbackEventNames;
out.transitionInputNames = transitionInputNames;
out.transitionInputMatrix = transitionInputMatrix;
out.transitionInputCount = transitionInputCount;
out.transitionInputConflict = transitionInputConflict;
out.transitionTable = transitionTable;
out.transitionEvaluated = transitionEvaluated;
out.sourceStateId = sourceStateId;
out.strictRequestedStateId = strictRequestedStateId;
out.reportedRequestedStateId = reportedRequestedStateId;
out.observedStateId = observedStateId;
out.transitionTableAllowed = transitionTableAllowed;
out.reportedTransitionTableAllowed = reportedTransitionTableAllowed;
out.strictGuardPass = strictGuardPass;
out.reportedGuardPass = reportedGuardPass;
out.strictPostconditionPass = strictPostconditionPass;
out.reportedPostconditionPass = reportedPostconditionPass;
out.strictTransitionPass = strictTransitionPass;
out.reportedTransitionPass = reportedTransitionPass;
out.policyStepAccepted = policyStepAccepted;
out.transitionHazard = transitionHazard;
out.priorityViolation = priorityViolation;
out.guardBypassed = guardBypassed;
out.strictSelectedInput = strictSelectedInput;
out.reportedSelectedInput = reportedSelectedInput;
out.stateIdTrace = stateIdTrace;
out.stateOccupancyTrace = stateOccupancyTrace;
out.readinessEvidenceCountTrace = readinessEvidenceCountTrace;
out.recoveryEvidenceCountTrace = recoveryEvidenceCountTrace;
out.readinessEvidenceCount = readinessEvidenceCount;
out.recoveryEvidenceCount = recoveryEvidenceCount;
out.readinessQualifiedStep = readinessQualifiedStep;
out.recoveryQualifiedStep = recoveryQualifiedStep;
out.stateObservationCount = stateObservationCount;
out.stateChangeCount = stateChangeCount;
out.sequenceCompleted = sequenceCompleted;
out.sequenceHalted = sequenceHalted;
out.sequenceFinalStateId = sequenceFinalStateId;
out.strictStateMachineAccepted = strictStateMachineAccepted;
out.reportedStateMachineAccepted = reportedStateMachineAccepted;
out.falseApproval = falseApproval;
out.assessmentDecisionCorrect = assessmentDecisionCorrect;
out.cancellationRequested = cancellationRequested;
out.timeoutRequested = timeoutRequested;
out.eventRequested = eventRequested;
out.observedInterruptionName = observedInterruptionName;
out.preemptedTransitionInput = preemptedTransitionInput;
out.cancellationObserved = cancellationObserved;
out.timeoutObserved = timeoutObserved;
out.eventObserved = eventObserved;
out.tieResolvedToCancellation = tieResolvedToCancellation;
out.rollbackTransitionExecuted = rollbackTransitionExecuted;
out.rollbackSourceStateId = rollbackSourceStateId;
out.rollbackRequestedStateId = rollbackRequestedStateId;
out.rollbackObservedStateId = rollbackObservedStateId;
out.rollbackTransitionTableAllowed = rollbackTransitionTableAllowed;
out.rollbackGuardPass = rollbackGuardPass;
out.rollbackPostconditionPass = rollbackPostconditionPass;
out.rollbackTransitionPass = rollbackTransitionPass;
out.rollbackHazard = rollbackHazard;
out.rollbackStateTrace = rollbackStateTrace;
out.rollbackPerformed = rollbackPerformed;
out.rollbackComplete = rollbackComplete;
out.rollbackFinalStateId = rollbackFinalStateId;
out.transitionViolationCount = transitionViolationCount;
out.reportedViolationCount = reportedViolationCount;
out.policyViolationCount = policyViolationCount;
out.rollbackViolationCount = rollbackViolationCount;
out.priorityViolationCount = priorityViolationCount;
out.totalViolationCount = totalViolationCount;
out.firstViolationStep = firstViolationStep;
out.terminalStatus = terminalStatus;
out.failureMode = failureMode;
out.reportingFailureMode = reportingFailureMode;
out.rollbackFailureMode = rollbackFailureMode;
out.terminalOutcomeHandled = terminalOutcomeHandled;
out.transitionCount = transitionCount;
out.stateCount = stateCount;
out.rollbackTransitionCount = rollbackTransitionCount;
out.eventCheckpointTransition = eventCheckpointTransition;
out.minimumReadinessConfirmations = minimumReadinessConfirmations;
out.maximumReadinessConfirmations = maximumReadinessConfirmations;
out.minimumRecoveryConfirmations = minimumRecoveryConfirmations;
out.maximumRecoveryConfirmations = maximumRecoveryConfirmations;
out.maximumSimultaneousTransitionInputs = ...
    maximumSimultaneousTransitionInputs;
end

function values = stateOneHot(stateId,stateCount)
values = zeros(1,stateCount);
values(stateId) = 1;
end

function normalized = normalizeIntegerScalar(value,inputName,lowerBound, ...
    upperBound,errorId)
if ~(isnumeric(value) && isscalar(value) && isreal(value) && isfinite(value))
    error(errorId,'%s must be a finite real numeric scalar.',inputName);
end
normalized = double(value);
if normalized ~= round(normalized) || normalized < lowerBound || ...
        normalized > upperBound
    error(errorId,'%s must be an integer inside its bounded range.', ...
        inputName);
end
end

function normalized = normalizeLogicalScalar(value,inputName,errorId)
if islogical(value) && isscalar(value)
    normalized = logical(value);
elseif isnumeric(value) && isscalar(value) && isreal(value) && ...
        isfinite(value) && (value == 0 || value == 1)
    normalized = logical(value);
else
    error(errorId,'%s must be one logical scalar or numeric zero/one.', ...
        inputName);
end
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
