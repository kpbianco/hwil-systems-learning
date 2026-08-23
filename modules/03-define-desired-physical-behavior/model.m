function out = model(commandDeg,naturalFrequencyHz,dampingRatio,commandLimitDeg,positionToleranceDeg,velocityToleranceDegPerSec,deadlineMs)
%MODEL Deterministic rotary-position behavior against a measurable envelope.
%   A requested angle drives a transparent second-order response. The
%   behavior contract includes command authority, position and velocity
%   tolerances, and a response deadline. No presentation or external I/O
%   occurs here.

if nargin < 1, commandDeg = 30; end
if nargin < 2, naturalFrequencyHz = 1.5; end
if nargin < 3, dampingRatio = 0.7; end
if nargin < 4, commandLimitDeg = 45; end
if nargin < 5, positionToleranceDeg = 0.5; end
if nargin < 6, velocityToleranceDegPerSec = 2; end
if nargin < 7, deadlineMs = 1200; end

sampleTimeMs = 2;
horizonMs = 10000;
maxDeadlineMs = 3000;
maxCommandMagnitudeDeg = 180;
maxNaturalFrequencyHz = 10;
maxCommandLimitDeg = 180;
maxPositionToleranceDeg = 30;
maxVelocityToleranceDegPerSec = 1000;

validateattributes(commandDeg,{'numeric'}, ...
    {'scalar','real','finite'},mfilename,'commandDeg');
validateattributes(naturalFrequencyHz,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'naturalFrequencyHz');
validateattributes(dampingRatio,{'numeric'}, ...
    {'scalar','real','finite'},mfilename,'dampingRatio');
validateattributes(commandLimitDeg,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'commandLimitDeg');
validateattributes(positionToleranceDeg,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'positionToleranceDeg');
validateattributes(velocityToleranceDegPerSec,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'velocityToleranceDegPerSec');
validateattributes(deadlineMs,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'deadlineMs');

commandDeg = double(commandDeg);
naturalFrequencyHz = double(naturalFrequencyHz);
dampingRatio = double(dampingRatio);
commandLimitDeg = double(commandLimitDeg);
positionToleranceDeg = double(positionToleranceDeg);
velocityToleranceDegPerSec = double(velocityToleranceDegPerSec);
deadlineMs = double(deadlineMs);

if dampingRatio <= 0 || dampingRatio > 1
    error('P03:InvalidDampingRatio', ...
        'dampingRatio must be greater than zero and at most one.');
end
if positionToleranceDeg > commandLimitDeg
    error('P03:InvalidTolerance', ...
        'positionToleranceDeg must not exceed commandLimitDeg.');
end
if abs(commandDeg) > maxCommandMagnitudeDeg || ...
        naturalFrequencyHz > maxNaturalFrequencyHz || ...
        commandLimitDeg > maxCommandLimitDeg || ...
        positionToleranceDeg > maxPositionToleranceDeg || ...
        velocityToleranceDegPerSec > maxVelocityToleranceDegPerSec || ...
        deadlineMs > maxDeadlineMs
    error('P03:ResourceBound', ...
        'Inputs exceed the fixed %.0f ms, %.0f-sample response envelope.', ...
        horizonMs,horizonMs/sampleTimeMs + 1);
end

effectiveCommandDeg = min(max(commandDeg,-commandLimitDeg),commandLimitDeg);
commandWasLimited = effectiveCommandDeg ~= commandDeg;
timeMs = (0:sampleTimeMs:horizonMs)';
timeSec = timeMs / 1000;
omegaNaturalRadPerSec = 2*pi*naturalFrequencyHz;

if dampingRatio == 1
    normalizedPosition = 1 - exp(-omegaNaturalRadPerSec*timeSec) .* ...
        (1 + omegaNaturalRadPerSec*timeSec);
    normalizedVelocityPerSec = omegaNaturalRadPerSec^2 .* timeSec .* ...
        exp(-omegaNaturalRadPerSec*timeSec);
