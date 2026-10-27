"""V missions are outside the Mod, including transient supported manual actors."""
from pathlib import Path
from lupa import LuaRuntime
from lua_test_support import install_module_loader
from autoload_fixture import make_game


def controller_fixture(source, ident=2):
    lua = LuaRuntime()
    install_module_loader(lua)
    lua.globals().ident = ident
    lua.execute('''
writes=0;padReads=0
sdk={hook=function()end,find_type_definition=function()return {get_method=function()end}end,
 get_managed_singleton=function()return {call=function(_,n)assert(n=='findManualPlayerID');return 2 end}end}
dmc5_switch_controller={hooked=true,enabled=true,oldShoulders=0,blocked=0,pending=1}
local mapping={get_size=function()return 4 end,read_dword=function(_,off)return off==0x2c and 16 or 256 end}
pad={call=function(_,n,v)
 if n:sub(1,4)=='set_'then writes=writes+1;return end
 padReads=padReads+1
 if n=='get_keyAssignArray'then return mapping
 elseif n=='get_padButton'then return 272 else return 0xffff end
end}
player={call=function(_,n)if n=='get_playerID'then return ident end;assert(n=='get_padInput');return pad end}
manager={call=function(_,n)assert(n=='get_manualPlayer');return player end}
''')
    c = lua.execute(source)
    c.manager = lua.globals().manager
    c.process(lua.globals().pad)
    return lua


old = Path('work/checkpoints/release-32-before-v-scene-boundary/outputs/dmc5_switch_controller.lua').read_text()
# Provide the original controller's paused-state queries as native false values.
old = old.replace("local gm=sdk.get_managed_singleton('app.GameManager')", "local gm={call=function()return false end}")
assert controller_fixture(old).globals().writes > 0, 'pre-fix V input suppression was not reproduced'
source = Path('outputs/DMC5CharacterSwitch/dmc5_switch_controller.lua').read_text()
for ident in (0, 1, 2, 4):
    lua = controller_fixture(source, ident)
    assert lua.globals().writes == 0 and lua.globals().padReads == 0
    assert lua.globals().dmc5_switch_controller.pending is None

for ident in (0, 1, 2, 4):
    lua = make_game(initial=ident)
    lua.execute('''
campaignID=2;nativeWrites=0;backgroundReads=0
local original=manager.call
manager.call=function(self,n,...)
 if n=='getPlayerByID'then backgroundReads=backgroundReads+1 end
 return original(self,n,...)
end
for _,id in ipairs({0,1,2,4})do if not players[id]then players[id]=actor(id)end end
local find=sdk.find_type_definition
sdk.find_type_definition=function(name)local t=find(name);t.get_methods=function()return {}end;return t end
''')
    for name, symbol in [('resources', 'Resources'), ('progression', 'Progression'), ('regen', 'Regen'), ('hud', 'Hud'), ('palace', 'Palace'), ('controller', 'Controller')]:
        lua.globals()[symbol] = lua.execute(Path(f'outputs/DMC5CharacterSwitch/dmc5_switch_{name}.lua').read_text())
    lua.globals().Party = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_party_hud.lua').read_text())
    lua.globals().Core = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_core.lua').read_text())
    lua.execute('''
tick(fps*8)
assert(next(loads)==nil and next(preloads)==nil and initializations==0 and switches==0)
assert(backgroundReads==0,'V scene scanned or modified party actors')
assert(dmc5_switch_loader.manager==nil and not S.request(1))
assert(Resources.error==nil and Progression.error==nil and Party.error==nil)
assert(not Core.hideReserve(manager,players[2])and not Core.parkNonParty(manager,players[2]))
assert(not Core.prepareReserve(manager,players[1]))
assert(not pcall(Core.switch,manager,1)and not pcall(Core.recoverSelected,manager,active))
assert(not S.hidePalaceExtra({})and not Palace.finishGauntletStage({},manager,{}))
local menu={call=function(_,n)assert(n=='get_IsPauseMenu');return true end,set_field=function()error('V menu changed')end}
dmc5_switch_input_menu.open(menu);dmc5_switch_input_menu.select(menu);dmc5_switch_input_menu.closed(menu)
assert(dmc5_switch_input_menu.error==nil)
assert(Party.entries and next(Party.entries)==nil)
''')

print('PASS: pre-fix V input suppression reproduced; native V mission blocks all party auto-hooks and direct switch paths, even when Nero/Dante/Vergil transiently become manual; zero pad writes, actor scans, loads, progression, HUD or flow mutations.')
