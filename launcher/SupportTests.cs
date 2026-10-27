#if SUPPORT_DIAGNOSTICS && MOD_TESTS
using System;
using System.Collections;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text;
using System.Windows.Forms;

namespace Dmc5SwitchLauncher
{
    public static class SupportTests
    {
        static void Check(bool value, string why) { if (!value) throw new Exception(why); }
        static string Entry(ZipArchive zip, string name) { using (var input = new StreamReader(zip.GetEntry(name).Open(), Encoding.UTF8)) return input.ReadToEnd(); }
        public static int Run(string reportPath)
        {
            string root = Path.Combine(Path.GetTempPath(), "dmc5-support-test-" + Guid.NewGuid().ToString("N"));
            Directory.CreateDirectory(root); var results = new List<string>();
            try
            {
                string game = Path.Combine(root, "game"), output = Path.Combine(root, "exports"); Directory.CreateDirectory(game);
                File.WriteAllText(Path.Combine(game, "DevilMayCry5.exe"), "fixture, never executed");
                Directory.CreateDirectory(Path.Combine(game, "reframework", "data", "dmc5_support"));
                File.WriteAllText(Path.Combine(game, "dinput8.dll"), "existing-loader-preserved");
                string originalLoader = SupportRecorder.Hash(File.ReadAllBytes(Path.Combine(game, "dinput8.dll")));
                string config = ConfigStore.ConfigPath(game); ConfigStore.Save(config, new Bindings { Next = 116, Previous = 117, ControllerCombo = false });
                string configHash = SupportRecorder.Hash(File.ReadAllBytes(config));
                SupportRecorder.Set(game, true, () => false); SupportRecorder.Set(game, true, () => false);
                Check(File.Exists(SupportRecorder.PathIn(game)), "recorder install");
                Check(SupportRecorder.Hash(File.ReadAllBytes(Path.Combine(game, "dinput8.dll"))) == originalLoader, "loader mutated");
                Check(SupportRecorder.Hash(File.ReadAllBytes(config)) == configHash, "config mutated");
                bool refused = false; try { SupportRecorder.Set(game, false, () => true); } catch (InvalidOperationException) { refused = true; }
                Check(refused && File.Exists(SupportRecorder.PathIn(game)), "running process guard");
                File.AppendAllText(SupportRecorder.PathIn(game), "changed"); refused = false;
                try { SupportRecorder.Set(game, false, () => false); } catch (IOException) { refused = true; }
                Check(refused, "foreign recorder overwritten");
                File.WriteAllBytes(SupportRecorder.PathIn(game), SupportRecorder.Payload());
                results.Add("independent recorder ownership, idempotence, process guard, unknown-file refusal; loader/config preserved");
                DateTime now = DateTime.UtcNow; long epoch = SupportExport.Epoch(now);
                string slots = Path.Combine(game, "reframework", "data", "dmc5_support");
                string[] lines = new[] {
                    SupportExport.Json.Serialize(new { schema = 1, utc = epoch - 1801, kind = "OLD" }),
                    SupportExport.Json.Serialize(new { schema = 1, utc = epoch - 1800, kind = "sample", mission = 19, manual = 1 }),
                    SupportExport.Json.Serialize(new { schema = 1, utc = epoch - 15, kind = "F8", mission = 19, manual = 4, modCurrent = 0, modStage = "<script>alert(1)</script>", players = new[] { new { id = 4, manual = true, enabled = false, draw = false, bodyMeshes = 2, automatic = true, hp = 5000, dt = 1000 } } }),
                    SupportExport.Json.Serialize(new { schema = 1, utc = epoch, kind = "sample", mission = 19, manual = 0 }),
                    SupportExport.Json.Serialize(new { schema = 1, utc = epoch + 1, kind = "FUTURE" }),
                    "{partial crash row"
                };
                File.WriteAllText(Path.Combine(slots, "slot-00.jsonl"), String.Join("\n", lines), new UTF8Encoding(false));
                string oldStamp = now.AddMinutes(-31).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss.fff"), stamp = now.AddMinutes(-1).ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss.fff");
                File.WriteAllText(Path.Combine(game, "re2_framework_log.txt"), "[" + oldStamp + "] OLD_NATIVE\n[" + stamp + "] recent native " + game + "\nstack continuation\n", Encoding.UTF8);
                File.WriteAllText(Path.Combine(game, "data000.bin"), "PRIVATE_SAVE_SENTINEL");
                File.WriteAllBytes(Path.Combine(game, "reframework_crash.dmp"), new byte[] { 1, 2, 3, 4 });
                File.SetLastWriteTimeUtc(Path.Combine(game, "reframework_crash.dmp"), now.AddSeconds(-15));
                File.WriteAllBytes(Path.Combine(game, "re2_framework_crash.dmp"), new byte[] { 8, 9 });
                File.SetLastWriteTimeUtc(Path.Combine(game, "re2_framework_crash.dmp"), now.AddMinutes(-31));
                string picture = Path.Combine(root, "PRIVATE_FILE_NAME.png"); using (var image = new Bitmap(40, 30)) image.Save(picture, ImageFormat.Png);
                string issue = "</script><img src=x onerror=alert(9)> " + Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                string zipPath = SupportExport.Export(game, output, issue, new[] { picture }, false, now);
                Check(File.Exists(zipPath) && !File.Exists(zipPath + ".partial"), "atomic export");
                using (var input = File.OpenRead(zipPath))
                using (var zip = new ZipArchive(input, ZipArchiveMode.Read))
                {
                    var manifest = SupportExport.Json.Deserialize<Dictionary<string, object>>(Entry(zip, "导出清单.json"));
                    Check(Convert.ToInt32(manifest["samples"]) == 3 && Convert.ToInt32(manifest["markers"]) == 1, "30 minute sample boundary");
                    string timeline = Entry(zip, "状态时间线.jsonl");
                    Check(!timeline.Contains("OLD") && !timeline.Contains("FUTURE") && !timeline.Contains("partial crash"), "wrong timestamp/partial line included");
                    string native = Entry(zip, "原生日志/re2_framework_log.txt");
                    Check(!native.Contains("OLD_NATIVE") && native.Contains("stack continuation") && native.Contains("<GAME>"), "native log filtering or redaction");
                    string report = Entry(zip, "诊断报告.html");
                    Check(!report.Contains("<img src=x") && !report.Contains("<script>alert(1)</script>"), "HTML injection");
                    Check(!report.Contains(game) && !Entry(zip, "问题描述.txt").Contains(Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)), "path privacy");
                    Check(zip.GetEntry("崩溃转储/reframework_crash.dmp") != null && zip.GetEntry("崩溃转储/re2_framework_crash.dmp") == null, "crash time range");
                    Check(zip.Entries.All(e => !e.FullName.Contains("data000") && !e.FullName.Contains("PRIVATE_FILE_NAME")), "save or image filename leaked");
                    Check(zip.GetEntry("附加截图/1.png") != null, "selected screenshot missing");
                    foreach (Dictionary<string, object> file in (IEnumerable)manifest["files"])
                    {
                        using (var buffer = new MemoryStream())
                        { zip.GetEntry((string)file["path"]).Open().CopyTo(buffer); Check(SupportRecorder.Hash(buffer.ToArray()) == (string)file["sha256"], "archive hash mismatch"); }
                    }
                }
                results.Add("exact 30 minute UTC boundary, F8 markers, partial-row tolerance, local-native timestamp filtering, recent-only crash dump");
                results.Add("ZIP hashes, HTML injection containment, known-path redaction, selected-image re-encoding, save exclusion");
                string future = SupportExport.Export(game, output, "no history", null, false, now.AddHours(1));
                using (var file = File.OpenRead(future)) using (var zip = new ZipArchive(file, ZipArchiveMode.Read))
                    Check(Entry(zip, "导出清单.json").Contains("没有可用状态历史"), "missing history was hidden");
                SupportRecorder.Set(game, false, () => false);
                Check(!File.Exists(SupportRecorder.PathIn(game)) && File.Exists(Path.Combine(slots, "slot-00.jsonl")), "disable removed history");
                results.Add("missing history reported, disable preserves logs, no game launch or actual game installation touched");
                Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(reportPath)));
                Application.EnableVisualStyles();
                using (var form = new LauncherForm())
                using (var bitmap = new Bitmap(form.Width, form.Height))
                {
                    form.Opacity = 0; form.ShowInTaskbar = false; form.Show(); Application.DoEvents();
                    form.DrawToBitmap(bitmap, new Rectangle(0, 0, bitmap.Width, bitmap.Height)); form.Hide();
                    bitmap.Save(Path.Combine(Path.GetDirectoryName(Path.GetFullPath(reportPath)), "support-launcher-ui.png"), ImageFormat.Png);
                    Check(form.Text.Contains("远端诊断版"), "diagnostic UI title");
                }
                File.WriteAllText(reportPath, SupportExport.Json.Serialize(new { passed = true, checks = results, artifactRoot = root, zip = zipPath }), Encoding.UTF8);
                return 0;
            }
            catch (Exception ex)
            { File.WriteAllText(reportPath, SupportExport.Json.Serialize(new { passed = false, error = ex.ToString(), artifactRoot = root }), Encoding.UTF8); return 1; }
        }
    }
}
#endif
