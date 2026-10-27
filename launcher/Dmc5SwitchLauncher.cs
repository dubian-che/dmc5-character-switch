using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.RegularExpressions;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: System.Reflection.AssemblyTitle("鬼泣5 切人Mod 正式版")]
[assembly: System.Reflection.AssemblyProduct("DMC5 Character Switch")]
[assembly: System.Reflection.AssemblyVersion("0.0.1.0")]
[assembly: System.Reflection.AssemblyFileVersion("0.0.1.0")]
#if SUPPORT_DIAGNOSTICS
[assembly: System.Reflection.AssemblyInformationalVersion("pre-0.0.1+release-47.support-47.1")]
#else
[assembly: System.Reflection.AssemblyInformationalVersion("pre-0.0.1+release-47-scripted-movement-guard")]
#endif

namespace Dmc5SwitchLauncher
{
    public sealed class KeyChoice
    {
        public int Code;
        public string Name;
        public KeyChoice(int code, string name) { Code = code; Name = name; }
        public override string ToString() { return Name; }
    }

    public static class KeyCatalog
    {
        public static bool Valid(int k)
        {
            return k == 8 || k == 9 || k == 13 || k == 19 || k == 20 ||
                (k >= 32 && k <= 40) || k == 46 || (k >= 48 && k <= 57) ||
                (k >= 65 && k <= 90) || (k >= 96 && k <= 111) || (k >= 112 && k <= 135) ||
                k == 144 || k == 145 || (k >= 186 && k <= 192) || (k >= 219 && k <= 222);
        }
        public static string Name(int k)
        {
            if (k >= 112 && k <= 135) return "F" + (k - 111);
            if ((k >= 48 && k <= 57) || (k >= 65 && k <= 90)) return ((char)k).ToString();
            if (k >= 96 && k <= 105) return "小键盘 " + (k - 96);
            switch (k)
            {
                case 8: return "Backspace"; case 9: return "Tab"; case 13: return "Enter";
                case 19: return "Pause"; case 20: return "Caps Lock"; case 32: return "空格";
                case 33: return "Page Up"; case 34: return "Page Down"; case 35: return "End";
                case 36: return "Home"; case 37: return "← 左"; case 38: return "↑ 上";
                case 39: return "→ 右"; case 40: return "↓ 下"; case 46: return "Delete";
                case 106: return "小键盘 *"; case 107: return "小键盘 +"; case 108: return "小键盘 分隔符";
                case 109: return "小键盘 -"; case 110: return "小键盘 ."; case 111: return "小键盘 /";
                case 144: return "Num Lock"; case 145: return "Scroll Lock";
                case 186: return "; 分号"; case 187: return "= 等号"; case 188: return ", 逗号";
                case 189: return "- 减号"; case 190: return ". 句号"; case 191: return "/ 斜线";
                case 192: return "` 反引号"; case 219: return "[ 左方括号";
                case 220: return "\\ 反斜线"; case 221: return "] 右方括号"; case 222: return "' 引号";
            }
            return "VK " + k.ToString("X2");
        }
        public static List<KeyChoice> All()
        {
            var result = new List<KeyChoice>();
            for (int k = 112; k <= 135; k++) result.Add(new KeyChoice(k, Name(k)));
            for (int k = 0; k < 256; k++)
                if (Valid(k) && !(k >= 112 && k <= 135)) result.Add(new KeyChoice(k, Name(k)));
            return result;
        }
    }

    public sealed class Bindings
    {
        public int Next = 128;
        public int Previous = 129;
        public bool ControllerCombo = true;
        public void Validate()
        {
            if (!KeyCatalog.Valid(Next) || !KeyCatalog.Valid(Previous))
                throw new InvalidDataException("请选择有效的单个键。Insert 留给 REFramework 面板使用。");
            if (Next == Previous) throw new InvalidDataException("下一位和上一位不能使用同一个键。");
        }
    }

