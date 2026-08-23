function out = model(sourceAngleDeg,payloadWordCount,senderVersion, ...
    sequenceNumber,sourceQualityValid,faultMode,eventMode,validationMode)
%MODEL Deterministic executable Interface Control Contract decision.
%   P08 formalizes one logical measurement handoff without changing P07's
%   local quality gate or P06's scalar observedAngleDeg input. The producer
%   and receiver must agree on interface identity, schema version, payload
%   length, units, range, sequence bounds, quality encoding, and checksum.
%   This is an instructional record-level contract, not wire, transport,
%   electrical, clock, scheduling, retry, or physical-interface behavior.

if nargin < 1, sourceAngleDeg = 30.021978021978; end
if nargin < 2, payloadWordCount = 6; end
if nargin < 3, senderVersion = 1; end
if nargin < 4, sequenceNumber = 42; end
if nargin < 5, sourceQualityValid = true; end
if nargin < 6, faultMode = 'none'; end
if nargin < 7, eventMode = 'none'; end
if nargin < 8, validationMode = 'complete'; end

contractInterfaceId = 801;
contractVersion = 1;
requiredPayloadWords = 6;
expectedUnit = 'deg';
minimumAngleDeg = -180;
maximumAngleDeg = 180;
maxModelAngleDeg = 360;
minimumPayloadWords = 0;
maximumPayloadWords = 16;
minimumVersion = 0;
maximumVersion = 255;
minimumSequence = 0;
maximumSequence = 65535;
checksumModulus = 65536;

sourceAngleDeg = normalizeBoundedScalar(sourceAngleDeg,'sourceAngleDeg', ...
    -maxModelAngleDeg,maxModelAngleDeg,'P08:InvalidAngle');
payloadWordCount = normalizeIntegerScalar(payloadWordCount, ...
    'payloadWordCount',minimumPayloadWords,maximumPayloadWords, ...
    'P08:InvalidPayloadWordCount');
senderVersion = normalizeIntegerScalar(senderVersion,'senderVersion', ...
    minimumVersion,maximumVersion,'P08:InvalidSenderVersion');
sequenceNumber = normalizeIntegerScalar(sequenceNumber,'sequenceNumber', ...
    minimumSequence,maximumSequence,'P08:InvalidSequence');
sourceQualityValid = normalizeLogicalScalar(sourceQualityValid, ...
    'sourceQualityValid','P08:InvalidQuality');
faultMode = normalizeChoice(faultMode, ...
    {'none','identifier-mismatch','unit-mismatch', ...
    'sequence-out-of-range','quality-code-invalid','checksum-corruption'}, ...
    'P08:InvalidFaultMode','faultMode');
eventMode = normalizeChoice(eventMode, ...
    {'none','cancellation','timeout','cancellation-timeout-tie'}, ...
    'P08:InvalidEventMode','eventMode');
validationMode = normalizeChoice(validationMode, ...
    {'complete','value-only'},'P08:InvalidValidationMode','validationMode');

clauseNames = { ...
    'Interface identity', ...
    'Schema version', ...
    'Payload length', ...
    'Engineering unit', ...
    'Value range', ...
    'Sequence range', ...
    'Quality encoding', ...
    'Checksum integrity'};
clauseQuestions = { ...
    'Is this the named producer-to-receiver interface?', ...
    'Can the receiver interpret this schema version?', ...
    'Does the record contain exactly the contracted number of words?', ...
    'Do producer and receiver attach the same physical meaning to the number?', ...
    'Is the value inside the inclusive declared engineering envelope?', ...
    'Is the sequence value inside its fixed unsigned range?', ...
    'Is quality represented by exactly zero or one?', ...
    'Does the transparent checksum cover the metadata and five non-checksum payload fields?'};
clauseCount = numel(clauseNames);

payloadFieldNames = { ...
    'interface-id','schema-version','sequence','angle','quality','checksum'};
