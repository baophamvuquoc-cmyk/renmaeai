import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type AIProvider = 'openai' | 'gemini_api' | 'custom';

interface AISettings {
    // OpenAI / ChatGPT
    openaiApiKey: string;
    openaiBaseUrl: string;
    openaiModel: string;

    // Gemini
    geminiApiKey: string;

    // Custom API Provider
    customApiKey: string;
    customBaseUrl: string;
    customModel: string;

    // Active content provider (checkbox selection)
    activeContentProvider: AIProvider | null;

    // Footage API Keys
    pexelsApiKey: string;
    pixabayApiKey: string;

    // Available models (fetched from API)
    availableModels: { id: string; name: string; description: string }[];

    // Connection Status
    connectionStatus: Record<string, 'unknown' | 'testing' | 'connected' | 'failed'>;
}

interface AISettingsStore extends AISettings {
    // Setters
    setOpenaiApiKey: (apiKey: string) => void;
    setOpenaiBaseUrl: (baseUrl: string) => void;
    setOpenaiModel: (model: string) => void;
    setGeminiApiKey: (apiKey: string) => void;
    setCustomApiKey: (apiKey: string) => void;
    setCustomBaseUrl: (baseUrl: string) => void;
    setCustomModel: (model: string) => void;
    setActiveContentProvider: (provider: AIProvider | null) => void;
    setPexelsApiKey: (apiKey: string) => void;
    setPixabayApiKey: (apiKey: string) => void;
    setConnectionStatus: (provider: string, status: 'unknown' | 'testing' | 'connected' | 'failed') => void;
    setAvailableModels: (models: { id: string; name: string; description: string }[]) => void;

    // Backend sync
    loadSettingsFromBackend: () => Promise<void>;
    saveSettingToBackend: (provider: string, data: any) => Promise<void>;
    saveFootageKeys: (pexelsKey: string, pixabayKey: string) => Promise<void>;
    fetchAvailableModels: (baseUrl?: string, apiKey?: string) => Promise<void>;
    isLoaded: boolean;

    // Utility
    reset: () => void;
    isProviderConfigured: (provider: AIProvider) => boolean;
    getActiveProvider: () => AIProvider | null;
}

const initialState: AISettings & { isLoaded: boolean } = {
    openaiApiKey: '',
    openaiBaseUrl: '',
    openaiModel: 'gpt-5.2',
    geminiApiKey: '',
    customApiKey: '',
    customBaseUrl: '',
    customModel: '',
    activeContentProvider: null,
    pexelsApiKey: '',
    pixabayApiKey: '',
    availableModels: [],
    connectionStatus: {},
    isLoaded: false,
};

