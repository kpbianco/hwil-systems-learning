function out = model(startupEnablePosition,shutdownPowerOffPosition, ...
    p08ContractConformant,p08InputEligible,faultMode,eventMode, ...
    assessmentMode)
%MODEL Evaluate one bounded startup/shutdown proposal and its safety guards.
%   P09 treats a sequence as an ordered proof: each requested action has a
%   precondition and an observable postcondition. The fixed trace consumes
%   P08 contract-conformance and input-eligibility facts without executing
%   an interface, and it leaves general state-machine design to P10,
%   elapsed timing and jitter to P11, and synchronization to P12.
%
%   Cancellation and timeout are injected logical events at a fixed
%   checkpoint. They carry no elapsed-time meaning. Their compensating
%   rollback demonstrates a bounded return to a modeled safe hold; it is
%   not physical safety evidence.

if nargin < 1, startupEnablePosition = 5; end
if nargin < 2, shutdownPowerOffPosition = 6; end
if nargin < 3, p08ContractConformant = true; end
if nargin < 4, p08InputEligible = true; end
if nargin < 5, faultMode = 'none'; end
if nargin < 6, eventMode = 'none'; end
if nargin < 7, assessmentMode = 'strict-order'; end

minimumStartupEnablePosition = 1;
maximumStartupEnablePosition = 5;
minimumShutdownPowerOffPosition = 1;
maximumShutdownPowerOffPosition = 6;
actionCount = 6;
stateCount = 7;
rollbackActionCount = 5;
eventCheckpointAction = 3;

startupEnablePosition = normalizeIntegerScalar(startupEnablePosition, ...
    'startupEnablePosition',minimumStartupEnablePosition, ...
    maximumStartupEnablePosition,'P09:InvalidStartupEnablePosition');
shutdownPowerOffPosition = normalizeIntegerScalar(shutdownPowerOffPosition, ...
    'shutdownPowerOffPosition',minimumShutdownPowerOffPosition, ...
    maximumShutdownPowerOffPosition,'P09:InvalidShutdownPowerOffPosition');
p08ContractConformant = normalizeLogicalScalar(p08ContractConformant, ...
    'p08ContractConformant','P09:InvalidP08Conformance');
p08InputEligible = normalizeLogicalScalar(p08InputEligible, ...
    'p08InputEligible','P09:InvalidP08Eligibility');
if p08InputEligible && ~p08ContractConformant
    error('P09:InconsistentP08Facts', ...
        'P08 input eligibility cannot be true for a nonconformant contract.');
end
faultMode = normalizeChoice(faultMode, ...
    {'none','actuator-stuck-on','quiescence-not-confirmed'}, ...
    'P09:InvalidFaultMode','faultMode');
eventMode = normalizeChoice(eventMode, ...
    {'none','cancellation','timeout','cancellation-timeout-tie'}, ...
    'P09:InvalidEventMode','eventMode');
assessmentMode = normalizeChoice(assessmentMode, ...
    {'strict-order','final-state-only'}, ...
    'P09:InvalidAssessmentMode','assessmentMode');

startupBaseActions = { ...
    'assert-command-inhibit', ...
    'energize-power', ...
    'boot-controller', ...
    'qualify-p08-interface', ...
    'release-command-inhibit'};
startupActionNames = insertAction(startupBaseActions, ...
    'enable-actuator',startupEnablePosition);
shutdownBaseActions = { ...
    'inhibit-new-commands', ...
    'command-safe-output', ...
    'disable-actuator', ...
    'confirm-quiescence', ...
    'close-p08-interface'};
shutdownActionNames = insertAction(shutdownBaseActions, ...
    'remove-power',shutdownPowerOffPosition);
rollbackActionNames = { ...
    'inhibit-new-commands', ...
    'command-safe-output', ...
    'disable-actuator', ...
    'confirm-quiescence-and-isolate', ...
    'remove-power'};
stateNames = { ...
    'Power on', ...
    'Controller online', ...
    'P08 interface qualified', ...
    'Actuator enabled', ...
    'Command inhibited', ...
    'Safe command asserted', ...
    'Quiescence confirmed'};
startupEnablePrerequisiteNames = { ...
    'Power on', ...
    'Controller online', ...
    'P08 contract qualified', ...
    'P08 input eligible', ...
    'Command inhibited', ...
    'Safe command asserted'};
shutdownPowerPrerequisiteNames = { ...
    'Command inhibited', ...
    'Safe command asserted', ...
    'Actuator disabled', ...
    'Quiescence confirmed', ...
    'P08 interface closed'};

