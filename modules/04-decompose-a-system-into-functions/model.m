function out = model(requestDeg,responseFraction,confirmationSamples, ...
    authorityDeg,toleranceDeg,deadlineMs,cancelAtMs,architectureMode)
%MODEL Deterministic functional decomposition of a rotary positioning request.
%   The model assigns observable input/output contracts to system functions
%   without allocating them to hardware or software. The transparent update is
%
%     position(k+1) = position(k) + responseFraction*(target-position(k))
%
%   and completion requires consecutive observations inside the request band.

if nargin < 1, requestDeg = 30; end
if nargin < 2, responseFraction = 0.35; end
if nargin < 3, confirmationSamples = 3; end
if nargin < 4, authorityDeg = 45; end
if nargin < 5, toleranceDeg = 0.5; end
if nargin < 6, deadlineMs = 1000; end
if nargin < 7, cancelAtMs = Inf; end
if nargin < 8, architectureMode = 'complete'; end

sampleTimeMs = 20;
horizonMs = 3000;
maxRequestMagnitudeDeg = 180;
maxAuthorityDeg = 180;
maxToleranceDeg = 30;
maxConfirmationSamples = 20;

validateattributes(requestDeg,{'numeric'}, ...
    {'scalar','real','finite'},mfilename,'requestDeg');
validateattributes(responseFraction,{'numeric'}, ...
    {'scalar','real','finite','>=',0,'<=',1},mfilename,'responseFraction');
validateattributes(confirmationSamples,{'numeric'}, ...
    {'scalar','real','finite','integer','positive'},mfilename,'confirmationSamples');
validateattributes(authorityDeg,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'authorityDeg');
validateattributes(toleranceDeg,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'toleranceDeg');
validateattributes(deadlineMs,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'deadlineMs');
if ~(isnumeric(cancelAtMs) && isscalar(cancelAtMs) && isreal(cancelAtMs) && ...
        ((isfinite(cancelAtMs) && cancelAtMs >= 0) || ...
        (isinf(cancelAtMs) && cancelAtMs > 0)))
    error('P04:InvalidCancelTime', ...
        'cancelAtMs must be a nonnegative scalar or positive Inf.');
end
if isstring(architectureMode)
    if ~isscalar(architectureMode)
        error('P04:InvalidArchitecture', ...
            'architectureMode must be complete or bypass-validation.');
    end
elseif ~(ischar(architectureMode) && isrow(architectureMode))
    error('P04:InvalidArchitecture', ...
        'architectureMode must be complete or bypass-validation.');
end

requestDeg = double(requestDeg);
responseFraction = double(responseFraction);
confirmationSamples = double(confirmationSamples);
authorityDeg = double(authorityDeg);
toleranceDeg = double(toleranceDeg);
deadlineMs = double(deadlineMs);
cancelAtMs = double(cancelAtMs);
architectureMode = lower(strtrim(char(architectureMode)));

if ~any(strcmp(architectureMode,{'complete','bypass-validation'}))
    error('P04:InvalidArchitecture', ...
        'architectureMode must be complete or bypass-validation.');
end
if toleranceDeg > authorityDeg
    error('P04:InvalidTolerance', ...
        'toleranceDeg must not exceed the declared command authority.');
end
if abs(deadlineMs/sampleTimeMs - round(deadlineMs/sampleTimeMs)) > 1e-10
    error('P04:InvalidDeadlineGrid', ...
        'deadlineMs must lie on the fixed 20 ms functional update grid.');
end
if isfinite(cancelAtMs) && ...
        abs(cancelAtMs/sampleTimeMs - round(cancelAtMs/sampleTimeMs)) > 1e-10
    error('P04:InvalidCancelTime', ...
        'Finite cancelAtMs must lie on the fixed 20 ms functional update grid.');
end
if abs(requestDeg) > maxRequestMagnitudeDeg || ...
        authorityDeg > maxAuthorityDeg || toleranceDeg > maxToleranceDeg || ...
        confirmationSamples > maxConfirmationSamples || deadlineMs > horizonMs || ...
        (isfinite(cancelAtMs) && cancelAtMs > horizonMs)
    error('P04:ResourceBound', ...
        'Inputs exceed the fixed %.0f ms, %.0f-sample functional envelope.', ...
        horizonMs,horizonMs/sampleTimeMs + 1);
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

