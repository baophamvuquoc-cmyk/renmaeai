Set oWS = WScript.CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

' Get current directory
currentDir = oFSO.GetParentFolderName(WScript.ScriptFullName)

' Start Backend (hidden console)
backendPath = currentDir & "\backend\dist\backend.exe"
If oFSO.FileExists(backendPath) Then
    oWS.Run """" & backendPath & """", 0, False
    WScript.Sleep 3000
Else
    MsgBox "Error: Backend executable not found at:" & vbCrLf & backendPath, vbCritical, "Error"
    WScript.Quit
End If

' Start Electron App (hidden npm console)
oWS.Run "cmd /c cd """ & currentDir & """ && npm run dev", 0, False

' Success - app is starting
WScript.Sleep 2000
