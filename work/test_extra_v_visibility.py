from autoload_fixture import make_game

# Native floor cleanup can reactivate the SAME V; identity is insufficient.
for fps in (30, 60, 144):
    lua = make_game(fps=fps)
    lua.execute('''
players[2]=actor(2);states[2]=6
tick(fps*4)
local v=players[2];assert(not v.visible and excludedCount==1)
v.visible=true;v.enabled=true;v.updating=true;v.paused=false
tick(fps)
assert(not v.visible and not v.enabled and v.paused and excludedCount==2,'cached V escaped after native reactivation')
tick(fps*5)
assert(excludedCount==2,'settled V was repeatedly rewritten')
assert(loads[2]==nil and preloads[2]==nil and v.initialized==0)
-- A native root draw update can disagree with the mediator's cached flag.
v.visible=true;v.medDraw=false
tick(fps);assert(not v.visible and excludedCount==3,'root draw reactivation bypassed mediator cache')
''')

print('PASS: native reactivation of the same cached V is detected; settled actors are not rewritten; no V initialization/load/unload.')

for phase in ('updateBattleFinish', 'updateNextStageWait', 'updateFadeoutShowStageResult', 'updateFloorFinalize'):
    for initial in (0, 1, 4):
        lua = make_game(initial=initial)
        lua.globals().phase = phase
        lua.execute('''
players[2]=actor(2);states[2]=6;tick(fps*4)
local v=players[2];local owner=active
bp={CurrentStageNo=20,IsTrainingMode=false,IsRetryProcessing=false,IsRetryTrainingRequest=false,CurrentFlowState=23}
function bp:get_field(name)return self[name]end
dmc5_switch_palace={run={owner=bp}}
local h=nativeHooks['app.BloodyPalaceManager.'..phase]
assert(h and S.extraVError==nil)
event=true;v.eventRun=true
h[1]({[2]=bp})
-- Original callback reactivates an existing V and advances native flow.
v.visible=true;v.medDraw=false;v.enabled=true;v.updating=true;v.paused=false;bp.CurrentFlowState=24
assert(h[2](777)==777)
assert(not v.visible and v.enabled and v.updating and not v.paused,'result hook changed native update/pause ownership')
assert(active==owner and owner.enabled and owner.visible and bp.CurrentFlowState==24)
local hides=v.hideCalls
for i=1,60 do h[1]({[2]=bp});h[2](777)end
assert(v.hideCalls==hides,'unchanged clear-stage actor repeatedly rewritten')
assert(loads[2]==nil and preloads[2]==nil and v.initialized==0)
''')

for exclusion in ('mode=0', 'bp.CurrentStageNo=101', 'bp.IsTrainingMode=true', 'bp.IsRetryProcessing=true',
                  'bp.IsRetryTrainingRequest=true', 'paused=true', 'dmc5_switch_palace.run.owner={}', 'active=players[2]'):
    lua = make_game()
    lua.execute('''
players[2]=actor(2);states[2]=6;tick(fps*4)
bp={CurrentStageNo=20,get_field=function(self,n)return self[n]end}
dmc5_switch_palace={run={owner=bp}}
players[2].visible=true;players[2].medDraw=true
''')
    lua.execute(exclusion)
    lua.execute('assert(not S.hidePalaceExtra(bp)and players[2].visible)')
print('PASS: native clear/result callbacks hide only extra V after original code; event-safe visual-only changes; no settled writes; native flow, manual V, ending, training/retry and other modes preserved.')
