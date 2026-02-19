using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

class RenmaeAILauncher
{
    static void Main()
    {
        string exeDir = AppDomain.CurrentDomain.BaseDirectory;
        string projectDir = exeDir.TrimEnd(Path.DirectorySeparatorChar);

        if (!File.Exists(Path.Combine(projectDir, "backend", "main.py")) ||
            !File.Exists(Path.Combine(projectDir, "package.json")))
        {
            Console.WriteLine("[ERROR] Place this .exe in the project root folder.");
            Console.ReadKey();
            return;
        }

        Console.Title = "RenmaeAI Studio";
        Console.WriteLine();
        Console.WriteLine("  RenmaeAI Studio is starting...");
        Console.WriteLine();

        string venvActivate = Path.Combine(projectDir, ".venv", "Scripts", "activate.bat");
        string backendDir = Path.Combine(projectDir, "backend");

        // Start Backend (hidden)
        string backendCmd;
        if (File.Exists(venvActivate))
            backendCmd = string.Format("/c cd /d \"{0}\" && call \"{1}\" && python -m uvicorn main:app --reload --port 8000", backendDir, venvActivate);
        else
            backendCmd = string.Format("/c cd /d \"{0}\" && python -m uvicorn main:app --reload --port 8000", backendDir);

        Process.Start(new ProcessStartInfo("cmd.exe", backendCmd)
        {
            WindowStyle = ProcessWindowStyle.Hidden,
            CreateNoWindow = true
        });

        // Start Electron immediately (it has its own wait-on logic)
        string frontendCmd = string.Format("/c cd /d \"{0}\" && npm run dev", projectDir);
        Process.Start(new ProcessStartInfo("cmd.exe", frontendCmd)
        {
            WindowStyle = ProcessWindowStyle.Hidden,
            CreateNoWindow = true
        });

        Console.WriteLine("  App is loading... the window will appear shortly.");
        Console.WriteLine("  Press any key to stop the app.");
        Console.ReadKey();

        // Cleanup on exit
        KillPort(8000);
        KillPort(5173);
    }

    static void KillPort(int port)
    {
        try
        {
            Process.Start(new ProcessStartInfo("cmd.exe",
                string.Format("/c for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{0} ^| findstr LISTENING') do taskkill /f /pid %a", port))
            {
                WindowStyle = ProcessWindowStyle.Hidden,
                CreateNoWindow = true
            });
        }
        catch { }
    }
}
