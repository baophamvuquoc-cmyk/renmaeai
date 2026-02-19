Set WshShell = CreateObject("WScript.Shell")

' Start backend silently (hidden window)
WshShell.Run "cmd /c cd /d c:\Users\Admin\Desktop\renmaeai\backend && python -m uvicorn main:app --reload --port 8000", 0, False

' Wait 2 seconds for backend to initialize
WScript.Sleep 2000

' Start frontend + electron silently (hidden window)
WshShell.Run "cmd /c cd /d c:\Users\Admin\Desktop\renmaeai && npm run dev", 0, False
