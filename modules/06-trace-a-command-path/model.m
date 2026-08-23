function out = model(requestedAngleDeg,observedAngleDeg,authorityLimitDeg, ...
    responseFraction,openBoundary,eventMode,assessmentMode)
%MODEL Deterministic command-path reachability and value trace for P06.
%   P04 defined the functions and P05 allocated their owners. P06 follows
%   one logical command through those owned handoffs. The inherited visible
%   calculations are
%
%     error_deg = accepted_target_deg - observed_position_deg
%     correction_deg_per_update = response_fraction * error_deg
%
%   Boundary state controls reachability. Cancellation and timeout are
%   already-asserted logical guard inputs before the actuator handoff; no
%   elapsed time, scheduling, retry timing, jitter, physical motion, or
%   achieved safe state is modeled.

if nargin < 1, requestedAngleDeg = 30; end
if nargin < 2, observedAngleDeg = 0; end
if nargin < 3, authorityLimitDeg = 45; end
if nargin < 4, responseFraction = 0.35; end
if nargin < 5, openBoundary = 'none'; end
if nargin < 6, eventMode = 'none'; end
if nargin < 7, assessmentMode = 'endpoint-receipt'; end

maxAbsAngleDeg = 180;
requestedAngleDeg = normalizeBoundedScalar(requestedAngleDeg, ...
    'requestedAngleDeg',-maxAbsAngleDeg,maxAbsAngleDeg,'P06:InvalidAngle');
observedAngleDeg = normalizeBoundedScalar(observedAngleDeg, ...
    'observedAngleDeg',-maxAbsAngleDeg,maxAbsAngleDeg,'P06:InvalidAngle');
authorityLimitDeg = normalizeBoundedScalar(authorityLimitDeg, ...
    'authorityLimitDeg',0,maxAbsAngleDeg,'P06:InvalidAuthority');
if authorityLimitDeg == 0
    error('P06:InvalidAuthority', ...
        'authorityLimitDeg must be positive and at most %.0f deg.', ...
        maxAbsAngleDeg);
end
responseFraction = normalizeBoundedScalar(responseFraction, ...
    'responseFraction',0,1,'P06:InvalidResponseFraction');
openBoundary = normalizeChoice(openBoundary, ...
    {'none','request-to-authority','authority-to-error', ...
    'error-to-correction','correction-to-actuator'}, ...
    'P06:InvalidBoundary','openBoundary');
eventMode = normalizeChoice(eventMode, ...
    {'none','cancellation','timeout','cancellation-timeout-tie'}, ...
    'P06:InvalidEventMode','eventMode');
assessmentMode = normalizeChoice(assessmentMode, ...
    {'endpoint-receipt','dispatch-only'}, ...
    'P06:InvalidAssessmentMode','assessmentMode');

stageNames = { ...
    'Capture intent', ...
    'Validate authority', ...
    'Compute error', ...
    'Generate correction', ...
    'Update physical state input latch'};
stageOwners = { ...
    'application-software', ...
    'independent-hardware', ...
    'application-software', ...
    'application-software', ...
    'hardware-interface'};
stageUnits = {'deg','deg','deg','deg/update','deg/update'};
stageQuestions = { ...
    'Was the operator target captured without changing it?', ...
    'Was the target inside the inherited authority envelope?', ...
    'Was error formed from the accepted target and named observation?', ...
    'Was the bounded correction generated from that error?', ...
    'Did the hardware-side input latch receive the correction?'};
boundaryNames = { ...
    'request-to-authority', ...
    'authority-to-error', ...
    'error-to-correction', ...
    'correction-to-actuator'};
boundaryLabels = { ...
    'Capture intent -> Validate authority', ...
    'Validate authority -> Compute error', ...
    'Compute error -> Generate correction', ...
    'Generate correction -> actuator input latch'};
stageCount = numel(stageNames);
boundaryCount = numel(boundaryNames);

stageReached = false(1,stageCount);
stageOutputValue = NaN(1,stageCount);
boundaryAttempted = false(1,boundaryCount);
boundaryCrossed = false(1,boundaryCount);
boundaryOpen = strcmp(openBoundary,boundaryNames);

stageReached(1) = true;
stageOutputValue(1) = requestedAngleDeg;

boundaryAttempted(1) = stageReached(1);
if boundaryAttempted(1) && ~boundaryOpen(1)
    boundaryCrossed(1) = true;
    stageReached(2) = true;
    stageOutputValue(2) = requestedAngleDeg;
end

authorityValid = abs(requestedAngleDeg) <= authorityLimitDeg;
authorityMarginDeg = authorityLimitDeg - abs(requestedAngleDeg);
if stageReached(2) && authorityValid
    boundaryAttempted(2) = true;
    if ~boundaryOpen(2)
        boundaryCrossed(2) = true;
        stageReached(3) = true;
    end
end

acceptedTargetDeg = NaN;
errorDeg = NaN;
if stageReached(2) && authorityValid
    acceptedTargetDeg = requestedAngleDeg;
end
if stageReached(3)
    errorDeg = acceptedTargetDeg - observedAngleDeg;
    stageOutputValue(3) = errorDeg;
    boundaryAttempted(3) = true;
    if ~boundaryOpen(3)
        boundaryCrossed(3) = true;
        stageReached(4) = true;
    end
end

