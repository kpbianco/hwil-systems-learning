function run_checks
%RUN_CHECKS Deterministic P02 invariants and edge cases.
baseline = model(12,25,18,80,true,Inf);
repeat = model(12,25,18,80,true,Inf);
assert(isequaln(baseline,repeat),'Repeated baseline calls must be deterministic.');
assert(baseline.plannedCommandReceiptMs == 12,'Command receipt must equal command-path latency.');
assert(baseline.plannedEffectReachedMs == 12 + 25,'Effect time must be command plus action time.');
assert(baseline.actualFeedbackArrivalMs == 12 + 25 + 18, ...
    'Feedback arrival must be the independent three-stage sum.');
assert(baseline.plannedScheduleMarginMs == 80 - (12 + 25 + 18),'Schedule margin mismatch.');
assert(baseline.achievedConfirmationMarginMs == 25,'Achieved confirmation margin mismatch.');
assert(strcmp(baseline.terminalState,'confirmed') && baseline.operatorGoalMet, ...
    'Baseline must be confirmed before the deadline.');

zeroLimit = model(0,0,0,1,true,Inf);
assert(zeroLimit.terminalTimeMs == 0 && zeroLimit.operatorGoalMet, ...
    'Zero path/action times must confirm at the request time.');
exactDeadline = model(12,25,43,80,true,Inf);
assert(exactDeadline.actualFeedbackArrivalMs == 80 && exactDeadline.operatorGoalMet, ...
    'Confirmation exactly at the deadline must be accepted.');

moreCommand = model(22,25,18,80,true,Inf);
assert(moreCommand.plannedEffectReachedMs - baseline.plannedEffectReachedMs == 10, ...
    'Command latency must shift the physical effect one-for-one.');
assert(moreCommand.plannedFeedbackArrivalMs - baseline.plannedFeedbackArrivalMs == 10, ...
    'Command latency must shift feedback one-for-one.');
moreFeedback = model(12,25,28,80,true,Inf);
assert(moreFeedback.plannedEffectReachedMs == baseline.plannedEffectReachedMs, ...
    'Feedback latency must not change physical-effect time.');
assert(moreFeedback.plannedFeedbackArrivalMs - baseline.plannedFeedbackArrivalMs == 10, ...
    'Feedback latency must shift only confirmation one-for-one.');

feedbackLoss = model(12,25,18,80,false,Inf);
assert(feedbackLoss.physicalGoalReached && ~feedbackLoss.operatorGoalMet, ...
    'Missing feedback may hide a completed physical effect.');
assert(strcmp(feedbackLoss.terminalState,'timeout-safe-hold') && feedbackLoss.safeHoldCommanded, ...
    'Missing feedback must timeout to safe hold.');
assert(isinf(feedbackLoss.actualFeedbackArrivalMs) && ...
    isnan(feedbackLoss.achievedConfirmationMarginMs), ...
    'Unconfirmed feedback and achieved margin must remain explicitly unavailable.');
operationalRecovery = model(12,25,18,80,true,Inf);
assert(isequaln(operationalRecovery,baseline), ...
    'Restored feedback and readiness must begin a clean transaction.');
lateFeedback = model(12,25,50,60,true,Inf);
assert(lateFeedback.physicalGoalReached && strcmp(lateFeedback.terminalState,'timeout-safe-hold'), ...
    'Late feedback must timeout even when the physical effect occurred.');
assert(isinf(lateFeedback.actualFeedbackArrivalMs), ...
    'Feedback after timeout must not appear as an occurred transaction event.');

cancelBeforeCommand = model(12,25,18,80,true,5);
assert(cancelBeforeCommand.cancelled && ~cancelBeforeCommand.physicalGoalReached, ...
    'Cancellation before command receipt must prevent the goal.');
assert(all(isinf(cancelBeforeCommand.eventTimesMs(2:4))), ...
    'Cancelled future events must not appear in the occurred-event timeline.');
cancelDuringAction = model(12,25,18,80,true,20);
assert(cancelDuringAction.cancelled && ~cancelDuringAction.physicalGoalReached, ...
    'Cancellation during action must prevent the goal.');
cancelAfterEffect = model(12,25,18,80,true,40);
assert(cancelAfterEffect.cancelled && cancelAfterEffect.physicalGoalReached, ...
    'Cancellation after the effect must preserve the observed physical history.');
cancelTie = model(12,25,18,80,true,55);
assert(cancelTie.cancelled && ~cancelTie.operatorGoalMet, ...
    'Cancellation must have safety priority when tied with confirmation.');
cancelTimeoutTie = model(12,25,18,80,false,80);
assert(cancelTimeoutTie.cancelled && ...
    strcmp(cancelTimeoutTie.terminalState,'cancelled-safe-hold'), ...
    'Cancellation must have safety priority when tied with timeout.');
assert(cancelTimeoutTie.terminalTimeMs == 80 && cancelTimeoutTie.physicalGoalReached, ...
    'A timeout tie must retain physical history through the cancellation time.');
cancelAfterConfirmation = model(12,25,18,80,true,56);
assert(cancelAfterConfirmation.operatorGoalMet && ~cancelAfterConfirmation.cancelled, ...
    'Cancellation after terminal confirmation must have no effect.');

integerInputs = model(uint16(12),uint16(25),uint16(18),uint16(80),true,Inf);
assert(isequaln(integerInputs,baseline),'Compatible integer scalars must normalize to the same result.');
assert(numel(baseline.eventTimesMs) == 6 && baseline.timelineSlotCount == 6, ...
    'The model must retain a fixed six-slot timeline resource bound.');
assert(baseline.occurredEventCount == 5 && cancelBeforeCommand.occurredEventCount == 2, ...
    'Occurred-event count must distinguish completion from early cancellation.');
assert(baseline.maxHorizonMs == 600000,'Declared time-horizon bound changed unexpectedly.');

expectAnyError(@() model(-1,25,18,80,true,Inf));
expectAnyError(@() model(NaN,25,18,80,true,Inf));
expectAnyError(@() model(Inf,25,18,80,true,Inf));
expectAnyError(@() model(1+1i,25,18,80,true,Inf));
expectAnyError(@() model([1 2],25,18,80,true,Inf));
expectErrorId(@() model(12,25,18,80,1,Inf),'P02:InvalidFeedbackFlag');
expectErrorId(@() model(12,25,18,80,true,-1),'P02:InvalidCancelTime');
expectErrorId(@() model(300000,300000,1,600000,true,Inf),'P02:ResourceBound');

recovered = model(12,25,18,80,true,Inf);
assert(isequaln(recovered,baseline), ...
    'A valid transaction after malformed calls must recover without hidden state.');
disp('P02 checks passed: baseline, limits, levers, failures, recovery, and bounds.');
end

function expectAnyError(callable)
didThrow = false;
try
    callable();
catch
    didThrow = true;
end
assert(didThrow,'Malformed input must be rejected.');
end

function expectErrorId(callable,expectedId)
didThrow = false;
try
    callable();
catch exception
    didThrow = true;
    assert(strcmp(exception.identifier,expectedId), ...
        sprintf('Unexpected error identifier: %s',exception.identifier));
end
assert(didThrow,sprintf('Expected error %s was not raised.',expectedId));
end
