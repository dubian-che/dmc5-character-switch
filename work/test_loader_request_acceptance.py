from autoload_fixture import make_game

lua=make_game(initial=1)
lua.execute('''
active.meshReady=false
tick(fps)
local B=dmc5_switch_loader
local generation=B.generation
assert(next(loads)==nil and not B.playable,'reserve loading started before native owner ready')
active.meshReady=true;tick(fps*5)
assert(B.generation==generation and B.known[1]==active and B.count==3)
''')

lua=make_game(initial=1)
lua.execute('''
local original=native.call;loadRequests=0
native.call=function(self,n,...)
 if n=='requestLoadPlayerResource'then
  loadRequests=loadRequests+1
  if loadRequests==1 then return end -- native void request silently refused
 end
 return original(self,n,...)
end
S.request(0);tick(fps*8)
assert(active.id==0 and switches==1 and loads[0]==1)
assert(loadRequests==3,'accepted native loads were requested twice')
assert(S.error==nil)
''')

lua=make_game(initial=1)
lua.execute('''
local original=native.call;loadRequests=0
native.call=function(self,n,...)
 if n=='requestLoadPlayerResource'then loadRequests=loadRequests+1;return end
 return original(self,n,...)
end
tick(fps*90)
assert(loadRequests<=18 and loadRequests>0,'silent refusal retries were unbounded')
assert(active.id==1 and switches==0 and next(loads)==nil)
assert(dmc5_switch_loader.error:find('not accepted'))
''')
print('PASS: late native-owner adoption, no early reserve loads, native void refusal recovery, no duplicate accepted requests, bounded permanent refusal')
