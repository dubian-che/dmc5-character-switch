from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader

def make_game():
    lua = LuaRuntime()
    install_module_loader(lua)
    lua.execute(Path('work/palace_engine_fixture.lua').read_text())
    for name, symbol in [('runtime', 'Runtime'), ('progression', 'Progression'), ('regen', 'Regen'), ('resources', 'Resources'), ('palace', 'Palace')]:
        lua.globals()[symbol] = lua.execute(Path(f'outputs/DMC5CharacterSwitch/dmc5_switch_{name}.lua').read_text())
    lua.execute('Progression.lockRedBike=function()return false end')
    return lua
