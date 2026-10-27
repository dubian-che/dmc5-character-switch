"""The native loader may accept, unload, then return to Preloaded."""
from pathlib import Path
import autoload_fixture as fixture

def setup(lua,target=0):
    lua.globals().target=target
    lua.execute('''
    retractions=0
    frames[#frames+1]=function()
      if states[target]==3 and retractions==0 then
        -- Engine-owned rollback: the queued actor is not published.
        states[target]=2;players[target]=nil;loadAt[target]=nil
        retractions=retractions+1
      end
    end
    S.request(target)
    ''')

current=fixture.SOURCE
try:
    fixture.SOURCE=Path('work/checkpoints/release-34-before-native-load-regression/outputs')
    old=fixture.make_game(initial=1)
    setup(old)
    old.execute('''
    tick(fps*10)
    assert(active.id==1 and states[0]==2 and retractions==1)
    assert(dmc5_switch_loader.task.phase=='load'and loads[0]==1,'old wait bug not reproduced')
    ''')
finally:
    fixture.SOURCE=current

for owner,target in [(1,0),(0,1),(1,4)]:
    lua=fixture.make_game(initial=owner)
    setup(lua,target)
    lua.execute('''
    tick(fps*10)
    assert(active.id==target and retractions==1 and switches==1)
    assert(loads[target]==2 and players[target].initialized==1)
    assert(S.error==nil)
    ''')

lua=fixture.make_game(initial=1)
lua.execute('''
locationBusy=true;S.request(0);tick(fps*20)
assert(next(loads)==nil and active.id==1,'native location boundary bypassed')
locationBusy=false;tick(fps*8)
assert(active.id==0 and switches==1)
''')

lua=fixture.make_game(initial=1)
lua.execute('''
retractions=0
frames[#frames+1]=function()
 for id,state in pairs(states)do
  if state==3 then
   states[id]=2;players[id]=nil;loadAt[id]=nil;retractions=retractions+1
  end
 end
end
tick(fps*90)
assert(active.id==1 and switches==0 and retractions>0 and retractions<=18)
assert(dmc5_switch_loader.error:find('returned to preload'))
''')
print('PASS: release-34 stuck load reproduced; all three targets recover from native rollback; native location wait respected; repeated rollback bounded; no incomplete actor initialization')
