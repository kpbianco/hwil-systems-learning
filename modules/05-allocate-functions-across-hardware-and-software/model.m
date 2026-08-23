function out = model(controlOwner,supervisionOwner,softwareCapacity, ...
    hardwareCapacity,softwareState,eventMode,assessmentMode)
%MODEL Deterministic hardware/software allocation assessment for P05.
%   P04's ten functions keep their identity. P05 assigns each function to
%   exactly one execution domain, sums transparent resource costs, and asks
%   whether cancellation/deadline supervision survives an application-
%   software stall. The governing resource equations are
%
%     D_sw = sum(c_sw(i)) for functions owned by software
%     D_hw = sum(c_hw(i)) for functions owned by hardware
%     margin_domain = capacity_domain - demand_domain
%
%   Work units and allocation units are instructional design quantities;
%   they are not execution times, path delays, WCET, jitter, or device data.

if nargin < 1, controlOwner = 'software'; end
if nargin < 2, supervisionOwner = 'hardware'; end
if nargin < 3, softwareCapacity = 30; end
if nargin < 4, hardwareCapacity = 40; end
if nargin < 5, softwareState = 'available'; end
if nargin < 6, eventMode = 'none'; end
if nargin < 7, assessmentMode = 'complete'; end

controlOwner = normalizeChoice(controlOwner,{'software','hardware'}, ...
    'P05:InvalidControlOwner','controlOwner');
supervisionOwner = normalizeChoice(supervisionOwner,{'software','hardware'}, ...
    'P05:InvalidSupervisionOwner','supervisionOwner');
softwareState = normalizeChoice(softwareState,{'available','stalled'}, ...
    'P05:InvalidSoftwareState','softwareState');
eventMode = normalizeChoice(eventMode,{'none','cancellation','deadline'}, ...
    'P05:InvalidEventMode','eventMode');
assessmentMode = normalizeChoice(assessmentMode,{'complete','resource-only'}, ...
    'P05:InvalidAssessmentMode','assessmentMode');

softwareCapacity = normalizeCapacity(softwareCapacity,'softwareCapacity');
hardwareCapacity = normalizeCapacity(hardwareCapacity,'hardwareCapacity');
maxCapacityUnits = 1000;
if softwareCapacity > maxCapacityUnits || hardwareCapacity > maxCapacityUnits
    error('P05:ResourceBound', ...
        'Declared capacities must not exceed %.0f domain units.',maxCapacityUnits);
end

functionNames = { ...
    'Capture intent', ...
    'Validate authority', ...
    'Observe position', ...
    'Compute error', ...
    'Generate correction', ...
    'Update physical state', ...
    'Confirm requested behavior', ...
    'Handle cancellation', ...
    'Enforce deadline', ...
    'Report outcome'};
functionInputs = { ...
    'request and cancellation', ...
    'requested angle and authority', ...
    'physical position', ...
    'accepted target and observation', ...
    'signed error and response fraction', ...
    'bounded correction', ...
    'request error, tolerance, and evidence depth', ...
    'cancellation and transaction state', ...
    'elapsed time and deadline', ...
    'terminal state and evidence'};
functionOutputs = { ...
    'preserved requested angle', ...
    'accepted or rejected request', ...
    'observed position in deg', ...
    'signed error in deg', ...
    'correction in deg per update', ...
    'new physical position in deg', ...
    'completion-proxy decision', ...
    'cancelled terminal state and safe-hold requirement', ...
    'deadline-missed terminal state and safe-hold requirement', ...
    'operator-visible result'};
functionFailureModes = { ...
    'intent lost', ...
    'out-of-authority request passes downstream', ...
    'state is unobservable', ...
    'wrong target or sign', ...
    'unstable or ineffective correction', ...
    'requested change not produced', ...
    'premature or missing confirmation', ...
    'cancellation ignored', ...
    'late result accepted', ...
    'local success misreported as system success'};
allocationReasons = { ...
    'fixed software-facing request boundary'; ...
    'supervision group selected by learner'; ...
    'fixed hardware sensor endpoint'; ...
    'control group selected by learner'; ...
    'control group selected by learner'; ...
    'fixed hardware actuation endpoint'; ...
    'fixed software evidence policy'; ...
    'supervision group selected by learner'; ...
    'supervision group selected by learner'; ...
    'fixed software-facing report boundary'};

% Costs are deliberately visible and fixed in P04 function order. A zero
% denotes an unsupported domain for a fixed binding, not a free function.
softwareCostUnitsPerUpdate = [2; 2; 0; 6; 8; 0; 4; 2; 2; 2];
hardwareCostAllocationUnits = [0; 3; 5; 7; 9; 8; 0; 3; 3; 0];
functionCount = numel(functionNames);
fixedSoftwareIndices = [1 7 10];
fixedHardwareIndices = [3 6];
controlFunctionIndices = [4 5];
supervisionFunctionIndices = [2 8 9];