payloadFieldUnits = {'-','-','count','declared-unit','Boolean code','count'};
payloadFieldCount = numel(payloadFieldNames);
envelopeMetadataNames = {'payload-word-count','engineering-unit'};
envelopeMetadataUnits = {'word','text'};
envelopeMetadataCount = numel(envelopeMetadataNames);

cancellationObserved = any(strcmp(eventMode, ...
    {'cancellation','cancellation-timeout-tie'}));
timeoutObserved = any(strcmp(eventMode, ...
    {'timeout','cancellation-timeout-tie'}));
eventObserved = cancellationObserved || timeoutObserved;
tieResolvedToCancellation = strcmp(eventMode,'cancellation-timeout-tie');
transferAttempted = ~eventObserved;

transmittedInterfaceId = contractInterfaceId;
payloadAngleValue = sourceAngleDeg;
payloadUnit = expectedUnit;
transmittedSequence = sequenceNumber;
wireQualityCode = double(sourceQualityValid);

switch faultMode
    case 'identifier-mismatch'
        transmittedInterfaceId = contractInterfaceId + 1;
    case 'unit-mismatch'
        payloadAngleValue = sourceAngleDeg*pi/180;
        payloadUnit = 'rad';
    case 'sequence-out-of-range'
        transmittedSequence = maximumSequence + 1;
    case 'quality-code-invalid'
        wireQualityCode = 2;
end

if strcmp(payloadUnit,'deg')
    unitCode = 1;
else
    unitCode = 2;
end
checksumExpected = mod(transmittedInterfaceId + senderVersion + ...
    payloadWordCount + transmittedSequence + ...
    round(1000*payloadAngleValue) + wireQualityCode + unitCode, ...
    checksumModulus);
transmittedChecksum = checksumExpected;
if strcmp(faultMode,'checksum-corruption')
    transmittedChecksum = mod(checksumExpected + 1,checksumModulus);
end

clauseEvaluated = false(1,clauseCount);
clausePass = false(1,clauseCount);
identityMatches = false;
versionMatches = false;
lengthMatches = false;
unitMatches = false;
rangeMatches = false;
receiverAssumedRangeMatches = false;
sequenceMatches = false;
qualityEncodingMatches = false;
checksumMatches = false;
rangeMarginDeg = NaN;
receiverAssumedRangeMarginDeg = NaN;
if transferAttempted
    candidateIdentityMatches = transmittedInterfaceId == contractInterfaceId;
    candidateVersionMatches = senderVersion == contractVersion;
    candidateLengthMatches = payloadWordCount == requiredPayloadWords;
    candidateUnitMatches = strcmp(payloadUnit,expectedUnit);
    candidateReceiverAssumedRangeMatches = ...
        payloadAngleValue >= minimumAngleDeg && ...
        payloadAngleValue <= maximumAngleDeg;
    candidateRangeMatches = candidateUnitMatches && ...
        candidateReceiverAssumedRangeMatches;
    candidateSequenceMatches = transmittedSequence >= minimumSequence && ...
        transmittedSequence <= maximumSequence && ...
        transmittedSequence == round(transmittedSequence);
    candidateQualityEncodingMatches = ...
        wireQualityCode == 0 || wireQualityCode == 1;
    candidateChecksumMatches = transmittedChecksum == checksumExpected;
    candidateClausePass = [candidateIdentityMatches candidateVersionMatches ...
        candidateLengthMatches candidateUnitMatches candidateRangeMatches ...
        candidateSequenceMatches candidateQualityEncodingMatches ...
        candidateChecksumMatches];
    clauseEvaluated(:) = true;
    clausePass = candidateClausePass;
    identityMatches = candidateIdentityMatches;
    versionMatches = candidateVersionMatches;
    lengthMatches = candidateLengthMatches;
    unitMatches = candidateUnitMatches;
    rangeMatches = candidateRangeMatches;
    receiverAssumedRangeMatches = candidateReceiverAssumedRangeMatches;
    sequenceMatches = candidateSequenceMatches;
    qualityEncodingMatches = candidateQualityEncodingMatches;
    checksumMatches = candidateChecksumMatches;
    receiverAssumedRangeMarginDeg = ...
        maximumAngleDeg - abs(payloadAngleValue);
    if unitMatches
        rangeMarginDeg = receiverAssumedRangeMarginDeg;
    end
