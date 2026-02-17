Set oWS = WScript.CreateObject("WScript.Shell")
sLinkFile = oWS.ExpandEnvironmentStrings("%USERPROFILE%\Desktop\Start Auto Media (Production).lnk")

Set oLink = oWS.CreateShortcut(sLinkFile)
oLink.TargetPath = oWS.CurrentDirectory & "\start-production.vbs"
oLink.WorkingDirectory = oWS.CurrentDirectory
oLink.Description = "Auto Media Architecture - Production Mode (Single Window)"
oLink.Save

MsgBox "Production shortcut created on Desktop!" & vbCrLf & vbCrLf & "Double-click 'Start Auto Media (Production)' to run the app with:" & vbCrLf & "• Fixed backend (no logging errors)" & vbCrLf & "• No visible terminals" & vbCrLf & "• Single app window only!", vbInformation, "Success"
