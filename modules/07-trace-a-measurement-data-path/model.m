function out = model(trueAngleDeg,adcBits,sampleAgeMs,freshnessLimitMs, ...
    openBoundary,eventMode,assessmentMode)
%MODEL Deterministic measurement-data reachability, value, and quality trace.
%   P05 fixes Observe position in hardware. P07 follows that observation
%   through sensor voltage, ADC count, calibrated degrees, sample quality,
%   and a P07-local qualified-control intake. P06's existing lesson consumes
%   only scalar observedAngleDeg; P07 supplies that scalar only when the local
%   value-plus-quality result is usable. The transparent conversions are
%
%     sensor_V = clamp(2.5 V + true_angle_deg/90, 0.5 V, 4.5 V)
%     adc_count = round((sensor_V - 0.5 V)/4 V * (2^bits - 1))
%     angle_deg = -180 deg + adc_count * 360 deg/(2^bits - 1)
%
%   Sample age is supplied metadata, not path-delay simulation. Cancellation
%   and timeout are already-asserted acquisition-entry guards; no scheduling,
%   jitter, retry, device, electrical, or physical sensing behavior is modeled.

if nargin < 1, trueAngleDeg = 30; end
if nargin < 2, adcBits = 12; end
if nargin < 3, sampleAgeMs = 5; end
if nargin < 4, freshnessLimitMs = 20; end
if nargin < 5, openBoundary = 'none'; end
if nargin < 6, eventMode = 'none'; end
if nargin < 7, assessmentMode = 'complete'; end

sensorFullScaleAngleDeg = 180;
maxPhysicalAngleDeg = 360;
sensorMinimumVolts = 0.5;
sensorMaximumVolts = 4.5;
sensorZeroVolts = 2.5;
sensorSpanVolts = sensorMaximumVolts - sensorMinimumVolts;
sensorSensitivityVoltsPerDeg = sensorSpanVolts/(2*sensorFullScaleAngleDeg);
minimumAdcBits = 4;
maximumAdcBits = 16;
maxAgeMs = 10000;

trueAngleDeg = normalizeBoundedScalar(trueAngleDeg,'trueAngleDeg', ...
    -maxPhysicalAngleDeg,maxPhysicalAngleDeg,'P07:InvalidAngle');
adcBits = normalizeIntegerScalar(adcBits,'adcBits',minimumAdcBits, ...
    maximumAdcBits,'P07:InvalidAdcBits');
sampleAgeMs = normalizeBoundedScalar(sampleAgeMs,'sampleAgeMs',0, ...
    maxAgeMs,'P07:InvalidSampleAge');
freshnessLimitMs = normalizeBoundedScalar(freshnessLimitMs, ...
    'freshnessLimitMs',0,maxAgeMs,'P07:InvalidFreshnessLimit');
openBoundary = normalizeChoice(openBoundary, ...
    {'none','sensor-to-adc','adc-to-calibration', ...
    'calibration-to-quality','quality-to-controller'}, ...
    'P07:InvalidBoundary','openBoundary');
eventMode = normalizeChoice(eventMode, ...
    {'none','cancellation','timeout','cancellation-timeout-tie'}, ...
    'P07:InvalidEventMode','eventMode');
assessmentMode = normalizeChoice(assessmentMode, ...
    {'complete','value-only'},'P07:InvalidAssessmentMode','assessmentMode');

stageNames = { ...
    'Observe position sensor', ...
    'Digitize sensor voltage', ...
    'Calibrate to engineering units', ...
    'Qualify sample', ...
    'P07 qualified-control intake'};
stageOwners = { ...
    'sensor-hardware', ...
    'acquisition-hardware', ...
    'hardware-interface', ...
    'measurement-supervision', ...
    'control-software'};
stageUnits = {'V','count','deg','deg','deg'};
stageQuestions = { ...
    'Did the hardware observation produce an in-range sensor voltage?', ...
    'Did the ADC receive and encode that voltage?', ...
    'Was the count converted transparently to degrees?', ...
    'Were saturation and freshness carried as measurement quality?', ...
    'Did the P07 intake receive the degree value and its quality evidence?'};
boundaryNames = { ...
    'sensor-to-adc', ...
    'adc-to-calibration', ...
    'calibration-to-quality', ...
    'quality-to-controller'};
boundaryLabels = { ...
    'Observe position sensor -> ADC', ...
    'ADC -> engineering-unit calibration', ...
    'Calibration -> sample qualification', ...
    'Qualification -> P07 qualified-control intake'};
stageCount = numel(stageNames);
boundaryCount = numel(boundaryNames);

stageReached = false(1,stageCount);
stageOutputValue = NaN(1,stageCount);
boundaryAttempted = false(1,boundaryCount);
boundaryCrossed = false(1,boundaryCount);
boundaryOpen = strcmp(openBoundary,boundaryNames);

cancellationObserved = any(strcmp(eventMode, ...
    {'cancellation','cancellation-timeout-tie'}));
