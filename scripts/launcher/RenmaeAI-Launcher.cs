using System;
using System.Diagnostics;
using System.IO;
using System.Threading;

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

        if (!File.Exists(backendMain))
        {
            Console.WriteLine("[ERROR] Cannot find backend\\main.py");
            Console.WriteLine("Place this .exe in the project root folder.");
            Console.WriteLine("Looking in: " + projectDir);
            Console.ReadKey();
            return;
        }

        if (!File.Exists(packageJson))
        {
            Console.WriteLine("[ERROR] Cannot find package.json");
            Console.ReadKey();
            return;
        }

        Console.WriteLine("========================================");
        Console.WriteLine("  RenmaeAI Studio - Starting...");
        Console.WriteLine("========================================");
        Console.WriteLine();

        // Check for venv
        string venvActivate = Path.Combine(projectDir, ".venv", "Scripts", "activate.bat");
        string backendDir = Path.Combine(projectDir, "backend");

        // Start Backend
        Console.WriteLine("[1/2] Starting Backend Server...");
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
        backendPsi.WindowStyle = ProcessWindowStyle.Minimized;
        backendPsi.CreateNoWindow = false;
        Process.Start(backendPsi);

        // Wait for backend to initialize
        Thread.Sleep(3000);

        // Start Frontend + Electron
        Console.WriteLine("[2/2] Starting Frontend + Electron...");
        string frontendCmd = string.Format("/c cd /d \"{0}\" && npm run dev", projectDir);
        ProcessStartInfo frontendPsi = new ProcessStartInfo("cmd.exe", frontendCmd);
        frontendPsi.WindowStyle = ProcessWindowStyle.Minimized;
        frontendPsi.CreateNoWindow = false;
        Process.Start(frontendPsi);

        Console.WriteLine();
        Console.WriteLine("========================================");
        Console.WriteLine("  RenmaeAI Studio is starting!");
        Console.WriteLine("  Backend:  http://localhost:8000");
        Console.WriteLine("  Frontend: http://localhost:5173");
        Console.WriteLine("========================================");
        Console.WriteLine();
        Console.WriteLine("The Electron window will open shortly.");
        Thread.Sleep(5000);
    }
}
