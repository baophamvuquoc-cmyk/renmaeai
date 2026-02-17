Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.ExpandEnvironmentStrings("%USERPROFILE%\Desktop\Auto Media Architecture.lnk")

Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.CurrentDirectory & "\START_APP.bat"
oLink.WorkingDirectory = oWS.CurrentDirectory
oLink.Description = "Auto Media Architecture - AI-Powered Media Production"
oLink.WindowStyle = 1
oLink.Save

WScript.Echo "Shortcut created on Desktop!" & vbCrLf & vbCrLf & "Double-click 'Auto Media Architecture' to start the app."
