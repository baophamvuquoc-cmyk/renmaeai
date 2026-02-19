using System;
using System.Diagnostics;
using System.IO;
using System.Threading;
using System.Net;

class RenmaeAILauncher
{
    static void Main()
    {
        // The .exe lives in the project root
        string exeDir = AppDomain.CurrentDomain.BaseDirectory;
        string projectDir = exeDir.TrimEnd(Path.DirectorySeparatorChar);

        // Verify project structure
        string backendMain = Path.Combine(projectDir, "backend", "main.py");
        string packageJson = Path.Combine(projectDir, "package.json");

        if (!File.Exists(backendMain) || !File.Exists(packageJson))
        {
            Console.WriteLine("[ERROR] Cannot find project files.");
            Console.WriteLine("Place this .exe in the project root folder.");
            Console.WriteLine("Looking in: " + projectDir);
            Console.ReadKey();
            return;
        }

        Console.Title = "RenmaeAI Studio";
        Console.WriteLine();
        Console.WriteLine("  ========================================");
        Console.WriteLine("    RenmaeAI Studio is starting...");
        Console.WriteLine("  ========================================");
        Console.WriteLine();

        // Check for venv
        string venvActivate = Path.Combine(projectDir, ".venv", "Scripts", "activate.bat");
        string backendDir = Path.Combine(projectDir, "backend");

        // Start Backend (completely hidden)
        Console.WriteLine("  [1/2] Starting Backend Server...");
        string backendCmd;
        if (File.Exists(venvActivate))
        {
            backendCmd = string.Format(
                "/c cd /d \"{0}\" && call \"{1}\" && python -m uvicorn main:app --reload --port 8000",
                backendDir, venvActivate);
        }
        else
        {
            backendCmd = string.Format(
                "/c cd /d \"{0}\" && python -m uvicorn main:app --reload --port 8000",
                backendDir);
        }

        ProcessStartInfo backendPsi = new ProcessStartInfo("cmd.exe", backendCmd);
        backendPsi.WindowStyle = ProcessWindowStyle.Hidden;
        backendPsi.CreateNoWindow = true;
        Process.Start(backendPsi);

        // Wait for backend to be ready
        Console.Write("  Waiting for backend");
        bool backendReady = false;
        for (int i = 0; i < 20; i++)
        {
            Thread.Sleep(500);
            Console.Write(".");
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create("http://localhost:8000/api/health");
                request.Timeout = 1000;
                request.Method = "GET";
                HttpWebResponse response = (HttpWebResponse)request.GetResponse();
                if (response.StatusCode == HttpStatusCode.OK)
                {
                    backendReady = true;
                    response.Close();
                    break;
                }
                response.Close();
            }
            catch { }
        }

        if (backendReady)
        {
            Console.WriteLine(" OK!");
        }
        else
        {
            Console.WriteLine(" (starting in background)");
        }

        // Start Frontend (completely hidden)
        Console.WriteLine("  [2/2] Opening app in browser...");
        string frontendCmd = string.Format("/c cd /d \"{0}\" && npm run dev:vite", projectDir);
        ProcessStartInfo frontendPsi = new ProcessStartInfo("cmd.exe", frontendCmd);
        frontendPsi.WindowStyle = ProcessWindowStyle.Hidden;
        frontendPsi.CreateNoWindow = true;
        Process.Start(frontendPsi);

        // Wait for Vite to start, then open browser
        Thread.Sleep(3000);

        Console.WriteLine();
        Console.WriteLine("  ========================================");
        Console.WriteLine("    RenmaeAI Studio is ready!");
        Console.WriteLine("    Opening http://localhost:5173 ...");
        Console.WriteLine("  ========================================");

        // Open browser
        Process.Start(new ProcessStartInfo
        {
            FileName = "http://localhost:5173",
            UseShellExecute = true
        });

        Console.WriteLine();
        Console.WriteLine("  You can close this window.");
        Console.WriteLine("  To stop the app, close this window or");
        Console.WriteLine("  press any key to exit.");
        Console.ReadKey();

        // Kill backend and frontend when user closes
        KillProcessesByPort(8000);
        KillProcessesByPort(5173);
    }

    static void KillProcessesByPort(int port)
    {
        try
        {
            ProcessStartInfo psi = new ProcessStartInfo("cmd.exe",
                string.Format("/c for /f \"tokens=5\" %a in ('netstat -aon ^| findstr :{0} ^| findstr LISTENING') do taskkill /f /pid %a", port));
            psi.WindowStyle = ProcessWindowStyle.Hidden;
            psi.CreateNoWindow = true;
            Process.Start(psi);
        }
        catch { }
    }
}
