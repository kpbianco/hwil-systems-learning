function interactive
%INTERACTIVE Bounded controls for the P05 allocation and fault-domain model.
modelFcn = @model; % Keep P05 bound after the launcher removes its path.
fig = uifigure('Name','P05 Allocate Functions Across Hardware and Software', ...
    'Position',[70 70 1420 790]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {'1x','1x',30,80};
layout.ColumnWidth = {'1x','1x','1x','1x','1x','1x','1x','1x'};

ownerAxes = uiaxes(layout);
ownerAxes.Layout.Row = 1; ownerAxes.Layout.Column = [1 4];
resourceAxes = uiaxes(layout);
resourceAxes.Layout.Row = 2; resourceAxes.Layout.Column = [1 4];
summary = uilabel(layout,'WordWrap','on','FontName','Courier New');
summary.Layout.Row = [1 2]; summary.Layout.Column = [5 8];

label = uilabel(layout,'Text','Control owner','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 1;
controlOwner = uidropdown(layout, ...
    'Items',{'Software','Hardware'},'Value','Software');
controlOwner.ItemsData = {'software','hardware'};
controlOwner.Layout.Row = 4; controlOwner.Layout.Column = 1;

label = uilabel(layout,'Text','Supervision owner','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 2;
supervisionOwner = uidropdown(layout, ...
    'Items',{'Hardware','Software'},'Value','Hardware');
supervisionOwner.ItemsData = {'hardware','software'};
supervisionOwner.Layout.Row = 4; supervisionOwner.Layout.Column = 2;

label = uilabel(layout,'Text','SW capacity (work/update)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 3;
softwareCapacity = uispinner(layout,'Limits',[0 60],'Step',1,'Value',30);
softwareCapacity.RoundFractionalValues = 'on';
softwareCapacity.Layout.Row = 4; softwareCapacity.Layout.Column = 3;

label = uilabel(layout,'Text','HW capacity (allocation)','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 4;
hardwareCapacity = uispinner(layout,'Limits',[0 60],'Step',1,'Value',40);
hardwareCapacity.RoundFractionalValues = 'on';
hardwareCapacity.Layout.Row = 4; hardwareCapacity.Layout.Column = 4;

label = uilabel(layout,'Text','Application software','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 5;
softwareState = uidropdown(layout, ...
    'Items',{'Available','Stalled'},'Value','Available');
softwareState.ItemsData = {'available','stalled'};
softwareState.Layout.Row = 4; softwareState.Layout.Column = 5;

label = uilabel(layout,'Text','Injected boundary event','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 6;
eventMode = uidropdown(layout, ...
    'Items',{'None','Cancellation','Deadline / timeout'},'Value','None');
eventMode.ItemsData = {'none','cancellation','deadline'};
eventMode.Layout.Row = 4; eventMode.Layout.Column = 6;

label = uilabel(layout,'Text','Assessment evidence','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 7;
assessmentMode = uidropdown(layout, ...
    'Items',{'Complete','Broken: resource only'},'Value','Complete');
assessmentMode.ItemsData = {'complete','resource-only'};
assessmentMode.Layout.Row = 4; assessmentMode.Layout.Column = 7;

resetButton = uibutton(layout,'Text','Reset baseline');
resetButton.Layout.Row = 4; resetButton.Layout.Column = 8;

controlOwner.ValueChangedFcn = @(~,~) updatePlots();
supervisionOwner.ValueChangedFcn = @(~,~) updatePlots();
softwareCapacity.ValueChangedFcn = @(~,~) updatePlots();
hardwareCapacity.ValueChangedFcn = @(~,~) updatePlots();
softwareState.ValueChangedFcn = @(~,~) updatePlots();
eventMode.ValueChangedFcn = @(~,~) updatePlots();
assessmentMode.ValueChangedFcn = @(~,~) updatePlots();
resetButton.ButtonPushedFcn = @(~,~) resetBaseline();
updatePlots();

    function updatePlots
        out = modelFcn(controlOwner.Value,supervisionOwner.Value, ...
            softwareCapacity.Value,hardwareCapacity.Value, ...
            softwareState.Value,eventMode.Value,assessmentMode.Value);

        cla(ownerAxes);
        imagesc(ownerAxes,1:2,1:out.functionCount,out.ownerMatrix);
        colormap(ownerAxes,[1 1 1; 0.10 0.45 0.75]); caxis(ownerAxes,[0 1]);
        ownerAxes.XTick = 1:2;
        ownerAxes.XTickLabel = {'Software','Hardware'};
        ownerAxes.YTick = 1:out.functionCount;
        ownerAxes.YTickLabel = out.functionNames;
        xlabel(ownerAxes,'Execution domain (-)');
        ylabel(ownerAxes,'P04 function contract');
        title(ownerAxes,'Exactly one owner per function; endpoints stay fixed');

        cla(resourceAxes);
        displayUtilizationPercent = [out.softwareUtilizationPercent, ...
            out.hardwareUtilizationPercent];
        displayUtilizationPercent(~isfinite(displayUtilizationPercent)) = 125;
        displayUtilizationPercent = min(displayUtilizationPercent,125);
        bar(resourceAxes,1:2,displayUtilizationPercent); hold(resourceAxes,'on');
        yline(resourceAxes,100,'--','Declared capacity'); hold(resourceAxes,'off');
        grid(resourceAxes,'on');
        resourceAxes.XTick = 1:2;
        resourceAxes.XTickLabel = {'Software work','Hardware allocation'};
        xlabel(resourceAxes,'Execution domain (-)');
        ylabel(resourceAxes,'Declared capacity used (%)');
        ylim(resourceAxes,[0 130]);
        title(resourceAxes,'Nominal demand; display clips utilization above 125%');

        if isempty(out.lostFunctionNames)
            lostText = 'none';
        else
            lostText = strjoin(out.lostFunctionNames,', ');
        end
        summary.Text = sprintf(['ALLOCATION RESULT\n\ncontrol owner       %s\n' ...
            'supervision owner   %s\nsoftware state      %s\n' ...
            'injected event      %s\nassessment          %s\n\n' ...
            'SW demand/capacity  %5.0f / %5.0f work units/update\n' ...
            'HW demand/capacity  %5.0f / %5.0f allocation units\n' ...
            'SW margin           %5.0f work units/update\n' ...
            'HW margin           %5.0f allocation units\n\n' ...
            'nominal resource fit:        %d\n' ...
            'fault-independent supervision: %d\n' ...
            'event guard available:       %d\n' ...
            'safe-hold request available: %d\n' ...
            'all functions available:     %d\n' ...
            'full allocation contract:    %d\n' ...
            'reported feasible:           %d\n' ...
            'false feasible:              %d\n\n' ...
            'decision: %s\nscenario: %s\nfailure: %s\n' ...
            'lost functions: %s'], ...
            out.inputs.controlOwner,out.inputs.supervisionOwner, ...
            out.inputs.softwareState,out.inputs.eventMode, ...
            out.inputs.assessmentMode,out.softwareDemandUnitsPerUpdate, ...
            out.inputs.softwareCapacity,out.hardwareDemandAllocationUnits, ...
            out.inputs.hardwareCapacity,out.softwareMarginUnitsPerUpdate, ...
            out.hardwareMarginAllocationUnits,out.nominalResourceFit, ...
            out.softwareFaultIndependentSupervision,out.eventGuardAvailable, ...
            out.safeHoldRequestAvailable,out.allRequiredFunctionsAvailable, ...
            out.allocationContractMet,out.reportedFeasible,out.falseFeasible, ...
            out.decisionStatus,out.scenarioStatus,out.failureMode,lostText);
    end

    function resetBaseline
        controlOwner.Value = 'software';
        supervisionOwner.Value = 'hardware';
        softwareCapacity.Value = 30;
        hardwareCapacity.Value = 40;
        softwareState.Value = 'available';
        eventMode.Value = 'none';
        assessmentMode.Value = 'complete';
        updatePlots();
    end
end
