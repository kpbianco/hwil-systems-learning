function run_checks
a=model(1,1,1,1,6,0,84);
assert(a.nominalTotal==4,'Nominal stage sum mismatch.');
assert(a.missProbability==0,'No-jitter latency below deadline should not miss.');
b=model(2,2,2,2,7,0,84);
assert(b.missProbability==1,'Deterministic latency above deadline should always miss.');
c=model(1,1,1,1,4.2,0.5,84);
assert(c.p99>c.nominalTotal,'Tail latency should exceed nominal under jitter.');
disp('P01 checks passed.');
end
