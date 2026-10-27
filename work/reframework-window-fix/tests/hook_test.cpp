
#include <Windows.h>
#include <chrono>
#include <memory>
#include <iostream>
#include <stdexcept>
#include "WindowsMessageHook.hpp"
static int nativeCalls=0, outerCalls=0;
static WNDPROC outerNext=nullptr;
static constexpr UINT testMessage=WM_APP+61;
void check(bool b,const char* why){if(!b)throw std::runtime_error(why);}
LRESULT CALLBACK gameProc(HWND w,UINT m,WPARAM a,LPARAM b){
 if(m==testMessage || m==testMessage+1){++nativeCalls;return 0x1234;}
 return DefWindowProc(w,m,a,b);
}
LRESULT CALLBACK outerProc(HWND w,UINT m,WPARAM a,LPARAM b){
 if(m==testMessage || m==testMessage+1)++outerCalls;
 return CallWindowProc(outerNext,w,m,a,b);
}
struct TestFramework {
 HWND m_wnd=nullptr;bool m_first_frame=true,m_message_hook_requested=false;
 std::unique_ptr<WindowsMessageHook> m_windows_message_hook;
 std::chrono::steady_clock::time_point m_last_message_time;
 int callbackCalls=0;bool nested=false;
 bool on_message(HWND w,UINT m,WPARAM,LPARAM){
  if(m==testMessage||m==testMessage+1)++callbackCalls;
  if(nested&&m==testMessage)SendMessage(w,testMessage+1,0,0);
  return true;
 }
 bool legacy_initialize();bool initialize();
};
#include "extracted-initializers.inc"
HWND makeWindow(){return CreateWindowEx(0,L"RFChainTest",L"",0,0,0,0,0,HWND_MESSAGE,nullptr,GetModuleHandle(nullptr),nullptr);}
int main(){try{
 WNDCLASS wc{};wc.lpfnWndProc=gameProc;wc.hInstance=GetModuleHandle(nullptr);wc.lpszClassName=L"RFChainTest";
 check(RegisterClass(&wc)!=0,"register class");
 // Reproduce the old chain corruption without dispatching the recursive chain.
 {
  TestFramework f;f.m_wnd=makeWindow();check(f.m_wnd!=nullptr,"legacy window");
  check(f.legacy_initialize(),"legacy init");auto rfProc=(WNDPROC)GetWindowLongPtr(f.m_wnd,GWLP_WNDPROC);
  outerNext=rfProc;SetWindowLongPtr(f.m_wnd,GWLP_WNDPROC,(LONG_PTR)outerProc);
  f.m_first_frame=false;f.m_message_hook_requested=true;f.legacy_initialize();
  check(f.m_windows_message_hook->get_original()==outerProc&&outerNext==rfProc,"legacy cycle must reproduce");
  f.m_windows_message_hook.reset();SetWindowLongPtr(f.m_wnd,GWLP_WNDPROC,(LONG_PTR)gameProc);DestroyWindow(f.m_wnd);
 }
 std::cout<<"PASS: old initializer constructs RF -> external -> RF cycle\n";
 {
  TestFramework f;check(!f.initialize(),"null HWND guarded");f.m_wnd=makeWindow();check(f.m_wnd!=nullptr,"fixed window");
  check(f.initialize(),"fixed init");auto* identity=f.m_windows_message_hook.get();
  check(identity->get_original()==gameProc,"native original");
  outerNext=(WNDPROC)GetWindowLongPtr(f.m_wnd,GWLP_WNDPROC);
  SetWindowLongPtr(f.m_wnd,GWLP_WNDPROC,(LONG_PTR)outerProc);
  check(!identity->is_hook_intact(),"external wrapper on top");
  check(identity->is_valid_for(f.m_wnd),"wrapped registration valid");
  check(!identity->is_valid_for(nullptr),"null window excluded");
  HWND other=makeWindow();check(!identity->is_valid_for(other),"different HWND excluded");DestroyWindow(other);
  nativeCalls=outerCalls=0;
  for(int i=0;i<10000;i++){
   f.m_first_frame=i<10;f.m_message_hook_requested=true;
   check(f.initialize(),"retry handled");
   check(f.m_windows_message_hook.get()==identity,"object identity preserved");
   check(identity->get_original()==gameProc,"original link preserved");
   check((WNDPROC)GetWindowLongPtr(f.m_wnd,GWLP_WNDPROC)==outerProc,"outer hook untouched");
   check(!f.m_message_hook_requested,"request consumed");
   check(SendMessage(f.m_wnd,testMessage,0,0)==0x1234,"native return preserved");
  }
  check(nativeCalls==10000&&outerCalls==10000&&f.callbackCalls==10000,"exactly one delivery per message");
  f.nested=true;SendMessage(f.m_wnd,testMessage,0,0);
  check(nativeCalls==10002&&outerCalls==10002&&f.callbackCalls==10002,"legitimate nested messages preserved");
  SetWindowLongPtr(f.m_wnd,GWLP_WNDPROC,(LONG_PTR)outerNext);f.m_windows_message_hook.reset();
  check((WNDPROC)GetWindowLongPtr(f.m_wnd,GWLP_WNDPROC)==gameProc,"native chain restored on teardown");DestroyWindow(f.m_wnd);
 }
 std::cout<<"PASS: 10000 watchdog retries, native/external/RF callbacks and return values, first frame, nested messages, HWND and teardown guards\n";
 return 0;
}catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 1;}}
