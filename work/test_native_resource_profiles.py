"""Readiness must follow the native loaded profile, never an assumed default."""
from pathlib import Path
import autoload_fixture as fixture

def scenario(source=None, owner=0, target=1, costume=1, situation=1):
    previous=fixture.SOURCE
    try:
        if source:fixture.SOURCE=source
        lua=fixture.make_game(initial=owner)
    finally:fixture.SOURCE=previous
    lua.globals().target=target
    lua.globals().costume=costume
    lua.globals().situation=situation
    lua.execute('''
    mode=0;missionNo=15
    profiles[target]={costume,situation};states[target]=6;players[target]=actor(target)
    local original=native.call
    native.call=function(self,name,id,c,s,...)
      if name=='isReadyPlayerResource'then
        local profile=profiles[id]or{0,0}
        return states[id]==6 and c==profile[1]and s==profile[2]
      end
      return original(self,name,id,c,s,...)
    end
    S.request(target);tick(fps*4)
    ''')
    return lua

old=scenario(Path('work/checkpoints/release-44-before-native-resource-profile/outputs/DMC5CharacterSwitch'))
old.execute('''
assert(active.id==0 and not dmc5_switch_loader.ready(manager,1))
assert(dmc5_switch_loader.task.id==1 and dmc5_switch_loader.task.phase=='load')
''')

for owner,target in [(0,1),(1,0),(0,4)]:
    for costume,situation in [(0,0),(1,0),(0,1),(1,1),(1,2),(1,3)]:
        lua=scenario(owner=owner,target=target,costume=costume,situation=situation)
        lua.execute('''
        local B=dmc5_switch_loader
        assert(active.id==target and switches==1,'native profile rejected')
        assert(loads[target]==nil,'existing native actor reloaded')
        assert(players[target].initialized==1)
        assert(B.ready(manager,target))
        -- Same actor/manager carried into another story mission retains readiness.
        missionNo=16;campaignID=target;tick(fps)
        assert(B.ready(manager,target)and players[target].initialized==1)
        -- A native reload or missing meshes must still revoke readiness.
        states[target]=3;assert(not B.ready(manager,target))
        states[target]=6;players[target].meshReady=false;assert(not B.ready(manager,target))
        players[target].meshReady=true;assert(B.ready(manager,target))
        -- Profile replacement must invalidate the cached native tuple, then
        -- adopt the new tuple without reinitializing/reloading the same actor.
        profiles[target]={costume+1,situation+1}
        assert(not B.ready(manager,target),'old appearance tuple reused after native replacement')
        tick(fps)
        assert(B.ready(manager,target)and players[target].initialized==1 and loads[target]==nil)
        ''')

# Initial/manual adoption uses the same policy as reserve preparation.
lua=fixture.make_game(initial=1)
lua.execute('''
mode=0;campaignID=1;profiles[1]={1,2};states[1]=6
local original=native.call
native.call=function(self,name,id,c,s,...)
 if name=='isReadyPlayerResource'and id==1 then return states[1]==6 and c==1 and s==2 end
 return original(self,name,id,c,s,...)
end
tick(fps*4)
assert(dmc5_switch_loader.playable and dmc5_switch_loader.ready(manager,1))
assert(players[1].initialized==0,'native manual actor unnecessarily initialized')
S.request(4);tick(fps*4);assert(active.id==4)
''')
print('PASS: release-44 M15 profile mismatch reproduced; three heroes and six profiles; scene carry, manual adoption, native reload and body-mesh guards.')
