declare global {
    interface Window {
        electron: {
            getAppPath: () => Promise<string>;
            selectDirectory: () => Promise<string | null>;
            selectFiles: () => Promise<string[]>;
        };
    }
}

export { };
