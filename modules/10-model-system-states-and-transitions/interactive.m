function fig = interactive()
%INTERACTIVE Explore P10 transition evidence with bounded MATLAB controls.
%   The callback captures the model handle so it remains valid if a launcher
%   later removes the module folder from the MATLAB path.

modelFcn = @model;
fig = uifigure('Name','P10 State and Transition Explorer', ...
    'Position',[90 90 1240 780]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {28,28,'1x',115};
layout.ColumnWidth = {155,105,155,105,155,155,155,'1x'};

uilabel(layout,'Text','Readiness confirmations');
readinessControl = uispinner(layout,'Limits',[1 4], ...
    'Step',1,'Value',2,'RoundFractionalValues','on');
uilabel(layout,'Text','Recovery confirmations');
recoveryControl = uispinner(layout,'Limits',[1 4], ...
    'Step',1,'Value',2,'RoundFractionalValues','on');
p09StartupControl = uicheckbox(layout, ...
    'Text','P09 startup proof','Value',true);
p09SafeOffControl = uicheckbox(layout, ...
    'Text','P09 safe-off proof','Value',true);
resetButton = uibutton(layout,'Text','Reset baseline', ...
    'ButtonPushedFcn',@resetBaseline);
questionLabel = uilabel(layout,'Text', ...
    'Move one control, then name the source, guard, priority, and observed destination.');

uilabel(layout,'Text','Scenario');
scenarioControl = uidropdown(layout);
scenarioControl.Items = {'Nominal','Recoverable feedback loss', ...
    'Fault/reset conflict','State stuck ACTIVE','Premature activation'};
scenarioControl.ItemsData = {'nominal','recoverable-feedback-loss', ...
    'fault-reset-conflict','state-stuck-active', ...
    'premature-activation'};
scenarioControl.Value = 'nominal';
uilabel(layout,'Text','Injected event');
eventControl = uidropdown(layout);
eventControl.Items = {'None','Cancellation','Timeout', ...
    'Cancellation/timeout tie'};
eventControl.ItemsData = {'none','cancellation','timeout', ...
    'cancellation-timeout-tie'};
eventControl.Value = 'none';
uilabel(layout,'Text','Arbitration rule');
arbitrationControl = uidropdown(layout);
arbitrationControl.Items = {'Guarded fault priority', ...
    'Broken last request wins'};
arbitrationControl.ItemsData = {'guarded-priority', ...
    'last-request-wins'};
arbitrationControl.Value = 'guarded-priority';
boundaryLabel = uilabel(layout,'Text', ...
    'Observation/event step is dimensionless; cancellation and timeout are asserted facts.');
boundaryLabel.Layout.Column = [7 8];

stateAxes = uiaxes(layout);
stateAxes.Layout.Row = 3;
stateAxes.Layout.Column = [1 4];
evidenceAxes = uiaxes(layout);
evidenceAxes.Layout.Row = 3;
evidenceAxes.Layout.Column = [5 8];
summaryLabel = uilabel(layout,'WordWrap','on', ...
    'VerticalAlignment','top');
summaryLabel.Layout.Row = 4;
summaryLabel.Layout.Column = [1 8];

readinessControl.ValueChangedFcn = @updateView;
recoveryControl.ValueChangedFcn = @updateView;
p09StartupControl.ValueChangedFcn = @updateView;
p09SafeOffControl.ValueChangedFcn = @updateView;
scenarioControl.ValueChangedFcn = @updateView;
eventControl.ValueChangedFcn = @updateView;
arbitrationControl.ValueChangedFcn = @updateView;

updateView([],[]);

    function updateView(~,~)
        out = modelFcn(readinessControl.Value,recoveryControl.Value, ...
            p09StartupControl.Value,p09SafeOffControl.Value, ...
            scenarioControl.Value,eventControl.Value, ...
            arbitrationControl.Value);

        stairs(stateAxes,1:out.transitionCount,out.stateIdTrace, ...
            'o-','LineWidth',1.5,'Color',[0.12 0.48 0.72]);
        stateAxes.XTick = 1:out.transitionCount;
        stateAxes.XTickLabel = out.eventNames;
        stateAxes.XTickLabelRotation = 24;
        stateAxes.YTick = 1:out.stateCount;
        stateAxes.YTickLabel = out.stateNames;
        stateAxes.YLim = [0.5 out.stateCount + 0.5];
        stateAxes.XLabel.String = 'Observation/event step (-)';
        stateAxes.YLabel.String = 'Observed state ID (-)';
        stateAxes.Title.String = sprintf( ...
            'READY step %s | recovery step %s', ...
            displayStep(out.readinessQualifiedStep), ...
            displayStep(out.recoveryQualifiedStep));
        grid(stateAxes,'on');

        evidence = double([out.transitionTableAllowed; ...
            out.strictGuardPass;out.strictPostconditionPass]');
        evidence(~out.transitionEvaluated,:) = NaN;
        bar(evidenceAxes,1:out.transitionCount,evidence);
        evidenceAxes.XTick = 1:out.transitionCount;
        evidenceAxes.XTickLabel = out.eventNames;
        evidenceAxes.XTickLabelRotation = 24;
        evidenceAxes.YTick = [0 1];
        evidenceAxes.YTickLabel = {'Fail','Pass'};
        evidenceAxes.YLim = [0 1.2];
        evidenceAxes.XLabel.String = 'Observation/event step (-)';
        evidenceAxes.YLabel.String = 'Transition evidence (Boolean -)';
        evidenceAxes.Title.String = ...
            'Strict guard and observed destination';
        legend(evidenceAxes,{'Legal edge','Guard','Postcondition'}, ...
            'Location','southoutside','Orientation','horizontal');
        grid(evidenceAxes,'on');

        summaryLabel.Text = sprintf([ ...
            'Terminal: %s | factual failure: %s | strict acceptance: %d | ' ...
            'reported acceptance: %d | false approval: %d | priority violations: %d count\n' ...
            'Rollback performed: %d | rollback complete: %d | rollback failure: %s. ' ...
            'Mechanism: a transition needs a legal source-to-target edge, its guard, explicit event priority, and the observed destination.'], ...
            out.terminalStatus,out.failureMode, ...
            out.strictStateMachineAccepted, ...
            out.reportedStateMachineAccepted,out.falseApproval, ...
            out.priorityViolationCount,out.rollbackPerformed, ...
            out.rollbackComplete,out.rollbackFailureMode);
    end

    function resetBaseline(~,~)
        readinessControl.Value = 2;
        recoveryControl.Value = 2;
        p09StartupControl.Value = true;
        p09SafeOffControl.Value = true;
        scenarioControl.Value = 'nominal';
        eventControl.Value = 'none';
        arbitrationControl.Value = 'guarded-priority';
        updateView([],[]);
    end

    function text = displayStep(value)
        if isnan(value)
            text = 'not-observed';
        else
            text = sprintf('%d',value);
        end
    end
end