end
contractConformant = transferAttempted && all(clausePass);
payloadArrived = transferAttempted;
receiverValuePlausible = transferAttempted && ...
    isfinite(payloadAngleValue) && receiverAssumedRangeMatches;

if strcmp(validationMode,'complete')
    receiverAccepted = contractConformant;
    receiverInputReleased = receiverAccepted && wireQualityCode == 1;
else
    receiverAccepted = receiverValuePlausible;
    receiverInputReleased = receiverAccepted;
end

contractInputEligible = contractConformant && wireQualityCode == 1;
falseAcceptance = receiverAccepted && ~contractConformant;
falseRelease = receiverInputReleased && ~contractInputEligible;
receiverDecisionCorrect = transferAttempted && ...
    (receiverAccepted == contractConformant);

p06ObservedAngleDeg = NaN;
if receiverInputReleased
    p06ObservedAngleDeg = payloadAngleValue;
end
semanticErrorDeg = NaN;
semanticValuePreserved = false;
if receiverInputReleased
    semanticErrorDeg = p06ObservedAngleDeg - sourceAngleDeg;
    semanticValuePreserved = abs(semanticErrorDeg) <= 1e-12;
end
p07QualityPreserved = payloadArrived && qualityEncodingMatches && ...
    wireQualityCode == double(sourceQualityValid);
p06ScalarContractMet = ...
    (contractInputEligible && isfinite(p06ObservedAngleDeg) && ...
    semanticValuePreserved) || ...
    (~contractInputEligible && ~receiverInputReleased && ...
    isnan(p06ObservedAngleDeg));

payloadValues = [transmittedInterfaceId senderVersion ...
    transmittedSequence payloadAngleValue wireQualityCode ...
    transmittedChecksum];

if cancellationObserved
    terminalStatus = 'cancelled';
elseif timeoutObserved
    terminalStatus = 'timed-out';
elseif ~receiverAccepted
    terminalStatus = 'rejected';
elseif receiverInputReleased
    terminalStatus = 'accepted-and-released';
else
    terminalStatus = 'accepted-quality-withheld';
end

if strcmp(terminalStatus,'cancelled')
    failureMode = 'transfer-cancelled';
elseif strcmp(terminalStatus,'timed-out')
    failureMode = 'transfer-timeout';
elseif ~identityMatches
    failureMode = 'identifier-mismatch';
elseif ~versionMatches
    failureMode = 'version-mismatch';
elseif ~lengthMatches
    failureMode = 'payload-length-mismatch';
elseif ~unitMatches
    failureMode = 'unit-mismatch';
elseif ~rangeMatches
    failureMode = 'angle-out-of-range';
elseif ~sequenceMatches
    failureMode = 'sequence-out-of-range';
elseif ~qualityEncodingMatches
    failureMode = 'quality-code-invalid';
elseif ~checksumMatches
    failureMode = 'checksum-mismatch';
elseif ~sourceQualityValid
    failureMode = 'source-quality-invalid';
else
    failureMode = 'none';
end

if falseAcceptance
    reportingFailureMode = 'value-only-false-acceptance';
elseif falseRelease
    reportingFailureMode = 'value-only-false-release';
else
    reportingFailureMode = 'none';
end
terminalOutcomeHandled = eventObserved || transferAttempted;

out = struct();
out.inputs = struct('sourceAngleDeg',sourceAngleDeg, ...
    'payloadWordCount',payloadWordCount,'senderVersion',senderVersion, ...
    'sequenceNumber',sequenceNumber, ...
    'sourceQualityValid',sourceQualityValid,'faultMode',faultMode, ...
    'eventMode',eventMode,'validationMode',validationMode);
