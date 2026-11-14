using System;
using System.IO;
using System.Linq;
using System.Text;
using System.Drawing;
using System.Diagnostics;
using System.Collections.Generic;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace Dmc5SwitchLauncher
{
    // The desktop frontend uses the release's verified manifest/engine, never
    // the historical launcher's embedded runtime or ModInstaller backend.
    public sealed class DesktopLauncher : Form
    {
        readonly string home;
        bool english, busy, loading;
        int capture = -1;
        readonly TextBox path = new TextBox();
        readonly ComboBox[] keys = new ComboBox[5], pads = new ComboBox[5];
        readonly Button[] record = new Button[5];
        readonly CheckBox controller = new CheckBox();
        readonly TextBox log = new TextBox();
        readonly Dictionary<Control, string[]> translations = new Dictionary<Control, string[]>();
        readonly Button language = new Button();
        readonly string languageFile = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DMC5CharacterSwitchLauncher", "language.txt");
        string T(string zh, string en) { return english ? en : zh; }
        void Register(Control c, string zh, string en) { translations[c] = new[] { zh, en }; c.Text = T(zh, en); }
        Label LabelAt(string zh, string en, int x, int y, int width)
        {
            var c = new Label { Location = new Point(x,y), Size = new Size(width,25), ForeColor = Color.FromArgb(218,224,235) };
            Register(c,zh,en); Controls.Add(c); return c;
        }
        Button ButtonAt(string zh, string en, int x, int y, int width, EventHandler action)
        {
            var b = new Button { Location = new Point(x,y), Size = new Size(width,36), FlatStyle = FlatStyle.Flat,
                BackColor = Color.FromArgb(45,58,78), ForeColor = Color.White };
            Register(b,zh,en); b.Click += action; Controls.Add(b); return b;
        }
        public DesktopLauncher(string folder)
        {
            home = folder;
            english = !System.Globalization.CultureInfo.CurrentUICulture.Name.StartsWith("zh");
            try { if (File.Exists(languageFile)) english = File.ReadAllText(languageFile).Trim()=="en"; } catch { }
            Text = "DMC5 Character Switch 1.0.0"; Font = new Font("Microsoft YaHei UI",10);
            BackColor = Color.FromArgb(22,28,39); ForeColor = Color.White;
            ClientSize = new Size(900,720); MinimumSize = new Size(916,759);
            AutoScroll = true; AutoScaleMode = AutoScaleMode.Dpi; StartPosition = FormStartPosition.CenterScreen; KeyPreview = true;
            var title = LabelAt("鬼泣 5 · 切人管理器", "DMC5 · Character Switch",24,20,600); title.Font = new Font(Font.FontFamily,18,FontStyle.Bold); title.Height=38;
            LabelAt("1.0.0  |  包含 3S、声音池与最新角色修复", "1.0.0  |  Includes 3S, audio pool and character fixes",24,63,820);
            language.Location=new Point(724,20); language.Size=new Size(150,36); language.Text="中文 / English"; language.Click += delegate { SetLanguage(!english, true); }; Controls.Add(language);
            LabelAt("游戏目录", "Game folder",24,108,150);
            path.Location=new Point(24,138);path.Size=new Size(672,28);Controls.Add(path);
            ButtonAt("浏览…","Browse…",710,134,164,delegate { Browse(); });
            ButtonAt("安装 / 更新","Install / Update",24,184,204,delegate { RunEngine("Install"); });
            ButtonAt("恢复安装前文件","Restore previous files",240,184,204,delegate { RunEngine("Restore"); });
            ButtonAt("导出诊断 ZIP","Export diagnostics",456,184,204,delegate { RunEngine("Collect"); });
            ButtonAt("启动游戏","Launch game",672,184,202,delegate { Launch(); });
            LabelAt("动作", "Action",24,244,145);LabelAt("键盘快捷键", "Keyboard",180,244,270);LabelAt("挑衅 + 手柄副键", "Taunt + controller button",532,244,340);
            string[] zh={"下一角色","上一角色","尼禄","但丁","维吉尔"}, en={"Next","Previous","Nero","Dante","Vergil"};
            for(int i=0;i<5;i++) {
                int slot=i,y=280+i*43;LabelAt(zh[i],en[i],24,y+5,150);
                keys[i]=new ComboBox { ForeColor=Color.Black,BackColor=Color.White,DropDownStyle=ComboBoxStyle.DropDownList, Location=new Point(180,y),Size=new Size(188,30) };Controls.Add(keys[i]);
                DrawCombo(keys[i]);
                record[i]=ButtonAt("录入按键","Capture key",382,y-2,132,delegate { capture=slot;Log(T("请按单个键；Esc 取消。","Press one key; Esc cancels.")); });
                pads[i]=new ComboBox { ForeColor=Color.Black,BackColor=Color.White,DropDownStyle=ComboBoxStyle.DropDownList,Location=new Point(532,y),Size=new Size(342,30) };
                pads[i].Items.AddRange(Bindings.PadChoices);DrawCombo(pads[i]);Controls.Add(pads[i]);
            }
            controller.Location=new Point(24,502);controller.Size=new Size(850,26);Register(controller,"启用手柄组合键（挑衅 + 所选副键）","Enable controller combinations (Taunt + selected button)");Controls.Add(controller);
            ButtonAt("恢复默认按键","Default bindings",24,540,204,delegate { SetBindings(Defaults()); });
            ButtonAt("重新读取配置","Reload settings",240,540,204,delegate { LoadBindings(); });
            ButtonAt("保存快捷键","Save bindings",456,540,204,delegate { SaveBindings(); });
            ButtonAt("保存并启动","Save && launch",672,540,202,delegate { if(SaveBindings())Launch(); });
            log.Location=new Point(24,596);log.Size=new Size(850,100);log.Multiline=true;log.ReadOnly=true;log.ScrollBars=ScrollBars.Vertical;
            log.BackColor=Color.FromArgb(15,20,29);log.ForeColor=Color.FromArgb(191,211,236);Controls.Add(log);
            path.Leave += delegate { if(!busy && !loading)LoadBindings(); };
            FormClosing += delegate(object sender,FormClosingEventArgs e) { if(busy)e.Cancel=true; };
            RefreshKeys(null);path.Text=Game.Find();LoadBindings();
        }
        static Bindings Defaults() { return new Bindings { Next=116,Previous=117 }; }
        static void DrawCombo(ComboBox box)
        {
            box.DrawMode=DrawMode.OwnerDrawFixed;box.ItemHeight=24;
            box.DrawItem+=delegate(object sender,DrawItemEventArgs e) {
                e.DrawBackground();int index=e.Index>=0?e.Index:box.SelectedIndex;
                if(index>=0)TextRenderer.DrawText(e.Graphics,box.Items[index].ToString(),box.Font,e.Bounds,Color.Black,TextFormatFlags.Left|TextFormatFlags.VerticalCenter);
                e.DrawFocusRectangle();
            };
        }
        void Log(string message) { log.Text=message; }
        string KeyName(int code)
        {
            if(code==0)return T("停用","Disabled");
            if(!english)return KeyCatalog.Name(code);
            if(code>=96 && code<=105)return "Numpad "+(code-96);
            return ((Keys)code).ToString();
        }
        void RefreshKeys(int[] values)
        {
            for(int i=0;i<5;i++) {
                keys[i].Items.Clear();if(i>=2)keys[i].Items.Add(new KeyChoice(0,KeyName(0)));
                foreach(var k in KeyCatalog.All())keys[i].Items.Add(new KeyChoice(k.Code,KeyName(k.Code)));
                Select(keys[i],values==null ? new[]{116,117,118,119,120}[i] : values[i]);
            }
        }
        static void Select(ComboBox box,int value) { foreach(KeyChoice k in box.Items)if(k.Code==value){box.SelectedItem=k;return;} }
        public void SetLanguage(bool en,bool persist)
        {
            int[] values=keys.Select(k=>k.SelectedItem==null?0:((KeyChoice)k.SelectedItem).Code).ToArray();
            english=en;foreach(var item in translations)item.Key.Text=item.Value[english?1:0];RefreshKeys(values);
            capture=-1;Log(T("语言已切换，尚未保存的按键选择保留。","Language changed. Unsaved binding selections are preserved."));
            if(persist)try{Directory.CreateDirectory(Path.GetDirectoryName(languageFile));File.WriteAllText(languageFile,english?"en":"zh");}catch{ }
        }
        void SetBindings(Bindings b)
        {
            int[] values={b.Next,b.Previous,b.Nero,b.Dante,b.Vergil};string[] buttons={b.PadPrevious,b.PadNext,b.PadNero,b.PadDante,b.PadVergil};
            for(int i=0;i<5;i++){Select(keys[i],values[i]);pads[i].SelectedItem=buttons[i];}controller.Checked=b.ControllerCombo;
        }
        Bindings ReadBindings()
        {
            int[] k=keys.Select(x=>((KeyChoice)x.SelectedItem).Code).ToArray();string[] p=pads.Select(x=>(string)x.SelectedItem).ToArray();
            if(k.Where(x=>x!=0).Distinct().Count()!=k.Count(x=>x!=0))throw new Exception(T("键盘快捷键不能重复。","Keyboard bindings must be unique."));
            if(p.Where(x=>x!="None").Distinct().Count()!=p.Count(x=>x!="None"))throw new Exception(T("手柄副键不能重复。","Controller buttons must be unique."));
            var b=new Bindings {Next=k[0],Previous=k[1],Nero=k[2],Dante=k[3],Vergil=k[4],PadPrevious=p[0],PadNext=p[1],PadNero=p[2],PadDante=p[3],PadVergil=p[4],ControllerCombo=controller.Checked};b.Validate();return b;
        }
        string Root()
        {
            if(String.IsNullOrWhiteSpace(path.Text)||(!File.Exists(Path.Combine(path.Text,"DevilMayCry5.exe"))&&!File.Exists(path.Text)))throw new Exception(T("请选择包含 DevilMayCry5.exe 的游戏目录。","Select the folder containing DevilMayCry5.exe."));
            return Game.Root(path.Text);
        }
        void LoadBindings()
        {
            loading=true;capture=-1;
            try {
                string file=ConfigStore.ConfigPath(Root()),warning;
                SetBindings(File.Exists(file)?ConfigStore.Load(file,out warning):Defaults());
                // Re-read warning explicitly because the missing-file branch has none.
                warning=null;if(File.Exists(file))ConfigStore.Load(file,out warning);
                Log(warning==null?T("快捷键已读取。更改后点击保存；F10 标记诊断现场。","Bindings loaded. Save changes to apply; F10 marks diagnostics."):T("配置读取异常，已显示默认值；保存将修复配置。","Could not read settings. Defaults shown; saving repairs the configuration."));
            }catch(Exception ex){SetBindings(Defaults());Log(ex.Message);}finally{loading=false;}
        }
        void Browse()
        {
            using(var picker=new OpenFileDialog {Title=T("选择鬼泣5游戏程序","Select the game executable"),Filter="Devil May Cry 5|DevilMayCry5.exe"})
                if(picker.ShowDialog(this)==DialogResult.OK){path.Text=Path.GetDirectoryName(picker.FileName);LoadBindings();}
        }
        bool SaveBindings()
        {
            try {string root=Root();ConfigStore.Save(ConfigStore.ConfigPath(root),ReadBindings());try{Game.Remember(root);}catch{ }
                Log(T("快捷键已保存，下次启动游戏时生效。","Bindings saved. They take effect on the next game start."));return true;
            }catch(Exception ex){Log(ex.Message);return false;}
        }
        void Launch()
        {
            try {Root();if(Game.Running())throw new Exception(T("游戏已在运行。","The game is already running."));Process.Start(new ProcessStartInfo("steam://rungameid/601150"){UseShellExecute=true});Log(T("已请求 Steam 启动游戏。","Launch requested through Steam."));}catch(Exception ex){Log(ex.Message);}
        }
        public static string InvokeEngine(string folder,string root,string mode,bool english)
        {
            if(mode!="Install"&&mode!="Restore"&&mode!="Collect")throw new ArgumentException("Invalid operation");
            var start=new ProcessStartInfo(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),@"WindowsPowerShell\v1.0\powershell.exe"));
            start.Arguments="-NoProfile -ExecutionPolicy Bypass -File \""+Path.Combine(folder,"Engine.ps1")+"\" -GamePath \""+root.TrimEnd('\\')+"\" -Mode "+mode+" -Language "+(english?"en":"zh");
            start.UseShellExecute=false;start.CreateNoWindow=true;start.RedirectStandardOutput=true;start.RedirectStandardError=true;
            start.StandardOutputEncoding=Encoding.UTF8;start.StandardErrorEncoding=Encoding.UTF8;
            start.EnvironmentVariables["PSModulePath"]=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),@"WindowsPowerShell\v1.0\Modules");
            using(var process=Process.Start(start)) {
                var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();process.WaitForExit();
                string text=output.Result+error.Result;if(process.ExitCode!=0)throw new Exception(text);return text;
            }
        }
        async void RunEngine(string mode)
        {
            try {
                string root=Root();bool en=english;busy=true;capture=-1;
                foreach(Control c in Controls)if(c!=log)c.Enabled=false;
                Log(T("正在处理，请稍候…","Working, please wait…"));
                string result=await Task.Run(()=>InvokeEngine(home,root,mode,en));Log(result);try{Game.Remember(root);}catch{ }
            }catch(Exception ex){Log(T("操作未完成：\r\n","Operation failed:\r\n")+ex.Message);}
            finally{busy=false;foreach(Control c in Controls)c.Enabled=true;}
        }
        protected override bool ProcessCmdKey(ref Message msg,Keys keyData)
        {
            if(capture<0)return base.ProcessCmdKey(ref msg,keyData);
            if(keyData==Keys.Escape){capture=-1;return true;}
            int code=(int)(keyData&Keys.KeyCode);
            if((keyData&Keys.Modifiers)!=Keys.None||!KeyCatalog.Valid(code)){Log(T("请使用单个按键，Insert 留给 REFramework。","Use a single key; Insert is reserved for REFramework."));return true;}
            Select(keys[capture],code);capture=-1;Log(T("按键已选，请保存。","Key selected. Save to apply."));return true;
        }
        public void TestAndRender(string output)
        {
            SetBindings(new Bindings {Next=116,Previous=117,PadPrevious="LT",PadNext="RT"});
            SetLanguage(false,false);Show();Application.DoEvents();using(var b=new Bitmap(Width,Height)){DrawToBitmap(b,new Rectangle(0,0,Width,Height));b.Save(Path.Combine(output,"launcher-zh.png"));}
            SetLanguage(true,false);Application.DoEvents();var selected=ReadBindings();
            if(selected.Next!=116||selected.PadPrevious!="LT"||selected.PadNext!="RT")throw new Exception("Language switch lost bindings");
            if(translations.Any(t=>t.Key.Text!=t.Value[1]))throw new Exception("Untranslated control");
            using(var b=new Bitmap(Width,Height)){DrawToBitmap(b,new Rectangle(0,0,Width,Height));b.Save(Path.Combine(output,"launcher-en.png"));}
            Select(keys[1],116);bool rejected=false;try{ReadBindings();}catch{rejected=true;}if(!rejected)throw new Exception("Duplicate key accepted");
            Hide();File.WriteAllText(Path.Combine(output,"gui-tests.txt"),"PASS: zh/en controls, unsaved keys and controller bindings preserved, duplicates rejected; rendered both languages.");
        }
    }
    public static class DesktopProgram
    {
        [STAThread] public static int Main(string[] args)
        {
            Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
            using(var form=new DesktopLauncher(AppDomain.CurrentDomain.BaseDirectory)) {
                if(args.Length==2&&args[0]=="--ui-test"){Directory.CreateDirectory(args[1]);form.TestAndRender(args[1]);return 0;}
                Application.Run(form);return 0;
            }
        }
    }
}
