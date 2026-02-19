Set WshShell = CreateObject("WScript.Shell")

' Start Backend silently
WshShell.Run "cmd /c cd backend && python main.py", 0, False

' Wait 3 seconds
WScript.Sleep 3000

' Start Frontend and Electron silently
WshShell.Run "cmd /c npm run dev", 0, False
