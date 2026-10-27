import sys
from pathlib import Path
sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime
lua=LuaRuntime()
lua.execute('''
sdk={find_type_definition=function()return {get_methods=function()return {}end}end}
dofile=function()return {}end
function scenario(id,mode,pending,valid,deferred,hasClone)
 state={mode=mode,pending=pending,valid=valid,off=0,destroy=0}
 local clone={get_field=function(_,key)assert(key=='_DoppelValid');return state.valid end}
 return {call=function(_,name,value)
  if name=='get_playerID' then return id
  elseif name=='get_cachedDoppel' then if hasClone then return clone end
  elseif name=='get_DoppelMode' then return state.mode
  elseif name=='get_isGenerateDoppelWait' then return state.pending
  elseif name=='setDoppelMode' then
   assert(value==false);state.mode=false;state.off=state.off+1
   if not deferred then state.valid=false end
  elseif name=='set_isGenerateDoppelWait' then state.pending=value
  elseif name=='destroyDoppelGanger' then state.valid=false;state.destroy=state.destroy+1
  else error('Unexpected call '..name)end
 end}
end
''')
core=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
for mode,pending,valid,deferred,clone in [
    (True,False,True,False,True),
    (True,False,True,True,True),
    (False,False,True,False,True),
    (False,True,False,False,False),
    (False,False,False,False,True),
]:
    p=lua.globals().scenario(4,mode,pending,valid,deferred,clone)
    core.dismissDoppel(p)
    s=lua.globals().state
    assert not s.mode and not s.pending and not s.valid
    calls=(s.off,s.destroy)
    core.dismissDoppel(p)
    assert calls==(s.off,s.destroy), 'repeated dismissal should not replay native effects'
for id in (0,1):
    p=lua.globals().scenario(id,True,True,True,False,True)
    core.dismissDoppel(p)
    assert lua.globals().state.off==0 and lua.globals().state.destroy==0
print('PASS: normal/deferred retirement, stranded clone, pending summon, repeat/no-op and other actors.')
