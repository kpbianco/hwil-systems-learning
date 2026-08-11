function out = model(swMs,transportMs,hardwareMs,plantMs,deadlineMs,jitterFraction,seed)
%MODEL End-to-end HWIL timing budget with seeded stage jitter.
arguments
    swMs (1,1) double {mustBeNonnegative} = 1.5
    transportMs (1,1) double {mustBeNonnegative} = 0.8
    hardwareMs (1,1) double {mustBeNonnegative} = 0.6
    plantMs (1,1) double {mustBeNonnegative} = 2.0
    deadlineMs (1,1) double {mustBePositive} = 8
    jitterFraction (1,1) double {mustBeNonnegative} = 0.1
    seed (1,1) double {mustBeInteger,mustBeNonnegative} = 84
end
stages=[swMs transportMs hardwareMs plantMs];
names=["Software","Transport","FPGA / I-O","Plant / sensor"];
rng(seed,'twister');
trials=2000;
noise=randn(trials,numel(stages)).*(jitterFraction*max(stages,0.01));
samples=max(0,stages+noise);
total=sum(samples,2);
out=struct();
out.stages=stages;
out.names=names;
out.cumulative=[0 cumsum(stages)];
out.nominalTotal=sum(stages);
out.margin=deadlineMs-sum(stages);
out.deadline=deadlineMs;
out.totalSamples=total;
out.missProbability=mean(total>deadlineMs);
out.p99=localPercentile(total,99);
out.jitterFraction=jitterFraction;
end

function q=localPercentile(x,p)
x=sort(x(:));
idx=max(1,min(numel(x),ceil(p/100*numel(x))));
q=x(idx);
end