else
    dampingComplement = sqrt(1 - dampingRatio^2);
    omegaDampedRadPerSec = omegaNaturalRadPerSec*dampingComplement;
    normalizedPosition = 1 - exp(-dampingRatio*omegaNaturalRadPerSec*timeSec) .* ...
        (cos(omegaDampedRadPerSec*timeSec) + ...
        dampingRatio/dampingComplement*sin(omegaDampedRadPerSec*timeSec));
    normalizedVelocityPerSec = omegaNaturalRadPerSec/dampingComplement .* ...
        exp(-dampingRatio*omegaNaturalRadPerSec*timeSec) .* ...
        sin(omegaDampedRadPerSec*timeSec);
end

positionDeg = effectiveCommandDeg*normalizedPosition;
velocityDegPerSec = effectiveCommandDeg*normalizedVelocityPerSec;
requestErrorDeg = commandDeg - positionDeg;
effectiveTargetErrorDeg = effectiveCommandDeg - positionDeg;
withinVelocityBand = abs(velocityDegPerSec) <= velocityToleranceDegPerSec;
withinRequestBand = abs(requestErrorDeg) <= positionToleranceDeg & withinVelocityBand;
withinEffectiveTargetBand = abs(effectiveTargetErrorDeg) <= positionToleranceDeg & ...
    withinVelocityBand;
horizonSec = timeSec(end);
if dampingRatio == 1
    futurePositionEnvelopeDeg = abs(effectiveCommandDeg) * ...
        exp(-omegaNaturalRadPerSec*horizonSec) * ...
        (1 + omegaNaturalRadPerSec*horizonSec);
    futureVelocityEnvelopeDegPerSec = abs(effectiveCommandDeg) * ...
        omegaNaturalRadPerSec^2*horizonSec * ...
        exp(-omegaNaturalRadPerSec*horizonSec);
    futureDecayIsMonotonic = horizonSec >= 1/omegaNaturalRadPerSec;
else
    futureDecayEnvelope = exp(-dampingRatio*omegaNaturalRadPerSec*horizonSec) / ...
        sqrt(1 - dampingRatio^2);
    futurePositionEnvelopeDeg = abs(effectiveCommandDeg)*futureDecayEnvelope;
    futureVelocityEnvelopeDegPerSec = abs(effectiveCommandDeg) * ...
        omegaNaturalRadPerSec*futureDecayEnvelope;
    futureDecayIsMonotonic = true;
end
if effectiveCommandDeg == 0
    % Zero input from zero initial state has no transient, regardless of rate.
    futureDecayIsMonotonic = true;
end
effectiveTargetFutureGuaranteed = futureDecayIsMonotonic && ...
    futurePositionEnvelopeDeg <= positionToleranceDeg && ...
    futureVelocityEnvelopeDegPerSec <= velocityToleranceDegPerSec;
requestFutureGuaranteed = futureDecayIsMonotonic && ...
    abs(commandDeg - effectiveCommandDeg) + futurePositionEnvelopeDeg <= ...
    positionToleranceDeg && ...
    futureVelocityEnvelopeDegPerSec <= velocityToleranceDegPerSec;
settlingTimeMs = sustainedEntryTime(timeMs,withinRequestBand,requestFutureGuaranteed);
effectiveTargetSettlingTimeMs = sustainedEntryTime(timeMs, ...
    withinEffectiveTargetBand,effectiveTargetFutureGuaranteed);

deadlineIndex = find(timeMs <= deadlineMs,1,'last');
deadlineSampleTimeMs = timeMs(deadlineIndex);
positionAtDeadlineDeg = positionDeg(deadlineIndex);
velocityAtDeadlineDegPerSec = velocityDegPerSec(deadlineIndex);
requestErrorAtDeadlineDeg = requestErrorDeg(deadlineIndex);
settledByDeadline = ~isinf(settlingTimeMs) && settlingTimeMs <= deadlineMs;
effectiveTargetSettledByDeadline = ~isinf(effectiveTargetSettlingTimeMs) && ...
    effectiveTargetSettlingTimeMs <= deadlineMs;
directionCorrect = commandDeg == 0 || ...
    all(positionDeg*sign(commandDeg) >= -1e-10);