timeMs = (0:sampleTimeMs:horizonMs)';
sampleCount = numel(timeMs);
functionCount = numel(functionNames);
positionDeg = zeros(sampleCount,1);
correctionDeg = zeros(sampleCount,1);
confirmationStreak = zeros(sampleCount,1);
functionActivation = false(sampleCount,functionCount);
functionActivation(1,1) = true;

authorityValid = abs(requestDeg) <= authorityDeg;
validationBypassed = strcmp(architectureMode,'bypass-validation');
effectiveTargetDeg = min(max(requestDeg,-authorityDeg),authorityDeg);
if validationBypassed
    monitorTargetDeg = effectiveTargetDeg;
else
    monitorTargetDeg = requestDeg;
    functionActivation(1,2) = true;
end

status = 'active';
reportIndex = NaN;
completionTimeMs = Inf;
cancelObservedTimeMs = Inf;

if ~validationBypassed && ~authorityValid
    status = 'rejected';
    reportIndex = 1;
    functionActivation(1,10) = true;
else
    for k = 1:sampleCount
        functionActivation(k,3) = true;
        functionActivation(k,8) = true;

        if isfinite(cancelAtMs) && timeMs(k) >= cancelAtMs
            status = 'cancelled';
            reportIndex = k;
            cancelObservedTimeMs = timeMs(k);
            functionActivation(k,10) = true;
            break;
        end

        functionActivation(k,7) = true;
        if abs(monitorTargetDeg - positionDeg(k)) <= toleranceDeg
            if k == 1
                confirmationStreak(k) = 1;
            else
                confirmationStreak(k) = confirmationStreak(k-1) + 1;
            end
        else
            confirmationStreak(k) = 0;
        end

        if confirmationStreak(k) >= confirmationSamples
            status = 'completed';
            reportIndex = k;
            completionTimeMs = timeMs(k);
            functionActivation(k,10) = true;
            break;
        end

        functionActivation(k,9) = true;
        if timeMs(k) >= deadlineMs
            status = 'deadline-missed';
            reportIndex = k;
            functionActivation(k,10) = true;
            break;
        end

        functionActivation(k,4:6) = true;
        correctionDeg(k) = responseFraction*(effectiveTargetDeg - positionDeg(k));
        positionDeg(k+1) = positionDeg(k) + correctionDeg(k);
    end
end

if isnan(reportIndex)
    error('P04:InternalNoTerminalState', ...
        'The fixed functional horizon ended without a terminal report.');
end
if reportIndex < sampleCount
    % Pad the bounded output after the terminal sample. This is trace
    % termination, not a commanded or verified physical hold.
    positionDeg(reportIndex+1:end) = positionDeg(reportIndex);
    confirmationStreak(reportIndex+1:end) = confirmationStreak(reportIndex);
end

requestErrorDeg = requestDeg - positionDeg;
monitorErrorDeg = monitorTargetDeg - positionDeg;
withinRequestTolerance = abs(requestErrorDeg) <= toleranceDeg;
withinMonitorTolerance = abs(monitorErrorDeg) <= toleranceDeg;
firstWithinRequestToleranceMs = firstTrueTime(timeMs,withinRequestTolerance);
firstWithinMonitorToleranceMs = firstTrueTime(timeMs,withinMonitorTolerance);
reportTimeMs = timeMs(reportIndex);
positionAtReportDeg = positionDeg(reportIndex);
requestErrorAtReportDeg = requestErrorDeg(reportIndex);
monitorErrorAtReportDeg = monitorErrorDeg(reportIndex);
reportedSuccess = strcmp(status,'completed');
requestSatisfiedAtReport = abs(requestErrorAtReportDeg) <= toleranceDeg;
falseSuccess = reportedSuccess && ~requestSatisfiedAtReport;
requirementsMet = reportedSuccess && authorityValid && ...
    requestSatisfiedAtReport && ~validationBypassed;
