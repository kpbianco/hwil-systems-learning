function fig = interactive()
%INTERACTIVE Explore P11 latency and jitter allocations with bounded controls.
%   The callback captures the model handle so it remains valid if a launcher
%   later removes the module folder from the MATLAB path.

modelFcn = @model;
fig = uifigure('Name','P11 Latency and Jitter Budget Explorer', ...
    'Position',[80 80 1280 800]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {30,30,'1x',125};
layout.ColumnWidth = {150,110,135,100,150,100,170,'1x'};

uilabel(layout,'Text','Transport nominal (ms)');
transportControl = uispinner(layout,'Limits',[0.6 2.4], ...
    'Step',0.1,'Value',1.2);
uilabel(layout,'Text','Jitter scale (-)');
jitterControl = uispinner(layout,'Limits',[0 2], ...
    'Step',0.1,'Value',1.0);
uilabel(layout,'Text','Deadline (ms)');
deadlineControl = uispinner(layout,'Limits',[0.5 10], ...
    'Step',0.1,'Value',4.2);
p10ProofControl = uicheckbox(layout,'Text','P10 activation proof', ...
    'Value',true);
resetButton = uibutton(layout,'Text','Reset baseline', ...
    'ButtonPushedFcn',@resetBaseline);

cancelControl = uicheckbox(layout,'Text','Request cancellation', ...
    'Value',false);
cancelTimeControl = uispinner(layout,'Limits',[0 72], ...
    'Step',0.1,'Value',15.0);
uilabel(layout,'Text','Cancellation time (ms)');
assessmentControl = uidropdown(layout);
assessmentControl.Items = {'Bounded additive sum', ...
    'Broken RSS (unproven independence)'};
assessmentControl.ItemsData = {'bounded-sum','rss-uncorrelated'};
assessmentControl.Value = 'bounded-sum';
questionLabel = uilabel(layout,'Text', ...
    'Move one lever, then name which owned term changed the deadline margin.');
questionLabel.Layout.Column = [5 8];

latencyAxes = uiaxes(layout);
latencyAxes.Layout.Row = 3;
latencyAxes.Layout.Column = [1 4];
budgetAxes = uiaxes(layout);
budgetAxes.Layout.Row = 3;
budgetAxes.Layout.Column = [5 8];
summaryLabel = uilabel(layout,'WordWrap','on', ...
    'VerticalAlignment','top');
summaryLabel.Layout.Row = 4;
summaryLabel.Layout.Column = [1 8];

transportControl.ValueChangedFcn = @updateView;
jitterControl.ValueChangedFcn = @updateView;
deadlineControl.ValueChangedFcn = @updateView;
p10ProofControl.ValueChangedFcn = @updateView;
cancelControl.ValueChangedFcn = @updateView;
cancelTimeControl.ValueChangedFcn = @updateView;
assessmentControl.ValueChangedFcn = @updateView;

updateView([],[]);

    function updateView(~,~)
        if cancelControl.Value
            cancelAtMs = cancelTimeControl.Value;
        else
            cancelAtMs = Inf;
        end
        out = modelFcn(transportControl.Value,jitterControl.Value, ...
            deadlineControl.Value,p10ProofControl.Value,cancelAtMs, ...
            assessmentControl.Value);

        plot(latencyAxes,out.cycleIndex,out.plannedLatencyMs, ...
            'o--','LineWidth',1.1,'Color',[0.55 0.55 0.55]);
        hold(latencyAxes,'on');
        plot(latencyAxes,out.cycleIndex,out.actualLatencyMs, ...
            'o-','LineWidth',1.7,'Color',[0.10 0.45 0.75], ...
            'MarkerFaceColor',[0.10 0.45 0.75]);
        yline(latencyAxes,out.inputs.deadlineMs,'--','Deadline');
        hold(latencyAxes,'off');
        latencyAxes.XLim = [1 out.cycleCount];
        latencyAxes.XTick = out.cycleIndex;
        latencyAxes.XLabel.String = 'Scheduled cycle (-)';
        latencyAxes.YLabel.String = 'End-to-end latency (ms)';
        latencyAxes.Title.String = ...
            'Offline plan versus completed-cycle evidence';
        legend(latencyAxes,{'Offline plan','Completed evidence','Deadline'}, ...
            'Location','best');
        grid(latencyAxes,'on');

        cumulativeNominalMs = cumsum(out.nominalStageLatencyMs);
        cumulativeJitterMs = cumsum(out.jitterAllocationMs);
        plot(budgetAxes,1:out.stageCount,cumulativeNominalMs, ...
            'o-','LineWidth',1.5);
        hold(budgetAxes,'on');
        plot(budgetAxes,1:out.stageCount, ...
            cumulativeNominalMs + cumulativeJitterMs, ...
            's-','LineWidth',1.5);
        plot(budgetAxes,1:out.stageCount, ...
            cumulativeNominalMs - cumulativeJitterMs, ...
            'd-','LineWidth',1.5);
        yline(budgetAxes,out.inputs.deadlineMs,'--','Deadline');
        hold(budgetAxes,'off');
        budgetAxes.XTick = 1:out.stageCount;
        budgetAxes.XTickLabel = out.stageNames;
        budgetAxes.XTickLabelRotation = 18;
        budgetAxes.XLabel.String = 'Owned processing stage (-)';
        budgetAxes.YLabel.String = ...
            'Cumulative elapsed time after release (ms)';
        budgetAxes.Title.String = 'Cumulative nominal and bounded envelope';
        legend(budgetAxes,{'Nominal','Bounded latest','Bounded earliest', ...
            'Deadline'},'Location','northwest');
        grid(budgetAxes,'on');

        summaryLabel.Text = sprintf([ ...
            'Terminal: %s | failure: %s | report failure: %s | completed: %d/%d cycles\n' ...
            'Nominal %.2f ms | strict upper %.2f ms | reported upper %.2f ms | deadline %.2f ms | strict margin %.2f ms | bounded peak-to-peak %.2f ms\n' ...
            'Strict approval %d | reported approval %d | false approval %d | cancellation %d | timeout %d | tie to cancellation %d\n' ...
            'Handoff: %s; SAFE-HOLD requested %d; rollback evidence available %d; rollback authority %s. One ideal time base only: no P12 synchronization claim.'], ...
            out.terminalStatus,out.failureMode,out.reportingFailureMode, ...
            out.completedCycleCount,out.cycleCount,out.nominalLatencyMs, ...
            out.strictUpperBoundMs,out.reportedUpperBoundMs, ...
            out.inputs.deadlineMs,out.strictMarginMs, ...
            out.strictPeakToPeakJitterMs,out.strictBudgetAccepted, ...
            out.reportedBudgetAccepted,out.falseApproval, ...
            out.cancellationObserved,out.timeoutObserved, ...
            out.tieResolvedToCancellation,out.handoffEvent, ...
            out.safeHoldRequested,out.rollbackEvidenceAvailable, ...
            out.rollbackAuthority);
    end

    function resetBaseline(~,~)
        transportControl.Value = 1.2;
        jitterControl.Value = 1.0;
        deadlineControl.Value = 4.2;
        p10ProofControl.Value = true;
        cancelControl.Value = false;
        cancelTimeControl.Value = 15.0;
        assessmentControl.Value = 'bounded-sum';
        updateView([],[]);
    end
end
