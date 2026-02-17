const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
    getAppPath: () => ipcRenderer.invoke('get-app-path'),
    selectDirectory: () => ipcRenderer.invoke('select-directory'),
    selectFiles: () => ipcRenderer.invoke('select-files'),
});