functionOwner = repmat({'unassigned'},functionCount,1);
functionOwner(fixedSoftwareIndices) = repmat({'software'}, ...
    numel(fixedSoftwareIndices),1);
functionOwner(fixedHardwareIndices) = repmat({'hardware'}, ...
    numel(fixedHardwareIndices),1);
functionOwner(controlFunctionIndices) = repmat({controlOwner}, ...
    numel(controlFunctionIndices),1);
functionOwner(supervisionFunctionIndices) = repmat({supervisionOwner}, ...
    numel(supervisionFunctionIndices),1);
if any(strcmp(functionOwner,'unassigned'))
    error('P05:InternalAllocation','Every P04 function must have one owner.');
end

softwareOwned = strcmp(functionOwner,'software');
hardwareOwned = strcmp(functionOwner,'hardware');
ownerCountPerFunction = double(softwareOwned) + double(hardwareOwned);
ownerMatrix = [double(softwareOwned),double(hardwareOwned)];
bindingValid = all(softwareOwned(fixedSoftwareIndices)) && ...
    all(hardwareOwned(fixedHardwareIndices));

softwareContributionUnits = softwareCostUnitsPerUpdate.*double(softwareOwned);
hardwareContributionUnits = hardwareCostAllocationUnits.*double(hardwareOwned);
softwareDemandUnitsPerUpdate = sum(softwareContributionUnits);
hardwareDemandAllocationUnits = sum(hardwareContributionUnits);
softwareMarginUnitsPerUpdate = softwareCapacity - softwareDemandUnitsPerUpdate;
hardwareMarginAllocationUnits = hardwareCapacity - hardwareDemandAllocationUnits;
softwareResourceFit = softwareDemandUnitsPerUpdate <= softwareCapacity;
hardwareResourceFit = hardwareDemandAllocationUnits <= hardwareCapacity;
nominalResourceFit = softwareResourceFit && hardwareResourceFit;
softwareUtilizationPercent = utilizationPercent( ...
    softwareDemandUnitsPerUpdate,softwareCapacity);
hardwareUtilizationPercent = utilizationPercent( ...
    hardwareDemandAllocationUnits,hardwareCapacity);

softwareAvailable = strcmp(softwareState,'available');
softwareExecutionAvailable = softwareAvailable && softwareResourceFit;
hardwareExecutionAvailable = hardwareResourceFit;
% Conservatively treat every function in an overloaded owner domain as
% unavailable; P05 has no scheduler from which to infer a partial subset.
functionAvailable = ...
    (softwareOwned & softwareExecutionAvailable) | ...
    (hardwareOwned & hardwareExecutionAvailable);
allRequiredFunctionsAvailable = all(functionAvailable);
lostFunctionNames = reshape(functionNames(~functionAvailable),1,[]);
softwareFaultIndependentSupervision = ...
    all(hardwareOwned(supervisionFunctionIndices));

eventFunctionIndex = 0;
eventGuardName = 'none';
if strcmp(eventMode,'cancellation')
    eventFunctionIndex = 8;
    eventGuardName = functionNames{eventFunctionIndex};
elseif strcmp(eventMode,'deadline')
    eventFunctionIndex = 9;
    eventGuardName = functionNames{eventFunctionIndex};
end
if eventFunctionIndex == 0
    eventGuardAvailable = true;
    eventHandled = true;
    safeHoldRequestAvailable = false;
    scenarioRequirementMet = allRequiredFunctionsAvailable;
else
    eventGuardAvailable = functionAvailable(eventFunctionIndex);
    eventHandled = eventGuardAvailable;
    safeHoldRequestAvailable = eventGuardAvailable;
    scenarioRequirementMet = eventHandled;
end

% This contract is an allocation/resource/fault-boundary decision. During
% cancellation or deadline injection it means the named guard remains able
% to emit a safe-hold request; it never means the full transaction succeeded
% or that physical safe hold was commanded or achieved.
allocationContractMet = nominalResourceFit && bindingValid && ...
    softwareFaultIndependentSupervision && scenarioRequirementMet;
resourceOnlyDecision = nominalResourceFit && bindingValid;
if strcmp(assessmentMode,'complete')
    reportedFeasible = allocationContractMet;
else
    reportedFeasible = resourceOnlyDecision;
end
falseFeasible = reportedFeasible && ~allocationContractMet;
if reportedFeasible
    decisionStatus = 'approved';
else
    decisionStatus = 'rejected';
end

if ~nominalResourceFit
    scenarioStatus = 'resource-overload';
elseif strcmp(eventMode,'none')
    if allRequiredFunctionsAvailable
        scenarioStatus = 'nominal-ready';
    else
        scenarioStatus = 'software-common-mode-loss';
    end
