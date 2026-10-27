from autoload_fixture import make_game

# Native additional loading can temporarily select an actor before resources
# and body meshes finish. Identity/manual control alone must not publish it.
lua = make_game()
lua.execute('''
tick(fps*4)
local B=dmc5_switch_loader
local dante=players[1]
states[1]=3;dante.meshReady=false;stalled=true
assert(not B.ready(manager,1),'cached identity bypassed native reload')
S.request(1);tick(fps)
assert(active.id==0 and switches==0,'switched to incomplete model')
states[1]=6;tick(fps)
assert(active.id==0 and switches==0,'native ready flag bypassed missing body meshes')
dante.meshReady=true;dante.meshBound=false;tick(fps)
assert(active.id==0 and switches==0,'allocated array with nil mesh bypassed readiness')
dante.meshBound=true;tick(fps)
assert(active==dante and switches==1 and loads[1]==1)
''')

lua = make_game()
lua.execute('''
tick(fps*4)
local B=dmc5_switch_loader
active=players[1];states[1]=3;active.meshReady=false;stalled=true
dmc5_switch_runtime.invalidate()
tick(fps)
local generation=B.generation
assert(not B.ready(manager,1),'temporary manual actor bypassed native readiness')
tick(fps*2)
assert(B.generation==generation,'pending manual actor repeatedly reset scene generation')
states[1]=6;tick(fps)
assert(not B.ready(manager,1),'manual actor published without body meshes')
active.meshReady=true;tick(fps)
assert(B.ready(manager,1)and B.generation==generation)
''')
print('PASS: cached native reload and transient manual actors wait for resources AND body meshes; stable generation; no duplicate loads.')
