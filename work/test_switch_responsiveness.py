from autoload_fixture import make_game

# A reserve load may finish after the user has selected another ready actor.
# Native control stealing must restore the latest selection, not load-start owner.
lua = make_game()
lua.execute('''
tick(fps*4)
states[1]=3;players[1].meshReady=false;stalled=true
tick(fps)
local B=dmc5_switch_loader
assert(B.task and B.task.id==1 and B.task.owner==players[0])
S.request(4);tick(2)
assert(active.id==4)
active=players[1];dmc5_switch_runtime.invalidate()
tick(1)
assert(active.id==4,'late native loading stole control back to an obsolete owner')
''')

# A settled party must not inherit the half-second background scan delay
# after an event. Conversely, a new event must block switching immediately.
lua = make_game()
lua.execute('''
tick(fps*4)
event=true;tick(fps)
event=false;S.request(1);tick(1)
assert(active.id==1,'ready switch waited for the background scan after event exit')
event=true;S.request(4);tick(1)
assert(active.id==1,'stale playable flag allowed switching into an event')
''')

# The latest deliberate direction replaces a waiting choice. Reversing the
# choice cancels it without a delayed switch when old resources finish.
lua = make_game()
lua.execute('''
tick(fps*4)
states[1]=3;players[1].meshReady=false;stalled=true
S.step(1);tick(1);assert(active.id==0)
S.step(-1);tick(1)
assert(active.id==0)
states[1]=6;players[1].meshReady=true;tick(fps)
assert(active.id==0,'cancelled pending switch executed later')
S.step(1);tick(1);assert(active.id==1)
''')

lua = make_game()
lua.execute('''
tick(fps*4)
states[1]=3;players[1].meshReady=false;stalled=true
dmc5_switch_palace={run={stage={}}}
assert(S.request(1,'palace'));tick(1)
assert(S.request(4,'user'))
assert(not S.request(1,'palace'),'automatic restore replaced explicit user selection')
tick(1);assert(active.id==4)
assert(dmc5_switch_loader.task.ownerID==4,'replacement selection did not own in-flight loading')
''')
print('PASS: latest loading owner survives native steals; ready switches bypass scan delay; events block immediately; pending direction can be cancelled without late execution.')
