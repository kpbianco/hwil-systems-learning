function interactive
%INTERACTIVE Bounded controls for the P07 measurement-data trace.
modelFcn = @model; % Keep P07 bound after the launcher removes its path.
fig = uifigure('Name','P07 Trace a Measurement Data Path', ...
    'Position',[30 40 1540 840]);
layout = uigridlayout(fig,[4 8]);
layout.RowHeight = {'1x','1x',30,80};
layout.ColumnWidth = {'1x','1x','1x','1x','1x','1x','1x','1x'};

stageAxes = uiaxes(layout);
stageAxes.Layout.Row = 1; stageAxes.Layout.Column = [1 4];
valueAxes = uiaxes(layout);
valueAxes.Layout.Row = 2; valueAxes.Layout.Column = [1 4];
summary = uilabel(layout,'WordWrap','on','FontName','Courier New');
summary.Layout.Row = [1 2]; summary.Layout.Column = [5 8];

label = uilabel(layout,'Text','Model truth (deg)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 1;
trueAngle = uispinner(layout,'Limits',[-360 360],'Step',5,'Value',30);
trueAngle.RoundFractionalValues = 'on';
trueAngle.Layout.Row = 4; trueAngle.Layout.Column = 1;

label = uilabel(layout,'Text','ADC resolution (bit)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 2;
adcBits = uispinner(layout,'Limits',[4 16],'Step',1,'Value',12);
adcBits.RoundFractionalValues = 'on';
adcBits.Layout.Row = 4; adcBits.Layout.Column = 2;

label = uilabel(layout,'Text','Sample age (ms)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 3;
sampleAge = uispinner(layout,'Limits',[0 100],'Step',1,'Value',5);
sampleAge.Layout.Row = 4; sampleAge.Layout.Column = 3;

label = uilabel(layout,'Text','Freshness limit (ms)', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 4;
freshnessLimit = uispinner(layout,'Limits',[0 100],'Step',1,'Value',20);
freshnessLimit.Layout.Row = 4; freshnessLimit.Layout.Column = 4;

label = uilabel(layout,'Text','Open boundary','HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 5;
openBoundary = uidropdown(layout, ...
    'Items',{'None','B1 sensor -> ADC','B2 ADC -> calibration', ...
    'B3 calibration -> quality','B4 quality -> P07 intake'},'Value','None');
openBoundary.ItemsData = {'none','sensor-to-adc','adc-to-calibration', ...
    'calibration-to-quality','quality-to-controller'};
openBoundary.Layout.Row = 4; openBoundary.Layout.Column = 5;

label = uilabel(layout,'Text','Acquisition-entry guard', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 6;
eventMode = uidropdown(layout, ...
    'Items',{'None','Cancellation','Timeout','Cancel + timeout tie'}, ...
    'Value','None');
eventMode.ItemsData = { ...
    'none','cancellation','timeout','cancellation-timeout-tie'};
eventMode.Layout.Row = 4; eventMode.Layout.Column = 6;

label = uilabel(layout,'Text','Usability evidence', ...
    'HorizontalAlignment','center');
label.Layout.Row = 3; label.Layout.Column = 7;
assessmentMode = uidropdown(layout, ...
    'Items',{'Complete: value + quality','Broken: value only'}, ...
    'Value','Complete: value + quality');
assessmentMode.ItemsData = {'complete','value-only'};
assessmentMode.Layout.Row = 4; assessmentMode.Layout.Column = 7;

resetButton = uibutton(layout,'Text','Reset baseline');
resetButton.Layout.Row = 4; resetButton.Layout.Column = 8;

trueAngle.ValueChangedFcn = @(~,~) updatePlots();
adcBits.ValueChangedFcn = @(~,~) updatePlots();
sampleAge.ValueChangedFcn = @(~,~) updatePlots();
freshnessLimit.ValueChangedFcn = @(~,~) updatePlots();
openBoundary.ValueChangedFcn = @(~,~) updatePlots();
eventMode.ValueChangedFcn = @(~,~) updatePlots();
assessmentMode.ValueChangedFcn = @(~,~) updatePlots();
resetButton.ButtonPushedFcn = @(~,~) resetBaseline();
updatePlots();

    function updatePlots
        out = modelFcn(trueAngle.Value,adcBits.Value,sampleAge.Value, ...
            freshnessLimit.Value,openBoundary.Value,eventMode.Value, ...
            assessmentMode.Value);

        cla(stageAxes);
        bar(stageAxes,1:out.stageCount,double(out.stageReached));
        grid(stageAxes,'on'); ylim(stageAxes,[0 1.2]);
        stageAxes.XTick = 1:out.stageCount;
        stageAxes.XTickLabel = out.stageNames;
        stageAxes.XTickLabelRotation = 25;
        stageAxes.YTick = [0 1];
        stageAxes.YTickLabel = {'No','Yes'};
        xlabel(stageAxes,'Measurement data stage (-)');
        ylabel(stageAxes,'Stage reached (Boolean -)');
        title(stageAxes,'Reachability distinguishes missing from received data');

        endpointAngleDeg = NaN;
        if out.endpointReceived
            endpointAngleDeg = out.stageOutputValue(5);
        end
        degreeView = [out.inputs.trueAngleDeg,out.sensorEquivalentAngleDeg, ...
            out.calibratedAngleDeg,endpointAngleDeg];
        cla(valueAxes);
        bar(valueAxes,1:4,degreeView);
        grid(valueAxes,'on');
        valueAxes.XTick = 1:4;
        valueAxes.XTickLabel = {'Truth reference','Sensor equivalent', ...
            'Calibrated','P07 qualified intake'};
        valueAxes.XTickLabelRotation = 20;
        xlabel(valueAxes,'Comparable degree-valued view (-)');
        ylabel(valueAxes,'Position (deg)');
        title(valueAxes,'A finite value and a valid measurement are separate facts');

        if out.firstOpenBoundary == 0
            openText = 'none';
        else
            openText = out.boundaryNames{out.firstOpenBoundary};
        end
        summary.Text = sprintf(['MEASUREMENT TRACE\n\ntruth reference         %9.3f deg\n' ...
            'sensor output          %9.6f V\nADC code               %9.0f / %.0f count\n' ...
            'calibrated value        %9.6f deg\nmeasurement error       %+9.6f deg\n' ...
            'quantization LSB        %9.6f deg/count\n\n' ...
            'sample age              %9.1f ms\nfreshness limit         %9.1f ms\n' ...
            'freshness margin        %+9.1f ms\n\n' ...
            'deepest stage           %9d / %d\ncrossed boundaries      %9d / %d\n' ...
            'first open boundary     %s\nentry permitted         %9d\n' ...
            'cancellation observed   %9d\ntimeout observed        %9d\n' ...
            'sensor saturated        %9d\nquality evaluated       %9d\n' ...
            'quality valid           %9d\nendpoint received       %9d\n' ...
            'measurement usable      %9d\nP06 input eligible      %9d\n' ...
            'P06 observedAngleDeg    %9.3f deg\nreported usable         %9d\n' ...
            'false usable            %9d\n\nterminal                %s\n' ...
            'trace contract met      %9d\nfailure                 %s\n' ...
            'reporting failure       %s'], ...
            out.inputs.trueAngleDeg,out.sensorVolts,out.adcCount, ...
            out.maxAdcCount,out.calibratedAngleDeg,out.measurementErrorDeg, ...
            out.quantizationStepDeg,out.inputs.sampleAgeMs, ...
            out.inputs.freshnessLimitMs,out.freshnessMarginMs, ...
            out.deepestReachedStage,out.stageCount,out.crossedBoundaryCount, ...
            out.boundaryCount,openText,out.entryPermitted, ...
            out.cancellationObserved,out.timeoutObserved,out.sensorSaturated, ...
            out.qualityEvaluated,out.qualityValid,out.endpointReceived, ...
            out.measurementUsable,out.p06InputEligible, ...
            out.p06ObservedAngleDeg,out.reportedUsable,out.falseUsable, ...
            out.terminalStatus,out.traceContractMet,out.failureMode, ...
            out.reportingFailureMode);
    end

    function resetBaseline
        trueAngle.Value = 30;
        adcBits.Value = 12;
        sampleAge.Value = 5;
        freshnessLimit.Value = 20;
        openBoundary.Value = 'none';
        eventMode.Value = 'none';
        assessmentMode.Value = 'complete';
        updatePlots();
    end
end