cancellationObserved = any(strcmp(eventMode, ...
    {'cancellation','cancellation-timeout-tie'}));
timeoutObserved = any(strcmp(eventMode, ...
    {'timeout','cancellation-timeout-tie'}));
eventObserved = cancellationObserved || timeoutObserved;
tieResolvedToCancellation = strcmp(eventMode,'cancellation-timeout-tie');

powerOn = false;
controllerOnline = false;
interfaceQualified = false;
actuatorEnabled = false;
commandInhibited = true;
safeCommandAsserted = true;
quiescenceConfirmed = true;

startupActionEvaluated = false(1,actionCount);
startupPreconditionPass = false(1,actionCount);
startupPostconditionPass = false(1,actionCount);
startupStepPass = false(1,actionCount);
startupHazard = false(1,actionCount);
startupStateTrace = NaN(actionCount,stateCount);
startupEnablePrerequisitePass = false(1,6);

for k = 1:actionCount
    if eventObserved && k > eventCheckpointAction
        break;
    end
    startupActionEvaluated(k) = true;
    action = startupActionNames{k};
    switch action
        case 'assert-command-inhibit'
            preconditionPass = true;
            commandInhibited = true;
            safeCommandAsserted = true;
            postconditionPass = commandInhibited && safeCommandAsserted;
        case 'energize-power'
            preconditionPass = commandInhibited && ...
                safeCommandAsserted && ~actuatorEnabled;
            powerOn = true;
            postconditionPass = powerOn;
        case 'boot-controller'
            preconditionPass = powerOn && commandInhibited;
            controllerOnline = true;
            postconditionPass = controllerOnline;
        case 'qualify-p08-interface'
            preconditionPass = powerOn && controllerOnline && ...
                p08ContractConformant;
            interfaceQualified = powerOn && controllerOnline && ...
                p08ContractConformant;
            postconditionPass = interfaceQualified;
        case 'enable-actuator'
            startupEnablePrerequisitePass = [powerOn controllerOnline ...
                interfaceQualified p08InputEligible commandInhibited ...
                safeCommandAsserted];
            preconditionPass = all(startupEnablePrerequisitePass);
            actuatorEnabled = true;
            quiescenceConfirmed = false;
            postconditionPass = actuatorEnabled;
        case 'release-command-inhibit'
            preconditionPass = powerOn && controllerOnline && ...
                interfaceQualified && p08InputEligible && ...
                actuatorEnabled && commandInhibited && ...
                safeCommandAsserted;
            commandInhibited = false;
            safeCommandAsserted = false;
            postconditionPass = ~commandInhibited && ...
                ~safeCommandAsserted;
    end
    startupPreconditionPass(k) = preconditionPass;
    startupPostconditionPass(k) = postconditionPass;
    startupStepPass(k) = preconditionPass && postconditionPass;
    startupHazard(k) = ~startupStepPass(k);
    startupStateTrace(k,:) = stateVector(powerOn,controllerOnline, ...
        interfaceQualified,actuatorEnabled,commandInhibited, ...
        safeCommandAsserted,quiescenceConfirmed);
end

startupCompleted = all(startupActionEvaluated);
startupFinalState = stateVector(powerOn,controllerOnline, ...
    interfaceQualified,actuatorEnabled,commandInhibited, ...
    safeCommandAsserted,quiescenceConfirmed);
startupFinalRunning = startupCompleted && powerOn && controllerOnline && ...
    interfaceQualified && p08InputEligible && actuatorEnabled && ...
    ~commandInhibited && ~safeCommandAsserted;
startupOrderValid = startupCompleted && all(startupStepPass);
if startupActionEvaluated(startupEnablePosition)
    startupEnableMissingPrerequisiteCount = ...
        sum(~startupEnablePrerequisitePass);
else
    startupEnableMissingPrerequisiteCount = NaN;
end

rollbackActionExecuted = false(1,rollbackActionCount);
rollbackPreconditionPass = false(1,rollbackActionCount);
rollbackPostconditionPass = false(1,rollbackActionCount);
rollbackStepPass = false(1,rollbackActionCount);
rollbackHazard = false(1,rollbackActionCount);
rollbackStateTrace = NaN(rollbackActionCount,stateCount);
rollbackPerformed = false;
rollbackSafeHold = false;

