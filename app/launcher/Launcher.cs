using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net.Sockets;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Windows.Forms;

[assembly: AssemblyTitle("Extra")]
[assembly: AssemblyDescription("Extra")]
[assembly: AssemblyConfiguration("")]
[assembly: AssemblyCompany("yantraOS")]
[assembly: AssemblyProduct("Extra")]
[assembly: AssemblyCopyright("Copyright (C) 2026 yantraOS. All rights reserved.")]
[assembly: AssemblyTrademark("Extra")]
[assembly: AssemblyCulture("")]
[assembly: AssemblyVersion("0.3.5.0")]
[assembly: AssemblyFileVersion("0.3.5.0")]

namespace ExtraLauncher
{
    /// <summary>
    /// Borderless splash: paints in &lt;100ms so the launch never feels dead.
    /// The bar only advances on real backend milestones ([SPLASH] stdout lines),
    /// with a slow honesty-capped creep between them. Never reaches 100%
    /// until the server answers and the cockpit window is visible.
    /// </summary>
    internal sealed class SplashForm : Form
    {
        private static readonly Color Ink = Color.FromArgb(0x1A, 0x1A, 0x1C);
        private static readonly Color Muted = Color.FromArgb(0x86, 0x8C, 0x98);
        private static readonly Color Track = Color.FromArgb(0xE2, 0xE7, 0xED);
        private static readonly Color Accent = Color.FromArgb(0x16, 0x77, 0xFF);

        private readonly Label _title;
        private readonly Label _subtitle;
        private readonly Label _status;
        private readonly Panel _track;
        private readonly System.Windows.Forms.Timer _timer;

        private double _current;
        private double _target;
        private string _stageLabel = "Starting Extra";
        private DateTime _lastMilestone = DateTime.UtcNow;
        private DateTime _started = DateTime.UtcNow;
        private int _dotTick;
        private int _slowIndex = -1;
        private readonly DateTime _t0 = DateTime.UtcNow;
        private bool _finishing;

        private static readonly string[] SlowTexts = new string[]
        {
            "First launch takes longer — unpacking the engine…",
            "Still working — warming the local relay…",
        };

        protected override CreateParams CreateParams
        {
            get
            {
                CreateParams cp = base.CreateParams;
                cp.ClassStyle |= 0x00020000; // CS_DROPSHADOW
                return cp;
            }
        }

        public SplashForm()
        {
            this.FormBorderStyle = FormBorderStyle.None;
            this.StartPosition = FormStartPosition.CenterScreen;
            this.Size = new Size(440, 268);
            this.BackColor = Color.White;
            this.TopMost = true;
            this.ShowInTaskbar = false;
            this.Text = "Extra";

            Panel brandStrip = new Panel();
            brandStrip.BackColor = Accent;
            brandStrip.Dock = DockStyle.Bottom;
            brandStrip.Height = 4;
            this.Controls.Add(brandStrip);

            _title = new Label();
            _title.Text = "Extra";
            _title.Font = new Font(SystemFonts.DefaultFont.FontFamily, 22f, FontStyle.Bold);
            _title.ForeColor = Ink;
            _title.AutoSize = true;
            _title.Location = new Point(36, 30);
            this.Controls.Add(_title);

            _subtitle = new Label();
            _subtitle.Text = "by YantraOS";
            _subtitle.Font = new Font(SystemFonts.DefaultFont.FontFamily, 11f, FontStyle.Regular);
            _subtitle.ForeColor = Muted;
            _subtitle.AutoSize = true;
            _subtitle.Location = new Point(38, 66);
            this.Controls.Add(_subtitle);

            _status = new Label();
            _status.Text = "Starting Extra";
            _status.Font = new Font(SystemFonts.DefaultFont.FontFamily, 11f, FontStyle.Regular);
            _status.ForeColor = Color.FromArgb(0x52, 0x58, 0x66);
            _status.AutoSize = false;
            _status.Location = new Point(36, 128);
            _status.Size = new Size(368, 22);
            this.Controls.Add(_status);

            _track = new Panel();
            _track.Location = new Point(36, 162);
            _track.Size = new Size(368, 6);
            _track.BackColor = Color.White;
            _track.Paint += new PaintEventHandler(Track_Paint);
            this.Controls.Add(_track);

            Label version = new Label();
            version.Text = "v0.3.5 · YantraOS";
            version.Font = new Font(SystemFonts.DefaultFont.FontFamily, 9f, FontStyle.Regular);
            version.ForeColor = Muted;
            version.AutoSize = true;
            version.Location = new Point(36, 224);
            this.Controls.Add(version);

            _timer = new System.Windows.Forms.Timer();
            _timer.Interval = 50;
            _timer.Tick += new EventHandler(Timer_Tick);
            _timer.Start();
        }