out.clauseNames = clauseNames;
out.clauseQuestions = clauseQuestions;
out.clauseCount = clauseCount;
out.clauseEvaluated = clauseEvaluated;
out.clausePass = clausePass;
out.payloadFieldNames = payloadFieldNames;
out.payloadFieldUnits = payloadFieldUnits;
out.payloadFieldCount = payloadFieldCount;
out.payloadValues = payloadValues;
out.envelopeMetadataNames = envelopeMetadataNames;
out.envelopeMetadataUnits = envelopeMetadataUnits;
out.envelopeMetadataCount = envelopeMetadataCount;
out.cancellationObserved = cancellationObserved;
out.timeoutObserved = timeoutObserved;
out.eventObserved = eventObserved;
out.tieResolvedToCancellation = tieResolvedToCancellation;
out.transferAttempted = transferAttempted;
out.payloadArrived = payloadArrived;
out.transmittedInterfaceId = transmittedInterfaceId;
out.payloadAngleValue = payloadAngleValue;
out.payloadUnit = payloadUnit;
out.transmittedSequence = transmittedSequence;
out.wireQualityCode = wireQualityCode;
out.checksumExpected = checksumExpected;
out.transmittedChecksum = transmittedChecksum;
out.identityMatches = identityMatches;
out.versionMatches = versionMatches;
out.lengthMatches = lengthMatches;
out.unitMatches = unitMatches;
out.rangeMatches = rangeMatches;
out.receiverAssumedRangeMatches = receiverAssumedRangeMatches;
out.sequenceMatches = sequenceMatches;
out.qualityEncodingMatches = qualityEncodingMatches;
out.checksumMatches = checksumMatches;
out.contractConformant = contractConformant;
out.receiverValuePlausible = receiverValuePlausible;
out.receiverAccepted = receiverAccepted;
out.receiverInputReleased = receiverInputReleased;
out.contractInputEligible = contractInputEligible;
out.falseAcceptance = falseAcceptance;
out.falseRelease = falseRelease;
out.receiverDecisionCorrect = receiverDecisionCorrect;
out.p06ObservedAngleDeg = p06ObservedAngleDeg;
out.semanticErrorDeg = semanticErrorDeg;
out.semanticValuePreserved = semanticValuePreserved;
out.p07QualityPreserved = p07QualityPreserved;
out.p06ScalarContractMet = p06ScalarContractMet;
out.rangeMarginDeg = rangeMarginDeg;
out.receiverAssumedRangeMarginDeg = receiverAssumedRangeMarginDeg;
out.terminalStatus = terminalStatus;
out.failureMode = failureMode;
out.reportingFailureMode = reportingFailureMode;
out.terminalOutcomeHandled = terminalOutcomeHandled;
out.contractInterfaceId = contractInterfaceId;
out.contractVersion = contractVersion;
out.requiredPayloadWords = requiredPayloadWords;
out.expectedUnit = expectedUnit;
out.minimumAngleDeg = minimumAngleDeg;
out.maximumAngleDeg = maximumAngleDeg;
out.maxModelAngleDeg = maxModelAngleDeg;
out.minimumPayloadWords = minimumPayloadWords;
out.maximumPayloadWords = maximumPayloadWords;
out.minimumVersion = minimumVersion;
out.maximumVersion = maximumVersion;
out.minimumSequence = minimumSequence;
out.maximumSequence = maximumSequence;
out.checksumModulus = checksumModulus;
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

function normalized = normalizeLogicalScalar(value,inputName,errorId)
if islogical(value) && isscalar(value)
    normalized = logical(value);
elseif isnumeric(value) && isscalar(value) && isreal(value) && ...
        isfinite(value) && (value == 0 || value == 1)
    normalized = logical(value);
else
    error(errorId,'%s must be one logical scalar or numeric zero/one.',inputName);
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
