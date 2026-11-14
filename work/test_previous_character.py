from autoload_fixture import make_game

for initial in (0, 1, 4):
    lua = make_game(initial=initial)
    lua.globals().initial = initial
    lua.execute('''
tick(fps*5)
assert(not S.requestDirect(initial)and switches==0 and S.previousCharacter==nil)
local other=initial==1 and 4 or 1
assert(S.requestDirect(other));tick(1)
assert(active.id==other and S.previousCharacter==initial)
assert(S.requestDirect(other));tick(1)
assert(active.id==initial and S.previousCharacter==other)
assert(S.requestDirect(initial));tick(1)
assert(active.id==other and S.previousCharacter==initial)
-- Cycling and designated controls share the successful-switch history.
S.step(1);tick(1);local current=active.id
assert(S.previousCharacter==other)
assert(S.requestDirect(current));tick(1);assert(active.id==other)
-- A same-ID internal recovery must not toggle or overwrite history.
local previous=S.previousCharacter
assert(S.request(active.id,'palace'));tick(1)
assert(active.id==other and S.previousCharacter==previous)
-- Native checkpoint/floor reload invalidates history even when IDs repeat.
dmc5_switch_loader.generation=dmc5_switch_loader.generation+1
assert(not S.requestDirect(active.id)and S.previousCharacter==nil)
''')

lua = make_game()
lua.execute('''
tick(fps*5)
-- A failed switch is never a successful previous character.
local real=core.switch
core.switch=function()error('injected handoff failure')end
assert(S.requestDirect(1));tick(1)
assert(active.id==0 and S.previousCharacter==nil and S.error)
core.switch=real
assert(not S.requestDirect(0))
assert(S.requestDirect(4));tick(1);assert(S.previousCharacter==0)
-- Duplicate queued selections do not toggle before their handoff succeeds.
states[1]=3;players[1].meshReady=false;stalled=true
assert(S.requestDirect(1));tick(1)
assert(not S.requestDirect(1));assert(S.previousCharacter==0)
assert(S.requestDirect(4));tick(1);assert(active.id==0 and S.previousCharacter==4)
states[1]=6;players[1].meshReady=true;tick(fps)
assert(active.id==0,'superseded load performed a late switch')
-- A native control change is not an invitation to use stale history.
active=players[1];dmc5_switch_runtime.invalidate()
assert(not S.requestDirect(1)and S.previousCharacter==nil)
''')
print('PASS: all initial heroes, empty history, two-way return, cycling, native same-ID recovery, scene generation, failed/queued/superseded switches and native control changes.')
