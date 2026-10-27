from autoload_fixture import make_game

for fps in (30, 60, 144):
    lua = make_game(fps=fps)
    lua.execute('''
tick(fps*4);S.request(1);tick(1)
local p=active;local B=dmc5_switch_loader
p.enabled=false;p.visible=false;p.paused=true;p.weaponS=-1;p.weaponL=-1
tick(2);assert(p.recoveries==nil,'recovered an intermediate native transition')
tick(1)
assert(p.enabled and p.visible and not p.paused and p.recoveries==1)
assert(p.hp==20000 and p.weaponS==-1 and p.weaponL==-1,'recovery forged equipment or health')
p.enabled=false;p.visible=false;tick(fps*3)
assert(p.recoveries==1,'recovery kept fighting native state every frame')
''')

for exclusion in ('event=true', 'paused=true', 'active.hp=0', 'active.devil=true', 'active.meshReady=false', 'active.enabled=true', 'active.componentEnabled=false', 'active.updating=false',
                  'dmc5_switch_palace={canRegen=function()return false end}'):
    lua = make_game()
    lua.execute('tick(fps*4);S.request(1);tick(1);active.enabled=false;active.visible=false;active.weaponS=-1;active.weaponL=-1')
    lua.execute(exclusion)
    lua.execute('tick(fps);assert(active.recoveries==nil)')

lua = make_game()
lua.execute('''
tick(fps*4);S.request(1);tick(fps*2)
active.enabled=false;active.visible=false;active.weaponS=-1;active.weaponL=-1
tick(fps);assert(active.recoveries==nil,'late combat state was pinned outside arrival window')
''')
lua = make_game(initial=1)
lua.execute('''
active.enabled=false;active.visible=false;active.weaponS=-1;active.weaponL=-1
tick(fps*3)
assert(active.recoveries==1 and active.enabled and active.visible,'native floor arrival without explicit request remained parked')
''')
print('PASS: selected disabled/hidden but updating actor recovers once after three observations; bounded arrival window; pause/event/death/DT/loading/normal action hiding excluded; no forged equipment or HP.')
for target in (0, 1, 4):
    lua = make_game(initial=(1 if target == 0 else 0))
    lua.globals().target = target
    lua.execute('''
tick(fps*4);S.request(target);tick(1)
local p=active;p.enabled=false;p.visible=false
tick(3)
assert(p.recoveries==1 and p.enabled and p.visible and p.hp==20000)
''')
    lua = make_game(initial=target)
    lua.execute('''
active.enabled=false;active.visible=false
tick(fps*3)
assert(active.recoveries==1 and active.enabled and active.visible)
''')
print('PASS: identical activation protocol for Nero/Dante/playable Vergil, including native floor arrival and preserved HP/equipment.')
