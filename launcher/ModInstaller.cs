using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;

namespace Dmc5SwitchLauncher
{
    public sealed class OwnedFile
    {
        public string Path { get; set; }
        public string InstalledHash { get; set; }
        public string Original { get; set; }
        public string OriginalHash { get; set; }
        public long OriginalTime { get; set; }
    }
    public sealed class InstallState
    {
        public int Version { get; set; }
        public List<OwnedFile> Files { get; set; }
    }
    public sealed class FileChange
    {
        public string Path { get; set; }
        public string Before { get; set; }
        public string BeforeHash { get; set; }
        public long BeforeTime { get; set; }
        public string AfterHash { get; set; }
        [System.Web.Script.Serialization.ScriptIgnore]
        public byte[] Bytes { get; set; }
        [System.Web.Script.Serialization.ScriptIgnore]
        public long WriteTime { get; set; }
    }

    // The only game paths this installer may change are this fixed allowlist.
    // Backups are immutable and kept outside REFramework's autorun directories.
    public sealed class ModInstaller
    {
        public const string Store = ".dmc5-character-switch";
        const string StatePath = Store + "/installed.json";
        const string LicensePath = Store + "/REFramework-LICENSE.txt";
        const string RuntimeHash = "CBA7C25F57D199E2FDFB73EB3BA8BA5BAF028D453D428498796E85FBDD75CB0F";
        public static readonly string[] Modules = {
            "dmc5_live_switch.lua", "dmc5_party_hud.lua", "dmc5_switch_core.lua", "dmc5_switch_hud.lua",
            "dmc5_switch_controller.lua", "dmc5_switch_keys.lua", "dmc5_switch_lifecycle.lua",
            "dmc5_switch_progression.lua", "dmc5_switch_regen.lua", "dmc5_switch_resources.lua",
            "dmc5_switch_voice.lua", "dmc5_switch_runtime.lua", "dmc5_switch_loader.lua", "dmc5_switch_input_menu.lua", "dmc5_switch_palace.lua" };
        readonly string root;
        readonly Func<bool> running;
        readonly Dictionary<string, byte[]> payload;
        string operation;
        int backupNumber;
#if MOD_TESTS
        // Compiled only into the separate development test executable.
        internal int FailAfter = -1;
        internal bool FailVerification;
#endif
        public ModInstaller(string gameRoot, Func<bool> isRunning = null)
        {
            root = Game.Root(gameRoot).TrimEnd(Path.DirectorySeparatorChar);
            running = isRunning ?? Game.Running;
            payload = new Dictionary<string, byte[]>(StringComparer.OrdinalIgnoreCase);
            foreach (string name in Modules) payload.Add(ModulePath(name), Resource(name));
            byte[] dll;
            using (var compressed = new MemoryStream(Resource("dinput8.dll.gz")))
            using (var gzip = new GZipStream(compressed, CompressionMode.Decompress))
            using (var output = new MemoryStream()) { gzip.CopyTo(output); dll = output.ToArray(); }
            if (Hash(dll) != RuntimeHash) throw new InvalidDataException("内置加载器校验失败，请重新获取启动器。");
            payload.Add("dinput8.dll", dll);
        }
        public static string ModulePath(string name)
        { return "reframework/" + (name == "dmc5_live_switch.lua" ? "autorun/" : "data/") + name; }
        static byte[] Resource(string name)
        {
            using (var source = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload." + name))
            using (var dest = new MemoryStream())
            {
                if (source == null) throw new InvalidDataException("启动器缺少内置文件：" + name);
                source.CopyTo(dest); return dest.ToArray();
            }
        }
        public static string Hash(byte[] data)
        { using (var sha = SHA256.Create()) return BitConverter.ToString(sha.ComputeHash(data)).Replace("-", ""); }
        string FileHash(string path) { return File.Exists(path) ? Hash(File.ReadAllBytes(path)) : null; }
        bool Allowed(string relative)
        { return relative == StatePath || relative == LicensePath || payload.ContainsKey(relative); }
        string Resolve(string relative)
        {
            if (String.IsNullOrEmpty(relative) || relative.Contains("\\") || relative.Contains(":") || relative.Split('/').Any(p => p == ".." || p == "." || p.Length == 0))
                throw new InvalidDataException("备份记录路径无效。");
            string path = Path.GetFullPath(Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)));
            if (!path.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("路径越出游戏目录。");
            // Reject junctions/symlinks rather than follow them into another folder.
            for (string cursor = path; !String.IsNullOrEmpty(cursor); cursor = Path.GetDirectoryName(cursor))
                if ((File.Exists(cursor) || Directory.Exists(cursor)) && (File.GetAttributes(cursor) & FileAttributes.ReparsePoint) != 0)
                    throw new InvalidDataException("安装路径包含链接，请选择实际游戏目录：" + cursor);
            return path;
        }
        string Target(string relative)
        {
            if (!Allowed(relative)) throw new InvalidDataException("记录包含非本 Mod 文件，已停止操作：" + relative);
            return Resolve(relative);
        }
        byte[] BackupBytes(string relative, string hash)
        {
            if (relative == null || !relative.StartsWith(Store + "/history/", StringComparison.Ordinal))
                throw new InvalidDataException("原文件备份记录无效。");
            byte[] bytes = File.ReadAllBytes(Resolve(relative));
            if (Hash(bytes) != hash) throw new InvalidDataException("备份校验失败，未改动游戏文件：" + relative);
            return bytes;
        }
        string Snapshot(string path)
        {
            string relative = operation + "/" + (++backupNumber) + ".bin";
            string dest = Resolve(relative);
            Directory.CreateDirectory(Path.GetDirectoryName(dest)); File.Copy(path, dest, false);
            return relative;
        }
        static byte[] Serialize(object value) { return new UTF8Encoding(false).GetBytes(ConfigStore.Json.Serialize(value)); }
        // Replace is atomic on NTFS; only this operation's unique temporary file is removed.
        void Write(string path, byte[] bytes, long time)
        {
            if (bytes == null) { if (File.Exists(path)) File.Delete(path); return; }
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            string temp = path + "." + Guid.NewGuid().ToString("N") + ".tmp";
            try
            {
                File.WriteAllBytes(temp, bytes);
                if (File.Exists(path)) File.Replace(temp, path, null, true); else File.Move(temp, path);
                if (time > 0) File.SetLastWriteTimeUtc(path, new DateTime(time, DateTimeKind.Utc));
            }
            finally { if (File.Exists(temp)) File.Delete(temp); }
        }
        InstallState ReadState()
        {
            string path = Target(StatePath);
            if (!File.Exists(path)) return new InstallState { Version = 1, Files = new List<OwnedFile>() };
            InstallState state;
            try { state = ConfigStore.Json.Deserialize<InstallState>(File.ReadAllText(path)); }
            catch (Exception ex) { throw new InvalidDataException("安装记录损坏，已停止操作以保留文件。", ex); }
            if (state == null || state.Version != 1 || state.Files == null) throw new InvalidDataException("安装记录版本无效。");
            var paths = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            foreach (var f in state.Files)
            {
                if (f == null || f.Path == null || !payload.ContainsKey(f.Path) || !paths.Add(f.Path) || String.IsNullOrEmpty(f.InstalledHash))
                    throw new InvalidDataException("安装记录包含未知或重复文件。");
                Target(f.Path);
                if (f.Original != null) { BackupBytes(f.Original, f.OriginalHash); new DateTime(f.OriginalTime, DateTimeKind.Utc); }
            }
            return state;
        }
        FileChange Change(string relative, byte[] bytes, long time = 0)
        {
            string path = Target(relative);
            bool exists = File.Exists(path);
            var result = new FileChange { Path = relative, Bytes = bytes, WriteTime = time, AfterHash = bytes == null ? null : Hash(bytes),
                BeforeHash = FileHash(path), BeforeTime = exists ? File.GetLastWriteTimeUtc(path).Ticks : 0 };
            if (exists) result.Before = Snapshot(path);
            return result;
        }
        void Rollback(List<FileChange> changes)
        {
            // Check every destination and backup before restoring any of them.
            foreach (var c in changes)
            {
                string now = FileHash(Target(c.Path));
                if (now != c.BeforeHash && now != c.AfterHash) throw new IOException("操作中断后文件又被修改，已保留现场，请查看备份：" + c.Path);
                if (c.Before != null) BackupBytes(c.Before, c.BeforeHash);
            }
            for (int i = changes.Count - 1; i >= 0; i--)
            {
                var c = changes[i];
                if (FileHash(Target(c.Path)) == c.BeforeHash) continue;
                Write(Target(c.Path), c.Before == null ? null : BackupBytes(c.Before, c.BeforeHash), c.BeforeTime);
            }
        }
        void Recover()
        {
            string pending = Resolve(Store + "/pending.json");
            if (!File.Exists(pending)) return;
            var changes = ConfigStore.Json.Deserialize<List<FileChange>>(File.ReadAllText(pending));
            if (changes == null || changes.Count > payload.Count + 2 || changes.Select(c => c.Path).Distinct(StringComparer.OrdinalIgnoreCase).Count() != changes.Count)
                throw new InvalidDataException("未完成的操作记录无效，已保留所有文件。");
            Rollback(changes); File.Delete(pending);
        }
        void Commit(List<FileChange> changes, Action verify = null)
        {
            string pending = Resolve(Store + "/pending.json");
            Write(pending, Serialize(changes), 0);
            try
            {
#if MOD_TESTS
                int count = 0;
#endif
                foreach (var c in changes)
                {
                    if (FileHash(Target(c.Path)) != c.BeforeHash) throw new IOException("文件在操作期间被其他程序修改：" + c.Path);
                    Write(Target(c.Path), c.Bytes, c.WriteTime);
#if MOD_TESTS
                    if (++count == FailAfter) throw new IOException("Injected test failure");
#endif
                }
                if (verify != null) verify();
                File.Delete(pending);
            }
            catch
            {
                Rollback(changes); File.Delete(pending); throw;
            }
        }
        bool OtherMods()
        {
            foreach (string folder in new[] { "reframework/autorun", "reframework/plugins" })
            {
                string path = Resolve(folder);
                if (!Directory.Exists(path)) continue;
                var queue = new Queue<string>(); queue.Enqueue(path);
                while (queue.Count > 0)
                {
                    string current = queue.Dequeue();
                    foreach (string entry in Directory.EnumerateFileSystemEntries(current))
                    {
                        var attr = File.GetAttributes(entry);
                        if ((attr & FileAttributes.ReparsePoint) != 0) return true;
                        if ((attr & FileAttributes.Directory) != 0) { queue.Enqueue(entry); continue; }
                        string extension = Path.GetExtension(entry);
                        if (!String.Equals(extension, ".lua", StringComparison.OrdinalIgnoreCase) && !String.Equals(extension, ".dll", StringComparison.OrdinalIgnoreCase)) continue;
                        string relative = entry.Substring(root.Length + 1).Replace('\\', '/');
                        if (!payload.ContainsKey(relative)) return true;
                    }
                }
            }
            return false;
        }
        public void VerifyInstalled()
        {
            foreach (var item in payload)
                if (FileHash(Target(item.Key)) != Hash(item.Value))
                    throw new InvalidDataException("安装文件缺失或与本版不一致，请重新安装：" + item.Key);
            if (FileHash(Target(LicensePath)) != Hash(Resource("REFramework-LICENSE.txt")))
                throw new InvalidDataException("REFramework 许可证缺失或不一致，请重新安装。");
#if MOD_TESTS
            if (FailVerification) throw new IOException("Injected verification failure");
#endif
        }
        public string Run(bool install)
        {
            if (running()) throw new InvalidOperationException("请先退出鬼泣 5，再安装或卸载 Mod。");
            // Lock spans recovery, planning, backup and commit; competing launchers cannot interleave.
            string lockPath = Resolve(Store + "/operation.lock"); Directory.CreateDirectory(Path.GetDirectoryName(lockPath));
            using (var lease = new FileStream(lockPath, FileMode.OpenOrCreate, FileAccess.ReadWrite, FileShare.None))
            {
                Recover();
                operation = Store + "/history/" + DateTime.UtcNow.ToString("yyyyMMdd-HHmmss") + "-" + Guid.NewGuid().ToString("N"); backupNumber = 0;
                var state = ReadState();
                var changes = new List<FileChange>();
                int untouched = 0;
                bool keptRuntime = false;
                if (install)
                {
                    foreach (var item in payload)
                    {
                        string path = Target(item.Key), current = FileHash(path);
                        var owned = state.Files.Find(f => f.Path == item.Key);
                        // Installation deploys one verified payload, including the loader.
                        // Change() backs up the current bytes even when an owned file was edited.
                        if (owned == null)
                        {
                            owned = new OwnedFile { Path = item.Key };
                            // An exact copy of this release is an existing installation of our Mod.
                            // Unknown same-name files are originals and are restored on uninstall.
                            if (current != null && current != Hash(item.Value))
                            { owned.Original = Snapshot(path); owned.OriginalHash = current; owned.OriginalTime = File.GetLastWriteTimeUtc(path).Ticks; }
                            state.Files.Add(owned);
                        }
                        owned.InstalledHash = Hash(item.Value);
                        changes.Add(Change(item.Key, item.Value));
                    }
                    changes.Add(Change(LicensePath, Resource("REFramework-LICENSE.txt")));
                    changes.Add(Change(StatePath, Serialize(state)));
                }
                else
                {
                    // Adopt only byte-for-byte known scripts when removing a pre-launcher install.
                    if (!File.Exists(Target(StatePath)))
                        foreach (var item in payload.Where(p => p.Key != "dinput8.dll"))
                        {
                            string hash = FileHash(Target(item.Key));
                            if (hash == Hash(item.Value)) state.Files.Add(new OwnedFile { Path = item.Key, InstalledHash = hash });
                            else if (hash != null) untouched++;
                        }
                    bool otherMods = OtherMods();
                    foreach (var owned in state.Files)
                    {
                        string current = FileHash(Target(owned.Path));
                        if (owned.Path == "dinput8.dll" &&
                            ((otherMods && owned.Original == null) || (current != null && current != owned.InstalledHash)))
                        { keptRuntime = true; continue; }
                        if (current != null && current != owned.InstalledHash)
                            throw new IOException("文件在安装后被修改，已停止卸载并保留原样：" + owned.Path);
                        changes.Add(Change(owned.Path, owned.Original == null ? null : BackupBytes(owned.Original, owned.OriginalHash), owned.OriginalTime));
                    }
                    // Unowned loaders and newly shared loaders without an original stay in place.
                    keptRuntime = keptRuntime || (File.Exists(Target("dinput8.dll")) && !state.Files.Any(f => f.Path == "dinput8.dll"));
                    changes.Add(Change(StatePath, null));
                }
                if (running()) throw new InvalidOperationException("游戏刚刚启动，已取消文件更改。请退出游戏后重试。");
                Commit(changes, install ? (Action)VerifyInstalled : null);
                if (install) return "安装完成，15 个脚本和 REFramework 加载器均已逐项校验。按键设置已保留。原文件备份在游戏目录的 " + Store + "/history/。";
                return (untouched == 0 ? "卸载完成，已恢复安装前的同名文件；按键设置和备份保留。" : "已移除可确认的本 Mod 文件；另有 " + untouched + " 个未知同名文件保留，需手动确认。") + (keptRuntime ? "原有或共用加载器保留。" : "");
            }
        }
    }
}
