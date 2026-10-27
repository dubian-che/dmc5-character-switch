"""Support recorder: bounded retention, crash persistence, safe reads and F8."""
import json
from pathlib import Path
from lupa import LuaRuntime

source=Path('support/zzz_dmc5_support_recorder.lua').read_text(encoding='utf-8')
lua=LuaRuntime(unpack_returned_tuples=True)
def plain(v):
    if hasattr(v,'items'):
        pairs=list(v.items())
        if pairs and all(isinstance(k,int) for k,_ in pairs):
            return [plain(v[i]) for i in range(1,len(pairs)+1)]
        return {str(k):plain(x) for k,x in pairs}
    return v
def table(v):
    if isinstance(v,dict):return lua.table_from({k:table(x)for k,x in v.items()})
    if isinstance(v,list):return lua.table_from([table(x)for x in v])
    return v
lua.globals().encode=lambda v,_:json.dumps(plain(v),separators=(',',':'))
lua.globals().decode=lambda s:table(json.loads(s))
lua.execute('''
now=1800000000;key=false;mutations=0;readCount=0;diskWrites=0;errors=0;files={};callbacks={}
os.time=function()return now end;os.clock=function()return .123 end
json={dump_string=encode,load_string=decode}
re={on_frame=function(f)callbacks[#callbacks+1]=f end}
reframework={is_key_down=function(_,k)assert(k==119);return key end}
log={error=function()errors=errors+1 end}
io={open=function(path,mode)
 assert(path:match('^dmc5_support/slot%-%d%d%.jsonl$'),'unexpected file access')
 if failing then return nil,'disk failure'end
 if mode=='r'and not files[path]then return nil end
 if mode=='w'then files[path]=''end
 return {write=function(_,...)diskWrites=diskWrites+1;files[path]=(files[path]or'')..table.concat({...})end,
  read=function(_,n)return files[path]and files[path]:sub(1,n)end,flush=function()end,close=function()end}
end}
local typeCache={}
function object(kind,values,fields)
 local o={values=values or{},fields=fields or{}}
 function o:get_address()return 123456 end
 function o:get_type_definition()
  if not typeCache[kind]then typeCache[kind]={get_full_name=function()return kind end,
   get_method=function(_,n)return {}end,get_field=function(_,n)return {}end}end
  return typeCache[kind]
 end
 function o:get_field(n)return self.fields[n]end
 function o:call(n,...)
  if n:sub(1,3)=='set'or n=='Clear'or n=='Add'then mutations=mutations+1;error('gameplay write')end
  readCount=readCount+1
  local v=self.values[n];if type(v)=='function'then return v(...)end;return v
 end
 return o
end
function array(values)
 local a=object('Array')
 a.get_size=function()return #values end;a.get_element=function(_,i)return values[i+1]end
 a.read_dword=function(_,offset)return values[(offset-0x20)//4+1]end
 return a
end
pad=object('PadInput',{get_buttonOnFlags=0,get_buttonTriggerFlags=0,get_buttonReleaseFlags=0})
local players={}
for _,id in ipairs({0,1,4})do
 local arms=array({3,1,7,2});local world=object('World',{get_Enabled=true})
 local mesh=array({object('Mesh')})
 local med=object('Mediator',{get_drawSelf=true,get_updateSelf=true})
 local charge=object('Charge',{get_padInput=pad,get_AutoCharge=false,get_state=0,get_currentLevel=1,get_padInputFlag=1},{Enable=true,LimitLevel=5})
 players[id]=object('Player'..id,{get_playerID=id,get_bodyMeshList=mesh,get_cachedCharacterController=world,
  get_cachedActivateMediator=med,get_padInput=pad,get_Enable=true,get_Enabled=true,get_hp=10000,
  get_maxHp=20000,get_devilTriggerGauge=1000,get_maxDevilTriggerGauge=10000,get_gauntletNum=4,
  get_gauntletStackCount=0,get_gauntletList=arms,get_isEasyAutomatic=false,get_currentWeaponS=3,
  get_isEventRun=true,get_isEventMove=false},{BlueRoseCharge=charge,['<theDTGauge>k__BackingField']=500})
end
manager=object('Manager',{get_manualPlayer=function()return players[active or 0]end,getPlayerNum=3,
 getPlayer=function(i)return players[({0,1,4})[i+1]]end,getPlayerByID=function(id)return players[id]end})
gm=object('GM',{get_missionNo=19,get_gameMode=0,get_isPause=false,get_isPauseMenu=false})
sdk={get_managed_singleton=function(n)if n=='app.GameManager'then return gm end;if n=='app.PlayerManager'then return manager end end}
dmc5_live_switch={build='release-47',current=0,stage='active Nero'}
dmc5_switch_loader={manager=manager,stage='ready',generation=1,available={['0']=true,['1']=true,['4']=true},ready=function()return not cold end}
function frame()for _,f in ipairs(callbacks)do f()end end
''')
lua.execute(source)
lua.execute('''
frame()
for second=1,2000 do
 now=now+1
 if second%20==0 then active=({0,1,4})[(second//20)%3+1];dmc5_live_switch.current=active end
 for i=1,60 do frame()end
end
assert(mutations==0 and errors==0)
assert(#callbacks==1 and dmc5_support_recorder.samples==2001)
local count=0;for _ in pairs(files)do count=count+1 end;assert(count==32,'unbounded disk files')
assert(dmc5_support_recorder.writes<2000/3,'unbatched disk flushes')
local before=dmc5_support_recorder.samples;key=true;frame();frame();frame()
assert(dmc5_support_recorder.samples==before+1,'held F8 repeated')
key=false;frame();key=true;frame();assert(dmc5_support_recorder.samples==before+1,'F8 cooldown bypassed')
key=false;now=now+3;frame();key=true;frame();key=false;frame()
assert(dmc5_support_recorder.samples==before+3)
''')
records=[]
for _,data in lua.globals().files.items():
    records.extend(json.loads(line)for line in data.splitlines())