timeoutObserved = any(strcmp(eventMode, ...
    {'timeout','cancellation-timeout-tie'}));
eventObserved = cancellationObserved || timeoutObserved;
tieResolvedToCancellation = strcmp(eventMode,'cancellation-timeout-tie');
entryPermitted = ~eventObserved;

maxAdcCount = 2^adcBits - 1;
quantizationStepDeg = 2*sensorFullScaleAngleDeg/maxAdcCount;
quantizationBoundDeg = 0.5*quantizationStepDeg;
freshnessCriterionMet = false;
freshnessMarginMs = NaN;

unclippedSensorVolts = NaN;
sensorVolts = NaN;
sensorEquivalentAngleDeg = NaN;
sensorSaturated = false;
adcCount = NaN;
reconstructedSensorVolts = NaN;
calibratedAngleDeg = NaN;
quantizationErrorDeg = NaN;
measurementErrorDeg = NaN;
qualityEvaluated = false;
qualityValid = false;

if entryPermitted
    stageReached(1) = true;
    unclippedSensorVolts = sensorZeroVolts + ...
        sensorSensitivityVoltsPerDeg*trueAngleDeg;
    sensorVolts = min(max(unclippedSensorVolts,sensorMinimumVolts), ...
        sensorMaximumVolts);
    sensorSaturated = unclippedSensorVolts < sensorMinimumVolts || ...
        unclippedSensorVolts > sensorMaximumVolts;
    sensorEquivalentAngleDeg = ...
        (sensorVolts - sensorZeroVolts)/sensorSensitivityVoltsPerDeg;
    stageOutputValue(1) = sensorVolts;

    boundaryAttempted(1) = true;
    if ~boundaryOpen(1)
        boundaryCrossed(1) = true;
        stageReached(2) = true;
    end
end

if stageReached(2)
    adcCount = round((sensorVolts - sensorMinimumVolts)/sensorSpanVolts* ...
        maxAdcCount);
    stageOutputValue(2) = adcCount;
    boundaryAttempted(2) = true;
    if ~boundaryOpen(2)
        boundaryCrossed(2) = true;
        stageReached(3) = true;
    end
end

if stageReached(3)
    reconstructedSensorVolts = sensorMinimumVolts + ...
        sensorSpanVolts*adcCount/maxAdcCount;
    calibratedAngleDeg = ...
        (reconstructedSensorVolts - sensorZeroVolts)/ ...
        sensorSensitivityVoltsPerDeg;
    quantizationErrorDeg = calibratedAngleDeg - sensorEquivalentAngleDeg;
    measurementErrorDeg = calibratedAngleDeg - trueAngleDeg;
    stageOutputValue(3) = calibratedAngleDeg;
    boundaryAttempted(3) = true;
    if ~boundaryOpen(3)
        boundaryCrossed(3) = true;
        stageReached(4) = true;
    end
end

if stageReached(4)
    qualityEvaluated = true;
    freshnessCriterionMet = sampleAgeMs <= freshnessLimitMs;
    freshnessMarginMs = freshnessLimitMs - sampleAgeMs;
    qualityValid = ~sensorSaturated && freshnessCriterionMet;
    stageOutputValue(4) = calibratedAngleDeg;
    boundaryAttempted(4) = true;
    if ~boundaryOpen(4)
        boundaryCrossed(4) = true;
        stageReached(5) = true;
        stageOutputValue(5) = calibratedAngleDeg;
    end
end

endpointReceived = stageReached(5);
endpointQualityValid = endpointReceived && qualityValid;
measurementUsable = endpointReceived && endpointQualityValid;
payloadPreservedToEndpoint = endpointReceived && ...
    stageOutputValue(5) == stageOutputValue(4);
qualityFlagPreservedToEndpoint = endpointReceived && ...
    endpointQualityValid == qualityValid;
p06InputEligible = measurementUsable;
p06ObservedAngleDeg = NaN;
if p06InputEligible
    p06ObservedAngleDeg = stageOutputValue(5);
end
p06ScalarAdapterMet = ...
    (p06InputEligible && isfinite(p06ObservedAngleDeg) && ...
    abs(p06ObservedAngleDeg) <= sensorFullScaleAngleDeg && ...
    p06ObservedAngleDeg == stageOutputValue(5)) || ...
    (~p06InputEligible && isnan(p06ObservedAngleDeg));

if strcmp(assessmentMode,'complete')
    reportedUsable = measurementUsable;
else
    reportedUsable = endpointReceived && isfinite(stageOutputValue(5));
end
falseUsable = reportedUsable && ~measurementUsable;

firstOpenBoundary = find(boundaryAttempted & boundaryOpen,1,'first');
if isempty(firstOpenBoundary), firstOpenBoundary = 0; end
deepestReachedStage = find(stageReached,1,'last');
if isempty(deepestReachedStage), deepestReachedStage = 0; end
crossedBoundaryCount = sum(boundaryCrossed);

if cancellationObserved
    terminalStatus = 'cancelled';
