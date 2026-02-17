import { app, BrowserWindow, ipcMain, dialog } from 'electron';
import path from 'path';
import { fileURLToPath } from 'url';
import { spawn } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;
let pythonProcess = null;

/**
 * Start Python backend in production mode
 * In dev mode, backend runs separately via start-backend.bat
 */
function startBackend() {
    if (app.isPackaged) {
        // Production: use packaged backend.exe
        console.log('[Backend] Starting packaged backend...');
        const backendPath = path.join(process.resourcesPath, 'bin', 'backend.exe');

        try {
            pythonProcess = spawn(backendPath, [], {
                detached: false,
                windowsHide: true,
                stdio: 'ignore'
            });

            pythonProcess.on('error', (err) => {
                console.error('[Backend] Failed to start:', err);
            });

            pythonProcess.on('exit', (code) => {
                console.log(`[Backend] Exited with code ${code}`);
            });

            console.log('[Backend] Started successfully on port 8000');
        } catch (error) {
            console.error('[Backend] Spawn error:', error);
        }
    } else {
        // Dev mode: auto-spawn Python uvicorn
        console.log('[Backend] Dev mode - Starting Python backend automatically...');
        const backendDir = path.join(__dirname, '..', 'backend');

        try {
            pythonProcess = spawn('python', ['-m', 'uvicorn', 'main:app', '--reload', '--port', '8000'], {
                cwd: backendDir,
                detached: false,
                windowsHide: true,
                stdio: ['ignore', 'pipe', 'pipe'],
                shell: true
            });

            pythonProcess.stdout.on('data', (data) => {
                console.log(`[Backend] ${data.toString().trim()}`);
            });

            pythonProcess.stderr.on('data', (data) => {
                console.log(`[Backend] ${data.toString().trim()}`);
            });

            pythonProcess.on('error', (err) => {
                console.error('[Backend] Failed to start:', err);
            });

            pythonProcess.on('exit', (code) => {
                console.log(`[Backend] Exited with code ${code}`);
            });

            console.log('[Backend] Dev server starting on port 8000...');
        } catch (error) {
            console.error('[Backend] Spawn error:', error);
        }
    }
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1200,
        minHeight: 700,
        backgroundColor: '#060E1B',
        webPreferences: {
            preload: path.join(__dirname, 'preload.cjs'),
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: false,
        },
        titleBarStyle: 'hidden',
        titleBarOverlay: {
            color: '#060E1B',
            symbolColor: '#E2E8F0',
            height: 40,
        },
        show: true,
    });

    mainWindow.maximize();

    // Load the app
    if (process.env.NODE_ENV === 'development') {
        // Wait for Vite dev server to be ready before loading
        const waitForServer = async (url, maxAttempts = 20, delay = 500) => {
            for (let i = 0; i < maxAttempts; i++) {
                try {
                    const response = await fetch(url, { method: 'HEAD' });
                    if (response.ok) {
                        console.log(`[Electron] Server ready after ${i + 1} attempts`);
                        return true;
                    }
                } catch (e) {
                    // Server not ready yet
                }
                await new Promise(resolve => setTimeout(resolve, delay));
            }
            return false;
        };

        waitForServer('http://localhost:5173').then(async (ready) => {
            if (ready) {
                await mainWindow.loadURL('http://localhost:5173');
                // DevTools: press F12 to open manually when needed
            } else {
                console.error('[Electron] Failed to connect to dev server');
                mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
            }
        });
    } else {
        mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
    }

    // Ensure window is visible (fallback)
    setTimeout(() => {
        if (mainWindow && !mainWindow.isVisible()) {
            mainWindow.show();
        }
    }, 1000);

    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(() => {
    // Start backend first, then create window
    startBackend();
    createWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// Clean up backend process when app quits
app.on('will-quit', () => {
    if (pythonProcess) {
        console.log('[Backend] Shutting down...');
        // On Windows with shell: true, we need to kill the process tree
        if (process.platform === 'win32') {
            spawn('taskkill', ['/pid', pythonProcess.pid.toString(), '/T', '/F'], { windowsHide: true });
        } else {
            pythonProcess.kill();
        }
        pythonProcess = null;
    }
});

// IPC Handlers
ipcMain.handle('get-app-path', () => {
    return app.getPath('userData');
});

ipcMain.handle('select-directory', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory'],
    });
    return result.filePaths[0] || null;
});

ipcMain.handle('select-files', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'Videos', extensions: ['mp4', 'mov', 'avi', 'mkv'] },
            { name: 'Images', extensions: ['jpg', 'png', 'jpeg', 'gif', 'webp'] },
            { name: 'All Files', extensions: ['*'] },
        ],
    });
    return result.filePaths || [];
});
