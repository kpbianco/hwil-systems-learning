function interactive
%INTERACTIVE Bounded controls for the P02 operator transaction.
modelFcn = @model; % Keep the P02 model bound after the launcher removes its path.
fig = uifigure('Name','P02 CONOPS Operator Transaction','Position',[100 100 1180 720]);
layout = uigridlayout(fig,[4 6]);
layout.RowHeight = {'1x','1x',30,80};
layout.ColumnWidth = {'1x','1x','1x','1x','1x','1x'};

timelineAxes = uiaxes(layout);
timelineAxes.Layout.Row = 1; timelineAxes.Layout.Column = [1 4];
criteriaAxes = uiaxes(layout);
criteriaAxes.Layout.Row = 2; criteriaAxes.Layout.Column = [1 4];
summary = uilabel(layout,'WordWrap','on','FontName','Courier New');
summary.Layout.Row = [1 2]; summary.Layout.Column = [5 6];

label = uilabel(layout,'Text','Command latency (ms)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 1;
commandLatency = uislider(layout,'Limits',[0 80],'Value',12);
commandLatency.Layout.Row = 4; commandLatency.Layout.Column = 1;

label = uilabel(layout,'Text','Feedback latency (ms)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 2;
feedbackLatency = uislider(layout,'Limits',[0 100],'Value',18);
feedbackLatency.Layout.Row = 4; feedbackLatency.Layout.Column = 2;

label = uilabel(layout,'Text','Decision deadline (ms)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 3;
deadline = uislider(layout,'Limits',[1 200],'Value',80);
deadline.Layout.Row = 4; deadline.Layout.Column = 3;

label = uilabel(layout,'Text','Observability','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 4;
feedbackAvailable = uicheckbox(layout,'Text','Feedback available','Value',true);
feedbackAvailable.Layout.Row = 4; feedbackAvailable.Layout.Column = 4;

label = uilabel(layout,'Text','Operator cancellation','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 5;
cancel = uidropdown(layout,'Items',{'None','At 0 ms','At 20 ms','At 40 ms','At 80 ms'});
cancel.ItemsData = [Inf 0 20 40 80]; cancel.Value = Inf;
cancel.Layout.Row = 4; cancel.Layout.Column = 5;

resetButton = uibutton(layout,'Text','Reset baseline');
resetButton.Layout.Row = 4; resetButton.Layout.Column = 6;

commandLatency.ValueChangingFcn = @(~,event) updatePlots(event.Value,feedbackLatency.Value,deadline.Value);
feedbackLatency.ValueChangingFcn = @(~,event) updatePlots(commandLatency.Value,event.Value,deadline.Value);
deadline.ValueChangingFcn = @(~,event) updatePlots(commandLatency.Value,feedbackLatency.Value,event.Value);
commandLatency.ValueChangedFcn = @(~,~) updatePlots();
feedbackLatency.ValueChangedFcn = @(~,~) updatePlots();
deadline.ValueChangedFcn = @(~,~) updatePlots();
feedbackAvailable.ValueChangedFcn = @(~,~) updatePlots();
cancel.ValueChangedFcn = @(~,~) updatePlots();
resetButton.ButtonPushedFcn = @(~,~) resetBaseline();
updatePlots();

    function updatePlots(commandOverride,feedbackOverride,deadlineOverride)
        if nargin < 1, commandOverride = commandLatency.Value; end
        if nargin < 2, feedbackOverride = feedbackLatency.Value; end
        if nargin < 3, deadlineOverride = deadline.Value; end
        out = modelFcn(commandOverride,25,feedbackOverride,deadlineOverride, ...
            feedbackAvailable.Value,cancel.Value);

        eventLabels = {'Sent','Received','Effect','Feedback','Deadline','Terminal'};
        displayTimes = out.eventTimesMs;
        displayTimes(isinf(displayTimes)) = NaN;
        cla(timelineAxes);
        bar(timelineAxes,1:numel(displayTimes),displayTimes);
        xticks(timelineAxes,1:numel(eventLabels)); xticklabels(timelineAxes,eventLabels);
        ylabel(timelineAxes,'Elapsed time (ms)'); grid(timelineAxes,'on');
        title(timelineAxes,'Occurred events; deadline is the decision reference');

        criterionLabels = {'Effect','Observed','Goal met','Safe hold'};
        cla(criteriaAxes);
        bar(criteriaAxes,1:numel(out.criteria),double(out.criteria));
        xticks(criteriaAxes,1:numel(criterionLabels)); xticklabels(criteriaAxes,criterionLabels);
        ylabel(criteriaAxes,'State (0 = no, 1 = yes)'); ylim(criteriaAxes,[0 1.2]);
        grid(criteriaAxes,'on'); title(criteriaAxes,'Decision criteria');

        if isinf(cancel.Value), cancelText = 'none'; else, cancelText = sprintf('%.0f ms',cancel.Value); end
        if isnan(out.achievedConfirmationMarginMs)
            achievedMarginText = 'n/a';
        else
            achievedMarginText = sprintf('%.1f ms',out.achievedConfirmationMarginMs);
        end
        summary.Text = sprintf(['OPERATOR TRANSACTION\n\nplanned command   %7.1f ms\n' ...
            'planned effect    %7.1f ms\nplanned feedback  %7.1f ms\n' ...
            'deadline          %7.1f ms\nterminal          %7.1f ms\n\n' ...
            'state: %s\nplanned margin: %.1f ms\nachieved margin: %s\ncancel: %s'], ...
            out.plannedCommandReceiptMs,out.plannedEffectReachedMs,out.plannedFeedbackArrivalMs, ...
            out.decisionDeadlineMs,out.terminalTimeMs,out.terminalState, ...
            out.plannedScheduleMarginMs,achievedMarginText,cancelText);
    end

    function resetBaseline
        commandLatency.Value = 12;
        feedbackLatency.Value = 18;
        deadline.Value = 80;
        feedbackAvailable.Value = true;
        cancel.Value = Inf;
        updatePlots();
    end
end
