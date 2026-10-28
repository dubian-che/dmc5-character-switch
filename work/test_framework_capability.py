"""Unsupported hosts must never install partial gameplay hooks."""
from pathlib import Path
from lupa import LuaRuntime

source = Path('outputs/DMC5CharacterSwitch/dmc5_live_switch.lua').read_text(encoding='utf-8')
for declaration in ('thread=nil', 'thread={}', 'thread={get_hook_storage=7}', 'thread="old host"'):
    lua = LuaRuntime()
    lua.execute('''
    loads=0;hooks=0;callbacks=0;errors={}
    dofile=function()loads=loads+1;error('module loaded on unsupported host')end
    sdk={hook=function()hooks=hooks+1 end}
    re={on_frame=function()callbacks=callbacks+1 end}
    log={error=function(message)errors[#errors+1]=message end}
    '''+declaration)
    blocked = lua.execute(source)
    assert blocked.stage == 'incompatible REFramework'
    assert 'thread.get_hook_storage' in blocked.error
    assert blocked.current == -1 and blocked.request is None
    assert lua.globals().loads == lua.globals().hooks == lua.globals().callbacks == 0
    assert len(lua.globals().errors) == 1

lua = LuaRuntime()
lua.execute('thread={get_hook_storage=function()return {}end}; dofile=function()error("supported-host-load")end')
try:
    lua.execute(source)
except Exception as error:
    assert 'supported-host-load' in str(error)
else:
    raise AssertionError('Compatible host did not proceed to module loading')
print('PASS: missing namespace, missing/invalid hook-storage API stop before all module loads, gameplay hooks and key callbacks; supported API proceeds normally')