shutdownActionEvaluated = false(1,actionCount);
shutdownPreconditionPass = false(1,actionCount);
shutdownPostconditionPass = false(1,actionCount);
shutdownStepPass = false(1,actionCount);
shutdownHazard = false(1,actionCount);
shutdownStateTrace = NaN(actionCount,stateCount);
shutdownPowerPrerequisitePass = false(1,5);
unsafePowerRemoval = false;

if eventObserved
    rollbackPerformed = true;
    for k = 1:rollbackActionCount
        rollbackActionExecuted(k) = true;
        switch rollbackActionNames{k}
            case 'inhibit-new-commands'
                preconditionPass = true;
                commandInhibited = true;
                postconditionPass = commandInhibited;
            case 'command-safe-output'
                preconditionPass = commandInhibited;
                safeCommandAsserted = true;
                postconditionPass = safeCommandAsserted;
            case 'disable-actuator'
                preconditionPass = commandInhibited && ...
                    safeCommandAsserted;
                if ~strcmp(faultMode,'actuator-stuck-on')
                    actuatorEnabled = false;
                end
                postconditionPass = ~actuatorEnabled;
            case 'confirm-quiescence-and-isolate'
                preconditionPass = commandInhibited && ...
                    safeCommandAsserted && ~actuatorEnabled;
                quiescenceConfirmed = preconditionPass && ...
                    ~strcmp(faultMode,'quiescence-not-confirmed');
                interfaceQualified = false;
                controllerOnline = false;
                postconditionPass = quiescenceConfirmed && ...
                    ~interfaceQualified && ~controllerOnline;
            case 'remove-power'
                preconditionPass = commandInhibited && ...
                    safeCommandAsserted && ~actuatorEnabled && ...
                    quiescenceConfirmed && ~interfaceQualified;
                powerOn = false;
                postconditionPass = ~powerOn;
        end
        rollbackPreconditionPass(k) = preconditionPass;
        rollbackPostconditionPass(k) = postconditionPass;
        rollbackStepPass(k) = preconditionPass && postconditionPass;
        rollbackHazard(k) = ~rollbackStepPass(k);
        rollbackStateTrace(k,:) = stateVector(powerOn, ...
            controllerOnline,interfaceQualified,actuatorEnabled, ...
            commandInhibited,safeCommandAsserted,quiescenceConfirmed);
    end
    rollbackSafeHold = all(rollbackStepPass) && ...
        ~powerOn && ~controllerOnline && ...
        ~interfaceQualified && ~actuatorEnabled && commandInhibited && ...
        safeCommandAsserted && quiescenceConfirmed;
else
    for k = 1:actionCount
        shutdownActionEvaluated(k) = true;
        action = shutdownActionNames{k};
        switch action
            case 'inhibit-new-commands'
                preconditionPass = true;
                commandInhibited = true;
                postconditionPass = commandInhibited;
            case 'command-safe-output'
                preconditionPass = commandInhibited;
                safeCommandAsserted = true;
                postconditionPass = safeCommandAsserted;
            case 'disable-actuator'
                preconditionPass = commandInhibited && ...
                    safeCommandAsserted;
                if ~strcmp(faultMode,'actuator-stuck-on')
                    actuatorEnabled = false;
                end
                postconditionPass = ~actuatorEnabled;
            case 'confirm-quiescence'
                preconditionPass = commandInhibited && ...
                    safeCommandAsserted && ~actuatorEnabled;
                quiescenceConfirmed = preconditionPass && ...
                    ~strcmp(faultMode,'quiescence-not-confirmed');
                postconditionPass = quiescenceConfirmed;
            case 'close-p08-interface'
                preconditionPass = commandInhibited && ...
                    ~actuatorEnabled && quiescenceConfirmed;
                interfaceQualified = false;
                postconditionPass = ~interfaceQualified;
            case 'remove-power'
                shutdownPowerPrerequisitePass = [commandInhibited ...
                    safeCommandAsserted ~actuatorEnabled ...
                    quiescenceConfirmed ~interfaceQualified];
                preconditionPass = all(shutdownPowerPrerequisitePass);
                unsafePowerRemoval = ~preconditionPass;
                powerOn = false;
                controllerOnline = false;
                postconditionPass = ~powerOn && ~controllerOnline;
        end
        shutdownPreconditionPass(k) = preconditionPass;
        shutdownPostconditionPass(k) = postconditionPass;
        shutdownStepPass(k) = preconditionPass && postconditionPass;
        shutdownHazard(k) = ~shutdownStepPass(k);
        shutdownStateTrace(k,:) = stateVector(powerOn, ...
            controllerOnline,interfaceQualified,actuatorEnabled, ...
            commandInhibited,safeCommandAsserted,quiescenceConfirmed);
    end
