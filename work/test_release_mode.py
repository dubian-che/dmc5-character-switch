"""Exercise normal play with development UI/timing/writes forbidden."""
from autoload_fixture import make_game

for fps in (30,60,144):
    for combo in (False,True):
        lua=make_game(fps=fps,config={'controllerCombo':combo})
        assert lua.globals().controller_loads == int(combo)
        lua.execute('''
os.clock=function()error('release timer invoked')end
assert(S.reload_core==nil and dmc5_switch_runtime.run==nil)
tick(fps*5);assert(dmc5_switch_loader.count==3)
for _,id in ipairs({1,4,0})do S.request(id);tick(1);assert(active.id==id)end
tick(fps*30);assert(config_reads==1 and switches==3)
-- Removing instrumentation must not remove failure containment or retry.
local original=core.switch
core.switch=function()error('simulated native failure')end
S.request(1);tick(1)
assert(S.stage=='error' and S.error:find('simulated native failure'))
assert(active.id==0)
tick(5);assert(active.id==0,'failed request retried every frame')
core.switch=original
S.request(1);tick(1);assert(active.id==1 and S.error==nil)
''')
print('PASS: no debug UI, timing or writes at 30/60/144 FPS; disabled combo never loads hooks; switching and contained-failure retry retained.')

lua=make_game(fps=60,config={'controllerCombo':False})
lua.execute('''
tick(60*5)
dmc5_switch_palace={run={stage={}}}
assert(S.request(1,'palace'))
dmc5_switch_palace.run={stage={}};tick(1)
assert(active.id==0 and S.stage=='Palace phase changed','old run committed an automatic role switch')
assert(S.request(1,'palace'))
dmc5_switch_palace.run.stage={};tick(1)
assert(active.id==0,'old arrival committed an automatic role switch')
assert(S.request(1,'palace'));tick(1);assert(active.id==1)
assert(S.request(4,'user'));dmc5_switch_palace.run=nil;tick(1)
assert(active.id==4,'Palace state blocked a manual choice')
''')
print('PASS: internal selections expire with their run/arrival; manual requests remain independent of Palace state.')

