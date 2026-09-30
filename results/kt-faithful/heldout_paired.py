import json,glob,random,statistics as st,math,sys
from tom.benchmarks.knowledge_triage_repro import load_configs
dev={c.label for c in load_configs('data/aac/sample',n_configs=20,seed=11)}
cur={}
for f in glob.glob('results/kt-faithful/heldout/curves/*.json'):
    r=json.load(open(f))
    if r['config'] not in dev: cur[(r['arm'],r['config'])]=r
arms=sorted({k[0] for k in cur}); cfgs=sorted({k[1] for k in cur}); print('fresh configs',len(cfgs))
for a in arms:
    ok=[cur[(a,c)] for c in cfgs if (a,c) in cur and 'error' not in cur[(a,c)]]
    cs=[r['per_type']['constraint'] for r in ok if not math.isnan(r['per_type']['constraint'])]
    ps=[r['per_type']['procedural'] for r in ok if not math.isnan(r['per_type']['procedural'])]
    print(a,'n',len(ok),'constraint',round(st.mean(cs),3),'proc',round(st.mean(ps),3),'overshoot',round(st.mean(r['overshoot'] for r in ok),2),'median raw/budget',round(st.median(r['raw_chars']/(r['budget']*4) for r in ok),2),'cost',round(sum(r['cost_usd'] for r in ok),3))
def paired(a,b,g):
    ls=[c for c in cfgs if all((x,c) in cur and 'error' not in cur[(x,c)] and not math.isnan(g(cur[(x,c)])) for x in (a,b))]
    d=[g(cur[(a,c)])-g(cur[(b,c)]) for c in ls]; rnd=random.Random(11)
    bs=sorted(st.mean(rnd.choices(d,k=len(d))) for _ in range(10000))
    return len(ls),round(st.mean(d),3),(round(bs[250],3),round(bs[9750],3))
for n in ('constraint','procedural'):
    print(n)
    for a,b in (('tom_budget','tom'),('tom_jev_budget','tom_jev'),('tom_jev_budget','tom_budget'),('tom_budget','vanilla'),('tom_jev_budget','vanilla'),('tom_jev','tom')):
        A,B=a+':gpt-6-luna',b+':gpt-6-luna'
        if any(k[0]==A for k in cur) and any(k[0]==B for k in cur): print(' ',a,'-',b,paired(A,B,lambda r:r['per_type'][n]))