export const useAISettingsStore = create<AISettingsStore>()(
    persist(
        (set, get) => ({
            ...initialState,
            isLoaded: false,

            setOpenaiApiKey: (apiKey) => {
                set({ openaiApiKey: apiKey });
                get().saveSettingToBackend('openai_api', { api_key: apiKey });
            },
            setOpenaiBaseUrl: (baseUrl) => {
                set({ openaiBaseUrl: baseUrl });
                get().saveSettingToBackend('openai_api', { base_url: baseUrl });
            },
            setOpenaiModel: (model) => {
                set({ openaiModel: model });
                get().saveSettingToBackend('openai_api', { model: model });
            },
            setGeminiApiKey: (apiKey) => {
                set({ geminiApiKey: apiKey });
                get().saveSettingToBackend('gemini_api', { api_key: apiKey });
            },
            setCustomApiKey: (apiKey) => {
                set({ customApiKey: apiKey });
                get().saveSettingToBackend('custom_api', { api_key: apiKey });
            },
            setCustomBaseUrl: (baseUrl) => {
                set({ customBaseUrl: baseUrl });
                get().saveSettingToBackend('custom_api', { base_url: baseUrl });
            },
            setCustomModel: (model) => {
                set({ customModel: model });
                get().saveSettingToBackend('custom_api', { model: model });
            },
            setActiveContentProvider: (provider) => {
                set({ activeContentProvider: provider });
                // Save active provider to backend app_settings
                (async () => {
                    try {
                        const { settingsApi } = await import('../lib/api');
                        await settingsApi.setActiveProvider(provider || '');
                    } catch (error) {
                        console.error('Failed to save active provider:', error);
                    }
                })();
            },
            setPexelsApiKey: (apiKey) => {
                set({ pexelsApiKey: apiKey });
            },
            setPixabayApiKey: (apiKey) => {
                set({ pixabayApiKey: apiKey });
            },
            setConnectionStatus: (provider, status) =>
                set((state) => ({
                    connectionStatus: {
                        ...state.connectionStatus,
                        [provider]: status,
                    },
                })),
            setAvailableModels: (models) => set({ availableModels: models }),

            fetchAvailableModels: async (baseUrl?: string, apiKey?: string) => {
                const state = get();
                const key = apiKey || state.openaiApiKey;
                const url = baseUrl || state.openaiBaseUrl || 'https://api.openai.com/v1';
                if (!key) return;
                try {
                    const { aiApi } = await import('../lib/api');
                    const models = await aiApi.fetchModels(url, key);
                    set({ availableModels: models });
                } catch (error) {
                    console.error('Failed to fetch models:', error);
                }
            },

            loadSettingsFromBackend: async () => {
                try {
                    const { settingsApi, footageApi } = await import('../lib/api');
                    const response = await settingsApi.getAllSettings();

                    if (response.success) {
                        const { settings, active_provider } = response;

                        set({
                            openaiApiKey: settings.openai_api?.api_key || '',
                            openaiBaseUrl: settings.openai_api?.base_url || '',
                            openaiModel: settings.openai_api?.model || 'gpt-5.2',
                            geminiApiKey: settings.gemini_api?.api_key || '',
                            customApiKey: settings.custom_api?.api_key || '',
                            customBaseUrl: settings.custom_api?.base_url || '',
                            customModel: settings.custom_api?.model || '',
                            activeContentProvider: active_provider || null,
                            isLoaded: true,
                        });
                    }

                    // Load footage keys from backend .env if not already in local state
                    try {
                        const currentState = get();
                        if (!currentState.pexelsApiKey && !currentState.pixabayApiKey) {
                            const footageConfig = await footageApi.getConfig();
                            if (footageConfig.success) {
                                set({
                                    pexelsApiKey: footageConfig.pexels_key || '',
                                    pixabayApiKey: footageConfig.pixabay_key || '',
                                });
                            }
                        }
                    } catch {
                        // Footage API may not be configured yet
                    }
                } catch (error) {
                    console.error('Failed to load settings from backend:', error);
                    set({ isLoaded: true });
                }
            },

            saveSettingToBackend: async (provider: string, data: any) => {
                try {
                    const { settingsApi } = await import('../lib/api');
                    await settingsApi.updateSetting(provider, data);
                } catch (error) {
                    console.error(`Failed to save ${provider} setting:`, error);
                }
            },

            saveFootageKeys: async (pexelsKey: string, pixabayKey: string) => {
                try {
                    const { footageApi } = await import('../lib/api');
                    await footageApi.updateConfig(pexelsKey, pixabayKey);
                    set({ pexelsApiKey: pexelsKey, pixabayApiKey: pixabayKey });
                } catch (error) {
                    console.error('Failed to save footage keys:', error);
                    throw error;
                }
            },

            reset: () => set(initialState),

            isProviderConfigured: (provider: AIProvider) => {
                const state = get();
                switch (provider) {
                    case 'openai':
                        return !!state.openaiApiKey;
                    case 'gemini_api':
                        return !!state.geminiApiKey;
                    case 'custom':
                        return !!state.customApiKey && !!state.customBaseUrl;
                    default:
                        return false;
                }
            },

            getActiveProvider: () => {
                return get().activeContentProvider;
            },
        }),
        {
            name: 'ai-settings-storage',
        }
    )
);
