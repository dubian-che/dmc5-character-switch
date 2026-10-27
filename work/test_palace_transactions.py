"""Native phase ordering, same-floor supply rooms and reloads with real modules."""
from palace_test_fixture import make_game

for fps in (30, 60, 144):
    game = make_game()
    game.globals().fps = fps
    game.execute('''
bp.CurrentStageNo=0;bp.IsGauntletStage=true;active=players[0]
active.count=0;active.armList=arms({})
phase('updateGauntletStageInit')
assert(Palace.run.stage.floor==0 and Palace.run.stage.kind=='supply')
assert(Palace.canRefill())
frames(fps)
assert(active.count==1 and active.refills==1,'supply-stage readiness blocked automatic empty-arm refill')
active.charge.timer=250;frames(fps*2)
assert(active.charge.timer==250 and active.charge.resets==0,'floor checks repeatedly reset valid Blue Rose charge')
-- Even with a committed transfer, manual input remains available.
phase('updateFadeout')
assert(dmc5_live_switch.request(1,'user'));frame()
assert(active.id==1 and Palace.run.preferred==1,'committed portal locked manual selection')
phase('updateCheckGaunletStage',function()bp.CurrentFlowState=6 end)
assert(not bp.IsGauntletStage)
reload('battle',1);settle()
assert(active.id==1 and Palace.run.stage.floor==1 and Palace.run.stage.kind=='battle')
''')

game = make_game()
game.execute('''
bp.CurrentStageNo=1;phase('updateBattleInit');choose(1)
players[1].dt=2154;players[1].sin=6669;players[1].hp=17890
players[4].dt=3333;players[4].sin=4444;players[4].weaponS=7;players[4].weaponSID=1
players[0].dt=10000
phase('updateFadeout',function()active=players[4]end)
local first=Palace.run.stage.snapshot
assert(first.choice==1 and first.rows[1].dt==2154 and first.rows[1].sin==6669)
assert(first.rows[4].weaponS==7 and first.rows[4].weaponSID==1)
local oldEpoch=Palace.run.stage.epoch
-- Supply interludes can retain the numeric floor. A new arrival epoch is
-- still required, and native initialization finishes BEFORE restore starts.
reload('supply',1,1)
assert(Palace.run.stage.epoch~=oldEpoch and Palace.run.stage.kind=='supply')
assert(players[0].rebuilds==0 and players[4].weapons==0,'arrival callback mutated actors before native update')
frames(10)
assert(active.id==4 and Palace.pendingVitals(1)and not Palace.canRegen(1))
players[1]=actor(1);players[1].dt=10000;players[1].sin=0
dmc5_switch_loader.known[1]=players[1]
settle()
assert(active.id==1 and Palace.run.preferred==1)
assert(players[1].hp==17890 and players[1].dt==2154 and players[1].sin==6669)
assert(players[1].weaponS==4 and players[1].weaponSID==0)
assert(players[1].weaponL==13 and players[1].weaponLID==0)
assert(players[1].slotsS.values[3]==7 and players[1].slotsL.values[2]==13,'deferred native weapon entry replaced restored loadout')
assert(players[4].sin==4444 and players[4].weaponS==7 and players[4].weaponSID==1)
assert(players[0].count==3 and players[0].armList.values[1]==3 and players[0].armList.values[3]==11)
assert(Progression.neroChargeWarning==nil and Palace.error==nil and Resources.error==nil)
-- Restored gauges/loadouts must not pin ordinary combat on repeated callbacks.
local writes=players[1].hpWrites;local equips=players[1].weapons
players[1].hp=players[1].hp-100;players[1].sin=players[1].sin-70
local epoch=Palace.run.stage.epoch;phase('updateGauntletStageInit');frames(180)
assert(Palace.run.stage.epoch==epoch)
assert(players[1].hp==17790 and players[1].sin==6599 and players[1].hpWrites==writes and players[1].weapons==equips)
-- Leave the supply room as Dante. Only the proven v25 adapter clears its
-- old supply flags; the original native function advances the game flow.
players[0].count=0;players[0].armList=arms({})
players[1].weaponS=7;players[1].weaponSID=1;players[1].dt=1234
phase('updateGauntletStageFinalize')
local supplySnapshot=Palace.run.stage.snapshot
phase('updateCheckGaunletStage',function()
 if active.id==0 and bp.IsGauntletStage then bp.IsGauntletStage=false;bp.CurrentGauntletStageInfo=nil end
 bp.CurrentFlowState=6
end)
assert(not bp.IsGauntletStage and bp.CurrentFlowState==6 and Palace.gauntletExits==1)
reload('battle',2)
settle()
assert(active.id==1 and players[1].dt==1234 and players[1].sin==6599 and players[1].hp==17790)
assert(players[1].weaponS==7 and players[1].weaponSID==1)
assert(players[4].weaponS==7 and players[4].weaponSID==1 and players[4].sin==4444)
assert(players[0].count==0,'empty source stock was not restored before gameplay refill')
frames(30)
assert(players[0].count==0,'reserve Nero refilled before becoming active')
choose(0);frames(60)
assert(players[0].count==1 and players[0].refills==1,'empty carried stock disabled ordinary automatic refill')
choose(4)
assert(players[4].weaponS==7 and players[4].sin==4444,'returning to reserve Vergil lost selected weapon or SDT')
-- A true run reset discards the source; same-run repeated arrivals do not.
phase('updateGameOver');assert(Palace.run==nil)
bp.CurrentStageNo=0;phase('updateGauntletStageInit')
assert(Palace.run.stage.source==nil and Palace.run.preferred==nil)
mode=0;frame();assert(Palace.run==nil)
''')

game = make_game()
game.execute('''
bp.CurrentStageNo=1;phase('updateBattleInit');choose(1)
players[4].hp=0;players[4].sin=3456
phase('updateFloorFinalize');reload('battle',2,1)
frames(30)
assert(active.id==4 and active.hp>0,'saved zero-HP reserve became the temporary manual actor before handoff')
players[1]=actor(1);dmc5_switch_loader.known[1]=players[1]
settle()
assert(active.id==1 and players[4].hp==0 and players[4].sin==3456)
-- Post-init partial failure is contained and never retries a mutation every frame.
phase('updateFloorFinalize');reload('battle',3)
local bad=players[4];local original=bad.call;bad.failures=0
bad.call=function(self,name,a,b)
 if name=='changeWeaponS'then self.failures=self.failures+1;error('native weapon unavailable')end
 return original(self,name,a,b)
end
frames(180)
assert(bad.failures==1 and Palace.error:find('native weapon unavailable'))
assert(dmc5_live_switch.request(0,'user'),'restore failure disabled user control')
''')

print('PASS: real native PRE/POST ordering; supply floor 0 and same-counter stage epochs; all party gauges, melee/ranged/variant IDs and ordered arms; reserve Vergil SDT; ordinary empty refill, manual override, deferred writes, no pinning, true run resets and contained failures.')
