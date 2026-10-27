"""Periodic writes must not treat an existing/cached actor as loaded."""
from pathlib import Path
import autoload_fixture as fixture

def verify(source=None):
    previous=fixture.SOURCE
    try:
        if source:fixture.SOURCE=source
        lua=fixture.make_game()
        lua.execute("tick(fps*4)")
        lua.execute('''
        gunWrites=0;chargeWrites=0;refills=0;skillWrites=0;progressCharge=0;healthWrites=0
        for _,p in pairs(players)do
          local original=p.call
          p.get_address=function()return p.id+1000 end
          local data={get_address=function()return p.id+2000 end,get_field=function(_,n)return n=='MaxHP'and 20 or 10 end}
          p.call=function(self,n,v,...)
            if n=='get_playerData'then return data end
            if n=='get_maxHp'then return 20000 end
            if n=='get_devilTriggerGauge'then return 5000 end
            if n=='get_maxDevilTriggerGauge'then return 10000 end
            if n=='set_devilTriggerGauge'or n=='set_hp'then healthWrites=healthWrites+1;return end
            return original(self,n,v,...)
          end
        end
        resources=dofile('reframework/data/dmc5_switch_resources.lua')
        resources.bindNeroGunInput=function()gunWrites=gunWrites+1 end
        resources.bindPlayerChargeInputs=function()chargeWrites=chargeWrites+1 end
        resources.refill=function()refills=refills+1 end
        progression=dofile('reframework/data/dmc5_switch_progression.lua')
        local progressHook=hooks[#hooks]
        progression.apply=function()skillWrites=skillWrites+1 end
        progression.refreshNeroCharge=function()progressCharge=progressCharge+1 end
        regen=dofile('reframework/data/dmc5_switch_regen.lua')
        function pulse()
          for _=1,120 do
            dmc5_switch_runtime.begin(manager)
            resources.tick(manager);progressHook({[2]=manager})
            dmc5_switch_runtime.finish()
          end
          regen.pending={[1]=100,[4]=100};regen.flush(manager)
        end
        -- Exact actor pointers remain cached while native resources reload.
        for id,p in pairs(players)do states[id]=3;p.meshReady=false end
        pulse()
        assert(gunWrites==0 and chargeWrites==0 and refills==0,'input/refill wrote before native readiness')
        assert(skillWrites==0 and progressCharge==0,'skill maintenance wrote before native readiness')
        assert(healthWrites==0,'regen wrote before native readiness')
        for id,p in pairs(players)do states[id]=6;p.meshReady=true end
        pulse()
        assert(gunWrites>0 and chargeWrites>0 and refills>0)
        assert(skillWrites==3 and progressCharge==1)
        assert(healthWrites==2,healthWrites)
        -- Same actors under a replacement manager must not reuse old acceptance.
        local other={call=manager.call}
        assert(not dmc5_switch_loader.ready(other,0))
        ''')
    finally:fixture.SOURCE=previous

try:
    verify(Path('work/checkpoints/release-44-before-native-resource-profile/outputs/DMC5CharacterSwitch'))
except Exception as e:
    assert 'wrote before native readiness' in str(e),str(e)
else:raise AssertionError('release-44 periodic-write bug not reproduced')
verify()
print('PASS: release-44 premature writes reproduced; input, refill, skills and regen wait for native readiness; maintenance resumes; manager identity checked.')
