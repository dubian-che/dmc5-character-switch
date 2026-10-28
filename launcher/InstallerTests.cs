using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

namespace Dmc5SwitchLauncher
{
    internal static class InstallerTests
    {
        static void Check(bool value, string label) { if (!value) throw new Exception(label); }
        static string CreateGame(string parent, string name)
        {
            string root = Path.Combine(parent, name); Directory.CreateDirectory(root);
            File.WriteAllText(Path.Combine(root, "DevilMayCry5.exe"), "fake game fixture; never executed");
            File.WriteAllText(Path.Combine(root, "re_chunk_000.pak"), "original game data");
            return root;
        }
        static string Target(string root, string relative) { return Path.Combine(root, relative.Replace('/', Path.DirectorySeparatorChar)); }
        static void Put(string root, string relative, string value)
        { string path = Target(root, relative); Directory.CreateDirectory(Path.GetDirectoryName(path)); File.WriteAllText(path, value); }
        static void MustFail(Action action, string message)
        {
            bool failed = false; try { action(); } catch { failed = true; }
            Check(failed, message);
        }
        static Dictionary<string, string> Snapshot(string root)
        {
            return Directory.GetFiles(root, "*", SearchOption.AllDirectories)
                .Where(f => !f.Substring(root.Length + 1).StartsWith(ModInstaller.Store + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                .ToDictionary(f => f.Substring(root.Length + 1), f => ModInstaller.Hash(File.ReadAllBytes(f)));
        }
        static void Same(Dictionary<string, string> before, string root, string label)
        {
            var after = Snapshot(root);
            Check(before.Count == after.Count && before.All(kv => after.ContainsKey(kv.Key) && after[kv.Key] == kv.Value), label);
        }
        public static int Run(string report)
        {
            string parent = Path.Combine(Path.GetTempPath(), "dmc5-install-test-" + Guid.NewGuid().ToString("N"));
            var passed = new List<string>();
            try
            {
                string root = CreateGame(parent, "clean");
                Put(root, "reframework/data/dmc5_switch_config.json", "{\"nextKey\":118,\"previousKey\":119}");
                var before = Snapshot(root);
                var installer = new ModInstaller(root, () => false);
                installer.Run(true);
                Check(Game.ModProblem(root) == null, "clean install complete");
                installer.Run(true); // An update must not turn our own prior files into originals.
                installer.Run(false); Same(before, root, "clean install/update/uninstall preserves exact original contents");
                installer.Run(false); Same(before, root, "repeated uninstall");
                passed.Add("clean installation + idempotent update + uninstall; original EXE/PAK/config unchanged");

                root = CreateGame(parent, "original-conflict");
                string originalPath = ModInstaller.ModulePath("dmc5_switch_core.lua");
                Put(root, originalPath, "pre-existing same-name content");
                DateTime originalTime = new DateTime(2024, 1, 2, 3, 4, 5, DateTimeKind.Utc);
                File.SetLastWriteTimeUtc(Target(root, originalPath), originalTime);
                Put(root, "dinput8.dll", "pre-existing third-party loader");
                Put(root, "reframework/autorun/another-mod.lua", "do not change");
                before = Snapshot(root); installer = new ModInstaller(root, () => false);
                installer.Run(true); installer.VerifyInstalled();
                Check(File.ReadAllText(Target(root, "dinput8.dll")) != "pre-existing third-party loader", "old loader was silently retained");
                installer.Run(true); installer.Run(false); Same(before, root, "original restore + other mod preservation");
                Check(File.GetLastWriteTimeUtc(Target(root, originalPath)) == originalTime, "restored timestamp");
                passed.Add("old loader replaced by pinned runtime; repeated update/uninstall restores original loader and scripts with other mods preserved");

                root = CreateGame(parent, "shared-runtime"); installer = new ModInstaller(root, () => false); installer.Run(true);
                string runtimeHash = ModInstaller.Hash(File.ReadAllBytes(Target(root, "dinput8.dll")));
                Put(root, "reframework/plugins/other.dll", "new shared-loader plugin");
                installer.Run(false);
                Check(ModInstaller.Hash(File.ReadAllBytes(Target(root, "dinput8.dll"))) == runtimeHash, "shared runtime removed");
                Check(File.Exists(Target(root, "reframework/plugins/other.dll")), "other plugin removed");
                Check(!File.Exists(Target(root, ModInstaller.ModulePath("dmc5_live_switch.lua"))), "our autorun remains");
                passed.Add("shared runtime retained after another plugin is installed");

                root = CreateGame(parent, "edited-owned-file"); installer = new ModInstaller(root, () => false); installer.Run(true);
                Put(root, originalPath, "user's post-install edits"); before = Snapshot(root);
                MustFail(() => installer.Run(false), "modified file uninstall allowed"); Same(before, root, "modified file not preserved on uninstall");
                installer.Run(true); installer.VerifyInstalled();
                Check(Directory.GetFiles(Target(root, ModInstaller.Store + "/history"), "*.bin", SearchOption.AllDirectories)
                    .Any(p => ModInstaller.Hash(File.ReadAllBytes(p)) == ModInstaller.Hash(Encoding.UTF8.GetBytes("user's post-install edits"))), "edited file not backed up before repair");
                passed.Add("edited files block uninstall; explicit update backs up edits and repairs the complete payload");

                root = CreateGame(parent, "verify-every-file"); installer = new ModInstaller(root, () => false); installer.Run(true);
                foreach (string module in ModInstaller.Modules)
                {
                    string file = Target(root, ModInstaller.ModulePath(module)); byte[] bytes = File.ReadAllBytes(file);
                    File.Delete(file); MustFail(installer.VerifyInstalled, "missing module passed verification: " + module);
                    File.WriteAllText(file, "corrupted module"); MustFail(installer.VerifyInstalled, "corrupt module passed verification: " + module);
                    File.WriteAllBytes(file, bytes);
                }
                Put(root, "dinput8.dll", "externally replaced old runtime");
                Check(Game.ModProblem(root) != null, "launcher accepted mismatching runtime");
                File.Delete(Target(root, ModInstaller.ModulePath("dmc5_switch_palace.lua")));
                installer.Run(true); installer.VerifyInstalled(); Check(Game.ModProblem(root) == null, "repaired installation still rejected");
                var verified = ConfigStore.Json.Deserialize<InstallState>(File.ReadAllText(Target(root, ModInstaller.Store + "/installed.json")));
                Check(verified.Files.Count == ModInstaller.Modules.Length + 1, "ownership did not cover all modules and runtime");
                Check(verified.Files.All(f => f.InstalledHash == ModInstaller.Hash(File.ReadAllBytes(Target(root, f.Path)))), "ownership hashes differ from installed files");
                passed.Add("each of 15 missing/corrupt modules detected; mismatching loader blocks launch; complete repair and 16 ownership hashes verified");

                root = CreateGame(parent, "post-verification-rollback");
                Put(root, "dinput8.dll", "original runtime before failed verification");
                Put(root, originalPath, "original script before failed verification"); before = Snapshot(root);
                installer = new ModInstaller(root, () => false); installer.FailVerification = true;
                MustFail(() => installer.Run(true), "post-write verification failure ignored"); Same(before, root, "post-write verification did not roll back");
                Check(!File.Exists(Target(root, ModInstaller.Store + "/pending.json")), "verification rollback journal left behind");
                installer.FailVerification = false; installer.FailAfter = 16;
                MustFail(() => installer.Run(true), "post-runtime failure ignored"); Same(before, root, "runtime replacement did not roll back");
                installer.FailAfter = -1; installer.Run(true); installer.Run(false); Same(before, root, "originals lost after failed verification and retry");
                passed.Add("verification failure and failure after DLL replacement both roll back; retry/uninstall restores exact originals");

                root = CreateGame(parent, "legacy-adoption"); installer = new ModInstaller(root, () => false); installer.Run(true);
                // Simulate the exact known scripts installed before launcher ownership records existed.
                File.Move(Target(root, ModInstaller.Store + "/installed.json"), Target(root, ModInstaller.Store + "/test-detached-state.json"));
                Put(root, originalPath, "unknown same-name file");
                string result = installer.Run(false);
                Check(result.Contains("未知同名文件"), "legacy warning missing");
                Check(File.ReadAllText(Target(root, originalPath)) == "unknown same-name file", "legacy unknown file deleted");
                Check(!File.Exists(Target(root, ModInstaller.ModulePath("dmc5_live_switch.lua"))), "legacy known autorun retained");
                Check(File.Exists(Target(root, "dinput8.dll")), "unowned loader removed");
                passed.Add("existing pre-launcher Mod identified by exact hashes; unknown files and unowned runtime retained");

                root = CreateGame(parent, "install-rollback"); Put(root, originalPath, "before failed install"); before = Snapshot(root);
                installer = new ModInstaller(root, () => false); installer.FailAfter = 5;
                MustFail(() => installer.Run(true), "failure injection not triggered"); Same(before, root, "failed installation rollback");
                Check(!File.Exists(Target(root, ModInstaller.Store + "/pending.json")), "rollback journal not cleared");
                installer.FailAfter = -1; installer.Run(true); before = Snapshot(root);
                installer.FailAfter = 5; MustFail(() => installer.Run(false), "uninstall failure not triggered"); Same(before, root, "failed uninstall rollback");
                installer.FailAfter = -1; installer.Run(false);
                Check(File.ReadAllText(Target(root, originalPath)) == "before failed install", "original lost during retries");
                passed.Add("partial install and uninstall failures roll back completely; retry still restores original");

                root = CreateGame(parent, "pending-recovery"); installer = new ModInstaller(root, () => false); installer.Run(true);
                string modPath = ModInstaller.ModulePath("dmc5_live_switch.lua");
                string snapshot = ModInstaller.Store + "/history/interrupted/1.bin";
                byte[] mod = File.ReadAllBytes(Target(root, modPath));
                Directory.CreateDirectory(Path.GetDirectoryName(Target(root, snapshot))); File.WriteAllBytes(Target(root, snapshot), mod);
                byte[] partial = Encoding.UTF8.GetBytes("interrupted operation");
                Put(root, ModInstaller.Store + "/pending.json", ConfigStore.Json.Serialize(new List<FileChange> {
                    new FileChange { Path = modPath, Before = snapshot, BeforeHash = ModInstaller.Hash(mod), BeforeTime = DateTime.UtcNow.Ticks, AfterHash = ModInstaller.Hash(partial) } }));
                File.WriteAllBytes(Target(root, modPath), partial);
                installer.Run(false);
                Check(!File.Exists(Target(root, modPath)), "interrupted operation did not recover before uninstall");
                passed.Add("interrupted transaction journal recovered before next operation");

                root = CreateGame(parent, "invalid-backup"); Put(root, originalPath, "must restore this"); installer = new ModInstaller(root, () => false); installer.Run(true);
                var state = ConfigStore.Json.Deserialize<InstallState>(File.ReadAllText(Target(root, ModInstaller.Store + "/installed.json")));
                var original = state.Files.Single(f => f.Path == originalPath);
                Put(root, original.Original, "corrupted backup"); before = Snapshot(root);
                MustFail(() => installer.Run(false), "corrupt backup accepted"); Same(before, root, "corrupt backup changed game files");
                passed.Add("corrupt backup stops uninstall before any game-file changes");

                root = CreateGame(parent, "manifest-traversal"); installer = new ModInstaller(root, () => false); installer.Run(true);
                state = ConfigStore.Json.Deserialize<InstallState>(File.ReadAllText(Target(root, ModInstaller.Store + "/installed.json")));
                state.Files[0].Path = "../outside.txt";
                Put(root, ModInstaller.Store + "/installed.json", ConfigStore.Json.Serialize(state)); before = Snapshot(root);
                MustFail(() => installer.Run(false), "manifest path traversal accepted"); Same(before, root, "invalid manifest changed game files");
                passed.Add("manifest paths confined to fixed Mod allowlist");

                root = CreateGame(parent, "running-game"); before = Snapshot(root);
                MustFail(() => new ModInstaller(root, () => true).Run(true), "running game install allowed");
                Same(before, root, "running-game guard mutated files");
                Check(!Directory.Exists(Target(root, ModInstaller.Store)), "running-game guard created backups");
                passed.Add("running-game guard blocks installation before any write");
                File.WriteAllText(report, ConfigStore.Json.Serialize(new { passed = true, testRoot = parent, checks = passed }), new UTF8Encoding(false)); return 0;
            }
            catch (Exception ex)
            { File.WriteAllText(report, ConfigStore.Json.Serialize(new { passed = false, testRoot = parent, checks = passed, error = ex.ToString() }), new UTF8Encoding(false)); return 1; }
        }
    }
}