end

shutdownCompleted = all(shutdownActionEvaluated);
if shutdownCompleted
    shutdownFinalState = stateVector(powerOn,controllerOnline, ...
        interfaceQualified,actuatorEnabled,commandInhibited, ...
        safeCommandAsserted,quiescenceConfirmed);
else
    shutdownFinalState = NaN(1,stateCount);
end
shutdownFinalSafeOff = shutdownCompleted && ~powerOn && ...
    ~controllerOnline && ~interfaceQualified && ~actuatorEnabled && ...
    commandInhibited && safeCommandAsserted && quiescenceConfirmed;
shutdownOrderValid = shutdownCompleted && all(shutdownStepPass);
if shutdownActionEvaluated(shutdownPowerOffPosition)
    shutdownPowerMissingPrerequisiteCount = ...
        sum(~shutdownPowerPrerequisitePass);
else
    shutdownPowerMissingPrerequisiteCount = NaN;
end

sequenceEvaluated = startupCompleted && shutdownCompleted;
strictLifecycleAccepted = sequenceEvaluated && startupOrderValid && ...
    startupFinalRunning && shutdownOrderValid && shutdownFinalSafeOff;
snapshotLifecycleAccepted = sequenceEvaluated && ...
    startupFinalRunning && shutdownFinalSafeOff;
if strcmp(assessmentMode,'strict-order')
    reportedLifecycleAccepted = strictLifecycleAccepted;
else
    reportedLifecycleAccepted = snapshotLifecycleAccepted;
end
falseApproval = sequenceEvaluated && reportedLifecycleAccepted && ...
    ~strictLifecycleAccepted;
assessmentDecisionCorrect = sequenceEvaluated && ...
    (reportedLifecycleAccepted == strictLifecycleAccepted);

startupViolationCount = sum(startupActionEvaluated & ~startupStepPass);
shutdownViolationCount = sum(shutdownActionEvaluated & ~shutdownStepPass);
rollbackViolationCount = sum(rollbackActionExecuted & ~rollbackStepPass);
totalViolationCount = startupViolationCount + shutdownViolationCount + ...
    rollbackViolationCount;

if cancellationObserved && rollbackSafeHold
    terminalStatus = 'cancelled-safe-hold';
elseif cancellationObserved
    terminalStatus = 'cancelled-rollback-incomplete';
elseif timeoutObserved && rollbackSafeHold
    terminalStatus = 'timed-out-safe-hold';
elseif timeoutObserved
    terminalStatus = 'timed-out-rollback-incomplete';
elseif strictLifecycleAccepted
    terminalStatus = 'completed-safe-off';
else
    terminalStatus = 'completed-with-hazard';
end

if cancellationObserved
    failureMode = 'startup-cancelled';
elseif timeoutObserved
    failureMode = 'startup-timeout';
elseif ~p08ContractConformant
    failureMode = 'p08-contract-not-conformant';
elseif ~p08InputEligible
    failureMode = 'p08-input-not-eligible';
elseif ~startupPreconditionPass(startupEnablePosition)
    failureMode = 'startup-enable-before-prerequisites';
elseif ~startupOrderValid || ~startupFinalRunning
    failureMode = 'startup-sequence-invalid';
elseif strcmp(faultMode,'actuator-stuck-on')
    failureMode = 'actuator-disable-failed';
elseif strcmp(faultMode,'quiescence-not-confirmed')
    failureMode = 'quiescence-not-confirmed';
elseif unsafePowerRemoval
    failureMode = 'power-removed-before-safe';
elseif ~shutdownOrderValid || ~shutdownFinalSafeOff
    failureMode = 'shutdown-sequence-invalid';
else
    failureMode = 'none';
end
if falseApproval
    reportingFailureMode = 'final-state-only-false-approval';
else
    reportingFailureMode = 'none';
end
if ~eventObserved || rollbackSafeHold
    rollbackFailureMode = 'none';
elseif ~rollbackPostconditionPass(3)
    rollbackFailureMode = 'actuator-disable-failed';
else
    rollbackFailureMode = 'quiescence-not-confirmed';
end
terminalOutcomeHandled = eventObserved || sequenceEvaluated;

out = struct();
out.inputs = struct('startupEnablePosition',startupEnablePosition, ...
    'shutdownPowerOffPosition',shutdownPowerOffPosition, ...
    'p08ContractConformant',p08ContractConformant, ...
    'p08InputEligible',p08InputEligible,'faultMode',faultMode, ...
    'eventMode',eventMode,'assessmentMode',assessmentMode);
