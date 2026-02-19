!macro customInstall
  ; Add Windows Defender exclusion for the install directory
  nsExec::ExecToLog 'powershell -ExecutionPolicy Bypass -Command "try { Add-MpPreference -ExclusionPath \"$INSTDIR\" -ErrorAction SilentlyContinue } catch {}"'
!macroend

!macro customUnInstall
  ; Remove Windows Defender exclusion on uninstall
  nsExec::ExecToLog 'powershell -ExecutionPolicy Bypass -Command "try { Remove-MpPreference -ExclusionPath \"$INSTDIR\" -ErrorAction SilentlyContinue } catch {}"'
!macroend
