function interactive
fig=uifigure('Name','P01 HWIL Timing Budget','Position',[100 100 1160 720]);
g=uigridlayout(fig,[3 7]); g.RowHeight={'1x','1x',100};
axBudget=uiaxes(g); axBudget.Layout.Row=1; axBudget.Layout.Column=[1 3];
axHist=uiaxes(g); axHist.Layout.Row=1; axHist.Layout.Column=[4 7];
axMargin=uiaxes(g); axMargin.Layout.Row=2; axMargin.Layout.Column=[1 5];
summary=uilabel(g,'WordWrap','on'); summary.Layout.Row=2; summary.Layout.Column=[6 7];

sw=uislider(g,'Limits',[0 6],'Value',1.5); sw.Layout.Row=3; sw.Layout.Column=1;
tr=uislider(g,'Limits',[0 6],'Value',0.8); tr.Layout.Row=3; tr.Layout.Column=2;
hw=uislider(g,'Limits',[0 6],'Value',0.6); hw.Layout.Row=3; hw.Layout.Column=3;
pl=uislider(g,'Limits',[0 8],'Value',2.0); pl.Layout.Row=3; pl.Layout.Column=4;
dl=uislider(g,'Limits',[1 20],'Value',8); dl.Layout.Row=3; dl.Layout.Column=5;
jt=uislider(g,'Limits',[0 0.5],'Value',0.1); jt.Layout.Row=3; jt.Layout.Column=6;
seed=uispinner(g,'Limits',[0 10000],'Value',84); seed.Layout.Row=3; seed.Layout.Column=7;
controls=[sw tr hw pl dl jt];
for i=1:numel(controls)
    controls(i).ValueChangingFcn=@(~,~) updatePlots();
    controls(i).ValueChangedFcn=@(~,~) updatePlots();
end
seed.ValueChangedFcn=@(~,~) updatePlots();
updatePlots();

    function updatePlots
        out=model(sw.Value,tr.Value,hw.Value,pl.Value,dl.Value,jt.Value,seed.Value);
        cla(axBudget); barh(axBudget,categorical(out.names),out.stages);
        grid(axBudget,'on'); xlabel(axBudget,'Delay (ms)'); title(axBudget,'Who owns the latency?');

        cla(axHist); histogram(axHist,out.totalSamples,50,'Normalization','probability');
        hold(axHist,'on'); xline(axHist,out.deadline,'--'); hold(axHist,'off');
        grid(axHist,'on'); xlabel(axHist,'End-to-end latency (ms)'); ylabel(axHist,'Probability');
        title(axHist,'Latency distribution');

        cla(axMargin); bar(axMargin,[out.nominalTotal out.p99 out.deadline]);
        xticks(axMargin,1:3); xticklabels(axMargin,{'Nominal','P99','Deadline'});
        ylabel(axMargin,'Milliseconds'); grid(axMargin,'on'); title(axMargin,'Mean versus tail versus requirement');

        summary.Text=sprintf(['nominal %.2f ms\nmargin %.2f ms\nP99 %.2f ms\n' ...
            'miss probability %.4f\njitter %.0f%%'],out.nominalTotal,out.margin, ...
            out.p99,out.missProbability,100*out.jitterFraction);
    end
end
