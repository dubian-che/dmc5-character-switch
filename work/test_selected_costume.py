from autoload_fixture import make_game

for costume in [0,1,2]:
    lua=make_game(initial=1)
    lua.globals().choice=costume
    lua.execute('''
selectedCostumes={[0]=choice,[1]=0,[4]=2};requests={}
local original=native.call
native.call=function(self,n,id,c,s,...)
 if n=='requestLoadPlayerResource'then
  assert(c==selectedCostumes[id],'costume belongs to wrong hero or is defaulted')
  assert(s==0,'situation handling changed')
  requests[id]=c;profiles[id]={c,s}
 end
 return original(self,n,id,c,s,...)
end
S.request(0);tick(fps*8)
assert(active.id==0 and requests[0]==choice and requests[4]==2)
-- Replace the scene owner and native resource records as a scene reload does.
selectedCostumes[0]=(choice==0 and 1 or 0)
players[0]=nil;states[0]=nil;profiles[0]=nil
players[1]=actor(1);active=players[1];dmc5_switch_runtime.invalidate()
tick(fps*8)
assert(requests[0]==selectedCostumes[0],'old scene choice cached across reload')
''')
print('PASS: per-character selection used for cold loads; fresh selection read after scene replacement; default and EX choices preserved')
