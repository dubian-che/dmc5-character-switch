from autoload_fixture import make_game

lua = make_game()
s = lua.globals().S
s.request(4)
lua.execute('paused=true;tick(4000);assert(next(loads)==nil);paused=false')
assert s.error is None and s.stage == 'requested Vergil'
for target in (4, 1, 0, 4):
    s.request(target)
    lua.execute('tick(180)')
    assert s.current == target, (target, s.stage, s.error)
    assert s.error is None
lua.execute('assert(loads[4]==1 and loads[1]==1);assert(preloads[0]>=1)')
print('PASS: cold Vergil first; 4000 paused frames; shared manual/automatic queue; one load per actor; native readiness before handoff.')
