function interactive
%INTERACTIVE Bounded controls for the P06 command-path trace.
modelFcn = @model; % Keep P06 bound after the launcher removes its path.
fig = uifigure('Name','P06 Trace a Command Path', ...
    'Position',[50 50 1500 820]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {'1x','1x',30,80};
layout.ColumnWidth = {'1x','1x','1x','1x','1x','1x','1x','1x'};

stageAxes = uiaxes(layout);
stageAxes.Layout.Row = 1; stageAxes.Layout.Column = [1 4];
boundaryAxes = uiaxes(layout);
boundaryAxes.Layout.Row = 2; boundaryAxes.Layout.Column = [1 4];
summary = uilabel(layout,'WordWrap','on','FontName','Courier New');
summary.Layout.Row = [1 2]; summary.Layout.Column = [5 8];

label = uilabel(layout,'Text','Requested target (deg)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 1;
requestedAngle = uispinner(layout,'Limits',[-180 180],'Step',5,'Value',30);
requestedAngle.RoundFractionalValues = 'on';
requestedAngle.Layout.Row = 4; requestedAngle.Layout.Column = 1;

label = uilabel(layout,'Text','Named observation (deg)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 2;
observedAngle = uispinner(layout,'Limits',[-180 180],'Step',5,'Value',0);
observedAngle.RoundFractionalValues = 'on';
observedAngle.Layout.Row = 4; observedAngle.Layout.Column = 2;

label = uilabel(layout,'Text','Authority limit (+/-deg)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 3;
authorityLimit = uispinner(layout,'Limits',[1 180],'Step',5,'Value',45);
authorityLimit.RoundFractionalValues = 'on';
authorityLimit.Layout.Row = 4; authorityLimit.Layout.Column = 3;

label = uilabel(layout,'Text','Response fraction (-)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 4;
responseFraction = uispinner(layout,'Limits',[0 1],'Step',0.05,'Value',0.35);
responseFraction.Layout.Row = 4; responseFraction.Layout.Column = 4;

label = uilabel(layout,'Text','Open boundary','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 5;
openBoundary = uidropdown(layout, ...
    'Items',{'None','B1 request -> authority','B2 authority -> error', ...
    'B3 error -> correction','B4 correction -> actuator'},'Value','None');
openBoundary.ItemsData = {'none','request-to-authority', ...
    'authority-to-error','error-to-correction','correction-to-actuator'};
openBoundary.Layout.Row = 4; openBoundary.Layout.Column = 5;

label = uilabel(layout,'Text','Final-handoff guard', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 6;
eventMode = uidropdown(layout, ...
    'Items',{'None','Cancellation','Timeout','Cancel + timeout tie'}, ...
    'Value','None');
eventMode.ItemsData = { ...
    'none','cancellation','timeout','cancellation-timeout-tie'};
eventMode.Layout.Row = 4; eventMode.Layout.Column = 6;

label = uilabel(layout,'Text','Delivery evidence', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 7;
assessmentMode = uidropdown(layout, ...
    'Items',{'Endpoint receipt','Broken: dispatch only'}, ...
    'Value','Endpoint receipt');
assessmentMode.ItemsData = {'endpoint-receipt','dispatch-only'};
assessmentMode.Layout.Row = 4; assessmentMode.Layout.Column = 7;

resetButton = uibutton(layout,'Text','Reset baseline');
resetButton.Layout.Row = 4; resetButton.Layout.Column = 8;

requestedAngle.ValueChangedFcn = @(~,~) updatePlots();
observedAngle.ValueChangedFcn = @(~,~) updatePlots();
authorityLimit.ValueChangedFcn = @(~,~) updatePlots();
responseFraction.ValueChangedFcn = @(~,~) updatePlots();
openBoundary.ValueChangedFcn = @(~,~) updatePlots();
eventMode.ValueChangedFcn = @(~,~) updatePlots();
assessmentMode.ValueChangedFcn = @(~,~) updatePlots();
resetButton.ButtonPushedFcn = @(~,~) resetBaseline();
updatePlots();

    function updatePlots
        out = modelFcn(requestedAngle.Value,observedAngle.Value, ...
            authorityLimit.Value,responseFraction.Value, ...
            openBoundary.Value,eventMode.Value,assessmentMode.Value);

        cla(stageAxes);
        bar(stageAxes,1:out.stageCount,double(out.stageReached));
        grid(stageAxes,'on'); ylim(stageAxes,[0 1.2]);
        stageAxes.XTick = 1:out.stageCount;
        stageAxes.XTickLabel = out.stageNames;
        stageAxes.XTickLabelRotation = 25;
        stageAxes.YTick = [0 1];
        stageAxes.YTickLabel = {'No','Yes'};
        xlabel(stageAxes,'P04/P05 command-path stage (-)');
        ylabel(stageAxes,'Stage reached (Boolean -)');
        title(stageAxes,'Reachability ends at the first rejected or missing handoff');

        cla(boundaryAxes);
        imagesc(boundaryAxes,1:3,1:out.boundaryCount, ...
            [double(out.boundaryAttempted(:)), ...
            double(out.boundaryCrossed(:)),double(out.boundaryOpen(:))]);
        colormap(boundaryAxes,[1 1 1; 0.10 0.45 0.75]);
        caxis(boundaryAxes,[0 1]);
        boundaryAxes.XTick = 1:3;
        boundaryAxes.XTickLabel = {'Guard evaluated','Crossed','Declared open'};
        boundaryAxes.YTick = 1:out.boundaryCount;
        boundaryAxes.YTickLabel = out.boundaryLabels;
        xlabel(boundaryAxes,'Boundary disposition (Boolean -)');
        ylabel(boundaryAxes,'Command handoff (-)');
        title(boundaryAxes,'A local stage output does not prove the next owner received it');

        if out.firstOpenBoundary == 0
            openText = 'none';
        else
            openText = out.boundaryNames{out.firstOpenBoundary};
        end
        summary.Text = sprintf(['COMMAND TRACE\n\nrequest                 %7.1f deg\n' ...
            'named observation       %7.1f deg\nauthority limit        +/-%5.1f deg\n' ...
            'response fraction       %7.2f -\n\naccepted target         %7.1f deg\n' ...
            'error                   %7.1f deg\ncorrection              %7.1f deg/update\n\n' ...
            'deepest stage           %7d / %d\ncrossed boundaries      %7d / %d\n' ...
            'first open boundary     %s\nevent guard reached     %7d\n' ...
            'cancellation observed   %7d\ntimeout observed        %7d\n' ...
            'safe-hold required      %7d\nsafe-hold request avail %7d\n' ...
            'local dispatch          %7d\nactuator input receipt  %7d\n\n' ...
            'terminal                %s\nterminal handled        %7d\n' ...
            'trace contract met      %7d\nreported delivery       %7d\n' ...
            'false success           %7d\nfailure                 %s'], ...
            out.inputs.requestedAngleDeg,out.inputs.observedAngleDeg, ...
            out.inputs.authorityLimitDeg,out.inputs.responseFraction, ...
            out.acceptedTargetDeg,out.errorDeg,out.correctionDegPerUpdate, ...
            out.deepestReachedStage,out.stageCount,out.crossedBoundaryCount, ...
            out.boundaryCount,openText,out.eventGuardReached, ...
            out.cancellationObserved,out.timeoutObserved,out.safeHoldRequired, ...
            out.safeHoldRequestAvailable,out.localDispatchObserved, ...
            out.actuatorCommandReceived,out.terminalStatus, ...
            out.terminalOutcomeHandled,out.traceContractMet, ...
            out.reportedSuccess,out.falseSuccess,out.failureMode);
    end

    function resetBaseline
        requestedAngle.Value = 30;
        observedAngle.Value = 0;
        authorityLimit.Value = 45;
        responseFraction.Value = 0.35;
        openBoundary.Value = 'none';
        eventMode.Value = 'none';
        assessmentMode.Value = 'endpoint-receipt';
        updatePlots();
    end
end