correctionDegPerUpdate = NaN;
localDispatchObserved = false;
eventGuardReached = false;
eventObserved = false;
cancellationObserved = false;
timeoutObserved = false;
tieResolvedToCancellation = false;
safeHoldRequired = false;
safeHoldRequestAvailable = false;
if stageReached(4)
    correctionDegPerUpdate = responseFraction*errorDeg;
    stageOutputValue(4) = correctionDegPerUpdate;
    localDispatchObserved = true;
    eventGuardReached = true;
    boundaryAttempted(4) = true;
    eventObserved = ~strcmp(eventMode,'none');
    cancellationObserved = any(strcmp(eventMode, ...
        {'cancellation','cancellation-timeout-tie'}));
    timeoutObserved = any(strcmp(eventMode, ...
        {'timeout','cancellation-timeout-tie'}));
    tieResolvedToCancellation = strcmp(eventMode,'cancellation-timeout-tie');
    if eventObserved
        safeHoldRequired = true;
        safeHoldRequestAvailable = true;
    elseif ~boundaryOpen(4)
        boundaryCrossed(4) = true;
        stageReached(5) = true;
        stageOutputValue(5) = correctionDegPerUpdate;
    end
end

if stageReached(2) && ~authorityValid
    safeHoldRequired = true;
    safeHoldRequestAvailable = true;
end

actuatorCommandReceived = stageReached(5);
payloadPreservedToEndpoint = actuatorCommandReceived && ...
    stageOutputValue(5) == stageOutputValue(4);
firstOpenBoundary = find(boundaryAttempted & boundaryOpen,1,'first');
if isempty(firstOpenBoundary), firstOpenBoundary = 0; end
deepestReachedStage = find(stageReached,1,'last');
crossedBoundaryCount = sum(boundaryCrossed);

if actuatorCommandReceived
    terminalStatus = 'delivered';
elseif stageReached(2) && ~authorityValid
    terminalStatus = 'authority-rejected';
elseif cancellationObserved
    terminalStatus = 'cancelled';
elseif timeoutObserved
    terminalStatus = 'timed-out';
elseif firstOpenBoundary > 0
    terminalStatus = 'boundary-open';
else
    terminalStatus = 'route-incomplete';
end

terminalOutcomeHandled = any(strcmp(terminalStatus, ...
    {'delivered','authority-rejected','cancelled','timed-out'}));
traceContractMet = terminalOutcomeHandled;
if strcmp(terminalStatus,'authority-rejected')
    failureMode = 'request-rejected';
elseif strcmp(terminalStatus,'cancelled')
    failureMode = 'cancelled';
elseif strcmp(terminalStatus,'timed-out')
    failureMode = 'timeout-observed';
elseif strcmp(terminalStatus,'boundary-open')
    failureMode = boundaryNames{firstOpenBoundary};
elseif strcmp(terminalStatus,'route-incomplete')
    failureMode = 'internal-route-incomplete';
else
    failureMode = 'none';
end

if strcmp(assessmentMode,'endpoint-receipt')
    reportedSuccess = actuatorCommandReceived;
else
    reportedSuccess = localDispatchObserved;
end
falseSuccess = reportedSuccess && ~actuatorCommandReceived;

out = struct();
out.inputs = struct('requestedAngleDeg',requestedAngleDeg, ...
    'observedAngleDeg',observedAngleDeg, ...
    'authorityLimitDeg',authorityLimitDeg, ...
    'responseFraction',responseFraction, ...
    'openBoundary',openBoundary,'eventMode',eventMode, ...
    'assessmentMode',assessmentMode);
out.stageNames = stageNames;
out.stageOwners = stageOwners;
out.stageUnits = stageUnits;
out.stageQuestions = stageQuestions;
out.boundaryNames = boundaryNames;
out.boundaryLabels = boundaryLabels;
out.stageReached = stageReached;
out.stageOutputValue = stageOutputValue;
out.boundaryAttempted = boundaryAttempted;
out.boundaryCrossed = boundaryCrossed;
out.boundaryOpen = boundaryOpen;
out.authorityValid = authorityValid;
out.authorityMarginDeg = authorityMarginDeg;
out.acceptedTargetDeg = acceptedTargetDeg;
out.errorDeg = errorDeg;
out.correctionDegPerUpdate = correctionDegPerUpdate;
out.localDispatchObserved = localDispatchObserved;
out.eventGuardReached = eventGuardReached;
out.eventObserved = eventObserved;
out.cancellationObserved = cancellationObserved;
out.timeoutObserved = timeoutObserved;
out.tieResolvedToCancellation = tieResolvedToCancellation;
out.safeHoldRequired = safeHoldRequired;
out.safeHoldRequestAvailable = safeHoldRequestAvailable;
out.actuatorCommandReceived = actuatorCommandReceived;
out.payloadPreservedToEndpoint = payloadPreservedToEndpoint;
out.terminalOutcomeHandled = terminalOutcomeHandled;
out.traceContractMet = traceContractMet;
out.reportedSuccess = reportedSuccess;
out.falseSuccess = falseSuccess;
out.terminalStatus = terminalStatus;
out.failureMode = failureMode;
out.firstOpenBoundary = firstOpenBoundary;
out.deepestReachedStage = deepestReachedStage;
out.crossedBoundaryCount = crossedBoundaryCount;
out.stageCount = stageCount;
out.boundaryCount = boundaryCount;
out.maxAbsAngleDeg = maxAbsAngleDeg;
end

function normalized = normalizeBoundedScalar(value,inputName,lowerBound, ...
    upperBound,errorId)
if ~(isnumeric(value) && isscalar(value) && isreal(value) && isfinite(value))
    error(errorId,'%s must be a finite real numeric scalar.',inputName);
end
normalized = double(value);
if normalized < lowerBound || normalized > upperBound
    error(errorId,'%s is outside its declared bounded range.',inputName);
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
