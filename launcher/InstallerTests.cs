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
                installer.Run(true); Check(File.ReadAllText(Target(root, "dinput8.dll")) == "pre-existing third-party loader", "existing loader replaced");
                installer.Run(true); installer.Run(false); Same(before, root, "original restore + other mod preservation");
                Check(File.GetLastWriteTimeUtc(Target(root, originalPath)) == originalTime, "restored timestamp");
                passed.Add("same-name originals restored byte-for-byte and timestamp; other mods and existing loader preserved");

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
                MustFail(() => installer.Run(true), "modified file update allowed"); Same(before, root, "modified file not preserved on update");
                passed.Add("post-install file edits block update and uninstall without any game-file changes");

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
