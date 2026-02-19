/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL?: string;
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}

interface Window {
    electron?: {
        getAppPath: () => Promise<string>;
        selectDirectory: () => Promise<string | null>;
        selectFiles: () => Promise<string[]>;
    };
}
