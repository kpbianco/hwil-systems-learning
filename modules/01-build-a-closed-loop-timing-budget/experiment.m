%% P01 - Build a Closed-Loop Timing Budget
close all; clc;
out=model(1.5,0.8,0.6,2.0,8,0.10,84);

figure('Name','P01 baseline');
subplot(2,1,1);
barh(categorical(out.names),out.stages);
grid on; xlabel('Nominal delay (ms)'); title('Stage-owned timing budget');
subplot(2,1,2);
histogram(out.totalSamples,50,'Normalization','probability'); hold on;
xline(out.deadline,'--','Deadline');
grid on; xlabel('End-to-end latency (ms)'); ylabel('Probability');
title(sprintf('Nominal %.2f ms, P99 %.2f ms, miss probability %.4f', ...
    out.nominalTotal,out.p99,out.missProbability));

%% Sweep 1 - transport delay
transport=[0.2 1.0 3.0];
fprintf('Transport sweep:\n');
for i=1:numel(transport)
    s=model(1.5,transport(i),0.6,2.0,8,0.1,84);
    fprintf('  %.1f ms -> margin %.2f ms, P(miss) %.4f\n', ...
        transport(i),s.margin,s.missProbability);
end

%% Sweep 2 - jitter
jit=[0 0.1 0.35];
figure('Name','P01 jitter sweep'); hold on; grid on;
for i=1:numel(jit)
    s=model(1.5,0.8,0.6,2.0,8,jit(i),84);
    histogram(s.totalSamples,50,'DisplayStyle','stairs','Normalization','probability', ...
        'LineWidth',1.2,'DisplayName',sprintf('jitter %.0f%%',100*jit(i)));
end
xline(8,'--','Deadline'); xlabel('Latency (ms)'); ylabel('Probability');
title('Tail latency determines deadline risk'); legend('Location','best');

%% Broken case - budget only the mean
broken=model(2.0,1.5,1.0,2.5,7.5,0.35,84);
figure('Name','P01 broken mean-only budget');
histogram(broken.totalSamples,60); hold on; xline(broken.deadline,'--');
grid on; xlabel('Latency (ms)');
title(sprintf('Broken: nominal margin %.2f ms but P(miss)=%.2f', ...
    broken.margin,broken.missProbability));

assert(abs(out.nominalTotal-sum(out.stages))<eps,'Stage sum mismatch.');
