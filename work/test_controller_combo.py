import sys
from pathlib import Path
sys.path.insert(0,'work/python-deps')
from lupa import LuaRuntime
from lua_test_support import install_module_loader
lua=LuaRuntime(unpack_returned_tuples=True)
install_module_loader(lua)
lua.execute('sdk={hook=function()end,find_type_definition=function()return {get_method=function()end}end}')
lua.execute('dmc5_switch_controller={hooked=true,oldShoulders=0,blocked=0}')
c=lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_controller.lua').read_text())
assert c.evaluate(256,False,True)[0] is None
c.evaluate(0,True,True)
assert c.evaluate(256,True,True)[0]==-1
for _ in range(120): assert c.evaluate(256,True,True)[0] is None
assert c.evaluate(256,False,True)[1]==256
c.evaluate(0,False,True)
assert c.evaluate(1024,True,True)[0]==1
c.evaluate(0,True,True)
assert c.evaluate(1280,True,True)[0] is None
c.evaluate(0,False,True)
assert c.evaluate(256,True,False)[0] is None
print('PASS: forward/reverse, no autorepeat, shoulders alone, both shoulders, pause, release suppression.')