requirementsMet = ~commandWasLimited && settledByDeadline && directionCorrect;

peakPositionMagnitudeDeg = max(abs(positionDeg));
peakVelocityMagnitudeDegPerSec = max(abs(velocityDegPerSec));
overshootDeg = max(0,peakPositionMagnitudeDeg - abs(effectiveCommandDeg));
if effectiveCommandDeg == 0
    overshootPercent = 0;
else
    overshootPercent = 100*overshootDeg/abs(effectiveCommandDeg);
end

if commandWasLimited
    failureMode = 'command-limited';
elseif ~directionCorrect
    failureMode = 'direction-error';
elseif ~settledByDeadline
    failureMode = 'deadline-missed';
else
    failureMode = 'none';
end

out = struct();
out.inputs = struct('commandDeg',commandDeg, ...
    'naturalFrequencyHz',naturalFrequencyHz, ...
    'dampingRatio',dampingRatio, ...
    'commandLimitDeg',commandLimitDeg, ...
    'positionToleranceDeg',positionToleranceDeg, ...
    'velocityToleranceDegPerSec',velocityToleranceDegPerSec, ...
    'deadlineMs',deadlineMs);
out.timeMs = timeMs;
out.positionDeg = positionDeg;
out.velocityDegPerSec = velocityDegPerSec;
out.requestErrorDeg = requestErrorDeg;
out.effectiveTargetErrorDeg = effectiveTargetErrorDeg;
out.withinRequestBand = withinRequestBand;
out.withinEffectiveTargetBand = withinEffectiveTargetBand;
out.requestedCommandDeg = commandDeg;
out.effectiveCommandDeg = effectiveCommandDeg;
out.commandWasLimited = commandWasLimited;
out.commandAuthorityMarginDeg = commandLimitDeg - abs(commandDeg);
out.omegaNaturalRadPerSec = omegaNaturalRadPerSec;
out.peakPositionMagnitudeDeg = peakPositionMagnitudeDeg;
out.peakVelocityMagnitudeDegPerSec = peakVelocityMagnitudeDegPerSec;
out.overshootDeg = overshootDeg;
out.overshootPercent = overshootPercent;
out.settlingTimeMs = settlingTimeMs;
out.effectiveTargetSettlingTimeMs = effectiveTargetSettlingTimeMs;
out.positionAtDeadlineDeg = positionAtDeadlineDeg;
out.velocityAtDeadlineDegPerSec = velocityAtDeadlineDegPerSec;
out.requestErrorAtDeadlineDeg = requestErrorAtDeadlineDeg;
out.deadlineSampleTimeMs = deadlineSampleTimeMs;
out.settledByDeadline = settledByDeadline;
out.effectiveTargetSettledByDeadline = effectiveTargetSettledByDeadline;
out.directionCorrect = directionCorrect;
out.requirementsMet = requirementsMet;
out.failureMode = failureMode;
out.finalPositionDeg = positionDeg(end);
out.finalRequestErrorDeg = requestErrorDeg(end);
out.futurePositionEnvelopeDeg = futurePositionEnvelopeDeg;
out.futureVelocityEnvelopeDegPerSec = futureVelocityEnvelopeDegPerSec;
out.requestFutureGuaranteed = requestFutureGuaranteed;
out.effectiveTargetFutureGuaranteed = effectiveTargetFutureGuaranteed;
out.sampleTimeMs = sampleTimeMs;
out.horizonMs = horizonMs;
out.maxDeadlineMs = maxDeadlineMs;
out.sampleCount = numel(timeMs);
end

function entryTimeMs = sustainedEntryTime(timeMs,withinBand,futureGuaranteed)
% Return the first sample after which every remaining sample is in band.
if ~futureGuaranteed
    entryTimeMs = Inf;
    return;
end
staysWithin = false(size(withinBand));
staysWithin(end) = withinBand(end);
for k = numel(withinBand)-1:-1:1
    staysWithin(k) = withinBand(k) && staysWithin(k+1);
end
index = find(staysWithin,1,'first');
if isempty(index)
    entryTimeMs = Inf;
else
    entryTimeMs = timeMs(index);
end
end