assert len(records)<=32*65
assert any(r['kind']=='F8'for r in records)
assert all(len(r['players'])==3 for r in records)
assert next(p for p in records[-1]['players']if p['id']==0)['arms']==[3,1,7,2]
assert all(r['players'][0]['running'] is True and r['players'][0]['scriptedMove'] is False for r in records)
lua.execute('local before=readCount;for i=1,10000 do frame()end;assert(readCount==before,\'native reads scaled with FPS instead of wall seconds\')')
# Same-minute restart appends persisted records instead of erasing pre-crash evidence.
lua.execute('beforeBytes=0;for _,v in pairs(files)do beforeBytes=beforeBytes+#v end;callbacks={};dmc5_support_recorder=nil')
lua.execute(source);lua.execute('frame();assert(dmc5_support_recorder.writes==1)')
lua.execute('afterBytes=0;for _,v in pairs(files)do afterBytes=afterBytes+#v end;assert(afterBytes>beforeBytes)')
# Incomplete actors are represented without probing charge/equipment components.
lua.execute('cold=true;now=now+1;key=true;frame();key=false;now=now+5;frame()')
latest=[]
for _,data in lua.globals().files.items():latest.extend(json.loads(line)for line in data.splitlines())
last=max(latest,key=lambda r:r['utc']);assert all(p['ready'] is False and 'charges'not in p for p in last['players'])
# Disk failure cannot escape into the game's frame callback or mutate gameplay.
lua.execute('failing=true;now=now+5;frame();now=now+5;frame();assert(errors==1 and mutations==0)')
assert lua.globals().readCount<600000, 'unexpected per-sample native read expansion'
for forbidden in ['sdk.hook','set_field','write_dword',":call('set_",'os.execute','io.popen']:
    assert forbidden not in source,forbidden
print('PASS: 2000-second/120000-frame simulation; 32 rotating slots, batch writes, F8 edge/cooldown/flush, same-minute restart persistence, exact ordered arms, running-vs-scripted state, cold-actor guard, isolated disk failures and zero gameplay mutation.')