    public static class ConfigStore
    {
        public static readonly JavaScriptSerializer Json = new JavaScriptSerializer();
        public static string ConfigPath(string root) { return Path.Combine(root, "reframework", "data", "dmc5_switch_config.json"); }
        public static int Number(Dictionary<string, object> data, string name, int fallback)
        {
            object value;
            if (!data.TryGetValue(name, out value)) return fallback;
            if (value == null || value is bool || value is string) throw new InvalidDataException("配置中的按键格式无效。");
            double number = Convert.ToDouble(value, CultureInfo.InvariantCulture);
            if (double.IsNaN(number) || number != Math.Truncate(number) || number < 0 || number > 1000)
                throw new InvalidDataException("配置中的按键数值无效。");
            return (int)number;
        }
        public static Bindings Load(string path, out string warning)
        {
            warning = null;
            if (!File.Exists(path)) return new Bindings();
            try
            {
                var data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path, Encoding.UTF8));
                if (data == null || Number(data, "version", 1) != 1) throw new InvalidDataException("配置版本不支持。");
                var result = new Bindings { Next = Number(data, "nextKey", 128), Previous = Number(data, "previousKey", 129) };
                object combo;
                if (data.TryGetValue("controllerCombo", out combo))
                {
                    if (!(combo is bool)) throw new InvalidDataException("手柄开关格式无效。");
                    result.ControllerCombo = (bool)combo;
                }
                result.Validate();
                return result;
            }
            catch (Exception ex)
            {
                warning = "配置无法读取，已显示默认按键。点击保存后修复。" + ex.Message;
                return new Bindings();
            }
        }
        public static void AtomicWrite(string path, string text)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                File.WriteAllText(temp, text, new UTF8Encoding(false));
                if (File.Exists(path)) File.Replace(temp, path, path + ".bak", true);
                else File.Move(temp, path);
            }
            finally { if (File.Exists(temp)) File.Delete(temp); }
        }
        public static void Save(string path, Bindings bindings)
        {
            bindings.Validate();
            var data = new Dictionary<string, object>();
            if (File.Exists(path))
            {
                try { data = Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(path, Encoding.UTF8)) ?? data; }
                catch (ArgumentException) { }
                catch (InvalidOperationException) { }
            }
            data["version"] = 1; data["nextKey"] = bindings.Next;
            data["previousKey"] = bindings.Previous; data["controllerCombo"] = bindings.ControllerCombo;
            AtomicWrite(path, Json.Serialize(data));
        }
    }

    public static class Game
    {
        public static string PreferencesPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "DMC5CharacterSwitchLauncher", "settings.json");
        public static string Root(string path)
        {
            if (String.IsNullOrWhiteSpace(path)) throw new InvalidDataException("请选择鬼泣 5 的游戏目录。");
            string root = Path.GetFullPath(path.Trim().Trim('"'));
            if (File.Exists(root) && String.Equals(Path.GetFileName(root), "DevilMayCry5.exe", StringComparison.OrdinalIgnoreCase)) root = Path.GetDirectoryName(root);
            if (!File.Exists(Path.Combine(root, "DevilMayCry5.exe"))) throw new InvalidDataException("这个目录里没有 DevilMayCry5.exe，请重新选择。");
            return root;
        }
        public static bool Running()
        {
            var processes = Process.GetProcessesByName("DevilMayCry5");
            bool running = processes.Length > 0;
            foreach (var p in processes) p.Dispose();
            return running;
        }
        public static string ModProblem(string root)
        {
            if (!File.Exists(Path.Combine(root, "dinput8.dll"))) return "未找到 REFramework（dinput8.dll），请先安装 DMC5 版 REFramework。";
            if (!File.Exists(Path.Combine(root, "reframework", "autorun", "dmc5_live_switch.lua"))) return "未找到切人 Mod，请先安装我们的 Mod 文件。";
            string keys = Path.Combine(root, "reframework", "data", "dmc5_switch_keys.lua");
            if (!File.Exists(keys) || !File.ReadAllText(keys).Contains("dmc5_switch_config.json")) return "切人 Mod 版本较旧，请安装支持启动器的新版。";
            foreach (string name in new [] { "core", "hud", "controller", "lifecycle", "progression", "regen", "resources", "voice", "runtime", "loader", "input_menu" })
                if (!File.Exists(Path.Combine(root, "reframework", "data", "dmc5_switch_" + name + ".lua"))) return "切人 Mod 文件不完整，请重新安装。";
            if (!File.Exists(Path.Combine(root, "reframework", "data", "dmc5_party_hud.lua"))) return "缺少队伍界面模块，请重新安装 Mod。";
            return null;
        }
        public static ProcessStartInfo StartInfo(string root)
        {
            return new ProcessStartInfo(Path.Combine(Root(root), "DevilMayCry5.exe")) { WorkingDirectory = root, UseShellExecute = true };
        }
        public static string Find()
        {
            var candidates = new List<string>();
            try
            {
                if (File.Exists(PreferencesPath))
                {
                    var saved = ConfigStore.Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(PreferencesPath));
                    object root; if (saved != null && saved.TryGetValue("gameRoot", out root)) candidates.Add(root as string);
                }
            }
            catch { }
            candidates.Add(AppDomain.CurrentDomain.BaseDirectory);
            candidates.Add(Path.GetDirectoryName(AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar)));
            var steamRoots = new List<string>();
            using (var key = Registry.CurrentUser.OpenSubKey(@"Software\Valve\Steam"))
                if (key != null) steamRoots.Add(key.GetValue("SteamPath") as string);
            steamRoots.Add(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), "Steam"));
            foreach (string steam in steamRoots)
            {
                if (String.IsNullOrWhiteSpace(steam)) continue;
                candidates.Add(Path.Combine(steam, "steamapps", "common", "Devil May Cry 5"));
                try
                {
                    string libraries = Path.Combine(steam, "steamapps", "libraryfolders.vdf");
                    if (!File.Exists(libraries)) continue;
                    foreach (Match match in Regex.Matches(File.ReadAllText(libraries), "\"path\"\\s+\"([^\"]+)\""))
                        candidates.Add(Path.Combine(match.Groups[1].Value.Replace(@"\\", @"\"), "steamapps", "common", "Devil May Cry 5"));
                }
                catch (IOException) { }
                catch (UnauthorizedAccessException) { }
            }
            foreach (string candidate in candidates)
            {
                try { return Root(candidate); } catch { }
            }
            return "";
        }
        public static void Remember(string root)
        {
            ConfigStore.AtomicWrite(PreferencesPath, ConfigStore.Json.Serialize(new Dictionary<string, object> { { "gameRoot", root } }));
        }
    }

    public sealed class LauncherForm : Form
    {
        static readonly Color Background = Color.FromArgb(16, 21, 30);
        static readonly Color Card = Color.FromArgb(27, 35, 48);
        static readonly Color Muted = Color.FromArgb(157, 173, 195);
        static readonly Color Accent = Color.FromArgb(92, 203, 246);
        TextBox gamePath;
        ComboBox next, previous;
        CheckBox controller;
        Label status;
        Button save, launch, captureNext, capturePrevious;
        int capturing;
        bool initialized;
        string loadedPath;

        public LauncherForm()
        {
            SuspendLayout();
            #if SUPPORT_DIAGNOSTICS
            Text = "鬼泣5 切人启动器 · pre-0.0.1 远端诊断版";
#else
            Text = "鬼泣5 切人启动器 · pre-0.0.1";
#endif
            AutoScaleMode = AutoScaleMode.None;
            ClientSize = new Size(860, 692);
            FormBorderStyle = FormBorderStyle.FixedSingle; MaximizeBox = false;
            StartPosition = FormStartPosition.Manual;
            BackColor = Background; ForeColor = Color.White;
            Font = new Font("Microsoft YaHei UI", 10F); KeyPreview = true;
            AddLabel(this, "鬼泣 5  /  切人启动器", 28, 22, 800, 38, 22F, Color.White);
            AddLabel(this, "启动前设置双向切换按键，设置会自动保留。", 30, 68, 800, 26, 10F, Muted);

            Panel pathCard = PanelAt(28, 110, 804, 104);
            AddLabel(pathCard, "游戏目录", 18, 10, 650, 26, 11F, Color.White);
            gamePath = new TextBox { Location = new Point(18, 48), Size = new Size(660, 30), BorderStyle = BorderStyle.FixedSingle,
                BackColor = Background, ForeColor = Color.White, Font = new Font("Segoe UI", 10F), AccessibleName = "游戏目录" };
            pathCard.Controls.Add(gamePath);
            Button browse = MakeButton(pathCard, "浏览…", 690, 44, 96, 38, false);
            browse.Click += delegate { Browse(); };
            gamePath.Leave += delegate { if (initialized && !String.Equals(gamePath.Text, loadedPath, StringComparison.OrdinalIgnoreCase)) LoadBindings(); };

            Panel forward = PanelAt(28, 234, 392, 144);
            Panel backward = PanelAt(440, 234, 392, 144);
            AddLabel(forward, "下一位  →", 18, 12, 350, 28, 13F, Accent);
            AddLabel(backward, "←  上一位", 18, 12, 350, 28, 13F, Accent);
            next = MakeCombo(forward, "下一位按键"); previous = MakeCombo(backward, "上一位按键");
            captureNext = MakeButton(forward, "按键录入", 246, 54, 128, 40, false);
            capturePrevious = MakeButton(backward, "按键录入", 246, 54, 128, 40, false);
            captureNext.Click += delegate { BeginCapture(1); };
            capturePrevious.Click += delegate { BeginCapture(-1); };
            AddLabel(forward, "尼禄 → 但丁 → 维吉尔", 18, 106, 355, 25, 9F, Muted);
            AddLabel(backward, "沿相反方向循环切换", 18, 106, 355, 25, 9F, Muted);
            controller = new CheckBox { Text = "启用手柄切人：按住挑衅 + LB 上一位 / RB 下一位", Location = new Point(30, 394), Size = new Size(800, 30), Checked = true, AccessibleName = "启用手柄切人" };
            Controls.Add(controller);
            AddLabel(this, "背键映射为键盘键时，请与这里的设置保持一致。支持单键与 F1–F24。", 30, 432, 800, 27, 9F, Muted);
            Button install = MakeButton(this, "安装 / 更新 Mod", 28, 478, 192, 42, false);
            Button uninstall = MakeButton(this, "卸载 Mod", 234, 478, 152, 42, false);
            install.Click += delegate { ManageMod(true); };
            uninstall.Click += delegate { ManageMod(false); };
            AddLabel(this, "安装前自动备份；卸载保留按键设置。\n请先退出游戏再安装或卸载。", 408, 476, 420, 48, 9F, Muted);
            status = AddLabel(this, "", 30, 540, 798, 72, 10F, Muted);
#if SUPPORT_DIAGNOSTICS
            install.Text = "安装 / 更新诊断版";
            foreach (Control item in Controls) {
                var label = item as Label;
                if (label != null && label.Top == 22) { label.Text = "鬼泣 5  /  远端诊断"; label.Font = new Font("Microsoft YaHei UI", 17F); }
                if (label != null && label.Top == 68) label.Text = "安装诊断版后重启游戏；故障时 F8 标记，再导出桌面 ZIP。";
            }
            status.Location = new Point(30, 578); status.Size = new Size(798, 42);
            var export = MakeButton(this, "导出最近30分钟 ZIP", 28, 532, 300, 36, true);
            var stop = MakeButton(this, "停止诊断记录", 342, 532, 192, 36, false);
            AddLabel(this, "F8：标记现场并立即保存", 552, 539, 280, 27, 9F, Muted);
            export.Click += delegate {
                try { SupportUi.Export(this, Game.Root(gamePath.Text), Message); }
                catch (Exception ex) { Message("未完成：" + ex.Message, true); }
            };
            stop.Click += delegate {
                try { Message(SupportRecorder.Set(Game.Root(gamePath.Text), false), false); }
                catch (Exception ex) { Message("未完成：" + ex.Message, true); }
            };
#endif
            Button defaults = MakeButton(this, "恢复 F17 / F18", 28, 628, 174, 42, false);
            defaults.Click += delegate { EndCapture(); SelectKey(next, 128); SelectKey(previous, 129); controller.Checked = true; ValidateChoices(); };
            save = MakeButton(this, "仅保存设置", 474, 628, 150, 42, false);
            launch = MakeButton(this, "保存并启动游戏", 640, 628, 192, 42, true);
            save.Click += delegate { Save(false); }; launch.Click += delegate { Save(true); };
            next.SelectedIndexChanged += delegate { if (initialized) ValidateChoices(); };
            previous.SelectedIndexChanged += delegate { if (initialized) ValidateChoices(); };
            gamePath.Text = Game.Find();
            initialized = true; LoadBindings();
            try { if (gamePath.Text.Length > 0) Icon = Icon.ExtractAssociatedIcon(Path.Combine(gamePath.Text, "DevilMayCry5.exe")); } catch { }
            AutoScaleDimensions = new SizeF(96F, 96F);
            AutoScaleMode = AutoScaleMode.Dpi;
            ResumeLayout(true);
            Shown += delegate {
                Rectangle area = Screen.PrimaryScreen.WorkingArea;
                Location = new Point(area.Left + Math.Max(0, (area.Width - Width) / 2), area.Top + Math.Max(0, (area.Height - Height) / 2));
            };
        }
        Panel PanelAt(int x, int y, int w, int h)
        {
            var panel = new Panel { Location = new Point(x, y), Size = new Size(w, h), BackColor = Card };
            Controls.Add(panel); return panel;
        }
        static Label AddLabel(Control parent, string text, int x, int y, int w, int h, float size, Color color)
        {
            var label = new Label { Text = text, Location = new Point(x, y), Size = new Size(w, h), ForeColor = color, Font = new Font("Microsoft YaHei UI", size), AutoEllipsis = true };
            parent.Controls.Add(label); return label;
        }
        static Button MakeButton(Control parent, string text, int x, int y, int w, int h, bool primary)
        {
            var button = new Button { Text = text, Location = new Point(x, y), Size = new Size(w, h), FlatStyle = FlatStyle.Flat,
                BackColor = primary ? Accent : Card, ForeColor = primary ? Background : Color.White, Cursor = Cursors.Hand, AccessibleName = text };
            button.FlatAppearance.BorderColor = primary ? Accent : Color.FromArgb(66, 83, 108);
            parent.Controls.Add(button); return button;
        }
        static ComboBox MakeCombo(Control parent, string name)
        {
            var combo = new ComboBox { Location = new Point(18, 56), Size = new Size(212, 36), DropDownStyle = ComboBoxStyle.DropDownList,
                Font = new Font("Microsoft YaHei UI", 13F), DropDownHeight = 300, AccessibleName = name };
            foreach (KeyChoice choice in KeyCatalog.All()) combo.Items.Add(choice);
            parent.Controls.Add(combo); return combo;
        }
        static void SelectKey(ComboBox combo, int code)
        {
            for (int i = 0; i < combo.Items.Count; i++) if (((KeyChoice)combo.Items[i]).Code == code) { combo.SelectedIndex = i; return; }
        }
        Bindings ReadChoices()
        {
            if (next.SelectedItem == null || previous.SelectedItem == null) throw new InvalidDataException("请选择两个切换按键。");
            var value = new Bindings { Next = ((KeyChoice)next.SelectedItem).Code, Previous = ((KeyChoice)previous.SelectedItem).Code, ControllerCombo = controller.Checked };
            value.Validate(); return value;
        }
        void Message(string text, bool error)
        {
            status.Text = text; status.ForeColor = error ? Color.FromArgb(255, 167, 158) : Muted;
        }
        void ValidateChoices()
        {
            try
            {
                ReadChoices(); save.Enabled = launch.Enabled = capturing == 0;
                Message(Game.Running() ? "游戏正在运行。可保存设置，下次启动游戏时生效。" : "设置将在下次启动时生效。游戏内仍使用各角色自己的操作配置。", false);
            }
            catch (Exception ex) { save.Enabled = launch.Enabled = false; Message(ex.Message, true); }
        }
        void LoadBindings()
        {
            EndCapture(); initialized = false;
            loadedPath = gamePath.Text;
            string warning = null;
            Bindings value = new Bindings();
            try { value = ConfigStore.Load(ConfigStore.ConfigPath(Game.Root(gamePath.Text)), out warning); }
            catch (Exception ex) { warning = ex.Message; }
            SelectKey(next, value.Next); SelectKey(previous, value.Previous); controller.Checked = value.ControllerCombo;
            initialized = true; ValidateChoices();
            if (warning != null) Message(warning, true);
        }
        void Browse()
        {
            EndCapture();
            using (var dialog = new OpenFileDialog { Title = "选择鬼泣 5 游戏程序", Filter = "Devil May Cry 5|DevilMayCry5.exe", CheckFileExists = true })
            {
                if (Directory.Exists(gamePath.Text)) dialog.InitialDirectory = gamePath.Text;
                if (dialog.ShowDialog(this) == DialogResult.OK) { gamePath.Text = Path.GetDirectoryName(dialog.FileName); LoadBindings(); }
            }
        }
        void BeginCapture(int direction)
        {
            capturing = direction; save.Enabled = launch.Enabled = false;
            captureNext.Text = direction == 1 ? "等待按键…" : "按键录入";
            capturePrevious.Text = direction == -1 ? "等待按键…" : "按键录入";
            Message("请按一个键；Esc 取消。F13–F24 也可直接从下拉列表选择。", false);
        }
        void EndCapture()
        {
            capturing = 0;
            if (captureNext != null) captureNext.Text = "按键录入";
            if (capturePrevious != null) capturePrevious.Text = "按键录入";
        }
        bool CaptureKey(Keys keyData)
        {
            int code = (int)(keyData & Keys.KeyCode);
            if (code == (int)Keys.Escape) { EndCapture(); ValidateChoices(); return true; }
            if ((keyData & Keys.Modifiers) != Keys.None || !KeyCatalog.Valid(code))
            { Message("请选择单个键，或从列表选择。Ctrl / Shift / Alt 组合键不作为切人键。", true); return true; }
            ComboBox target = capturing == 1 ? next : previous;
            EndCapture(); SelectKey(target, code); ValidateChoices(); return true;
        }
        protected override bool ProcessCmdKey(ref System.Windows.Forms.Message msg, Keys keyData)
        {
            if (capturing != 0) return CaptureKey(keyData);
            return base.ProcessCmdKey(ref msg, keyData);
        }
        protected override void OnKeyDown(KeyEventArgs e)
        {
            if (capturing != 0) { CaptureKey(e.KeyData); e.Handled = true; e.SuppressKeyPress = true; return; }
            base.OnKeyDown(e);
        }
        void Save(bool start)
        {
            try
            {
                string root = Game.Root(gamePath.Text);
                Bindings value = ReadChoices();
                string problem = Game.ModProblem(root);
                if (problem != null) throw new InvalidDataException(problem);
                ConfigStore.Save(ConfigStore.ConfigPath(root), value);
                string remembered = "";
                try { Game.Remember(root); } catch { remembered = "（游戏目录未能记住）"; }
                if (!start) { Message("已保存：下一位 " + KeyCatalog.Name(value.Next) + " / 上一位 " + KeyCatalog.Name(value.Previous) + "。下次启动生效。" + remembered, false); return; }
                if (Game.Running()) { Message("设置已保存。游戏正在运行，请退出游戏后再从这里启动。", false); return; }
#if SUPPORT_DIAGNOSTICS
                if (!File.Exists(SupportRecorder.PathIn(root))) throw new IOException("请先退出游戏并点击“安装 / 更新诊断版”，再启动记录。");
                Process.Start(Game.StartInfo(root));
                Message("游戏已启动。可保留此窗口；故障时按F8，随后导出最近30分钟ZIP。", false);
#else
                Process.Start(Game.StartInfo(root)); Close();
#endif
            }
            catch (Exception ex) { Message("未完成：" + ex.Message, true); }
        }
        void ManageMod(bool install)
        {
            EndCapture(); ValidateChoices();
            try
            {
                string root = Game.Root(gamePath.Text);
                UseWaitCursor = true;
#if SUPPORT_DIAGNOSTICS
                if (!install) SupportRecorder.Set(root, false);
                string result = new ModInstaller(root).Run(install);
                if (install) result += "\n" + SupportRecorder.Set(root, true);
                Message(result, false);
#else
                Message(new ModInstaller(root).Run(install), false);
#endif
                try { Game.Remember(root); } catch { }
            }
            catch (Exception ex) { Message("未完成：" + ex.Message, true); }
            finally { UseWaitCursor = false; }
        }
    }

    public static class Program
    {
        [STAThread]
        public static int Main(string[] args)
        {
#if SUPPORT_DIAGNOSTICS
            if (args.Length == 3 && args[0] == "--support-capture") return SupportExport.CaptureHelper(args[1], args[2]);
#if MOD_TESTS
            if (args.Length == 2 && args[0] == "--support-self-test") return SupportTests.Run(args[1]);
#endif
#endif
#if MOD_TESTS
            if (args.Length == 2 && args[0] == "--self-test") return SelfTest(args[1]);
            if (args.Length == 2 && args[0] == "--installer-test") return InstallerTests.Run(args[1]);
#endif
            Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new LauncherForm()); return 0;
        }
#if MOD_TESTS
        static void Check(bool condition, string message) { if (!condition) throw new Exception(message); }
        static int SelfTest(string reportPath)
        {
            string root = Path.Combine(Path.GetTempPath(), "dmc5-launcher-test-" + Guid.NewGuid().ToString("N"));
            try
            {
                Directory.CreateDirectory(root);
                File.WriteAllText(Path.Combine(root, "DevilMayCry5.exe"), "test fixture; never executed");
                string path = ConfigStore.ConfigPath(root), warning;
                var defaults = ConfigStore.Load(path, out warning);
                Check(defaults.Next == 128 && defaults.Previous == 129 && defaults.ControllerCombo && warning == null, "defaults");
                var custom = new Bindings { Next = 118, Previous = 119, ControllerCombo = false };
                ConfigStore.Save(path, custom);
                var read = ConfigStore.Load(path, out warning);
                Check(read.Next == 118 && read.Previous == 119 && !read.ControllerCombo && warning == null, "round trip");
                ConfigStore.Save(path, new Bindings()); ConfigStore.Save(path, custom);
                Check(File.Exists(path + ".bak"), "atomic backup");
                bool rejected = false;
                try { ConfigStore.Save(path, new Bindings { Next = 118, Previous = 118 }); } catch (InvalidDataException) { rejected = true; }
                Check(rejected && ConfigStore.Load(path, out warning).Previous == 119, "duplicate rejection preserves file");
                File.WriteAllText(path, "{broken");
                Check(ConfigStore.Load(path, out warning).Next == 128 && warning != null, "corrupt fallback");
                ConfigStore.Save(path, custom); Check(ConfigStore.Load(path, out warning).Next == 118, "repair corrupt config");
                File.WriteAllText(path, "{\"nextKey\":118.5,\"previousKey\":119}");
                Check(ConfigStore.Load(path, out warning).Next == 128 && warning != null, "fractional rejection");
                Check(!KeyCatalog.Valid(45) && !KeyCatalog.Valid(17) && KeyCatalog.Valid(135), "key allowlist");
                var launch = Game.StartInfo(root);
                Check(launch.FileName == Path.Combine(root, "DevilMayCry5.exe") && launch.WorkingDirectory == root && launch.UseShellExecute, "launch destination");
                ConfigStore.Save(path, custom);
                File.WriteAllText(reportPath, ConfigStore.Json.Serialize(new { passed = true, configPath = path, keyCodes = KeyCatalog.All().ConvertAll(k => k.Code), checks = "defaults, JSON roundtrip, atomic backup, duplicate rejection, malformed repair, allowlist, launch destination (not executed)" }), new UTF8Encoding(false));
                return 0;
            }
            catch (Exception ex)
            {
                File.WriteAllText(reportPath, ConfigStore.Json.Serialize(new { passed = false, error = ex.ToString() }), new UTF8Encoding(false)); return 1;
            }
        }
#endif
    }
}
