#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdio.h>
#include <wchar.h>
#include <intrin.h>
#include "deps/minhook-1.3.4/include/MinHook.h"
#include "verified_proxy.h"

// Forward the Windows multimedia API unchanged. Only the identified DMC5
// SoundEngine default pool creation is enlarged, before the pool owns objects.
constexpr uintptr_t PoolCreateRva=0x4419760;
constexpr uintptr_t DefaultPoolReturnRva=0x436ef45;
constexpr uint32_t PoolBudget=32u*1024*1024;
using CreatePoolFn=int32_t(*)(void*,uint32_t,uint32_t,uint32_t,uint32_t);
static CreatePoolFn originalCreatePool;
static uintptr_t gameBase;
static wchar_t statusPath[MAX_PATH];
static uint32_t desiredBytes(uintptr_t caller,void* memory,uint32_t bytes,uint32_t block,uint32_t attributes) {
    if(caller==DefaultPoolReturnRva&&!memory&&block==64&&attributes==1&&bytes>64&&bytes<PoolBudget)return PoolBudget;
    return bytes;
}
static void status(const char* state,uint32_t before=0,uint32_t after=0,int32_t pool=-1) {
    if(!statusPath[0])return;
    HANDLE f=CreateFileW(statusPath,GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(f==INVALID_HANDLE_VALUE)return;
    char text[512];int count=sprintf_s(text,"{\"schema\":1,\"revision\":\"wwise-default-pool-32m-1\",\"state\":\"%s\",\"beforeBytes\":%u,\"afterBytes\":%u,\"poolID\":%d,\"pid\":%lu}\n",state,before,after,pool,GetCurrentProcessId());
    DWORD wrote=0;if(count>0)WriteFile(f,text,count,&wrote,nullptr);CloseHandle(f);
}
static int32_t createPoolHook(void* memory,uint32_t bytes,uint32_t block,uint32_t attributes,uint32_t alignment) {
    uintptr_t caller=(uintptr_t)_ReturnAddress()-gameBase;
    uint32_t actual=desiredBytes(caller,memory,bytes,block,attributes);
    int32_t pool=originalCreatePool(memory,actual,block,attributes,alignment);
    if(caller==DefaultPoolReturnRva)status(pool<0?"pool_creation_failed":actual!=bytes?"applied":"native_budget_preserved",bytes,actual,pool);
    return pool;
}

#ifndef POOL_FIX_TEST
extern "C" { FARPROC winmmFunctions[EXPORT_COUNT]={}; }
static HMODULE systemWinmm;
static bool loadWindowsExports() {
    wchar_t file[MAX_PATH];UINT n=GetSystemDirectoryW(file,MAX_PATH);
    if(!n||n>MAX_PATH-12)return false;
    wcscat_s(file,L"\\winmm.dll");systemWinmm=LoadLibraryW(file);if(!systemWinmm)return false;
    for(unsigned i=0;i<EXPORT_COUNT;i++) {
        winmmFunctions[i]=GetProcAddress(systemWinmm,ExportNames[i][0]?ExportNames[i]:MAKEINTRESOURCEA(ExportOrdinals[i]));
        if(!winmmFunctions[i])return false;
    }
    return true;
}
static void installFix() {
    wchar_t file[MAX_PATH];if(!GetModuleFileNameW(nullptr,file,MAX_PATH))return;
    wchar_t* leaf=wcsrchr(file,L'\\');if(!leaf||_wcsicmp(leaf+1,L"DevilMayCry5.exe"))return;
    *leaf=0;swprintf_s(statusPath,L"%s\\.dmc5-character-switch\\audio-pool-fix-status.json",file);
    gameBase=(uintptr_t)GetModuleHandleW(nullptr);
    auto dos=(IMAGE_DOS_HEADER*)gameBase;
    auto nt=(IMAGE_NT_HEADERS64*)(gameBase+dos->e_lfanew);
    if(nt->OptionalHeader.SizeOfImage!=GAME_IMAGE_SIZE||
        memcmp((void*)(gameBase+PoolCreateRva),PoolCreateSignature,sizeof(PoolCreateSignature))||
        memcmp((void*)(gameBase+0x436ef16),PoolCallerSignature,sizeof(PoolCallerSignature))) {
        status("unsupported_game_signature");return;
    }
    MH_STATUS init=MH_Initialize();
    if(init!=MH_OK&&init!=MH_ERROR_ALREADY_INITIALIZED){status("hook_initialization_failed");return;}
    if(MH_CreateHook((void*)(gameBase+PoolCreateRva),(void*)createPoolHook,(void**)&originalCreatePool)!=MH_OK){status("hook_creation_failed");return;}
    if(MH_EnableHook((void*)(gameBase+PoolCreateRva))!=MH_OK){MH_RemoveHook((void*)(gameBase+PoolCreateRva));status("hook_enable_failed");return;}
    status("waiting_for_default_pool");
}
BOOL WINAPI DllMain(HINSTANCE module,DWORD reason,LPVOID) {
    if(reason==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(module);if(!loadWindowsExports())return FALSE;installFix();}
    return TRUE;
}
#else
static uint32_t observed[4];
static int32_t fakeCreate(void* memory,uint32_t bytes,uint32_t block,uint32_t attributes,uint32_t alignment) {
    observed[0]=bytes;observed[1]=block;observed[2]=attributes;observed[3]=alignment;return memory?9:2;
}
int main(int argc,char**) {
    if(desiredBytes(DefaultPoolReturnRva,nullptr,10*1024*1024,64,1)!=PoolBudget)return 1;
    if(desiredBytes(DefaultPoolReturnRva,nullptr,64*1024*1024,64,1)!=64*1024*1024)return 2;
    if(desiredBytes(DefaultPoolReturnRva-1,nullptr,10*1024*1024,64,1)!=10*1024*1024)return 3;
    if(desiredBytes(DefaultPoolReturnRva,(void*)1,10*1024*1024,64,1)!=10*1024*1024)return 4;
    if(desiredBytes(DefaultPoolReturnRva,nullptr,10*1024*1024,32,1)!=10*1024*1024)return 5;
    if(desiredBytes(DefaultPoolReturnRva,nullptr,10*1024*1024,64,9)!=10*1024*1024)return 6;
    originalCreatePool=fakeCreate;
    if(createPoolHook(nullptr,100,64,1,16)!=2||observed[0]!=100||observed[1]!=64||observed[2]!=1||observed[3]!=16)return 7;
    if(argc>1){
        HMODULE proxy=LoadLibraryW(L".\\winmm.dll");if(!proxy)return 8;
        auto time=(DWORD(WINAPI*)())GetProcAddress(proxy,"timeGetTime");
        auto begin=(UINT(WINAPI*)(UINT))GetProcAddress(proxy,"timeBeginPeriod");
        auto end=(UINT(WINAPI*)(UINT))GetProcAddress(proxy,"timeEndPeriod");
        if(!time||!begin||!end||!time()||begin(1)||end(1))return 9;
        FreeLibrary(proxy);
    }
    printf("PASS: exact default-pool scope, larger native budgets preserved, unrelated pools unchanged, pool ID/alignment forwarding and Windows timer exports.\n");return 0;
}
#endif
