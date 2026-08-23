function interactive
%INTERACTIVE Bounded controls for the P04 functional decomposition.
modelFcn = @model; % Keep the P04 model bound after the launcher removes its path.
fig = uifigure('Name','P04 Decompose a System into Functions', ...
    'Position',[80 80 1380 780]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {'1x','1x',30,80};
layout.ColumnWidth = {'1x','1x','1x','1x','1x','1x','1x','1x'};

positionAxes = uiaxes(layout);
positionAxes.Layout.Row = 1; positionAxes.Layout.Column = [1 6];
functionAxes = uiaxes(layout);
functionAxes.Layout.Row = 2; functionAxes.Layout.Column = [1 6];
summary = uilabel(layout,'WordWrap','on','FontName','Courier New');
summary.Layout.Row = [1 2]; summary.Layout.Column = [7 8];

label = uilabel(layout,'Text','Request (deg)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 1;
request = uislider(layout,'Limits',[-75 75],'Value',30);
request.Layout.Row = 4; request.Layout.Column = 1;

label = uilabel(layout,'Text','Response fraction (-)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 2;
response = uislider(layout,'Limits',[0 0.90],'Value',0.35);
response.Layout.Row = 4; response.Layout.Column = 2;

label = uilabel(layout,'Text','Confirmation samples','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 3;
confirmation = uispinner(layout,'Limits',[1 10],'Step',1,'Value',3);
confirmation.RoundFractionalValues = 'on';
confirmation.Layout.Row = 4; confirmation.Layout.Column = 3;

label = uilabel(layout,'Text','Authority (deg)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 4;
authority = uislider(layout,'Limits',[20 60],'Value',45);
authority.Layout.Row = 4; authority.Layout.Column = 4;

label = uilabel(layout,'Text','Deadline (ms)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 5;
deadlineValues = 100:20:2000;
deadline = uidropdown(layout,'Items',cellstr(compose('%d ms',deadlineValues)));
deadline.ItemsData = deadlineValues;
deadline.Value = 1000;
deadline.Layout.Row = 4; deadline.Layout.Column = 5;

label = uilabel(layout,'Text','Cancellation','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 6;
cancellation = uidropdown(layout, ...
    'Items',{'None','At 0 ms','At 120 ms','At 240 ms'},'Value','None');
cancellation.ItemsData = [Inf 0 120 240];
cancellation.Layout.Row = 4; cancellation.Layout.Column = 6;

label = uilabel(layout,'Text','Architecture','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 7;
architecture = uidropdown(layout, ...
    'Items',{'Complete','Broken: overwrite intent'},'Value','Complete');
architecture.ItemsData = {'complete','bypass-validation'};
architecture.Layout.Row = 4; architecture.Layout.Column = 7;

resetButton = uibutton(layout,'Text','Reset baseline');
resetButton.Layout.Row = 4; resetButton.Layout.Column = 8;

request.ValueChangingFcn = @(~,event) updatePlots(event.Value,response.Value,authority.Value);
response.ValueChangingFcn = @(~,event) updatePlots(request.Value,event.Value,authority.Value);
authority.ValueChangingFcn = @(~,event) updatePlots(request.Value,response.Value,event.Value);
request.ValueChangedFcn = @(~,~) updatePlots();
response.ValueChangedFcn = @(~,~) updatePlots();
confirmation.ValueChangedFcn = @(~,~) updatePlots();
authority.ValueChangedFcn = @(~,~) updatePlots();
deadline.ValueChangedFcn = @(~,~) updatePlots();
cancellation.ValueChangedFcn = @(~,~) updatePlots();
architecture.ValueChangedFcn = @(~,~) updatePlots();
resetButton.ButtonPushedFcn = @(~,~) resetBaseline();
updatePlots();

    function updatePlots(requestOverride,responseOverride,authorityOverride)
        if nargin < 1, requestOverride = request.Value; end
        if nargin < 2, responseOverride = response.Value; end
        if nargin < 3, authorityOverride = authority.Value; end
        out = modelFcn(requestOverride,responseOverride,confirmation.Value, ...
            authorityOverride,0.5,deadline.Value,cancellation.Value,architecture.Value);

        viewEndMs = min(out.horizonMs,max(400,out.inputs.deadlineMs + 200));
        cla(positionAxes);
        plot(positionAxes,out.timeMs,out.positionDeg,'LineWidth',1.5, ...
            'DisplayName','Observed position'); hold(positionAxes,'on');
        yline(positionAxes,out.requestedTargetDeg,'--','Original request');
        yline(positionAxes,out.effectiveTargetDeg,':','Effective target');
        yline(positionAxes,out.requestedTargetDeg + out.inputs.toleranceDeg,':');
        yline(positionAxes,out.requestedTargetDeg - out.inputs.toleranceDeg,':');
        xline(positionAxes,out.inputs.deadlineMs,'--','Deadline');
        xline(positionAxes,out.reportTimeMs,':','Report'); hold(positionAxes,'off');
        grid(positionAxes,'on'); xlabel(positionAxes,'Elapsed functional time (ms)');
        ylabel(positionAxes,'Rotary position (deg)'); xlim(positionAxes,[0 viewEndMs]);
        title(positionAxes,'Original request, effective target, and observed state');

        cla(functionAxes);
        imagesc(functionAxes,out.timeMs,1:out.functionCount, ...
            double(out.functionActivation'));
        colormap(functionAxes,[1 1 1; 0.10 0.45 0.75]); caxis(functionAxes,[0 1]);
        functionAxes.YTick = 1:out.functionCount;
        functionAxes.YTickLabel = out.functionNames;
        xlabel(functionAxes,'Elapsed functional time (ms)');
        ylabel(functionAxes,'Named system function'); xlim(functionAxes,[0 viewEndMs]);
        title(functionAxes,'Function activation exposes omissions and terminal ownership');

        if isinf(out.firstWithinRequestToleranceMs)
            firstEntryText = 'not reached';
        else
            firstEntryText = sprintf('%.0f ms',out.firstWithinRequestToleranceMs);
        end
        summary.Text = sprintf(['FUNCTIONAL RESULT\n\nrequest          %7.1f deg\n' ...
            'effective target %7.1f deg\nauthority margin %7.1f deg\n' ...
            'first request-band entry %s\nreport time      %7.0f ms\n' ...
            'request error    %7.3f deg\nlocal error      %7.3f deg\n' ...
            'functions seen   %7d / %d\n\nreported success: %d\n' ...
            'false success:    %d\nrequest goal met: %d\nsafe hold required: %d\n' ...
            'failure: %s'], ...
            out.requestedTargetDeg,out.effectiveTargetDeg,out.authorityMarginDeg, ...
            firstEntryText,out.reportTimeMs,out.requestErrorAtReportDeg, ...
            out.monitorErrorAtReportDeg,out.executedFunctionCount,out.functionCount, ...
            out.reportedSuccess,out.falseSuccess,out.requestGoalMet, ...
            out.safeHoldRequired,out.failureMode);
    end

    function resetBaseline
        request.Value = 30;
        response.Value = 0.35;
        confirmation.Value = 3;
        authority.Value = 45;
        deadline.Value = 1000;
        cancellation.Value = Inf;
        architecture.Value = 'complete';
        updatePlots();
    end
end