out.startupActionNames = startupActionNames;
out.shutdownActionNames = shutdownActionNames;
out.rollbackActionNames = rollbackActionNames;
out.stateNames = stateNames;
out.startupEnablePrerequisiteNames = startupEnablePrerequisiteNames;
out.shutdownPowerPrerequisiteNames = shutdownPowerPrerequisiteNames;
out.startupActionEvaluated = startupActionEvaluated;
out.startupPreconditionPass = startupPreconditionPass;
out.startupPostconditionPass = startupPostconditionPass;
out.startupStepPass = startupStepPass;
out.startupHazard = startupHazard;
out.startupStateTrace = startupStateTrace;
out.startupEnablePrerequisitePass = startupEnablePrerequisitePass;
out.startupEnableMissingPrerequisiteCount = ...
    startupEnableMissingPrerequisiteCount;
out.startupCompleted = startupCompleted;
out.startupFinalState = startupFinalState;
out.startupFinalRunning = startupFinalRunning;
out.startupOrderValid = startupOrderValid;
out.shutdownActionEvaluated = shutdownActionEvaluated;
out.shutdownPreconditionPass = shutdownPreconditionPass;
out.shutdownPostconditionPass = shutdownPostconditionPass;
out.shutdownStepPass = shutdownStepPass;
out.shutdownHazard = shutdownHazard;
out.shutdownStateTrace = shutdownStateTrace;
out.shutdownPowerPrerequisitePass = shutdownPowerPrerequisitePass;
out.shutdownPowerMissingPrerequisiteCount = ...
    shutdownPowerMissingPrerequisiteCount;
out.unsafePowerRemoval = unsafePowerRemoval;
out.shutdownCompleted = shutdownCompleted;
out.shutdownFinalState = shutdownFinalState;
out.shutdownFinalSafeOff = shutdownFinalSafeOff;
out.shutdownOrderValid = shutdownOrderValid;
out.rollbackActionExecuted = rollbackActionExecuted;
out.rollbackPreconditionPass = rollbackPreconditionPass;
out.rollbackPostconditionPass = rollbackPostconditionPass;
out.rollbackStepPass = rollbackStepPass;
out.rollbackHazard = rollbackHazard;
out.rollbackStateTrace = rollbackStateTrace;
out.rollbackPerformed = rollbackPerformed;
out.rollbackSafeHold = rollbackSafeHold;
out.cancellationObserved = cancellationObserved;
out.timeoutObserved = timeoutObserved;
out.eventObserved = eventObserved;
out.tieResolvedToCancellation = tieResolvedToCancellation;
out.sequenceEvaluated = sequenceEvaluated;
out.strictLifecycleAccepted = strictLifecycleAccepted;
out.snapshotLifecycleAccepted = snapshotLifecycleAccepted;
out.reportedLifecycleAccepted = reportedLifecycleAccepted;
out.falseApproval = falseApproval;
out.assessmentDecisionCorrect = assessmentDecisionCorrect;
out.startupViolationCount = startupViolationCount;
out.shutdownViolationCount = shutdownViolationCount;
out.rollbackViolationCount = rollbackViolationCount;
out.totalViolationCount = totalViolationCount;
out.terminalStatus = terminalStatus;
out.failureMode = failureMode;
out.reportingFailureMode = reportingFailureMode;
out.rollbackFailureMode = rollbackFailureMode;
out.terminalOutcomeHandled = terminalOutcomeHandled;
out.actionCount = actionCount;
out.stateCount = stateCount;
out.rollbackActionCount = rollbackActionCount;
out.eventCheckpointAction = eventCheckpointAction;
out.minimumStartupEnablePosition = minimumStartupEnablePosition;
out.maximumStartupEnablePosition = maximumStartupEnablePosition;
out.minimumShutdownPowerOffPosition = minimumShutdownPowerOffPosition;
out.maximumShutdownPowerOffPosition = maximumShutdownPowerOffPosition;
end

function actions = insertAction(baseActions,insertedAction,position)
actions = [baseActions(1:position-1) {insertedAction} ...
    baseActions(position:end)];
end

function values = stateVector(powerOn,controllerOnline, ...
    interfaceQualified,actuatorEnabled,commandInhibited, ...
    safeCommandAsserted,quiescenceConfirmed)
values = double([powerOn controllerOnline interfaceQualified ...
    actuatorEnabled commandInhibited safeCommandAsserted ...
    quiescenceConfirmed]);
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