elseif timeoutObserved
    terminalStatus = 'timed-out';
elseif endpointReceived && qualityValid
    terminalStatus = 'delivered-valid';
elseif endpointReceived
    terminalStatus = 'delivered-invalid';
elseif firstOpenBoundary > 0
    terminalStatus = 'boundary-open';
else
    terminalStatus = 'route-incomplete';
end

if strcmp(terminalStatus,'cancelled')
    failureMode = 'acquisition-cancelled';
elseif strcmp(terminalStatus,'timed-out')
    failureMode = 'acquisition-timeout';
elseif strcmp(terminalStatus,'boundary-open')
    failureMode = boundaryNames{firstOpenBoundary};
elseif strcmp(terminalStatus,'delivered-invalid') && ...
        sensorSaturated && ~freshnessCriterionMet
    failureMode = 'sensor-saturated-and-stale';
elseif strcmp(terminalStatus,'delivered-invalid') && sensorSaturated
    failureMode = 'sensor-saturated';
elseif strcmp(terminalStatus,'delivered-invalid')
    failureMode = 'stale-sample';
elseif strcmp(terminalStatus,'route-incomplete')
    failureMode = 'internal-route-incomplete';
else
    failureMode = 'none';
end

if falseUsable
    reportingFailureMode = 'value-only-false-usable';
else
    reportingFailureMode = 'none';
end
terminalOutcomeHandled = eventObserved || endpointReceived;
traceContractMet = eventObserved || ...
    (endpointReceived && payloadPreservedToEndpoint && ...
    qualityFlagPreservedToEndpoint && p06ScalarAdapterMet);

out = struct();
out.inputs = struct('trueAngleDeg',trueAngleDeg,'adcBits',adcBits, ...
    'sampleAgeMs',sampleAgeMs,'freshnessLimitMs',freshnessLimitMs, ...
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
out.entryPermitted = entryPermitted;
out.eventObserved = eventObserved;
out.cancellationObserved = cancellationObserved;
out.timeoutObserved = timeoutObserved;
out.tieResolvedToCancellation = tieResolvedToCancellation;
out.unclippedSensorVolts = unclippedSensorVolts;
out.sensorVolts = sensorVolts;
out.sensorEquivalentAngleDeg = sensorEquivalentAngleDeg;
out.sensorSaturated = sensorSaturated;
out.adcCount = adcCount;
out.maxAdcCount = maxAdcCount;
out.reconstructedSensorVolts = reconstructedSensorVolts;
out.calibratedAngleDeg = calibratedAngleDeg;
out.quantizationStepDeg = quantizationStepDeg;
out.quantizationBoundDeg = quantizationBoundDeg;
out.quantizationErrorDeg = quantizationErrorDeg;
out.measurementErrorDeg = measurementErrorDeg;
out.freshnessCriterionMet = freshnessCriterionMet;
out.freshnessMarginMs = freshnessMarginMs;
out.qualityEvaluated = qualityEvaluated;
out.qualityValid = qualityValid;
out.endpointReceived = endpointReceived;
out.endpointQualityValid = endpointQualityValid;
out.measurementUsable = measurementUsable;
out.payloadPreservedToEndpoint = payloadPreservedToEndpoint;
out.qualityFlagPreservedToEndpoint = qualityFlagPreservedToEndpoint;
out.p06InputEligible = p06InputEligible;
out.p06ObservedAngleDeg = p06ObservedAngleDeg;
out.p06ScalarAdapterMet = p06ScalarAdapterMet;
out.reportedUsable = reportedUsable;
out.falseUsable = falseUsable;
out.terminalOutcomeHandled = terminalOutcomeHandled;
out.traceContractMet = traceContractMet;
out.terminalStatus = terminalStatus;
out.failureMode = failureMode;
out.reportingFailureMode = reportingFailureMode;
out.firstOpenBoundary = firstOpenBoundary;
out.deepestReachedStage = deepestReachedStage;
out.crossedBoundaryCount = crossedBoundaryCount;
out.stageCount = stageCount;
out.boundaryCount = boundaryCount;
out.sensorFullScaleAngleDeg = sensorFullScaleAngleDeg;
out.maxPhysicalAngleDeg = maxPhysicalAngleDeg;
out.sensorMinimumVolts = sensorMinimumVolts;
out.sensorMaximumVolts = sensorMaximumVolts;
out.sensorZeroVolts = sensorZeroVolts;
out.sensorSensitivityVoltsPerDeg = sensorSensitivityVoltsPerDeg;
out.minimumAdcBits = minimumAdcBits;
out.maximumAdcBits = maximumAdcBits;
out.maxAgeMs = maxAgeMs;
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

function normalized = normalizeIntegerScalar(value,inputName,lowerBound, ...
    upperBound,errorId)
normalized = normalizeBoundedScalar(value,inputName,lowerBound,upperBound,errorId);
if normalized ~= round(normalized)
    error(errorId,'%s must be an integer-valued scalar.',inputName);
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
