from autoload_fixture import make_game

for initial in (0, 1, 4):
    for fps in (30, 60, 144):
        lua = make_game(initial, fps)
        lua.execute('''
local original=active
tick(fps*5)
assert(S.error==nil,S.error)
assert(dmc5_switch_loader.error==nil,dmc5_switch_loader.error)
assert(dmc5_switch_loader.count==3 and dmc5_switch_loader.stage=='party ready')
assert(active==original and switches==0,'automatic loading changed control')
assert(initializations==2)
for _,id in ipairs({0,1,4})do
 if id~=initial_id then
  assert(loads[id]==1 and players[id].initialized==1)
  assert(not players[id].visible and not players[id].enabled and players[id].paused)
 else assert(not loads[id] and players[id].initialized==0)end
end
local before=scans
tick(fps*10)
-- Lifecycle retains its <=4 Hz orphan checks; warm-up does not rescan records.
assert(scans-before<=41,'steady-state load queue repeatedly scans records')
assert(initializations==2 and switches==0)
for _,id in ipairs({4,0,1,4})do
 local before=initializations
 S.request(id);tick(1)
 assert(S.current==id and initializations==before,'ready switch reloads a reserve')
end
''')

lua = make_game()
lua.execute('''
event=true;tick(fps*5);assert(next(loads)==nil)
event=false;paused=true;tick(fps*5);assert(next(loads)==nil)
paused=false;active=actor(2);players[2]=active;tick(fps*5);assert(next(loads)==nil)
active=players[0];tick(fps*5);assert(dmc5_switch_loader.count==3)
''')

# Actual cold-start Nero reports isThinkEnable=false while fully controllable.
# The native fixture clock must continue advancing independently of that flag.
lua = make_game()
lua.execute('''
thinking=false;S.request(4);tick(fps*5)
assert(dmc5_switch_loader.count==3 and S.current==4 and switches==1)
assert(dmc5_switch_loader.playable and S.error==nil)
assert(loads[1]==1 and loads[4]==1)
''')

lua = make_game()
lua.execute('''
thinking=false;stealControl=true;local original=active
tick(fps*5)
assert(active==original and S.current==initial_id and switches==0)
assert(dmc5_switch_loader.count==3 and initializations==2 and ownerRestores==2)
assert(dmc5_switch_loader.generation==1,'native loading was mistaken for a scene change')
for _,id in ipairs({1,4})do assert(not players[id].visible and players[id].paused)end
''')

lua = make_game()
lua.execute('''
tick(12) -- Dante model exists, but native loading has not finished.
assert(players[1] and states[1]==3 and players[1].initialized==0)
S.request(1);tick(1)
assert(active.id==0 and switches==0,'visible actor bypassed readiness gate')
tick(fps*3);assert(active.id==1 and loads[1]==1 and players[1].initialized==1)
assert(dmc5_switch_loader.count==3)
''')

lua = make_game()
lua.execute('''
tick(fps*4)
local oldDante=players[1]
S.request(4) -- Must be cancelled if a new scene replaces the manual actor.
players[0]=actor(0);active=players[0];players[1]=nil;players[4]=nil
tick(fps*6)
assert(active.id==0 and switches==0,'old scene request leaked into new scene')
assert(players[1]~=oldDante and loads[1]==2 and loads[4]==2)
assert(dmc5_switch_loader.count==3 and S.error==nil)
-- A native scene transition may also retain the same manual actor.
players[1]=nil;players[4]=nil
tick(fps*6)
assert(loads[1]==3 and loads[4]==3 and dmc5_switch_loader.count==3)
assert(active.id==0 and switches==0)
''')

lua = make_game()
lua.execute('''
stalled=true;tick(fps)
local warmClock=dmc5_switch_loader.clock
paused=true;tick(fps*100)
assert(dmc5_switch_loader.clock==warmClock and dmc5_switch_loader.error==nil)
paused=false;event=true;tick(fps*100)
assert(dmc5_switch_loader.clock==warmClock and dmc5_switch_loader.error==nil)
event=false;tick(fps*61)
assert(dmc5_switch_loader.error and dmc5_switch_loader.error:find('timed out'))
assert(loads[1]==1,'timeout duplicated in-flight load')
stalled=false;tick(fps*10)
assert(dmc5_switch_loader.count==3 and dmc5_switch_loader.error==nil)
assert(loads[1]==1 and loads[4]==1)
''')
for initial in (0, 1, 4):
    for fps in (30, 60, 144):
        lua = make_game(initial, fps)
        lua.execute('''
players[2]=actor(2);local extra=players[2]
paused=true;tick(fps);assert(extra.visible and excludedCount==0)
paused=false;event=true;tick(fps);assert(extra.visible and excludedCount==0)
event=false;extra.eventRun=true;tick(fps);assert(extra.visible and excludedCount==0)
extra.eventRun=false;states[2]=3;tick(fps)
assert(extra.visible and excludedCount==0,'V paused before native loading completed')
states[2]=6;tick(fps*5)
assert(not extra.visible and not extra.enabled and extra.paused)
assert(extra.initialized==0 and loads[2]==nil and preloads[2]==nil)
assert(active.id==initial_id and switches==0 and excludedCount==1)
tick(fps*4);assert(excludedCount==1,'V repeatedly parked during steady play')
players[2]=actor(2);tick(fps)
assert(not players[2].visible and excludedCount==2,'replacement V escaped exclusion')
''')

lua = make_game(initial=2)
lua.execute('''
tick(fps*5)
assert(active.id==2 and active.visible and active.enabled and not active.paused)
assert(excludedCount==0 and next(loads)==nil,'native playable V was disabled')
''')
print('PASS: three-person party at 30/60/144 FPS; extra native V parked once without loading/unloading; playable V, pause/events protected; scene recovery and bounded retry retained.')
