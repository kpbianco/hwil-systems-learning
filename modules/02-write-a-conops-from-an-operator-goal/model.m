function out = model(commandLatencyMs,actionDurationMs,feedbackLatencyMs,decisionDeadlineMs,feedbackAvailable,cancelAtMs)
%MODEL Deterministic operator transaction for a CONOPS decision.
%   The operator requests a test-article state at t=0. The command travels,
%   the physical action completes, feedback returns, and the operator either
%   confirms success or commands safe hold on cancellation or timeout.

if nargin < 1, commandLatencyMs = 12; end
if nargin < 2, actionDurationMs = 25; end
if nargin < 3, feedbackLatencyMs = 18; end
if nargin < 4, decisionDeadlineMs = 80; end
if nargin < 5, feedbackAvailable = true; end
if nargin < 6, cancelAtMs = Inf; end

maxHorizonMs = 600000;
validateattributes(commandLatencyMs,{'numeric'}, ...
    {'scalar','real','finite','nonnegative'},mfilename,'commandLatencyMs');
validateattributes(actionDurationMs,{'numeric'}, ...
    {'scalar','real','finite','nonnegative'},mfilename,'actionDurationMs');
validateattributes(feedbackLatencyMs,{'numeric'}, ...
    {'scalar','real','finite','nonnegative'},mfilename,'feedbackLatencyMs');
validateattributes(decisionDeadlineMs,{'numeric'}, ...
    {'scalar','real','finite','positive'},mfilename,'decisionDeadlineMs');
if ~(islogical(feedbackAvailable) && isscalar(feedbackAvailable))
    error('P02:InvalidFeedbackFlag','feedbackAvailable must be one logical scalar.');
end
if ~(isnumeric(cancelAtMs) && isscalar(cancelAtMs) && isreal(cancelAtMs))
    error('P02:InvalidCancelTime','cancelAtMs must be a nonnegative scalar or positive Inf.');
end

commandLatencyMs = double(commandLatencyMs);
actionDurationMs = double(actionDurationMs);
feedbackLatencyMs = double(feedbackLatencyMs);
decisionDeadlineMs = double(decisionDeadlineMs);
cancelAtMs = double(cancelAtMs);
if isnan(cancelAtMs) || cancelAtMs < 0
    error('P02:InvalidCancelTime','cancelAtMs must be a nonnegative scalar or positive Inf.');
end
if any([commandLatencyMs actionDurationMs feedbackLatencyMs decisionDeadlineMs] > maxHorizonMs)
    error('P02:ResourceBound','Each finite time must be at most %.0f ms.',maxHorizonMs);
end
if ~isinf(cancelAtMs) && cancelAtMs > maxHorizonMs
    error('P02:ResourceBound','Finite cancellation time must be at most %.0f ms.',maxHorizonMs);
end

plannedCommandReceiptMs = commandLatencyMs;
plannedEffectReachedMs = plannedCommandReceiptMs + actionDurationMs;
plannedFeedbackArrivalMs = plannedEffectReachedMs + feedbackLatencyMs;
if plannedFeedbackArrivalMs > maxHorizonMs
    error('P02:ResourceBound','The derived transaction horizon exceeds %.0f ms.',maxHorizonMs);
end
if feedbackAvailable
    availableFeedbackArrivalMs = plannedFeedbackArrivalMs;
else
    availableFeedbackArrivalMs = Inf;
end

firstNoncancelEventMs = min(availableFeedbackArrivalMs,decisionDeadlineMs);
if cancelAtMs <= firstNoncancelEventMs
    terminalState = 'cancelled-safe-hold';
    terminalTimeMs = cancelAtMs;
    cancelled = true;
    confirmed = false;
elseif feedbackAvailable && availableFeedbackArrivalMs <= decisionDeadlineMs
    terminalState = 'confirmed';
    terminalTimeMs = availableFeedbackArrivalMs;
    cancelled = false;
    confirmed = true;
else
    terminalState = 'timeout-safe-hold';
    terminalTimeMs = decisionDeadlineMs;
    cancelled = false;
    confirmed = false;
end

if cancelled
    % Cancellation has safety priority over events at the same timestamp.
    commandWasReceived = plannedCommandReceiptMs < terminalTimeMs;
    physicalGoalReached = plannedEffectReachedMs < terminalTimeMs;
else
    commandWasReceived = plannedCommandReceiptMs <= terminalTimeMs;
    physicalGoalReached = plannedEffectReachedMs <= terminalTimeMs;
end
feedbackObserved = confirmed;
safeHoldCommanded = ~confirmed;
actualCommandReceiptMs = Inf;
actualEffectReachedMs = Inf;
actualFeedbackArrivalMs = Inf;
if commandWasReceived, actualCommandReceiptMs = plannedCommandReceiptMs; end
if physicalGoalReached, actualEffectReachedMs = plannedEffectReachedMs; end
if feedbackObserved, actualFeedbackArrivalMs = plannedFeedbackArrivalMs; end
achievedConfirmationMarginMs = NaN;
if confirmed
    achievedConfirmationMarginMs = decisionDeadlineMs - terminalTimeMs;
end

out = struct();
out.inputs = struct('commandLatencyMs',commandLatencyMs, ...
    'actionDurationMs',actionDurationMs, ...
    'feedbackLatencyMs',feedbackLatencyMs, ...
    'decisionDeadlineMs',decisionDeadlineMs, ...
    'feedbackAvailable',feedbackAvailable, ...
    'cancelAtMs',cancelAtMs);
out.plannedCommandReceiptMs = plannedCommandReceiptMs;
out.plannedEffectReachedMs = plannedEffectReachedMs;
out.plannedFeedbackArrivalMs = plannedFeedbackArrivalMs;
out.actualCommandReceiptMs = actualCommandReceiptMs;
out.actualEffectReachedMs = actualEffectReachedMs;
out.actualFeedbackArrivalMs = actualFeedbackArrivalMs;
out.decisionDeadlineMs = decisionDeadlineMs;
out.terminalTimeMs = terminalTimeMs;
out.terminalState = terminalState;
out.physicalGoalReached = physicalGoalReached;
out.feedbackObserved = feedbackObserved;
out.operatorGoalMet = confirmed;
out.safeHoldCommanded = safeHoldCommanded;
out.cancelled = cancelled;
out.plannedScheduleMarginMs = decisionDeadlineMs - plannedFeedbackArrivalMs;
out.achievedConfirmationMarginMs = achievedConfirmationMarginMs;
out.eventTimesMs = [0 actualCommandReceiptMs actualEffectReachedMs actualFeedbackArrivalMs ...
    decisionDeadlineMs terminalTimeMs];
out.criteria = [physicalGoalReached feedbackObserved confirmed safeHoldCommanded];
out.maxHorizonMs = maxHorizonMs;
out.timelineSlotCount = numel(out.eventTimesMs);
out.occurredEventCount = 2 + double(commandWasReceived) + ...
    double(physicalGoalReached) + double(feedbackObserved);
end
