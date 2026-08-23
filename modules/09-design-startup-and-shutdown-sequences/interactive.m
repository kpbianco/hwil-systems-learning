function fig = interactive()
%INTERACTIVE Explore P09 ordering guards with bounded MATLAB controls.
%   The callback captures the model handle so it remains valid if a launcher
%   later removes the module folder from the MATLAB path.

modelFcn = @model;
fig = uifigure('Name','P09 Startup and Shutdown Sequence Explorer', ...
    'Position',[100 100 1180 760]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {28,28,'1x',105};
layout.ColumnWidth = {150,105,150,105,145,145,145,'1x'};

uilabel(layout,'Text','Startup enable position');
startupPosition = uispinner(layout,'Limits',[1 5], ...
    'Step',1,'Value',5,'RoundFractionalValues','on');
uilabel(layout,'Text','Shutdown power position');
shutdownPosition = uispinner(layout,'Limits',[1 6], ...
    'Step',1,'Value',6,'RoundFractionalValues','on');
p08Conformance = uicheckbox(layout,'Text','P08 conformant', ...
    'Value',true);
p08Eligibility = uicheckbox(layout,'Text','P08 input eligible', ...
    'Value',true);
resetButton = uibutton(layout,'Text','Reset baseline', ...
    'ButtonPushedFcn',@resetBaseline);
questionLabel = uilabel(layout,'Text', ...
    'Move one position at a time; read the missing prerequisite before the final snapshot.');

uilabel(layout,'Text','Injected shutdown fault');
faultMode = uidropdown(layout);
faultMode.Items = {'None','Actuator stuck on','Quiescence not confirmed'};
faultMode.ItemsData = {'none','actuator-stuck-on', ...
    'quiescence-not-confirmed'};
faultMode.Value = 'none';
uilabel(layout,'Text','Injected startup event');
eventMode = uidropdown(layout);
eventMode.Items = {'None','Cancellation','Timeout', ...
    'Cancellation/timeout tie'};
eventMode.ItemsData = {'none','cancellation','timeout', ...
    'cancellation-timeout-tie'};
eventMode.Value = 'none';
uilabel(layout,'Text','Assessment rule');
assessmentMode = uidropdown(layout);
assessmentMode.Items = {'Strict ordered evidence', ...
    'Broken final snapshots only'};
assessmentMode.ItemsData = {'strict-order','final-state-only'};
assessmentMode.Value = 'strict-order';
boundaryLabel = uilabel(layout,'Text', ...
    'Action index is dimensionless; timeout is an asserted event, not measured time.');
boundaryLabel.Layout.Column = [7 8];

startupAxes = uiaxes(layout);
startupAxes.Layout.Row = 3;
startupAxes.Layout.Column = [1 4];
shutdownAxes = uiaxes(layout);
shutdownAxes.Layout.Row = 3;
shutdownAxes.Layout.Column = [5 8];
summaryLabel = uilabel(layout,'WordWrap','on', ...
    'VerticalAlignment','top');
summaryLabel.Layout.Row = 4;
summaryLabel.Layout.Column = [1 8];

startupPosition.ValueChangedFcn = @updateView;
shutdownPosition.ValueChangedFcn = @updateView;
p08Conformance.ValueChangedFcn = @updateView;
p08Eligibility.ValueChangedFcn = @updateView;
faultMode.ValueChangedFcn = @updateView;
eventMode.ValueChangedFcn = @updateView;
assessmentMode.ValueChangedFcn = @updateView;

updateView([],[]);

    function updateView(~,~)
        if ~p08Conformance.Value && p08Eligibility.Value
            p08Eligibility.Value = false;
        end
        out = modelFcn(startupPosition.Value,shutdownPosition.Value, ...
            p08Conformance.Value,p08Eligibility.Value,faultMode.Value, ...
            eventMode.Value,assessmentMode.Value);

        startupValues = double(out.startupEnablePrerequisitePass);
        if isnan(out.startupEnableMissingPrerequisiteCount)
            startupValues(:) = NaN;
        end
        bar(startupAxes,1:numel(startupValues),startupValues, ...
            'FaceColor',[0.12 0.48 0.72]);
        startupAxes.XTick = 1:numel(startupValues);
        startupAxes.XTickLabel = out.startupEnablePrerequisiteNames;
        startupAxes.XTickLabelRotation = 22;
        startupAxes.YTick = [0 1];
        startupAxes.YTickLabel = {'Missing','Present'};
        startupAxes.YLim = [0 1.2];
        startupAxes.XLabel.String = 'Actuator-enable prerequisite (-)';
        startupAxes.YLabel.String = 'Observed fact (Boolean -)';
        startupAxes.Title.String = sprintf( ...
            'Startup position %d: missing %s prerequisites', ...
            out.inputs.startupEnablePosition, ...
            displayCount(out.startupEnableMissingPrerequisiteCount));
        grid(startupAxes,'on');

        shutdownValues = double(out.shutdownPowerPrerequisitePass);
        if isnan(out.shutdownPowerMissingPrerequisiteCount)
            shutdownValues(:) = NaN;
        end
        bar(shutdownAxes,1:numel(shutdownValues),shutdownValues, ...
            'FaceColor',[0.58 0.24 0.68]);
        shutdownAxes.XTick = 1:numel(shutdownValues);
        shutdownAxes.XTickLabel = out.shutdownPowerPrerequisiteNames;
        shutdownAxes.XTickLabelRotation = 22;
        shutdownAxes.YTick = [0 1];
        shutdownAxes.YTickLabel = {'Missing','Present'};
        shutdownAxes.YLim = [0 1.2];
        shutdownAxes.XLabel.String = 'Power-removal prerequisite (-)';
        shutdownAxes.YLabel.String = 'Observed fact (Boolean -)';
        shutdownAxes.Title.String = sprintf( ...
            'Shutdown position %d: missing %s prerequisites', ...
            out.inputs.shutdownPowerOffPosition, ...
            displayCount(out.shutdownPowerMissingPrerequisiteCount));
        grid(shutdownAxes,'on');

        summaryLabel.Text = sprintf([ ...
            'Terminal: %s | factual failure: %s | strict acceptance: %d | ' ...
            'reported acceptance: %d | false approval: %d | rollback safe hold: %d | ' ...
            'rollback failure: %s\n' ...
            'Mechanism: guards and postconditions retain transient order. ' ...
            'The broken final-state-only rule can discard that evidence even when running and off snapshots look correct.'], ...
            out.terminalStatus,out.failureMode,out.strictLifecycleAccepted, ...
            out.reportedLifecycleAccepted,out.falseApproval, ...
            out.rollbackSafeHold,out.rollbackFailureMode);
    end

    function resetBaseline(~,~)
        startupPosition.Value = 5;
        shutdownPosition.Value = 6;
        p08Conformance.Value = true;
        p08Eligibility.Value = true;
        faultMode.Value = 'none';
        eventMode.Value = 'none';
        assessmentMode.Value = 'strict-order';
        updateView([],[]);
    end

    function text = displayCount(value)
        if isnan(value)
            text = 'not-evaluated';
        else
            text = sprintf('%d',value);
        end
    end
end