safeHoldRequired = any(strcmp(status, ...
    {'rejected','cancelled','deadline-missed'}));

if falseSuccess
    failureMode = 'intent-lost';
elseif validationBypassed
    failureMode = 'validation-bypassed';
elseif strcmp(status,'rejected')
    failureMode = 'request-rejected';
elseif strcmp(status,'cancelled')
    failureMode = 'cancelled';
elseif strcmp(status,'deadline-missed')
    failureMode = 'deadline-missed';
else
    failureMode = 'none';
end

out = struct();
out.inputs = struct('requestDeg',requestDeg, ...
    'responseFraction',responseFraction, ...
    'confirmationSamples',confirmationSamples, ...
    'authorityDeg',authorityDeg, ...
    'toleranceDeg',toleranceDeg, ...
    'deadlineMs',deadlineMs, ...
    'cancelAtMs',cancelAtMs, ...
    'architectureMode',architectureMode);
out.timeMs = timeMs;
out.positionDeg = positionDeg;
out.correctionDeg = correctionDeg;
out.requestErrorDeg = requestErrorDeg;
out.monitorErrorDeg = monitorErrorDeg;
out.confirmationStreak = confirmationStreak;
out.withinRequestTolerance = withinRequestTolerance;
out.withinMonitorTolerance = withinMonitorTolerance;
out.requestedTargetDeg = requestDeg;
out.effectiveTargetDeg = effectiveTargetDeg;
out.monitorTargetDeg = monitorTargetDeg;
out.authorityMarginDeg = authorityDeg - abs(requestDeg);
out.authorityValid = authorityValid;
out.validationBypassed = validationBypassed;
out.status = status;
out.terminalState = status;
out.failureMode = failureMode;
out.reportedSuccess = reportedSuccess;
out.falseSuccess = falseSuccess;
out.requirementsMet = requirementsMet;
out.requestGoalMet = requirementsMet;
out.safeHoldRequired = safeHoldRequired;
out.traceTerminated = true;
out.requestSatisfiedAtReport = requestSatisfiedAtReport;
out.physicalMotionOccurred = any(abs(diff(positionDeg)) > 1e-12);
out.positionAtReportDeg = positionAtReportDeg;
out.requestErrorAtReportDeg = requestErrorAtReportDeg;
out.monitorErrorAtReportDeg = monitorErrorAtReportDeg;
out.firstWithinRequestToleranceMs = firstWithinRequestToleranceMs;
out.firstWithinMonitorToleranceMs = firstWithinMonitorToleranceMs;
out.completionTimeMs = completionTimeMs;
out.reportTimeMs = reportTimeMs;
out.terminalSampleIndex = reportIndex;
out.cancelObservedTimeMs = cancelObservedTimeMs;
out.cancellationRequested = isfinite(cancelAtMs);
out.cancellationObserved = strcmp(status,'cancelled');
out.functionNames = functionNames;
out.functionInputs = functionInputs;
out.functionOutputs = functionOutputs;
out.functionFailureModes = functionFailureModes;
out.functionActivation = functionActivation;
out.executedFunctionCount = sum(any(functionActivation,1));
out.functionActivationCount = sum(functionActivation(:));
if validationBypassed
    out.architecturallyOmittedFunctionNames = functionNames(2);
else
    out.architecturallyOmittedFunctionNames = cell(1,0);
end
out.sampleTimeMs = sampleTimeMs;
out.horizonMs = horizonMs;
out.sampleCount = sampleCount;
out.functionCount = functionCount;
out.maxRequestMagnitudeDeg = maxRequestMagnitudeDeg;
out.maxAuthorityDeg = maxAuthorityDeg;
out.maxToleranceDeg = maxToleranceDeg;
out.maxConfirmationSamples = maxConfirmationSamples;
end

function eventTimeMs = firstTrueTime(timeMs,mask)
index = find(mask,1,'first');
if isempty(index)
    eventTimeMs = Inf;
else
    eventTimeMs = timeMs(index);
end
end
