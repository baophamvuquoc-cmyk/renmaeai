# Python Backend Exe Integration - Quick Reference

## Development Mode (Current Workflow - No Changes)

Start the app as usual:
```bash
.\start-app.bat
```

The Python backend runs separately. Everything works as before.

---

## Production Build

### Build Backend Only
```bash
cd backend
.\build-backend.bat
```
Creates `backend\dist\backend.exe` (~150-200MB)

### Build Complete App
```bash
.\build-all.bat
```

This will:
1. Build Python backend → `backend.exe`
2. Build React frontend → `dist/`
3. Package Electron app with installer → `release/`

### Test Production Build
1. Run the installer from `release/`
2. Launch the app
3. **No console window should appear** ✓
4. Backend auto-starts on port 8000
5. App connects and works normally

---

## How It Works

### Dev Mode (`NODE_ENV=development`)
- Electron: `npm run dev:electron`
- Backend: Runs separately via `start-backend.bat`
- No changes to current workflow

### Production Mode (`app.isPackaged`)
- Electron auto-starts `resources/bin/backend.exe`
- Console window hidden with `windowsHide: true`
- Backend runs silently on port 8000
- Process killed when app closes

---

## Troubleshooting

### Backend exe fails to start
Check logs in Electron DevTools console (production mode doesn't auto-open DevTools)

### Port 8000 already in use
Kill existing processes:
```bash
netstat -ano | findstr :8000
taskkill /PID <pid> /F
```

### Build errors
1. Ensure PyInstaller is installed: `pip install pyinstaller`
2. Check all dependencies in `requirements.txt` are installed
3. Try building backend manually: `pyinstaller backend.spec`

---

## File Structure

```
renmaeai/
├── backend/
│   ├── backend.spec          # PyInstaller config
│   ├── build-backend.bat     # Build script
│   ├── dist/
│   │   └── backend.exe       # Generated exe (gitignored)
│   └── main.py
├── electron/
│   └── main.js               # Updated with backend spawning
├── package.json              # Updated with build scripts
├── build-all.bat             # Master build script
└── release/                  # Final installer output
    └── Auto Media Architecture Setup.exe
```
