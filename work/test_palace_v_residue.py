"""Floor cleanup revives a child of an already parked reserve Vergil."""
import runpy
from pathlib import Path
lua=runpy.run_path('work/test_park_reserve_instance.py')['lua']
lua.execute("hooks={};sdk.find_type_definition=function(t)return {get_method=function(_,n)return t..'.'..n end}end;sdk.hook=function(n,a,b)hooks[n]={a,b}end;sdk.to_managed_object=function(v)return v end")
lua.globals().R=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_resources.lua').read_text())
lua.execute('''
resourcesStub.parkWorldVChild=R.parkWorldVChild
allowed=true;mode=3;ends=0
sdk.get_managed_singleton=function(n)
 if n=='app.PlayerManager'then return manager end
 assert(n=='app.GameManager');return {call=function(_,m)assert(m=='get_gameMode');return mode end}
end
active=actor(1);local owner=actor(4)
assert(M.parkReserve(manager,owner))
local childMed={draw=true,update=true,call=function(self,n,v)
 if n=='get_drawSelf'then return self.draw end
 if n=='get_updateSelf'then return self.update end
 if n=='set_drawSelf'then self.draw=v;return end
 if n=='set_updateSelf'then self.update=v;return end
 assert(n=='applyDrawSelf'or n=='applyUpdateSelf')
end}
local child={enabled=true,call=function(self,n,v)
 if n=='get_Enable'then return self.enabled end
 if n=='set_Enable'then self.enabled=v;return end
 if n=='get_cachedActivateMediator'then return childMed end
 assert(n=='get_ownerVergilPL');return foreign and active or owner
end}
owner.fields.summonGilver=child
resourcesStub.finishWorldV=function(p)
 assert(p==owner);ends=ends+1
 -- Reproduce the live failure: native exit alone leaves the child visible.
 -- Native exit may restore owner's presentation: parking must follow it.
 owner.enabled=true;owner.draw=true;owner.update=true;return true
end
for floor=1,3 do
 -- Cover full reactivation, draw-only residue and update-only reactivation.
 child.enabled=floor==1
 childMed.draw=floor~=3;childMed.update=floor~=2
 assert(M.parkReserve(manager,owner))
 assert(not child.enabled and not owner.enabled and not owner.draw and not owner.update)
 assert(not childMed.draw and not childMed.update)
 assert(ends==floor)
 local before=writes
 for i=1,20 do assert(M.parkReserve(manager,owner))end
 assert(ends==floor and writes==before,'settled child repeatedly ended')
end
assert(resourcesStub.worldVReserveRepairs==3)
child.enabled=true;mode=0;M.parkReserve(manager,owner);assert(ends==3 and child.enabled)
mode=3;foreign=true;M.parkReserve(manager,owner);assert(ends==3 and child.enabled)
foreign=false;owner.event=true;assert(not M.parkReserve(manager,owner));assert(ends==3)
owner.event=false;owner.fields.IsDoppel=true;assert(not M.parkReserve(manager,owner));assert(ends==3)
owner.fields.IsDoppel=false;active=owner;owner.enabled=true
assert(not M.parkReserve(manager,owner));assert(ends==3 and child.enabled,'active WorldV interrupted')
child.enabled=false
local init=hooks['app.PlayerVergilPL.vModeInit'];assert(init and R.worldVChildRestoreHook)
init[1]({[2]=owner});assert(init[2](123)==123)
assert(childMed.draw and childMed.update and not child.enabled,'restore must leave native activation in charge')
assert(not R.restoreWorldVChild(owner,manager)and R.worldVChildRestores==1)
''')
print('PASS: repeated floor revival cleared before settled-owner early exit; owner reparked after native exit; active skill/story/foreign child/events/clone untouched')
