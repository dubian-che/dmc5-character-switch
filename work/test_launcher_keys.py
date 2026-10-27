"""Check the compiled launcher's JSON contract and the actual Lua startup callback."""
import json
import sys
from pathlib import Path

sys.path.insert(0, 'work/python-deps')
from lupa import LuaRuntime
from autoload_fixture import make_game

report = json.loads(Path('work/launcher-self-test.json').read_text(encoding='utf-8'))
assert report['passed'], report
saved = json.loads(Path(report['configPath']).read_text(encoding='utf-8'))
lua = LuaRuntime(unpack_returned_tuples=True)
k = lua.execute(Path('outputs/DMC5CharacterSwitch/dmc5_switch_keys.lua').read_text())
lua.globals().K = k
lua.execute("json={load_file=function(path) assert(path=='dmc5_switch_config.json'); return supplied end}")


def read_config(value):
    lua.globals().supplied = lua.table_from(value) if isinstance(value, dict) else value
    result = k.load_config()
    return result if isinstance(result, tuple) else (result, None)


config, warning = read_config(saved)
assert config.nextKey == 118 and config.previousKey == 119 and not config.controllerCombo
assert warning is None
assert set(report['keyCodes']) == {i for i in range(256) if k.valid_key(i)}
for value in (None, {}):
    config, warning = read_config(value)
    assert config.nextKey == 128 and config.previousKey == 129 and config.controllerCombo
    assert warning is None
for value in (False, 42, 'wrong', {'version': 2}, {'nextKey': False},
              {'nextKey': 118.5}, {'nextKey': '118'}, {'nextKey': 45},
              {'nextKey': 129}, {'controllerCombo': 'false'}):
    config, warning = read_config(value)
    assert config.nextKey == 128 and config.previousKey == 129 and config.controllerCombo
    assert warning, value
lua.execute("json.load_file=function()error('unreadable JSON')end")
config, warning = k.load_config()
assert config.nextKey == 128 and warning

# Full autorun startup uses the emitted JSON, polls custom keys and reads disk once.
lua = make_game(config=saved)
lua.execute('''
assert(S.config.nextKey==118 and S.config.previousKey==119)
assert(not S.config.controllerCombo and S.configWarning==nil)
tick(fps*5);assert(active.id==0 and switches==0)
key_down[128]=true;key_down[129]=true;tick(10)
assert(switches==0,'old defaults still active after custom configuration')
key_down={};tick(1)
key_down[118]=true;tick(1);assert(active.id==1 and switches==1)
tick(fps);assert(switches==1,'held key repeats')
key_down={};tick(1)
key_down[118]=true;tick(1);assert(active.id==4 and switches==2)
key_down={};tick(1)
key_down[119]=true;tick(1);assert(active.id==1 and switches==3)
key_down={};tick(1)
key_down[118]=true;key_down[119]=true;tick(10);assert(switches==3)
key_down[118]=nil;tick(10);assert(switches==3,'chord release triggers a switch')
key_down={};tick(1)
key_down[119]=true;tick(1);assert(active.id==0 and switches==4)
tick(fps*10);assert(config_reads==1,'configuration reread during frames')
''')
print('PASS: C#/Lua JSON and key parity, invalid config fallback, custom-key startup, edge triggering, both-key cancellation, one-time disk read.')