        public void ReportMilestone(string stage, string label)
        {
            // Called from the worker thread.
            double target = _target;
            if (stage == "engine" && target < 28) { target = 28; }
            else if (stage == "server" && target < 62) { target = 62; }
            else if (stage == "window" && target < 86) { target = 86; }
            if (!string.IsNullOrEmpty(label)) { _stageLabel = label; }
            _target = target;
            _lastMilestone = DateTime.UtcNow;
        }

        public void ReportFinished()
        {
            _finishing = true;
            _target = 100;
        }

        private void Timer_Tick(object sender, EventArgs e)
        {
            // Ease toward the target: fast early, slow late. Creep forward
            // slowly between milestones but never past 90 until truly done.
            double gap = _target - _current;
            double step = _finishing ? Math.Max(gap * 0.3, 2.0) : gap * 0.07;
            double idle = (DateTime.UtcNow - _lastMilestone).TotalSeconds;
            if (!_finishing && _current < 90 && gap < 1.0 && idle > 4)
            {
                step = Math.Max(step, 0.12);
            }
            _current = Math.Min(100, _current + Math.Max(step, 0));
            if (_finishing && _current >= 99.5)
            {
                _timer.Stop();
                this.Close();
                return;
            }

            _dotTick++;
            string dots = new string('.', 1 + ((_dotTick / 10) % 3));

            double elapsed = (DateTime.UtcNow - _t0).TotalSeconds;
            string text = _stageLabel;
            if (!_finishing && elapsed > 25 && _current < 86)
            {
                int idx = (int)(elapsed / 8) % SlowTexts.Length;
                if (idx != _slowIndex) { _slowIndex = idx; }
                text = SlowTexts[idx];
            }
            _status.Text = text + dots;
            _track.Invalidate();
        }

        private void Track_Paint(object sender, PaintEventArgs e)
        {
            Graphics g = e.Graphics;
            g.SmoothingMode = SmoothingMode.AntiAlias;
            Rectangle track = new Rectangle(0, 0, _track.Width - 1, _track.Height - 1);
            using (GraphicsPath path = RoundedRect(track, 3))
            using (SolidBrush bg = new SolidBrush(Track))
            {
                g.FillPath(bg, path);
            }
            int fillW = (int)Math.Round((_track.Width - 1) * (_current / 100.0));
            if (fillW > 0)
            {
                Rectangle fill = new Rectangle(0, 0, fillW, _track.Height - 1);
                using (GraphicsPath path = RoundedRect(fill, 3))
                using (SolidBrush fg = new SolidBrush(Accent))
                {
                    g.FillPath(fg, path);
                }
            }
        }

        private static GraphicsPath RoundedRect(Rectangle r, int radius)
        {
            GraphicsPath path = new GraphicsPath();
            int d = radius * 2;
            path.AddArc(r.X, r.Y, d, d, 180, 90);
            path.AddArc(r.Right - d, r.Y, d, d, 270, 90);
            path.AddArc(r.Right - d, r.Bottom - d, d, d, 0, 90);
            path.AddArc(r.X, r.Bottom - d, d, d, 90, 90);
            path.CloseFigure();
            return path;
        }
    }

    static class Program
    {
        [DllImport("shell32.dll", SetLastError = true)]
        private static extern void SetCurrentProcessExplicitAppUserModelID([MarshalAs(UnmanagedType.LPWStr)] string AppID);

        [DllImport("user32.dll", SetLastError = true)]
        private static extern IntPtr FindWindow(string lpClassName, string lpWindowName);

        [DllImport("user32.dll")]
        private static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool SetForegroundWindow(IntPtr hWnd);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);