elseif eventGuardAvailable
    scenarioStatus = [eventMode '-contained'];
else
    scenarioStatus = [eventMode '-unhandled'];
end

if ~softwareResourceFit && ~hardwareResourceFit
    failureMode = 'dual-capacity-exceeded';
elseif ~softwareResourceFit
    failureMode = 'software-capacity-exceeded';
elseif ~hardwareResourceFit
    failureMode = 'hardware-capacity-exceeded';
elseif ~bindingValid
    failureMode = 'fixed-binding-violated';
elseif ~strcmp(eventMode,'none') && ~eventHandled
    failureMode = [eventMode '-unhandled'];
elseif strcmp(eventMode,'none') && ~allRequiredFunctionsAvailable
    failureMode = 'required-functions-unavailable';
elseif ~softwareFaultIndependentSupervision
    failureMode = 'common-mode-supervision';
else
    failureMode = 'none';
end

out = struct();
out.inputs = struct('controlOwner',controlOwner, ...
    'supervisionOwner',supervisionOwner, ...
    'softwareCapacity',softwareCapacity, ...
    'hardwareCapacity',hardwareCapacity, ...
    'softwareState',softwareState, ...
    'eventMode',eventMode, ...
    'assessmentMode',assessmentMode);
out.functionNames = functionNames;
out.functionInputs = functionInputs;
out.functionOutputs = functionOutputs;
out.functionFailureModes = functionFailureModes;
out.allocationReasons = allocationReasons;
out.functionOwner = functionOwner;
out.functionOwnerCodes = double(hardwareOwned);
out.ownerMatrix = ownerMatrix;
out.ownerCountPerFunction = ownerCountPerFunction;
out.functionAvailable = functionAvailable;
out.lostFunctionNames = lostFunctionNames;
out.softwareCostUnitsPerUpdate = softwareCostUnitsPerUpdate;
out.hardwareCostAllocationUnits = hardwareCostAllocationUnits;
out.softwareContributionUnits = softwareContributionUnits;
out.hardwareContributionUnits = hardwareContributionUnits;
out.softwareDemandUnitsPerUpdate = softwareDemandUnitsPerUpdate;
out.hardwareDemandAllocationUnits = hardwareDemandAllocationUnits;
out.softwareMarginUnitsPerUpdate = softwareMarginUnitsPerUpdate;
out.hardwareMarginAllocationUnits = hardwareMarginAllocationUnits;
out.softwareUtilizationPercent = softwareUtilizationPercent;
out.hardwareUtilizationPercent = hardwareUtilizationPercent;
out.softwareResourceFit = softwareResourceFit;
out.hardwareResourceFit = hardwareResourceFit;
out.nominalResourceFit = nominalResourceFit;
out.bindingValid = bindingValid;
out.softwareAvailable = softwareAvailable;
out.softwareExecutionAvailable = softwareExecutionAvailable;
out.hardwareExecutionAvailable = hardwareExecutionAvailable;
out.allRequiredFunctionsAvailable = allRequiredFunctionsAvailable;
out.softwareFaultIndependentSupervision = ...
    softwareFaultIndependentSupervision;
out.eventFunctionIndex = eventFunctionIndex;
out.eventGuardName = eventGuardName;
out.eventGuardAvailable = eventGuardAvailable;
out.eventHandled = eventHandled;
out.safeHoldRequestAvailable = safeHoldRequestAvailable;
out.scenarioRequirementMet = scenarioRequirementMet;
out.allocationContractMet = allocationContractMet;
out.resourceOnlyDecision = resourceOnlyDecision;
out.reportedFeasible = reportedFeasible;
out.falseFeasible = falseFeasible;
out.decisionStatus = decisionStatus;
out.scenarioStatus = scenarioStatus;
out.failureMode = failureMode;
out.fixedSoftwareIndices = fixedSoftwareIndices;
out.fixedHardwareIndices = fixedHardwareIndices;
out.controlFunctionIndices = controlFunctionIndices;
out.supervisionFunctionIndices = supervisionFunctionIndices;
out.functionCount = functionCount;
out.domainCount = 2;
out.maxCapacityUnits = maxCapacityUnits;
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

function normalized = normalizeCapacity(value,inputName)
if ~(isnumeric(value) && isscalar(value) && isreal(value) && ...
        isfinite(value) && value >= 0)
    error('P05:InvalidCapacity', ...
        '%s must be a finite nonnegative numeric scalar.',inputName);
end
normalized = double(value);
end

function percent = utilizationPercent(demand,capacity)
if capacity == 0
    if demand == 0
        percent = 0;
    else
        percent = Inf;
    end
else
    percent = 100*demand/capacity;
end
end
