"""Park/resume regression: motion entry alone must not resume the old action.

Fixture semantics follow TDB67 parameter names and the native call paths saved
in native-entry-action-disasm.txt / native-entry-dependencies.txt. This checks
the next action tick, not just whether a reset method was called.
"""
import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime

lua = LuaRuntime()
lua.execute('''
dofile=function()return {}end
local method={get_name=function()return 'setCommandAction'end,
 get_param_types=function()return {{get_full_name=function()return 'app.Player.Actions'end},1,1,1,1,1,1}end,
 call=function(_,p,action,initAdd,initOverwrite,puppet,priority,blend,mode)
  -- These booleans initialize layers 1 and 2; neither is a force flag.
  p.main=action
  if initAdd then p.add=0 end
  if initOverwrite then p.overwrite=0 end
  assert(not puppet and priority==0 and blend>=0 and blend<0.1 and mode==1)
 end}
sdk={find_type_definition=function()return {get_methods=function()return {method}end}end}
function parkedActor(id,oldAction,overlay,think,blendLocked)
 local p={id=id,main=oldAction,add=overlay,overwrite=overlay,
  thinkAction=think and oldAction or nil,blendLocked=blendLocked,
  speedY=3.2,jumpCount=1,hp=8000,dt=4000,sin=6300,weapon=2}
 function p:call(name,a,b)
  if name=='resetThink'then
   assert(a==true and b==-1,'use native automatic tree selection')
   self.thinkAction=nil
  elseif name=='resetBlendRateLock'then self.blendLocked=false
  else error('Unexpected player operation: '..name)end
 end
 function p:tick()
  if self.thinkAction then self.main=self.thinkAction end
  self.inputBlocked=self.main==500 or self.overwrite~=0 or self.add~=0 or self.blendLocked
 end
 return p
end
''')
core=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
for actor_id in (0,1,4):
    for airborne,expected in ((False,1),(True,75)):
        for overlay in (0,600):
            for think in (False,True):
                for blend_locked in (False,True):
                    p=lua.globals().parkedActor(actor_id,500,overlay,think,blend_locked)
                    core.resetEntryAction(p,airborne)
                    p.tick(p)
                    assert p.main==expected, 'old behavior tree resumed the parked attack'
                    assert not p.inputBlocked, 'parked overlay/recovery still blocks fresh input'
                    assert (p.speedY,p.jumpCount,p.hp,p.dt,p.sin,p.weapon)==(3.2,1,8000,4000,6300,2)
print('PASS: all three actors resume at Wait/Fall on the next tick; parked behavior, overlays and blend locks cleared; resources, equipment and air counters preserved.')
