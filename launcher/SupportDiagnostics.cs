#if SUPPORT_DIAGNOSTICS
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Imaging;
using System.Globalization;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Web;
using System.Web.Script.Serialization;
using System.Windows.Forms;

namespace Dmc5SwitchLauncher
{
    public static class SupportRecorder
    {
        public const string Name = "zzz_dmc5_support_recorder.lua";
        public const string Version = "support-50.1";
        public static byte[] Payload()
        {
            using (var input = Assembly.GetExecutingAssembly().GetManifestResourceStream("support.recorder.lua"))
            using (var output = new MemoryStream()) { if (input == null) throw new IOException("缺少诊断记录器。"); input.CopyTo(output); return output.ToArray(); }
        }
        public static string Hash(byte[] data)
        { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(data)).Replace("-", ""); }
        public static string PathIn(string root) { return Path.Combine(root, "reframework", "autorun", Name); }
        public static string Set(string root, bool enable, Func<bool> running = null)
        {
            root = Game.Root(root);
            if ((running ?? Game.Running)()) throw new InvalidOperationException("请先完全退出游戏；启用／停止记录需重启游戏。");
            if (enable && !File.Exists(Path.Combine(root, "dinput8.dll"))) throw new IOException("未检测到 REFramework；请先安装现有切人 Mod 或加载器。");
            string path = PathIn(root), own = Path.Combine(root, ".dmc5-character-switch", "support-recorder.json");
            Directory.CreateDirectory(Path.GetDirectoryName(own));
            using (var lease = new FileStream(own + ".lock", FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            {
                string current = File.Exists(path) ? Hash(File.ReadAllBytes(path)) : null;
                string expected = Hash(Payload());
                Dictionary<string, object> state = null;
                if (File.Exists(own)) state = SupportExport.Json.Deserialize<Dictionary<string, object>>(File.ReadAllText(own));
                string recorded = state != null && state.ContainsKey("hash") ? Convert.ToString(state["hash"]) : null;
                if (current != null && current != recorded && current != expected) throw new IOException("同名记录器来源不同或已修改，已保留文件：" + path);
                if (enable)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(path));
                    Atomic(path, Payload());
                    Atomic(own, Encoding.UTF8.GetBytes(SupportExport.Json.Serialize(new { version = Version, hash = expected, installedUtc = DateTime.UtcNow.ToString("o") })));
                    return "诊断记录已启用；重启游戏后开始记录。F8 可标记故障现场。";
                }
                if (current != null) File.Delete(path);
                if (File.Exists(own)) File.Delete(own);
                return "已停止诊断记录；历史日志保留，可继续导出。重启游戏后生效。";
            }
        }
        static void Atomic(string path, byte[] bytes)
        {
            string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try { File.WriteAllBytes(temp, bytes); if (File.Exists(path)) File.Replace(temp, path, null); else File.Move(temp, path); }
            finally { if (File.Exists(temp)) File.Delete(temp); }
        }
    }

    public static class SupportExport
    {
        public static readonly JavaScriptSerializer Json = new JavaScriptSerializer { MaxJsonLength = 32 * 1024 * 1024, RecursionLimit = 80 };
        const long ArtifactLimit = 64L * 1024 * 1024;
        const int SnapshotLimit = 16 * 1024 * 1024;
        static readonly Regex LogStamp = new Regex(@"^\[(\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:\.\d+)?)\]", RegexOptions.Compiled);
        public static long Epoch(DateTime utc) { return (long)(utc.ToUniversalTime() - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalSeconds; }
        public static string Redact(string value, string root)
        {
            if (value == null) return "";
            foreach (var pair in new[] { new[] { root, "<GAME>" }, new[] { Environment.GetFolderPath(Environment.SpecialFolder.UserProfile), "<USER>" } })
                if (!String.IsNullOrEmpty(pair[0]))
                    foreach (string form in new[] { pair[0].Replace("\\", "\\\\"), pair[0].Replace("\\", "/"), pair[0] })
                        value = Regex.Replace(value, Regex.Escape(form), pair[1].Replace("$", "$$"), RegexOptions.IgnoreCase);
            return value;
        }
        public static bool SafeFile(string root, string path)
        {
            string full = Path.GetFullPath(path), prefix = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            if (!full.StartsWith(prefix, StringComparison.OrdinalIgnoreCase) || !File.Exists(full)) return false;
            for (string p = full; !String.Equals(p, prefix.TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase); p = Path.GetDirectoryName(p))
                if (String.IsNullOrEmpty(p) || (File.GetAttributes(p) & FileAttributes.ReparsePoint) != 0) return false;
            return true;
        }
        static object Get(Dictionary<string, object> row, string name)
        { object value; return row != null && row.TryGetValue(name, out value) ? value : null; }
        static long Number(object value)
        { try { return Convert.ToInt64(value, CultureInfo.InvariantCulture); } catch { return 0; } }
        static string ReadShared(string path, int maximum, bool tail)
        {
            using (var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            {
                bool skip = tail && file.Length > maximum;
                if (skip) file.Seek(-maximum, SeekOrigin.End);
                using (var reader = new StreamReader(file, Encoding.UTF8, true))
                { if (skip) reader.ReadLine(); char[] buffer = new char[maximum]; int n = reader.ReadBlock(buffer, 0, maximum); return new string(buffer, 0, n); }
            }
        }
        public static string FilterLog(string text, DateTime from, DateTime until, List<string> warnings)
        {
            bool include = false; var output = new StringBuilder(); int unknown = 0;
            foreach (string line in text.Replace("\r\n", "\n").Split('\n'))
            {
                var match = LogStamp.Match(line);
                if (match.Success)
                {
                    DateTime local;
                    if (DateTime.TryParse(match.Groups[1].Value, CultureInfo.InvariantCulture, DateTimeStyles.AssumeLocal, out local))
                    { DateTime utc = local.ToUniversalTime(); include = utc >= from && utc <= until; }
                    else { include = false; unknown++; }
                }
                if (include) output.AppendLine(line);
                else if (!match.Success && output.Length == 0 && line.Length > 0) unknown++;
            }
            if (unknown > 0) warnings.Add("原生日志中有无时间戳／无法归属的行；未混入最近30分钟记录。");
            return output.ToString();
        }
        public static string Export(string gameRoot, string destination, string note, string[] attachments, bool screenshot, DateTime? at = null)
        {
            string root = Game.Root(gameRoot);
            DateTime now = (at ?? DateTime.UtcNow).ToUniversalTime(), from = now.AddMinutes(-30);
            Directory.CreateDirectory(destination);
            string output = Path.Combine(destination, "DMC5诊断_" + now.ToLocalTime().ToString("yyyyMMdd_HHmmss") + "_" + Guid.NewGuid().ToString("N").Substring(0, 6) + ".zip");
            string temp = output + ".partial";
            var warnings = new List<string>(); var files = new List<object>();
            var rows = new List<Dictionary<string, object>>(); int bytes = 0, invalid = 0;
            for (int index = 0; index < 32; index++)
            {
                string path = Path.Combine(root, "reframework", "data", "dmc5_support", "slot-" + index.ToString("00") + ".jsonl");
                try
                {
                    if (!SafeFile(root, path)) continue;
                    if (new FileInfo(path).Length > 2 * 1024 * 1024) warnings.Add("记录槽过大，仅读取尾部：" + Path.GetFileName(path));
                    foreach (string line in ReadShared(path, 2 * 1024 * 1024, true).Split('\n'))
                    {
                        if (line.Length == 0 || line.Length > 65536) continue;
                        try
                        {
                            var row = Json.Deserialize<Dictionary<string, object>>(line);
                            long epoch = Number(Get(row, "utc"));
                            if (Number(Get(row, "schema")) != 1 || epoch < Epoch(from) || epoch > Epoch(now)) continue;
                            if (bytes + line.Length > SnapshotLimit || rows.Count >= 6000) { warnings.Add("状态记录达到导出上限；部分记录未纳入。"); break; }
                            bytes += line.Length; rows.Add(row);
                        }
                        catch { invalid++; }
                    }
                }
                catch (Exception ex) { warnings.Add("无法读取状态槽 " + index + ": " + ex.GetType().Name); }
            }
            rows = rows.OrderBy(r => Number(Get(r, "utc"))).ToList();
            if (invalid > 0) warnings.Add("忽略 " + invalid + " 条不完整记录（可能来自崩溃或正在写入）。");
            if (rows.Count == 0) warnings.Add("没有可用状态历史：请启用诊断记录、重启游戏后复现；既有原生日志仍会单独收集。");
            else if (Number(Get(rows[0], "utc")) > Epoch(from) + 5) warnings.Add("实际记录不足30分钟；覆盖范围以首末样本为准。");
            warnings.Add("普通采样约每秒一次、约每5秒批量落盘；突发崩溃可能丢失最后数秒。F8 标记会立即落盘。");
            warnings.Add("截图为导出时的游戏画面，不是此前30分钟的视频回放。");
            var nativeEvents = ReadEvents(from, now, warnings);
            object system = SystemInfo(root, warnings);
            string screenshotPath = null; string screenshotStatus = "未选择截图";
            try
            {
                if (screenshot)
                {
                    System.Threading.Thread.Sleep(3000);
                    screenshotPath = CaptureGame(root, warnings, out screenshotStatus);
                }
                using (var stream = new FileStream(temp, FileMode.CreateNew, FileAccess.Write, FileShare.None))
                using (var zip = new ZipArchive(stream, ZipArchiveMode.Create))
                {
                    Action<string, byte[]> add = (name, data) => {
                        var entry = zip.CreateEntry(name, CompressionLevel.Optimal);
                        using (var target = entry.Open()) target.Write(data, 0, data.Length);
                        files.Add(new { path = name, bytes = data.Length, sha256 = SupportRecorder.Hash(data) });
                    };
                    Action<string, string> text = (name, value) => add(name, Encoding.UTF8.GetBytes(Redact(value, root)));
                    text("状态时间线.jsonl", String.Join("\n", rows.Select(r => Json.Serialize(r)).ToArray()));
                    text("系统与进程.json", Json.Serialize(system));
                    text("Windows游戏异常.json", Json.Serialize(nativeEvents));
                    text("问题描述.txt", (note ?? "").Substring(0, Math.Min(4000, (note ?? "").Length)));
                    foreach (string name in new[] { "re2_framework_log.txt", "reframework.log", "reframework_crash.txt" })
                    {
                        string path = Path.Combine(root, name);
                        if (!SafeFile(root, path)) continue;
                        try
                        {
                            if (new FileInfo(path).Length > 8 * 1024 * 1024) warnings.Add(name + " 超过8 MiB，仅检查尾部。");
                            text("原生日志/" + name, FilterLog(ReadShared(path, 8 * 1024 * 1024, true), from, now, warnings));
                        }
                        catch (Exception ex) { warnings.Add("未收集 " + name + ": " + ex.GetType().Name); }
                    }
                    foreach (string name in new[] { "reframework_crash.dmp", "re2_framework_crash.dmp" })
                    {
                        string path = Path.Combine(root, name);
                        if (!SafeFile(root, path)) continue;
                        var info = new FileInfo(path);
                        if (info.LastWriteTimeUtc < from || info.LastWriteTimeUtc > now) continue;
                        if (info.Length > ArtifactLimit) { warnings.Add("崩溃转储超过64 MiB，未包含：" + name); continue; }
                        try { add("崩溃转储/" + name, ReadBinary(path, ArtifactLimit)); }
                        catch (Exception ex) { warnings.Add("无法读取转储：" + ex.GetType().Name); }
                    }
                    var inventory = new List<object>();
                    foreach (string name in ModInstaller.Modules)
                    {
                        string path = Path.Combine(root, ModInstaller.ModulePath(name).Replace('/', Path.DirectorySeparatorChar));
                        inventory.Add(FileIdentity(root, path, name));
                    }
                    inventory.Add(FileIdentity(root, Path.Combine(root, "dinput8.dll"), "dinput8.dll"));
                    inventory.Add(FileIdentity(root, SupportRecorder.PathIn(root), SupportRecorder.Name));
                    text("安装文件校验.json", Json.Serialize(inventory));
                    string config = ConfigStore.ConfigPath(root);
                    if (SafeFile(root, config))
                    {
                        string warning; Bindings b = ConfigStore.Load(config, out warning);
                        text("按键配置.json", Json.Serialize(new { nextKey = b.Next, previousKey = b.Previous, controllerCombo = b.ControllerCombo, warning = warning }));
                    }
                    if (screenshotPath != null && File.Exists(screenshotPath)) add("现场截图.png", ReadBinary(screenshotPath, 16 * 1024 * 1024));
                    var pictures = new List<string>(); int pictureIndex = 0;
                    foreach (string path in (attachments ?? new string[0]).Take(3))
                    {
                        try
                        {
                            if (new FileInfo(path).Length > 10 * 1024 * 1024) { warnings.Add("附加截图超过10 MiB，已跳过。"); continue; }
                            // Re-encode only selected images, discarding filenames and EXIF metadata.
                            using (var original = Image.FromFile(path))
                            {
                            if (original.Width > 8192 || original.Height > 8192 || (long)original.Width * original.Height > 32000000) throw new IOException("截图尺寸过大");
                            using (var bitmap = new Bitmap(original.Width, original.Height))
                            using (var graphics = Graphics.FromImage(bitmap))
                            using (var buffer = new MemoryStream())
                            {
                                graphics.DrawImage(original, 0, 0); bitmap.Save(buffer, ImageFormat.Png);
                                if (buffer.Length > 16 * 1024 * 1024) throw new IOException("PNG过大");
                                string name = "附加截图/" + (++pictureIndex) + ".png"; add(name, buffer.ToArray()); pictures.Add(name);
                            }
                            }
                        }
                        catch (Exception ex) { warnings.Add("附加截图未收集：" + ex.GetType().Name); }
                    }
                    var manifest = new { schema = 1, tool = SupportRecorder.Version, exportUtc = now.ToString("o"),
                        requestedFromUtc = from.ToString("o"), requestedUntilUtc = now.ToString("o"),
                        firstSampleUtc = rows.Count > 0 ? Get(rows[0], "utc") : null,
                        lastSampleUtc = rows.Count > 0 ? Get(rows[rows.Count - 1], "utc") : null,
                        samples = rows.Count, markers = rows.Count(r => Convert.ToString(Get(r, "kind")) == "F8"),
                        screenshot = screenshotStatus, screenshotUtc = screenshotPath == null ? null : DateTime.UtcNow.ToString("o"),
                        warnings = warnings.Distinct().ToArray(), files = files.ToArray(),
                        privacy = "仅游戏诊断、Mod按键、游戏窗口和主动附加截图；不含游戏存档、账号目录、全局键盘历史或其他窗口截图。" };
                    text("导出清单.json", Json.Serialize(manifest));
                    text("诊断报告.html", Report(rows, manifest, note, screenshotPath != null, pictures));
                }
                File.Move(temp, output); return output;
            }
            finally
            {
                if (File.Exists(temp)) File.Delete(temp);
                if (screenshotPath != null) { try { Directory.Delete(Path.GetDirectoryName(screenshotPath), true); } catch { } }
            }
        }
        static byte[] ReadBinary(string path, long max)
        {
            using (var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite | FileShare.Delete))
            using (var buffer = new MemoryStream())
            { if (file.Length > max) throw new IOException("文件超限"); byte[] data = new byte[65536]; int n; while ((n = file.Read(data, 0, data.Length)) > 0) { if (buffer.Length + n > max) throw new IOException("文件增长超限"); buffer.Write(data, 0, n); } return buffer.ToArray(); }
        }
        static object FileIdentity(string root, string path, string name)
        {
            try
            {
                if (!SafeFile(root, path)) return new { name = name, exists = false };
                byte[] data = ReadBinary(path, 128 * 1024 * 1024);
                string build = null;
                if (name == "dmc5_live_switch.lua") { var m = Regex.Match(Encoding.UTF8.GetString(data), @"build\s*=\s*'([^']+)'"); if (m.Success) build = m.Groups[1].Value; }
                return new { name = name, exists = true, bytes = data.Length, sha256 = SupportRecorder.Hash(data), build = build };
            }
            catch (Exception ex) { return new { name = name, error = ex.GetType().Name }; }
        }
        static object SystemInfo(string root, List<string> warnings)
        {
            var processes = new List<object>();
            foreach (var p in Process.GetProcessesByName("DevilMayCry5"))
            {
                using (p) try
                {
                    if (!String.Equals(p.MainModule.FileName, Path.Combine(root, "DevilMayCry5.exe"), StringComparison.OrdinalIgnoreCase)) continue;
                    processes.Add(new { pid = p.Id, startedUtc = p.StartTime.ToUniversalTime().ToString("o"), workingSet = p.WorkingSet64, privateBytes = p.PrivateMemorySize64, responding = p.Responding });
                }
                catch (Exception ex) { warnings.Add("游戏进程详情不可读：" + ex.GetType().Name); }
            }
            string gameVersion = null;
            try { gameVersion = FileVersionInfo.GetVersionInfo(Path.Combine(root, "DevilMayCry5.exe")).FileVersion; } catch { warnings.Add("游戏版本资源不可读。"); }
            return new { os = Environment.OSVersion.ToString(), os64 = Environment.Is64BitOperatingSystem,
                launcher64 = Environment.Is64BitProcess, processors = Environment.ProcessorCount, framework = Environment.Version.ToString(),
                gameVersion = gameVersion, gameExeBytes = new FileInfo(Path.Combine(root, "DevilMayCry5.exe")).Length,
                localUtcOffset = TimeZoneInfo.Local.GetUtcOffset(DateTime.Now).ToString(), processes = processes };
        }
        static object ReadEvents(DateTime from, DateTime until, List<string> warnings)
        {
            var result = new List<object>();
            try
            {
                using (var log = new EventLog("Application"))
                {
                    int count = log.Entries.Count;
                    for (int i = count - 1; i >= Math.Max(0, count - 1000) && result.Count < 30; i--)
                    {
                        var entry = log.Entries[i]; DateTime utc = entry.TimeGenerated.ToUniversalTime();
                        if (utc < from) break; if (utc > until) continue;
                        if (entry.Source != "Application Error" && entry.Source != "Windows Error Reporting") continue;
                        string message = entry.Message;
                        if (message.IndexOf("DevilMayCry5", StringComparison.OrdinalIgnoreCase) < 0 && message.IndexOf("reframework", StringComparison.OrdinalIgnoreCase) < 0) continue;
                        result.Add(new { utc = utc.ToString("o"), source = entry.Source, id = entry.InstanceId, message = message.Substring(0, Math.Min(message.Length, 16000)) });
                    }
                }
            }
            catch (Exception ex) { warnings.Add("Windows异常记录不可读：" + ex.GetType().Name); }
            return result;
        }
        static string Report(List<Dictionary<string, object>> rows, object manifest, string note, bool screenshot, List<string> pictures)
        {
            string data = Json.Serialize(rows).Replace("<", "\\u003c").Replace(">", "\\u003e").Replace("&", "\\u0026");
            var html = new StringBuilder(@"<!doctype html><meta charset='utf-8'><title>DMC5 远端诊断</title><style>body{background:#111827;color:#e5e7eb;font:15px system-ui;margin:32px;max-width:1200px}h1{color:#7dd3fc}.cards{display:flex;gap:12px;flex-wrap:wrap}.card{background:#1f2937;padding:16px;border-radius:10px;min-width:160px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1f2937;padding:16px;border-radius:10px}input{width:100%}img{max-width:100%;border-radius:8px}td,th{padding:8px;text-align:left;border-bottom:1px solid #374151}table{border-collapse:collapse;width:100%}.muted{color:#9ca3af}</style><h1>DMC5 远端诊断</h1><p class='muted'>先看问题描述与现场截图，再拖动时间线；数据为读取值，提示不等于已确认根因。</p><h2>问题描述</h2><pre>");
            html.Append(HttpUtility.HtmlEncode(note ?? "未填写")).Append("</pre>");
            if (screenshot) html.Append("<h2>导出时游戏画面</h2><img src='现场截图.png'><p class='muted'>全屏模式可能出现黑图；请结合主动附加截图。</p>");
            foreach (string image in pictures) html.Append("<img src='").Append(HttpUtility.HtmlAttributeEncode(image)).Append("'>");
            html.Append(@"<h2>最近30分钟状态</h2><div id='coverage' class='muted'></div><input id='time' type='range' min='0' value='0'><div id='cards' class='cards'></div><h3>该时刻角色状态</h3><table><thead><tr><th>角色</th><th>主控</th><th>显示 / 启用</th><th>HP / DT / SDT</th><th>自动辅助</th><th>机械手</th></tr></thead><tbody id='party'></tbody></table><h3>线索</h3><pre id='hints'></pre><details><summary>该时刻完整原始状态</summary><pre id='raw'></pre></details><h2>导出范围与完整性</h2><pre>");
            html.Append(HttpUtility.HtmlEncode(Json.Serialize(manifest))).Append("</pre><script>const rows=").Append(data).Append(@";const $=id=>document.getElementById(id), names={0:'尼禄',1:'但丁',2:'V',4:'维吉尔'};const val=v=>v==null?'—':v,fmt=t=>new Date(t*1000).toISOString(),arr=v=>Array.isArray(v)?v:Object.values(v||{});function cell(tr,v){let c=document.createElement('td');c.textContent=v==null?'—':String(v);tr.appendChild(c)}function show(){let r=rows[+$('time').value];if(!r){$('coverage').textContent='没有状态记录：需先启用诊断并重启游戏。';return}$('cards').textContent='';for(const [k,v]of Object.entries({'UTC时间':fmt(r.utc),'关卡 / 模式':val(r.mission)+' / '+val(r.mode),'实际主控':names[r.manual]||r.manual,'Mod状态':r.modStage||'不可用','采样类型':r.kind})){let c=document.createElement('div');c.className='card';c.textContent=k+'：'+v;$('cards').appendChild(c)}$('party').textContent='';let hints=[];for(const p of arr(r.players)){let tr=document.createElement('tr');for(const v of [names[p.id]||p.id,p.manual?'是':'',p.ready===false?'加载中／未就绪':val(p.draw)+' / '+val(p.enabled),val(p.hp)+' / '+val(p.dt)+' / '+val(p.sin),p.automatic,p.arms?JSON.stringify(p.arms):'—'])cell(tr,v);$('party').appendChild(tr);if(p.manual&&(p.enabled===false||p.draw===false||p.bodyMeshes===0))hints.push('当前主控存在隐藏、禁用或无绑定模型的读数。');if(p.manual&&p.automatic)hints.push('当前角色自动辅助开启，可能解释自动出招、蓄力或换武器。')}if(r.modCurrent!=null&&r.manual!=null&&r.modCurrent!==r.manual)hints.push('Mod记录与实际主控不同；检查加载、原生交接与切人顺序。');if(r.error)hints.push(r.error);if(arr(r.enemies).some(e=>e.masterLockRestricted))hints.push('部分敌人禁止本地主控锁定；旁观敌人可能正常如此，需结合场景判断。');$('hints').textContent=hints.join('\n')||'本样本未产生上述提示。';$('raw').textContent=JSON.stringify(r,null,2)}$('time').max=Math.max(0,rows.length-1);$('time').value=Math.max(0,rows.length-1);$('time').oninput=show;if(rows.length)$('coverage').textContent='实际覆盖 '+fmt(rows[0].utc)+' 至 '+fmt(rows[rows.length-1].utc)+'，共 '+rows.length+' 个样本（含F8标记）。';show();</script>");
            return html.ToString();
        }
        public static string CaptureGame(string root, List<string> warnings, out string status)
        {
            status = "游戏未运行或窗口不可用";
            foreach (var process in Process.GetProcessesByName("DevilMayCry5"))
            using (process) try
            {
                if (!String.Equals(process.MainModule.FileName, Path.Combine(root, "DevilMayCry5.exe"), StringComparison.OrdinalIgnoreCase)) continue;
                IntPtr window = process.MainWindowHandle;
                if (window == IntPtr.Zero || IsIconic(window)) { status = "游戏窗口最小化或不存在；未截图"; return null; }
                string dir = Path.Combine(Path.GetTempPath(), "dmc5-support-capture-" + Guid.NewGuid().ToString("N")); Directory.CreateDirectory(dir);
                string path = Path.Combine(dir, "game.png");
                using (var child = Process.Start(new ProcessStartInfo(Application.ExecutablePath, "--support-capture " + window.ToInt64().ToString(CultureInfo.InvariantCulture) + " \"" + path + "\"") { UseShellExecute = false, CreateNoWindow = true, WindowStyle = ProcessWindowStyle.Hidden }))
                {
                    if (!child.WaitForExit(4000)) { child.Kill(); child.WaitForExit(1000); status = "游戏窗口截图超时（仅结束截图助手，游戏未受影响）"; }
                    else status = child.ExitCode == 0 && File.Exists(path) ? "已获取游戏窗口；全屏黑图请主动附加截图" : "游戏窗口抓取失败；可主动附加截图";
                }
                if (File.Exists(path)) return path;
                Directory.Delete(dir, true); return null;
            }
            catch (Exception ex) { warnings.Add("游戏截图不可用：" + ex.GetType().Name); }
            return null;
        }
        [StructLayout(LayoutKind.Sequential)] struct Rect { public int Left, Top, Right, Bottom; }
        [DllImport("user32.dll")] static extern bool GetWindowRect(IntPtr hwnd, out Rect rect);
        [DllImport("user32.dll")] static extern bool PrintWindow(IntPtr hwnd, IntPtr dc, uint flags);
        [DllImport("user32.dll")] static extern bool IsIconic(IntPtr hwnd);
        [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint pid);
        public static int CaptureHelper(string handle, string output)
        {
            try
            {
                // The launcher only spawns this helper with its own unique temp path.
                string full = Path.GetFullPath(output), parent = Path.GetDirectoryName(full);
                if (!parent.StartsWith(Path.GetTempPath(), StringComparison.OrdinalIgnoreCase) || !Path.GetFileName(parent).StartsWith("dmc5-support-capture-", StringComparison.Ordinal) || Path.GetFileName(full) != "game.png") return 2;
                IntPtr window = new IntPtr(Int64.Parse(handle, CultureInfo.InvariantCulture)); Rect rect;
                uint pid; GetWindowThreadProcessId(window, out pid);
                using (var process = Process.GetProcessById((int)pid))
                    if (!String.Equals(process.ProcessName, "DevilMayCry5", StringComparison.OrdinalIgnoreCase)) return 3;
                if (!GetWindowRect(window, out rect) || IsIconic(window)) return 3;
                int width = rect.Right - rect.Left, height = rect.Bottom - rect.Top;
                if (width <= 0 || height <= 0 || width > 8192 || height > 8192 || (long)width * height > 32000000) return 4;
                using (var bitmap = new Bitmap(width, height))
                using (var graphics = Graphics.FromImage(bitmap))
                {
                    IntPtr dc = graphics.GetHdc(); bool ok;
                    try { ok = PrintWindow(window, dc, 2); } finally { graphics.ReleaseHdc(dc); }
                    if (!ok) return 5; bitmap.Save(full, ImageFormat.Png);
                }
                return 0;
            }
            catch { return 6; }
        }
    }

    public static class SupportUi
    {
        public static void Export(Form owner, string root, Action<string, bool> status)
        {
            using (var dialog = new Form { Text = "导出最近30分钟 · 远端诊断", ClientSize = new Size(620, 340), StartPosition = FormStartPosition.CenterParent, FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false, MinimizeBox = false, Font = owner.Font })
            {
                var label = new Label { Text = "描述问题、关卡、角色和复现顺序（可留空）：", Location = new Point(20, 16), Size = new Size(580, 26) };
                var note = new TextBox { Multiline = true, MaxLength = 4000, ScrollBars = ScrollBars.Vertical, Location = new Point(20, 47), Size = new Size(580, 125) };
                var screen = new CheckBox { Text = "3秒后抓取游戏窗口（导出时可切回游戏；不截取桌面）", Checked = true, Location = new Point(20, 182), Size = new Size(580, 30) };
                var attach = new Button { Text = "附加现场截图…", Location = new Point(20, 225), Size = new Size(180, 36) };
                var count = new Label { Text = "最多3张，每张10 MiB；不含存档", Location = new Point(214, 232), Size = new Size(380, 28) };
                string[] images = new string[0];
                attach.Click += delegate { using (var pick = new OpenFileDialog { Filter = "截图|*.png;*.jpg;*.jpeg;*.bmp", Multiselect = true }) if (pick.ShowDialog(dialog) == DialogResult.OK) { images = pick.FileNames.Take(3).ToArray(); count.Text = "已选择 " + images.Length + " 张截图"; } };
                var ok = new Button { Text = "导出到桌面 ZIP", DialogResult = DialogResult.OK, Location = new Point(390, 285), Size = new Size(210, 38) };
                dialog.Controls.AddRange(new Control[] { label, note, screen, attach, count, ok }); dialog.AcceptButton = ok;
                if (dialog.ShowDialog(owner) != DialogResult.OK) return;
                string description = note.Text; bool capture = screen.Checked;
                status("正在导出最近30分钟；如需截图，现在可切回游戏…", false);
                owner.Enabled = false;
                var worker = new BackgroundWorker();
                worker.DoWork += delegate(object sender, DoWorkEventArgs args) { args.Result = SupportExport.Export(root, Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory), description, images, capture); };
                worker.RunWorkerCompleted += delegate(object sender, RunWorkerCompletedEventArgs args) {
                    owner.Enabled = true;
                    if (args.Error != null) { status("导出未完成：" + args.Error.Message, true); return; }
                    string path = (string)args.Result; status("已导出到桌面：" + Path.GetFileName(path), false);
                    if (MessageBox.Show(owner, "诊断包已保存到桌面。解压后打开“诊断报告.html”查看时间线。\n\n打开文件所在位置？", "导出完成", MessageBoxButtons.YesNo, MessageBoxIcon.Information) == DialogResult.Yes)
                        Process.Start("explorer.exe", "/select,\"" + path + "\"");
                    worker.Dispose();
                };
                worker.RunWorkerAsync();
            }
        }
    }
}
#endif