        [DllImport("user32.dll")]
        private static extern int GetWindowThreadProcessId(IntPtr hWnd, out int lpdwProcessId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern IntPtr OpenProcess(int dwDesiredAccess, bool bInheritHandle, int dwProcessId);

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool CloseHandle(IntPtr hObject);

        [DllImport("psapi.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern int GetModuleFileNameEx(IntPtr hProcess, IntPtr hModule, StringBuilder lpFilename, int nSize);

        [DllImport("user32.dll")]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool IsWindowVisible(IntPtr hWnd);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr hWnd, StringBuilder lpString, int nMaxCount);

        private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

        private const int SW_RESTORE = 9;
        private static Mutex _appMutex;
        private static volatile bool _windowSeen;
        private static IntPtr _foundHwnd = IntPtr.Zero;

        private static void QuietBoot(string[] args)
        {
            Thread worker = new Thread(delegate () { RunBackend(args, null); });
            worker.IsBackground = false;
            worker.Start();
            worker.Join();
        }

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool AttachConsole(int dwProcessId);

        [DllImport("user32.dll")]
        private static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

        private static NotifyIcon _notifyIcon;
        private static Process _backendProc;
        private static volatile bool _backendStarted;

        private static void InitializeTrayIcon()
        {
            try
            {
                _notifyIcon = new NotifyIcon();
                Icon appIcon = null;
                try
                {
                    appIcon = Icon.ExtractAssociatedIcon(Assembly.GetExecutingAssembly().Location);
                }
                catch { }
                if (appIcon == null)
                {
                    appIcon = SystemIcons.Application;
                }
                _notifyIcon.Icon = appIcon;
                _notifyIcon.Text = "Extra Desktop — Active\nDouble-click to open Cockpit";
                _notifyIcon.Visible = true;

                ContextMenu menu = new ContextMenu();
                MenuItem openItem = new MenuItem("Open Extra Cockpit", delegate { FocusOrReopenWindow(); });
                openItem.DefaultItem = true;
                menu.MenuItems.Add(openItem);

                menu.MenuItems.Add(new MenuItem("Emergency Panic Stop (Ctrl+Alt+Esc)", delegate { TriggerEmergencyStop(); }));
                menu.MenuItems.Add(new MenuItem("-"));
                menu.MenuItems.Add(new MenuItem("Quit Extra", delegate { ExitApplication(); }));

                _notifyIcon.ContextMenu = menu;

                _notifyIcon.DoubleClick += delegate { FocusOrReopenWindow(); };
                _notifyIcon.Click += delegate (object s, EventArgs e)
                {
                    MouseEventArgs me = e as MouseEventArgs;
                    if (me != null && me.Button == MouseButtons.Left)
                    {
                        FocusOrReopenWindow();
                    }
                };
            }
            catch { }
        }

        private static void FocusOrReopenWindow()
        {
            IntPtr existingHwnd = FindWindow(null, "Extra");
            if (existingHwnd != IntPtr.Zero && !IsAppWindow(existingHwnd))
            {
                existingHwnd = IntPtr.Zero;
            }
            if (existingHwnd == IntPtr.Zero)
            {
                FindExtraWindow();
                existingHwnd = _foundHwnd;
            }
            if (existingHwnd != IntPtr.Zero)
            {
                ShowWindow(existingHwnd, SW_RESTORE);
                SetForegroundWindow(existingHwnd);
                return;
            }
            QuietBoot(new string[0]);
        }

        private static void TriggerEmergencyStop()
        {
            try
            {
                keybd_event(0x11, 0, 0, UIntPtr.Zero);
                keybd_event(0x12, 0, 0, UIntPtr.Zero);
                keybd_event(0x1B, 0, 0, UIntPtr.Zero);
                Thread.Sleep(50);
                keybd_event(0x1B, 0, 2, UIntPtr.Zero);
                keybd_event(0x12, 0, 2, UIntPtr.Zero);
                keybd_event(0x11, 0, 2, UIntPtr.Zero);
            }
            catch { }
        }

        private static void ExitApplication()
        {
            try
            {
                if (_notifyIcon != null)
                {
                    _notifyIcon.Visible = false;
                    _notifyIcon.Dispose();
                    _notifyIcon = null;
                }
            }
            catch { }
            try
            {
                if (_backendProc != null && !_backendProc.HasExited)
                {
                    _backendProc.Kill();
                }
            }
            catch { }
            try
            {
                Application.Exit();
            }
            catch { }
        }

        private const int ATTACH_PARENT_PROCESS = -1;

        [STAThread]
        static void Main(string[] args)
        {
            try
            {
                SetCurrentProcessExplicitAppUserModelID("yantraOS.Extra");
            }
            catch { }

            string[] passArgs = args ?? new string[0];

            // If CLI arguments are provided (e.g. `extra connect --key ...`), dispatch directly to Extra CLI!
            if (passArgs.Length > 0)
            {
                int exitCode = RunCli(passArgs);
                Environment.Exit(exitCode);
                return;
            }

            // 0. Single-Instance Fast Path: no splash when just refocusing.
            bool createdNew;
            _appMutex = new Mutex(true, "yantraOS_Extra_MissionControl_Mutex", out createdNew);
            if (!createdNew)
            {
                IntPtr existingHwnd = FindWindow(null, "Extra");
                if (existingHwnd != IntPtr.Zero && !IsAppWindow(existingHwnd))
                {
                    existingHwnd = IntPtr.Zero;
                }
                if (existingHwnd == IntPtr.Zero)
                {
                    // Fall back to substring match (Edge app window titles vary).
                    FindExtraWindow();
                    existingHwnd = _foundHwnd;
                }
                if (existingHwnd != IntPtr.Zero)
                {
                    ShowWindow(existingHwnd, SW_RESTORE);
                    SetForegroundWindow(existingHwnd);
                    return; // Instant exit
                }
                // Backend alive but windowless (user closed the window, server
                // kept running): revive quietly without a splash. run_app will
                // focus or reopen the window against the live server.
                QuietBoot(passArgs);
                return;
            }

            // Immediately release launcher check mutex so python worker process can claim the persistent mutex
            try
            {
                _appMutex.ReleaseMutex();
                _appMutex.Close();
            }
            catch { }

            SplashForm splash = new SplashForm();
            Thread worker = new Thread(delegate () { RunBackend(passArgs, splash); });
            worker.IsBackground = true;
            worker.Start();
            Application.Run(splash);

            if (_backendStarted)
            {
                InitializeTrayIcon();
                Application.Run();
            }
        }

        private static int RunCli(string[] args)
        {
            try
            {
                AttachConsole(ATTACH_PARENT_PROCESS);
            }
            catch { }

            string pyExe = FindPython();
            if (pyExe == null)
            {
                Console.Error.WriteLine("[!] Error: Python runtime not found for Extra CLI.");
                return 1;
            }

            StringBuilder sb = new StringBuilder();
            sb.Append("-m extra.cli");
            for (int i = 0; i < args.Length; i++)
            {
                sb.Append(' ');
                string a = args[i];
                if (a.Contains(" ") || a.Contains("\""))
                {
                    sb.Append('"').Append(a.Replace("\"", "\\\"")).Append('"');
                }
                else
                {
                    sb.Append(a);
                }
            }

            ProcessStartInfo psi = new ProcessStartInfo();
            psi.FileName = pyExe;
            psi.Arguments = sb.ToString();
            psi.UseShellExecute = false;

            string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string extraAppDir = Path.Combine(userProfile, @".extra\app");
            string extraSrc = Path.Combine(extraAppDir, "src");
            string pythonPath = extraSrc + ";" + extraAppDir + @";D:\yantra_workspace\extra\src;D:\yantra_workspace\extra;" + (Environment.GetEnvironmentVariable("PYTHONPATH") ?? "");
            psi.EnvironmentVariables["PYTHONPATH"] = pythonPath;

            try
            {
                using (Process proc = Process.Start(psi))
                {
                    proc.WaitForExit();
                    return proc.ExitCode;
                }
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine("[!] Error running Extra CLI: " + ex.Message);
                return 1;
            }
        }

        private static void RunBackend(string[] args, SplashForm splash)
        {
            string targetScript = FindScript();
            string pyExe = FindPython();
            string onedirExe = FindOnedir();

            if (targetScript != null && pyExe != null)
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = pyExe;
                    StringBuilder sb = new StringBuilder();
                    sb.Append('"').Append(targetScript).Append('"');
                    if (args != null)
                    {
                        for (int i = 0; i < args.Length; i++)
                        {
                            sb.Append(' ').Append(args[i]);
                        }
                    }
                    psi.Arguments = sb.ToString();
                    psi.WorkingDirectory = Path.GetDirectoryName(targetScript);
                    psi.UseShellExecute = false;
                    psi.CreateNoWindow = true;
                    psi.RedirectStandardOutput = true;
                    psi.WindowStyle = ProcessWindowStyle.Hidden;

                    Process proc = new Process();
                    _backendProc = proc;
                    proc.EnableRaisingEvents = true;
                    proc.Exited += delegate {
                        try {
                            if (_notifyIcon != null) {
                                _notifyIcon.Visible = false;
                                _notifyIcon.Dispose();
                                _notifyIcon = null;
                            }
                            Application.Exit();
                        } catch { }
                    };
                    proc.StartInfo = psi;
                    proc.OutputDataReceived += delegate (object s, DataReceivedEventArgs e)
                    {
                        if (splash == null || splash.IsDisposed) { return; }
                        string line = e.Data;
                        if (string.IsNullOrEmpty(line)) { return; }
                        int at = line.IndexOf("[SPLASH]", StringComparison.Ordinal);
                        if (at < 0) { return; }
                        string rest = line.Substring(at + "[SPLASH]".Length).Trim();
                        string stage = ParseField(rest, "stage");
                        string label = ParseField(rest, "label");
                        try
                        {
                            splash.Invoke(new Action(delegate ()
                            {
                                if (!splash.IsDisposed) { splash.ReportMilestone(stage, label); }
                            }));
                        }
                        catch { }
                    };
                    proc.Start();
                    proc.BeginOutputReadLine();

                    WaitForReady(splash);
                    _backendStarted = true;
                    if (splash != null)
                    {
                        try
                        {
                            if (!splash.IsDisposed)
                            {
                                splash.Invoke(new Action(delegate ()
                                {
                                    if (!splash.IsDisposed) { splash.ReportFinished(); }
                                }));
                            }
                        }
                        catch { }
                    }
                    return;
                }
                catch (Exception ex)
                {
                    CloseSplash(splash);
                    MessageBox.Show("Extra failed to start: " + ex.Message, "Extra",
                        MessageBoxButtons.OK, MessageBoxIcon.Error);
                    return;
                }
            }

            if (onedirExe != null)
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo();
                    psi.FileName = onedirExe;
                    psi.WorkingDirectory = Path.GetDirectoryName(onedirExe);
                    Process.Start(psi);
                }
                catch { }
                CloseSplash(splash);
                return;
            }

            CloseSplash(splash);
            MessageBox.Show(
                "Unable to locate Extra runtime environment.\nPlease verify Python 3.13 or Extra application installation.",
                "Extra",
                MessageBoxButtons.OK,
                MessageBoxIcon.Error);
        }

        private static string ParseField(string rest, string key)
        {
            string needle = key + "=";
            int i = rest.IndexOf(needle, StringComparison.Ordinal);
            if (i < 0) { return string.Empty; }
            string tail = rest.Substring(i + needle.Length);
            // label is always last; stage has no spaces. Take label to end of line.
            if (key == "label") { return tail.Trim(); }
            int sp = tail.IndexOf(' ');
            if (sp < 0) { return tail.Trim(); }
            return tail.Substring(0, sp).Trim();
        }

        /// <summary>
        /// Blocks until the cockpit server answers AND the app window is
        /// visible (or 120s pass — then the splash just gets out of the way).
        /// </summary>
        private static void WaitForReady(SplashForm splash)
        {
            DateTime deadline = DateTime.UtcNow.AddSeconds(120);
            while (DateTime.UtcNow < deadline)
            {
                if (splash != null && splash.IsDisposed) { return; }
                if (PortResponds(5173) || PortResponds(5174))
                {
                    // Give the Edge window a moment to appear, then finish.
                    DateTime winDeadline = DateTime.UtcNow.AddSeconds(10);
                    while (DateTime.UtcNow < winDeadline)
                    {
                        if (splash != null && splash.IsDisposed) { return; }
                        if (FindExtraWindow()) { return; }
                        Thread.Sleep(250);
                    }
                    return;
                }
                Thread.Sleep(300);
            }
        }

        private static bool PortResponds(int port)
        {
            try
            {
                using (TcpClient c = new TcpClient())
                {
                    IAsyncResult ar = c.BeginConnect("127.0.0.1", port, null, null);
                    bool ok = ar.AsyncWaitHandle.WaitOne(400);
                    if (!ok) { return false; }
                    c.EndConnect(ar);
                    return true;
                }
            }
            catch { return false; }
        }

        /// <summary>
        /// Title matching alone is not identity: unrelated windows (an Explorer
        /// artifact, another program's tab) can also contain "Extra". Only the
        /// Edge/Chrome host we launched may claim a boot.
        /// </summary>
        private static bool IsAppWindow(IntPtr hWnd)
        {
            try
            {
                int pid;
                GetWindowThreadProcessId(hWnd, out pid);
                if (pid == 0) { return false; }
                const int PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
                IntPtr hProcess = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
                if (hProcess == IntPtr.Zero) { return false; }
                try
                {
                    StringBuilder path = new StringBuilder(260);
                    if (GetModuleFileNameEx(hProcess, IntPtr.Zero, path, path.Capacity) == 0)
                    {
                        return false;
                    }
                    string exe = path.ToString().ToLowerInvariant();
                    return exe.EndsWith("msedge.exe") || exe.EndsWith("chrome.exe");
                }
                finally
                {
                    CloseHandle(hProcess);
                }
            }
            catch { return false; }
        }

        private static bool FindExtraWindow()
        {
            _windowSeen = false;
            _foundHwnd = IntPtr.Zero;
            try
            {
                EnumWindows(delegate (IntPtr hWnd, IntPtr lParam)
                {
                    if (!IsWindowVisible(hWnd)) { return true; }
                    StringBuilder sb = new StringBuilder(256);
                    GetWindowText(hWnd, sb, sb.Capacity);
                    string title = sb.ToString();
                    if (!string.IsNullOrEmpty(title) &&
                        title.IndexOf("Extra", StringComparison.OrdinalIgnoreCase) >= 0 &&
                        IsAppWindow(hWnd))
                    {
                        _windowSeen = true;
                        _foundHwnd = hWnd;
                        return false;
                    }
                    return true;
                }, IntPtr.Zero);
            }
            catch { }
            return _windowSeen;
        }

        private static void CloseSplash(SplashForm splash)
        {
            if (splash == null) { return; }
            try
            {
                if (!splash.IsDisposed)
                {
                    splash.Invoke(new Action(delegate ()
                    {
                        if (!splash.IsDisposed) { splash.Close(); }
                    }));
                }
            }
            catch { }
        }

        private static string FindScript()
        {
            string baseDir = AppDomain.CurrentDomain.BaseDirectory;
            string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string extraDir = Path.Combine(userProfile, ".extra");
            string[] candidates = new string[]
            {
                @"D:\yantra_workspace\extra\app\run_app.py",
                Path.Combine(extraDir, @"app\run_app.py"),
                Path.Combine(baseDir, "run_app.py"),
                Path.Combine(baseDir, @"app\run_app.py"),
                @"D:\yantra_workspace\extraApp\run_app.py",
            };
            for (int i = 0; i < candidates.Length; i++)
            {
                if (File.Exists(candidates[i])) { return candidates[i]; }
            }
            return null;
        }

        private static string FindPython()
        {
            string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string[] candidates = new string[]
            {
                Path.Combine(userProfile, @".extra\venv\Scripts\python.exe"),
                @"C:\Program Files\Python313\python.exe",
                @"C:\Program Files\Python312\python.exe",
                @"C:\Program Files\Python311\python.exe",
                Path.Combine(userProfile, @"AppData\Local\Programs\Python\Python313\python.exe"),
                Path.Combine(userProfile, @"AppData\Local\Programs\Python\Python312\python.exe"),
                @"D:\yantra_workspace\extra\.venv\Scripts\python.exe",
            };
            for (int i = 0; i < candidates.Length; i++)
            {
                if (File.Exists(candidates[i])) { return candidates[i]; }
            }
            string pathEnv = Environment.GetEnvironmentVariable("PATH") ?? "";
            string[] parts = pathEnv.Split(';');
            for (int i = 0; i < parts.Length; i++)
            {
                string p = parts[i].Trim();
                if (p.Length == 0) { continue; }
                string cand = Path.Combine(p, "python.exe");
                if (File.Exists(cand)) { return cand; }
            }
            return null;
        }

        private static string FindOnedir()
        {
            string userProfile = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
            string extraDir = Path.Combine(userProfile, ".extra");
            string onedirExe = Path.Combine(extraDir, @"app\Extra.exe");
            if (File.Exists(onedirExe)) { return onedirExe; }
            return null;
        }
    }
}
