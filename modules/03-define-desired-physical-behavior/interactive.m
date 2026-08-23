function interactive
%INTERACTIVE Bounded controls for the P03 rotary behavior envelope.
modelFcn = @model; % Keep the P03 model bound after the launcher removes its path.
fig = uifigure('Name','P03 Desired Physical Behavior','Position',[100 100 1200 740]);
layout = uigridlayout(fig,[4 6]);
layout.RowHeight = {'1x','1x',30,80};
layout.ColumnWidth = {'1x','1x','1x','1x','1x','1x'};

positionAxes = uiaxes(layout);
positionAxes.Layout.Row = 1; positionAxes.Layout.Column = [1 4];
velocityAxes = uiaxes(layout);
velocityAxes.Layout.Row = 2; velocityAxes.Layout.Column = [1 4];
summary = uilabel(layout,'WordWrap','on','FontName','Courier New');
summary.Layout.Row = [1 2]; summary.Layout.Column = [5 6];

label = uilabel(layout,'Text','Command angle (deg)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 1;
command = uislider(layout,'Limits',[-75 75],'Value',30);
command.Layout.Row = 4; command.Layout.Column = 1;

label = uilabel(layout,'Text','Damping ratio (-)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 2;
damping = uislider(layout,'Limits',[0.2 1.0],'Value',0.7);
damping.Layout.Row = 4; damping.Layout.Column = 2;

label = uilabel(layout,'Text','Natural frequency (Hz)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 3;
frequency = uislider(layout,'Limits',[0.5 3.0],'Value',1.5);
frequency.Layout.Row = 4; frequency.Layout.Column = 3;

label = uilabel(layout,'Text','Command authority (deg)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 4;
authority = uislider(layout,'Limits',[20 60],'Value',45);
authority.Layout.Row = 4; authority.Layout.Column = 4;

label = uilabel(layout,'Text','Response deadline (ms)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 5;
deadline = uislider(layout,'Limits',[300 2500],'Value',1200);
deadline.Layout.Row = 4; deadline.Layout.Column = 5;

resetButton = uibutton(layout,'Text','Reset baseline');
resetButton.Layout.Row = 4; resetButton.Layout.Column = 6;

command.ValueChangingFcn = @(~,event) updatePlots(event.Value,damping.Value, ...
    frequency.Value,authority.Value,deadline.Value);
damping.ValueChangingFcn = @(~,event) updatePlots(command.Value,event.Value, ...
    frequency.Value,authority.Value,deadline.Value);
frequency.ValueChangingFcn = @(~,event) updatePlots(command.Value,damping.Value, ...
    event.Value,authority.Value,deadline.Value);
authority.ValueChangingFcn = @(~,event) updatePlots(command.Value,damping.Value, ...
    frequency.Value,event.Value,deadline.Value);
deadline.ValueChangingFcn = @(~,event) updatePlots(command.Value,damping.Value, ...
    frequency.Value,authority.Value,event.Value);
command.ValueChangedFcn = @(~,~) updatePlots();
damping.ValueChangedFcn = @(~,~) updatePlots();
frequency.ValueChangedFcn = @(~,~) updatePlots();
authority.ValueChangedFcn = @(~,~) updatePlots();
deadline.ValueChangedFcn = @(~,~) updatePlots();
resetButton.ButtonPushedFcn = @(~,~) resetBaseline();
updatePlots();

    function updatePlots(commandOverride,dampingOverride,frequencyOverride,authorityOverride,deadlineOverride)
        if nargin < 1, commandOverride = command.Value; end
        if nargin < 2, dampingOverride = damping.Value; end
        if nargin < 3, frequencyOverride = frequency.Value; end
        if nargin < 4, authorityOverride = authority.Value; end
        if nargin < 5, deadlineOverride = deadline.Value; end
        out = modelFcn(commandOverride,frequencyOverride,dampingOverride, ...
            authorityOverride,0.5,2,deadlineOverride);

        cla(positionAxes);
        plot(positionAxes,out.timeMs,out.positionDeg,'LineWidth',1.5); hold(positionAxes,'on');
        yline(positionAxes,out.requestedCommandDeg,'--','Requested');
        yline(positionAxes,out.effectiveCommandDeg,':','Effective target');
        yline(positionAxes,out.requestedCommandDeg + out.inputs.positionToleranceDeg,':');
        yline(positionAxes,out.requestedCommandDeg - out.inputs.positionToleranceDeg,':');
        xline(positionAxes,out.inputs.deadlineMs,'--','Deadline'); hold(positionAxes,'off');
        grid(positionAxes,'on'); xlabel(positionAxes,'Time from accepted command (ms)');
        ylabel(positionAxes,'Rotary position (deg)');
        xlim(positionAxes,[0 3000]);
        title(positionAxes,'Requested, effective, and observed position');

        cla(velocityAxes);
        plot(velocityAxes,out.timeMs,out.velocityDegPerSec,'LineWidth',1.5); hold(velocityAxes,'on');
        yline(velocityAxes,out.inputs.velocityToleranceDegPerSec,':','Velocity tolerance');
        yline(velocityAxes,-out.inputs.velocityToleranceDegPerSec,':');
        xline(velocityAxes,out.inputs.deadlineMs,'--','Deadline'); hold(velocityAxes,'off');
        grid(velocityAxes,'on'); xlabel(velocityAxes,'Time from accepted command (ms)');
        ylabel(velocityAxes,'Rotary velocity (deg/s)');
        xlim(velocityAxes,[0 3000]);
        title(velocityAxes,'Motion must be quiet as well as close to target');

        if isinf(out.settlingTimeMs)
            settlingText = 'not achieved';
        else
            settlingText = sprintf('%.0f ms',out.settlingTimeMs);
        end
        summary.Text = sprintf(['DESIRED BEHAVIOR\n\nrequested       %7.1f deg\n' ...
            'effective       %7.1f deg\nauthority margin %7.1f deg\n' ...
            'peak position   %7.1f deg\npeak velocity   %7.1f deg/s\n' ...
            'overshoot       %7.2f %%\nsettling        %s\n\n' ...
            'deadline met: %d\nbehavior met: %d\nfailure: %s'], ...
            out.requestedCommandDeg,out.effectiveCommandDeg,out.commandAuthorityMarginDeg, ...
            out.peakPositionMagnitudeDeg,out.peakVelocityMagnitudeDegPerSec, ...
            out.overshootPercent,settlingText,out.settledByDeadline, ...
            out.requirementsMet,out.failureMode);
    end

    function resetBaseline
        command.Value = 30;
        damping.Value = 0.7;
        frequency.Value = 1.5;
        authority.Value = 45;
        deadline.Value = 1200;
        updatePlots();
    end
end
