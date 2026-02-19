import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
    baseURL: API_BASE_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

export const fileApi = {
    async listDirectory(path: string) {
        const response = await api.post('/api/files/list', { path });
        return response.data;
    },

    async renamePreview(path: string, files: string[], pattern: any) {
        const response = await api.post('/api/files/rename-preview', {
            path,
            files,
            pattern,
        });
        return response.data;
    },

    async renameExecute(path: string, renameMap: Record<string, string>) {
        const response = await api.post('/api/files/rename-execute', {
            path,
            rename_map: renameMap,
        });
        return response.data;
    },
};

export const aiApi = {
    async getProviders() {
        const response = await api.get('/api/ai/providers');
        return response.data;
    },

    async fetchModels(baseUrl: string, apiKey: string): Promise<{ id: string; name: string; description: string }[]> {
        try {
            const response = await fetch(`${baseUrl}/models`, {
                headers: {
                    'Authorization': `Bearer ${apiKey}`,
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            if (data.data && Array.isArray(data.data)) {
                const models: { id: string; name: string; description: string }[] = [];

                for (const m of data.data) {
                    const modelId = m.id;
                    const idLower = modelId.toLowerCase();

                    //  STEP 1: Exclude non-chat / non-vision models 
                    const isExcluded = [
                        'embedding', 'tts', 'whisper', 'dall-e', 'davinci',
                        'babbage', 'realtime', 'transcribe', 'moderation',
                        'vision-preview',
                        // Code-only models (no vision/chat capability)
                        'codex',
                        // Internal/experimental models
                        'tab_',
                    ].some(skip => idLower.includes(skip));

                    if (isExcluded) continue;

                    //  STEP 2: Only include models that support VISION 
                    // These model families support multimodal (text + image input)
                    const isVisionCapable = [
                        // OpenAI GPT-5.x series (all base models support vision)
                        'gpt-5.2', 'gpt-5.1', 'gpt-5.3', 'gpt-5',
                        // OpenAI GPT-4 vision models
                        'gpt-4o', 'gpt-4.1', 'gpt-4.5', 'gpt-4-turbo', 'chatgpt-4o',
                        // Google Gemini (all support vision)
                        'gemini-3', 'gemini-2.5', 'gemini-2', 'gemini-1.5',
                        // Anthropic Claude 3+ (all support vision)
                        'claude-sonnet-4', 'claude-opus-4', 'claude-3',
                        // Open-source vision models
                        'llama-3.2', 'llama-3.3',
                        // Other multimodal
                        'gpt-oss',
                    ].some(prefix => idLower.includes(prefix));

                    if (!isVisionCapable) continue;

                    //  STEP 3: Exclude weak/lite variants 
                    const isTooWeak = [
                        '-lite',    // Too small for quality vision
                        '-nano',    // Too small
                    ].some(suffix => idLower.includes(suffix));

                    if (isTooWeak) continue;

                    // Get display name and description
                    const { name, description } = this.getModelDisplayInfo(modelId);

                    models.push({ id: modelId, name, description });
                }

                // Sort models by priority
                return this.sortModels(models);
            }
            return [];
        } catch (error) {
            console.error('Failed to fetch models:', error);
            return [];
        }
    },

    getModelDisplayInfo(modelId: string): { name: string; description: string } {
        const id = modelId.toLowerCase();

        // 
        // GPT-5.2 Series (Latest Flagship - Feb 2026)
        // 
        if (id.includes('gpt-5.2-pro')) return { name: 'GPT-5.2 Pro', description: 'Research-grade, most powerful' };
        if (id.includes('gpt-5.2-thinking')) return { name: 'GPT-5.2 Thinking', description: 'Step-by-step reasoning' };
        if (id.includes('gpt-5.2-instant')) return { name: 'GPT-5.2 Instant', description: 'Ultra-fast responses' };
        if (id.includes('gpt-5.2-auto') || id === 'gpt-5.2') return { name: 'GPT-5.2 Auto', description: 'Auto-selects best mode' };

        // GPT-5.1 Series
        if (id.includes('gpt-5.1-pro')) return { name: 'GPT-5.1 Pro', description: 'High capability' };
        if (id.includes('gpt-5.1-thinking')) return { name: 'GPT-5.1 Thinking', description: 'Reasoning mode' };
        if (id.includes('gpt-5.1-instant')) return { name: 'GPT-5.1 Instant', description: 'Fast responses' };
        if (id.includes('gpt-5.1-codex-mini')) return { name: 'GPT-5.1 Codex Mini', description: 'Coding optimized' };
        if (id.includes('gpt-5.1')) return { name: 'GPT-5.1', description: 'Previous flagship' };

        // GPT-5.0 Series
        if (id.includes('gpt-5')) return { name: 'GPT-5', description: 'GPT-5 base' };

        // 
        // O-Series Reasoning Models (Latest)
        // 
        if (id.includes('o4-mini')) return { name: 'o4-mini', description: 'Lightweight reasoning, STEM optimized' };
        if (id.includes('o3-pro')) return { name: 'o3-pro', description: 'Extended thinking, best performance' };
        if (id.includes('o3-mini')) return { name: 'o3-mini', description: 'Fast reasoning, cost-effective' };
        if (id === 'o3' || id.startsWith('o3-2')) return { name: 'o3', description: 'Advanced reasoning for coding/math' };
        if (id.includes('o1-pro')) return { name: 'o1-pro', description: 'Previous gen, advanced reasoning' };
        if (id === 'o1' || id.startsWith('o1-2')) return { name: 'o1', description: 'Previous gen reasoning' };
        if (id.includes('o1-mini')) return { name: 'o1-mini', description: 'Previous gen, fast' };
        if (id.includes('o1-preview')) return { name: 'o1-preview', description: 'Preview reasoning' };

        // 
        // GPT-4 Series (Legacy - Still available via API)
        // 
        // GPT-4.5 series
        if (id.includes('gpt-4.5')) return { name: 'GPT-4.5 Preview', description: 'Preview model' };

        // GPT-4.1 series
        if (id.includes('gpt-4.1-nano')) return { name: 'GPT-4.1 Nano', description: 'Smallest, fastest' };
        if (id.includes('gpt-4.1-mini')) return { name: 'GPT-4.1 Mini', description: 'Balanced speed/quality' };
        if (id.includes('gpt-4.1')) return { name: 'GPT-4.1', description: 'Large context window' };

        // GPT-4o series
        if (id.includes('gpt-4o-mini')) return { name: 'GPT-4o Mini', description: 'Fast & affordable' };
        if (id.includes('gpt-4o-search')) return { name: 'GPT-4o Search', description: 'Web search enabled' };
        if (id.includes('gpt-4o-audio')) return { name: 'GPT-4o Audio', description: 'Audio input/output' };
        if (id.includes('chatgpt-4o')) return { name: 'ChatGPT-4o Latest', description: 'Dynamic ChatGPT model' };
        if (id.includes('gpt-4o')) return { name: 'GPT-4o', description: 'Multimodal model (legacy flagship)' };

        // GPT-4 Turbo
        if (id.includes('gpt-4-turbo-preview')) return { name: 'GPT-4 Turbo Preview', description: 'Latest GPT-4 preview' };
        if (id.includes('gpt-4-turbo')) return { name: 'GPT-4 Turbo', description: 'Previous generation turbo' };

        // GPT-4
        if (id.includes('gpt-4')) return { name: 'GPT-4', description: 'Original GPT-4' };

        // GPT-3.5
        if (id.includes('gpt-3.5')) return { name: 'GPT-3.5 Turbo', description: 'Fast, budget option' };

        // Claude (OpenRouter)
        if (id.includes('claude-3.5-sonnet')) return { name: 'Claude 3.5 Sonnet', description: 'Best balance' };
        if (id.includes('claude-3-opus')) return { name: 'Claude 3 Opus', description: 'Most capable' };
        if (id.includes('claude-3-sonnet')) return { name: 'Claude 3 Sonnet', description: 'Balanced' };
        if (id.includes('claude-3-haiku')) return { name: 'Claude 3 Haiku', description: 'Fast' };
        if (id.includes('claude')) return { name: modelId, description: 'Claude model' };

        // Llama (OpenRouter, Together, etc.)
        if (id.includes('llama-3.3')) return { name: 'Llama 3.3', description: 'Meta latest' };
        if (id.includes('llama-3.2')) return { name: 'Llama 3.2', description: 'Meta' };
        if (id.includes('llama-3.1')) return { name: 'Llama 3.1', description: 'Meta' };
        if (id.includes('llama')) return { name: modelId, description: 'Meta Llama' };

        // Mistral
        if (id.includes('mistral-large')) return { name: 'Mistral Large', description: 'Flagship' };
        if (id.includes('mistral-medium')) return { name: 'Mistral Medium', description: 'Balanced' };
        if (id.includes('mistral-small')) return { name: 'Mistral Small', description: 'Fast' };
        if (id.includes('mixtral')) return { name: 'Mixtral', description: 'MoE model' };
        if (id.includes('mistral')) return { name: modelId, description: 'Mistral' };

        // DeepSeek
        if (id.includes('deepseek-r1')) return { name: 'DeepSeek R1', description: 'Reasoning' };
        if (id.includes('deepseek-v3')) return { name: 'DeepSeek V3', description: 'Latest' };
        if (id.includes('deepseek-coder')) return { name: 'DeepSeek Coder', description: 'Coding' };
        if (id.includes('deepseek')) return { name: modelId, description: 'DeepSeek' };

        // Qwen
        if (id.includes('qwen')) return { name: modelId, description: 'Alibaba Qwen' };

        // Gemini 3 Series (Latest)
        if (id.includes('gemini-3-pro-image')) return { name: 'Gemini 3 Pro Image', description: 'Vision + image generation' };
        if (id.includes('gemini-3-pro-high')) return { name: 'Gemini 3 Pro High', description: 'Highest quality, vision + reasoning' };
        if (id.includes('gemini-3-pro')) return { name: 'Gemini 3 Pro', description: 'Pro multimodal' };
        if (id.includes('gemini-3-flash')) return { name: 'Gemini 3 Flash', description: 'Fast multimodal' };
        // Gemini 2.5
        if (id.includes('gemini-2.5-flash')) return { name: 'Gemini 2.5 Flash', description: 'Fast, thinking' };
        if (id.includes('gemini-2.5-pro')) return { name: 'Gemini 2.5 Pro', description: 'Pro model' };
        // Gemini 2.0
        if (id.includes('gemini-2.0')) return { name: 'Gemini 2.0', description: 'Gemini 2.0' };
        if (id.includes('gemini-1.5-pro')) return { name: 'Gemini 1.5 Pro', description: 'Pro model' };
        if (id.includes('gemini-1.5-flash')) return { name: 'Gemini 1.5 Flash', description: 'Fast' };
        if (id.includes('gemini')) return { name: modelId, description: 'Google Gemini' };

        // Claude 4 Series
        if (id.includes('claude-opus-4-6-thinking')) return { name: 'Claude Opus 4.6 Thinking', description: 'Most capable + deep reasoning' };
        if (id.includes('claude-opus-4-6')) return { name: 'Claude Opus 4.6', description: 'Flagship multimodal' };
        if (id.includes('claude-opus-4-5-thinking')) return { name: 'Claude Opus 4.5 Thinking', description: 'Deep reasoning + vision' };
        if (id.includes('claude-opus-4-5')) return { name: 'Claude Opus 4.5', description: 'Advanced multimodal' };
        if (id.includes('claude-sonnet-4-5-thinking')) return { name: 'Claude Sonnet 4.5 Thinking', description: 'Fast reasoning + vision' };
        if (id.includes('claude-sonnet-4-5')) return { name: 'Claude Sonnet 4.5', description: 'Balanced, vision capable' };
        if (id.includes('claude-sonnet-4')) return { name: 'Claude Sonnet 4', description: 'Balanced' };

        // GPT-OSS (Open-source multimodal)
        if (id.includes('gpt-oss')) return { name: 'GPT-OSS 120B', description: 'Open-source multimodal' };

        // Default
        return { name: modelId, description: 'AI model' };
    },

    sortModels(models: { id: string; name: string; description: string }[]): { id: string; name: string; description: string }[] {
        const priority: Record<string, number> = {
            // GPT-5 Series (Highest Priority)
            'gpt-5.3': 0,
            'gpt-5.2-pro': 1, 'gpt-5.2': 2,
            'gpt-5.1-pro': 3, 'gpt-5.1': 4,
            'gpt-5': 5,
            // Gemini 3 Series
            'gemini-3-pro-high': 10, 'gemini-3-pro-image': 11, 'gemini-3-pro': 12, 'gemini-3-flash': 13,
            // Claude 4 Series
            'claude-opus-4-6': 20, 'claude-opus-4-5': 21, 'claude-sonnet-4-5': 22, 'claude-sonnet-4': 23,
            // Gemini 2.5
            'gemini-2.5-flash': 30, 'gemini-2.5-pro': 31,
            // GPT-4 Series (Legacy)
            'gpt-4.5': 40, 'gpt-4.1': 41, 'gpt-4o': 42, 'chatgpt-4o': 42,
            'gpt-4-turbo': 43, 'gpt-4': 44,
            // Claude 3.5
            'claude-3.5': 50, 'claude-3-opus': 51, 'claude-3-sonnet': 52,
            // Gemini 2.0 / 1.5
            'gemini-2': 60, 'gemini-1.5-pro': 61, 'gemini-1.5-flash': 62,
            // Open-source multimodal
            'gpt-oss': 70,
            'llama-3.3': 71, 'llama-3.2': 72,
        };

        const getPriority = (id: string): number => {
            for (const [key, value] of Object.entries(priority)) {
                if (id.toLowerCase().includes(key)) return value;
            }
            return 50;
        };

        // Remove duplicates by name
        const seen = new Set<string>();
        const unique = models.filter(m => {
            if (seen.has(m.name)) return false;
            seen.add(m.name);
            return true;
        });

        return unique.sort((a, b) => getPriority(a.id) - getPriority(b.id));
    },

    async generateScenes(
        script: string,
        provider: string = 'gemini_api',
        language: string = 'vi',
        useSmartModel: boolean = false,
        aiSettings?: {
            openaiApiKey?: string;
            geminiApiKey?: string;
        }
    ) {
        const response = await api.post('/api/ai/generate', {
            script,
            provider,
            language,
            use_smart_model: useSmartModel,
            ai_settings: aiSettings ? {
                openai_api_key: aiSettings.openaiApiKey,
                gemini_api_key: aiSettings.geminiApiKey,
            } : null,
        });
        return response.data;
    },

    async testConnection(
        provider: string = 'gemini_api',
        aiSettings?: {
            openaiApiKey?: string;
            openaiBaseUrl?: string;
            openaiModel?: string;
            geminiApiKey?: string;
        }
    ) {
        const response = await api.post('/api/ai/test-connection', {
            provider,
            ai_settings: aiSettings ? {
                openai_api_key: aiSettings.openaiApiKey,
                openai_base_url: aiSettings.openaiBaseUrl,
                openai_model: aiSettings.openaiModel,
                gemini_api_key: aiSettings.geminiApiKey,
            } : null,
        });
        return response.data;
    },
};

// AI Settings API
export const settingsApi = {
    async getAllSettings() {
        const response = await api.get('/api/ai/settings');
        return response.data;
    },

    async getSetting(provider: string) {
        const response = await api.get(`/api/ai/settings/${provider}`);
        return response.data;
    },

    async updateSetting(
        provider: string,
        data: {
            api_key?: string;
            base_url?: string;
            model?: string;
        }
    ) {
        const response = await api.post(`/api/ai/settings/${provider}`, data);
        return response.data;
    },

    async setDefaultProvider(provider: string) {
        const response = await api.post('/api/ai/settings/default-provider', { provider });
        return response.data;
    },

    async getDefaultProvider() {
        const response = await api.get('/api/ai/settings/default-provider');
        return response.data;
    },

    async setActiveProvider(provider: string) {
        const response = await api.post('/api/ai/settings/active-provider', { provider });
        return response.data;
    },

    async getActiveProvider() {
        const response = await api.get('/api/ai/settings/active-provider');
        return response.data;
    },
};



// Script Workflow API
export const workflowApi = {


    // 3-Step Style Analysis with SSE streaming progress
    async analyzeToStyleAStream(
        scripts: string[],
        model: string | undefined,
        onProgress: (step: string, percentage: number, message: string) => void,
        analysisLanguage: string = 'vi',
        outputLanguage: string = '',
        signal?: AbortSignal
    ): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/api/workflow/analyze-to-style-a-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scripts, model, analysis_language: analysisLanguage, output_language: outputLanguage }),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return new Promise((resolve, reject) => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let eventType = 'message';
            let resolved = false;

            function processChunk(chunk: string) {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (eventType === 'result') {
                                if (!resolved) { resolved = true; resolve(data); }
                                return;
                            } else if (eventType === 'error') {
                                if (!resolved) { resolved = true; reject(new Error(data.error || 'SSE error')); }
                                return;
                            } else {
                                // Progress update
                                onProgress(data.step, data.percentage, data.message);
                            }
                        } catch (e) {
                            // Skip non-JSON lines
                        }
                        eventType = 'message';
                    }
                }
            }

            function read(): void {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer.trim()) processChunk('\n');
                        if (!resolved) { resolved = true; reject(new Error('Stream closed without result')); }
                        return;
                    }
                    processChunk(decoder.decode(value, { stream: true }));
                    read();
                }).catch((err) => {
                    if (!resolved) { resolved = true; reject(err); }
                });
            }
            read();
        });
    },

    // Analyze title/description/thumbnail styles with SSE streaming
    async analyzeMetadataStylesStream(
        titleSamples: string[],
        descriptionSamples: string[],
        thumbnailDescriptions: string[],
        model: string | undefined,
        onProgress: (step: string, percentage: number, message: string) => void,
        thumbnailImages: string[] = [],
        signal?: AbortSignal,
        outputLanguage: string = ''
    ): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/api/workflow/analyze-metadata-styles-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title_samples: titleSamples,
                description_samples: descriptionSamples,
                thumbnail_descriptions: thumbnailDescriptions,
                thumbnail_images: thumbnailImages,
                model,
                output_language: outputLanguage,
            }),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return new Promise((resolve, reject) => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let eventType = 'message';
            let resolved = false;

            function processChunk(chunk: string) {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (eventType === 'result') {
                                if (!resolved) { resolved = true; resolve(data); }
                                return;
                            } else if (eventType === 'error') {
                                if (!resolved) { resolved = true; reject(new Error(data.error || 'SSE error')); }
                                return;
                            } else {
                                onProgress(data.step, data.percentage, data.message);
                            }
                        } catch (e) {
                            // Skip non-JSON lines
                        }
                        eventType = 'message';
                    }
                }
            }

            function read(): void {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer.trim()) processChunk('\n');
                        if (!resolved) { resolved = true; reject(new Error('Stream closed without result')); }
                        return;
                    }
                    processChunk(decoder.decode(value, { stream: true }));
                    read();
                }).catch((err) => {
                    if (!resolved) { resolved = true; reject(err); }
                });
            }
            read();
        });
    },

    // Analyze sync references (character/style/context) with SSE streaming
    async analyzeSyncReferencesStream(
        characterText: string,
        styleText: string,
        contextText: string,
        characterImages: string[],
        styleImages: string[],
        contextImages: string[],
        model: string | undefined,
        onProgress: (step: string, percentage: number, message: string) => void,
        signal?: AbortSignal,
        outputLanguage: string = 'vi'
    ): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/api/workflow/analyze-sync-references-stream`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                character_text: characterText,
                style_text: styleText,
                context_text: contextText,
                character_images: characterImages,
                style_images: styleImages,
                context_images: contextImages,
                model,
                output_language: outputLanguage,
            }),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return new Promise((resolve, reject) => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let eventType = 'message';
            let resolved = false;

            function processChunk(chunk: string) {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (eventType === 'result') {
                                if (!resolved) { resolved = true; resolve(data); }
                                return;
                            } else if (eventType === 'error') {
                                if (!resolved) { resolved = true; reject(new Error(data.error || 'SSE error')); }
                                return;
                            } else {
                                onProgress(data.step, data.percentage, data.message);
                            }
                        } catch (e) {
                            // Skip non-JSON lines
                        }
                        eventType = 'message';
                    }
                }
            }

            function read(): void {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer.trim()) processChunk('\n');
                        if (!resolved) { resolved = true; reject(new Error('Stream closed without result')); }
                        return;
                    }
                    processChunk(decoder.decode(value, { stream: true }));
                    read();
                }).catch((err) => {
                    if (!resolved) { resolved = true; reject(err); }
                });
            }
            read();
        });
    },

    async getTemplates() {
        const response = await api.get('/api/workflow/templates');
        return response.data;
    },

    async getTemplate(templateId: string) {
        const response = await api.get(`/api/workflow/templates/${templateId}`);
        return response.data;
    },

    // 
    // ADVANCED REMAKE - CONVERSATION PIPELINE
    // 

    advancedRemake: {
        //  Full Pipeline Conversation with SSE streaming progress
        async fullPipelineConversationStream(
            params: {
                original_script: string;
                target_word_count: number;
                source_language?: string;
                language?: string;
                dialect?: string;
                channel_name?: string;
                country?: string;
                add_quiz?: boolean;
                value_type?: 'sell' | 'engage' | 'community' | '';
                storytelling_style?: string;
                narrative_voice?: string;
                custom_narrative_voice?: string;
                audience_address?: string;
                custom_audience_address?: string;
                style_profile?: any;
                model?: string;
                custom_value?: string;
            },
            onProgress: (step: string, percentage: number, message: string) => void,
            signal?: AbortSignal
        ): Promise<any> {
            const response = await fetch(`${API_BASE_URL}/api/workflow/advanced-remake/full-pipeline-conversation-stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params),
                signal,
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            return new Promise((resolve, reject) => {
                const reader = response.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = '';


                let resolved = false;
                let eventType = 'message'; // Persists across chunk boundaries for correct SSE event/data pairing

                function read(): void {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            if (buffer.trim()) processChunk('\n');
                            // If we reach here without resolving, the stream closed unexpectedly
                            if (!resolved) {
                                resolved = true;
                                reject(new Error('Stream closed without result'));
                            }
                            return;
                        }
                        processChunk(decoder.decode(value, { stream: true }));
                        read();
                    }).catch((err) => {
                        if (!resolved) {
                            resolved = true;
                            reject(err);
                        }
                    });
                }

                function processChunk(chunk: string) {
                    buffer += chunk;
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith('data: ')) {
                            const jsonStr = line.slice(6);
                            try {
                                const data = JSON.parse(jsonStr);
                                if (eventType === 'result') {
                                    resolved = true;
                                    resolve(data);
                                    return;
                                } else if (eventType === 'error') {
                                    resolved = true;
                                    reject(new Error(data.error || 'Pipeline error'));
                                    return;
                                } else {
                                    if (data.step !== undefined && data.percentage !== undefined && data.message !== undefined) {
                                        onProgress(data.step, data.percentage, data.message);
                                    } else if (data.message) {
                                        onProgress(data.step || 'processing', data.percentage ?? 0, data.message);
                                    }
                                }
                            } catch (e) {
                                // Skip non-JSON lines
                            }
                            eventType = 'message';
                        }
                    }
                }

                read();
            });
        },

        //  Split script into scenes (language-aware)
        // split_mode: 'voiceover' (5-8s) or 'footage' (3-5s)
        async splitScriptToScenes(script: string, model?: string, language?: string, splitMode: 'voiceover' | 'footage' = 'voiceover') {
            const response = await api.post('/api/workflow/split-to-scenes', {
                script,
                model,
                language,
                split_mode: splitMode,
            }, { timeout: 300000 }); // 5 min timeout
            return response.data;
        },

        //  Analyze scene context (characters & settings) for consistency
        async analyzeSceneContext(params: {
            script: string;
            language?: string;
            model?: string;
        }): Promise<any> {
            const response = await api.post('/api/workflow/analyze-scene-context', params, { timeout: 120000 });
            return response.data;
        },

        //  Analyze script concept for footage alignment
        async analyzeConcept(params: {
            script: string;
            model?: string;
        }): Promise<any> {
            const response = await api.post('/api/workflow/analyze-concept', params, { timeout: 120000 });
            return response.data;
        },

        //  Generate AI keywords & prompts for scenes (mode-based)
        async generateSceneKeywords(
            params: {
                scenes: { scene_id: number; content: string; audio_duration?: number }[];
                language?: string;
                model?: string;
                mode?: 'footage' | 'concept' | 'storytelling' | 'custom';
                generate_image_prompt?: boolean;
                generate_video_prompt?: boolean;
                generate_keywords?: boolean;
                prompt_style?: string;
                main_character?: string;
                consistent_characters?: boolean;
                consistent_settings?: boolean;
                scene_context?: { characters?: any[]; settings?: any[] } | null;
                concept_analysis?: any;  // Concept data from /analyze-concept
                context_description?: string;  // Environment/setting description for full_sync
                image_prompt_mode?: string;   // reference | scene_builder | concept
                video_prompt_mode?: string;   // character_sync | scene_sync | full_sync
                directions?: { scene_id: number; direction_notes: string }[];  // Direction analysis results
                sync_analysis?: any;  // Sync analysis data (characters, settings, visual_style)
            },
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            const response = await fetch(`${API_BASE_URL}/api/workflow/generate-scene-keywords`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params),
                signal,
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }

            return new Promise((resolve, reject) => {
                const reader = response.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let eventType = 'message';
                let resolved = false;

                function processChunk(chunk: string) {
                    buffer += chunk;
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith('data: ')) {
                            const jsonStr = line.slice(6);
                            try {
                                const data = JSON.parse(jsonStr);
                                if (eventType === 'result') {
                                    if (!resolved) { resolved = true; resolve(data); }
                                    return;
                                } else if (eventType === 'error') {
                                    if (!resolved) { resolved = true; reject(new Error(data.error || 'Keyword generation error')); }
                                    return;
                                } else if (data.type === 'progress') {
                                    onProgress(data.message, data.percentage);
                                }
                            } catch (e) {
                                // Skip non-JSON
                            }
                            eventType = 'message';
                        }
                    }
                }

                function read(): void {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            if (buffer.trim()) processChunk('\n');
                            if (!resolved) { resolved = true; reject(new Error('Stream closed without result')); }
                            return;
                        }
                        processChunk(decoder.decode(value, { stream: true }));
                        read();
                    }).catch((err) => {
                        if (!resolved) { resolved = true; reject(err); }
                    });
                }
                read();
            });
        },

        // ── Video Prompt Pipeline (5-Step Sequential) ──

        // Helper: SSE fetch with progress callback
        async _sseCall(
            endpoint: string,
            params: any,
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            const response = await fetch(`${API_BASE_URL}/api/workflow/${endpoint}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params),
                signal,
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP ${response.status}: ${errorText}`);
            }
            return new Promise((resolve, reject) => {
                const reader = response.body!.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let eventType = 'message';
                let resolved = false;

                function processChunk(chunk: string) {
                    buffer += chunk;
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    for (const line of lines) {
                        if (line.startsWith('event: ')) {
                            eventType = line.slice(7).trim();
                        } else if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (eventType === 'result') { if (!resolved) { resolved = true; resolve(data); } return; }
                                else if (eventType === 'error') { if (!resolved) { resolved = true; reject(new Error(data.error || 'Pipeline error')); } return; }
                                else if (data.type === 'progress') { onProgress(data.message, data.percentage); }
                            } catch { /* skip non-JSON */ }
                            eventType = 'message';
                        }
                    }
                }

                function read(): void {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            if (buffer.trim()) processChunk('\n');
                            if (!resolved) { resolved = true; reject(new Error('Stream closed without result')); }
                            return;
                        }
                        processChunk(decoder.decode(value, { stream: true }));
                        read();
                    }).catch((err) => {
                        if (!resolved) { resolved = true; reject(err); }
                    });
                }
                read();
            });
        },

        // Step 1: Analyze video direction (text script → directing notes)
        async analyzeVideoDirection(
            params: {
                scenes: { scene_id: number; content: string }[];
                language?: string;
                model?: string;
                prompt_style?: string;
                main_character?: string;
                context_description?: string;
                sync_analysis?: any;
            },
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            return this._sseCall('analyze-video-direction', params, onProgress, signal);
        },

        // Step 2: Generate video prompts (direction notes → video generation prompts)
        async generateVideoPrompts(
            params: {
                scenes: { scene_id: number; content: string; direction_notes?: string; audio_duration?: number }[];
                language?: string;
                model?: string;
                prompt_style?: string;
                main_character?: string;
                context_description?: string;
                video_prompt_mode?: string;
                sync_analysis?: any;
            },
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            return this._sseCall('generate-video-prompts', params, onProgress, signal);
        },


        // Step 3: Extract recurring entities (characters, environments, props ≥2 appearances)
        async extractEntities(
            params: {
                video_prompts: { scene_id: number; video_prompt: string }[];
                language?: string;
                model?: string;
                script_scenes?: { scene_id: number; content: string }[];
            },
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            return this._sseCall('extract-entities', params, onProgress, signal);
        },

        // Step 4: Generate VEO3 reference image prompts for each entity
        async generateReferencePrompts(
            params: {
                entities: { name: string; type: string; description: string; scene_ids?: number[] }[];
                model?: string;
                prompt_style?: string;
                sync_analysis?: any;
            },
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            return this._sseCall('generate-reference-prompts', params, onProgress, signal);
        },

        // Step 5: Generate scene builder prompts with [Name] references
        async generateSceneBuilderPrompts(
            params: {
                video_prompts: { scene_id: number; video_prompt: string }[];
                entities: { name: string; type: string; description: string; scene_ids?: number[] }[];
                directions?: any[];
                model?: string;
                prompt_style?: string;
                sync_analysis?: any;
            },
            onProgress: (message: string, percentage: number) => void,
            signal?: AbortSignal
        ): Promise<any> {
            return this._sseCall('generate-scene-builder-prompts', params, onProgress, signal);
        },

        // Generate YouTube metadata (Title, Description, Thumbnail Prompt)
        async generateYoutubeMetadata(params: {
            script: string;
            style_profile?: any;
            title_samples?: string[];
            description_samples?: string[];
            title_style_analysis?: any;
            description_style_analysis?: any;
            thumbnail_style_analysis?: any;
            generate_title: boolean;
            generate_description: boolean;
            generate_thumbnail_prompt: boolean;
            model?: string;
            custom_cta?: string;
            sync_analysis?: any;
            voice_timestamps?: Array<{ scene_id: number; timestamp: string; content: string; duration: number }>;
            total_duration?: string;
            language?: string;
        }): Promise<{
            success: boolean;
            title: string;
            description: string;
            thumbnail_prompt: string;
        }> {
            const response = await api.post('/api/workflow/generate-youtube-metadata', params, { timeout: 120000 });
            return response.data;
        },
    },
};


// 
// VOICE GENERATION API
// 

export const voiceApi = {
    // List available voices
    async getVoices() {
        const response = await api.get('/api/voice/voices');
        return response.data;
    },

    // Generate voice for a single scene
    async generateVoice(params: {
        text: string;
        voice?: string;
        language?: string;
        speed?: number;
        scene_id?: number;
    }) {
        const response = await api.post('/api/voice/generate', {
            text: params.text,
            voice: params.voice || 'vi-VN-HoaiMyNeural',
            language: params.language || 'vi',
            speed: params.speed || 1.0,
            scene_id: params.scene_id || 1,
        }, { timeout: 60000 });
        return response.data;
    },

    // Generate voice batch with SSE streaming progress
    async generateBatch(
        params: {
            scenes: { scene_id: number; content: string; voiceExport: boolean }[];
            voice?: string;
            language?: string;
            speed?: number;
            session_id?: string;
        },
        onProgress: (current: number, total: number, sceneId: number, percentage: number, durationSeconds?: number) => void,
        signal?: AbortSignal,
        onSceneDone?: (sceneId: number, filename: string, durationSeconds: number) => void
    ): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/api/voice/generate-batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scenes: params.scenes,
                voice: params.voice || 'vi-VN-HoaiMyNeural',
                language: params.language || 'vi',
                speed: params.speed || 1.0,
                session_id: params.session_id || null,
            }),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return new Promise((resolve, reject) => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let resolved = false;
            let eventType = 'message';

            function processChunk(chunk: string) {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (eventType === 'result' || data.type === 'result') {
                                if (!resolved) { resolved = true; resolve(data); }
                                return;
                            } else if (data.type === 'scene_done' && onSceneDone) {
                                onSceneDone(data.scene_id, data.filename, data.duration_seconds);
                            } else if (data.type === 'progress') {
                                onProgress(data.current, data.total, data.scene_id, data.percentage);
                            }
                        } catch (e) {
                            // Skip non-JSON
                        }
                        eventType = 'message';
                    }
                }
            }

            function read(): void {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer.trim()) processChunk('\n');
                        if (!resolved) {
                            resolved = true;
                            resolve({ success: true, message: 'Stream completed' });
                        }
                        return;
                    }
                    processChunk(decoder.decode(value, { stream: true }));
                    read();
                }).catch((err) => {
                    if (!resolved) {
                        resolved = true;
                        reject(err);
                    }
                });
            }
            read();
        });
    },

    // Get audio file URL for playback
    getAudioUrl(filename: string, sessionId?: string): string {
        if (sessionId) {
            return `${API_BASE_URL}/api/voice/download/${sessionId}/${filename}`;
        }
        return `${API_BASE_URL}/api/voice/download/${filename}`;
    },

    // Download all voice files as zip
    async downloadAll(filenames: string[]) {
        const response = await fetch(`${API_BASE_URL}/api/voice/download-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filenames }),
        });

        if (!response.ok) {
            throw new Error(`Download failed: ${response.status}`);
        }

        // Trigger browser download
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `voices_${Date.now()}.zip`;
        a.click();
        URL.revokeObjectURL(url);
    },

    // List generated voice files
    async listFiles() {
        const response = await api.get('/api/voice/files');
        return response.data;
    },

    // Cleanup voice files
    async cleanup(filenames?: string[]) {
        const response = await api.post('/api/voice/cleanup', { filenames: filenames || null });
        return response.data;
    },

    // Delete session folder (voice_output/<sessionId>/)
    async cleanupSession(sessionId: string) {
        try {
            const response = await api.delete(`/api/voice/session/${sessionId}`);
            return response.data;
        } catch (e) {
            console.warn('[voiceApi] cleanupSession failed (non-blocking):', e);
            return null;
        }
    },
};


// 
// FOOTAGE SEARCH & VIDEO ASSEMBLY API
// 

export const footageApi = {
    // Check API key status
    async getStatus() {
        const response = await api.get('/api/footage/status');
        return response.data;
    },

    // Update API keys
    async updateKeys(pexelsKey: string, pixabayKey: string) {
        const response = await api.post('/api/footage/update-keys', {
            pexels_api_key: pexelsKey,
            pixabay_api_key: pixabayKey,
        });
        return response.data;
    },

    // Search footage for a single scene
    async searchForScene(keyword: string, orientation?: string, targetDuration?: number) {
        const params = new URLSearchParams({
            keyword,
            orientation: orientation || 'landscape',
            target_duration: String(targetDuration || 7.0),
        });
        const response = await api.get(`/api/footage/search-for-scene?${params.toString()}`, { timeout: 30000 });
        return response.data;
    },

    // Search footage for all scenes with SSE streaming progress
    async searchBatch(
        params: {
            scenes: { scene_id: number; keyword: string; keywords?: string[]; target_duration?: number; target_clip_duration?: number; scene_text?: string }[];
            orientation?: string;
            prefer_source?: string;
            pexels_api_key?: string;
            pixabay_api_key?: string;
            use_ai_concepts?: boolean;
            full_script?: string;
            concept_analysis?: any;  // Concept data from /analyze-concept
        },
        onProgress: (message: string, percentage: number, sceneId?: number) => void,
        onSceneResult?: (sceneId: number, footage: any, footageList?: any[]) => void,
        signal?: AbortSignal
    ): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/api/footage/search-batch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return new Promise((resolve, reject) => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let eventType = 'message';

            function processChunk(chunk: string) {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (eventType === 'result' || data.type === 'result') {
                                resolve(data);
                                return;
                            } else if (eventType === 'error') {
                                reject(new Error(data.error || 'Footage search error'));
                                return;
                            } else if (data.type === 'scene_result' && onSceneResult) {
                                onSceneResult(data.scene_id, data.footage, data.footage_list);
                            } else if (data.type === 'progress') {
                                onProgress(data.message, data.percentage, data.scene_id);
                            }
                        } catch (e) {
                            // Skip non-JSON
                        }
                        eventType = 'message';
                    }
                }
            }

            function read(): void {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer.trim()) processChunk('\n');
                        return;
                    }
                    processChunk(decoder.decode(value, { stream: true }));
                    read();
                }).catch(reject);
            }
            read();
        });
    },

    // Download footage for a scene
    async downloadFootage(url: string, sceneId: number) {
        const response = await api.post('/api/footage/download', {
            url,
            scene_id: sceneId,
        }, { timeout: 120000 });
        return response.data;
    },

    // Assemble footage + audio with SSE progress (supports auto-sync + post-production)
    async assembleScenes(
        params: {
            scenes: { scene_id: number; footage_url?: string; audio_filename: string; keyword?: string; subtitle_text?: string; video_id?: string; source?: string }[];
            orientation?: string;
            transition_duration?: number;
            bgm_volume?: number;
            video_quality?: string;
            enable_subtitles?: boolean;
            session_id?: string;
        },
        onProgress: (message: string, percentage: number, sceneId?: number) => void,
        onSceneComplete?: (sceneId: number, videoPath: string) => void,
        signal?: AbortSignal,
        onFootageFound?: (sceneId: number, footage: { video_id: string; source: string; duration: number; thumbnail_url: string; download_url: string }) => void,
    ): Promise<any> {
        const response = await fetch(`${API_BASE_URL}/api/footage/assemble`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
            signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        return new Promise((resolve, reject) => {
            const reader = response.body!.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let resolved = false;
            let eventType = 'message';

            function processChunk(chunk: string) {
                buffer += chunk;
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        eventType = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        const jsonStr = line.slice(6);
                        try {
                            const data = JSON.parse(jsonStr);
                            if (eventType === 'result' || data.type === 'result') {
                                if (!resolved) { resolved = true; resolve(data); }
                                return;
                            } else if (eventType === 'error') {
                                if (!resolved) { resolved = true; reject(new Error(data.error || 'Assembly error')); }
                                return;
                            } else if (data.type === 'scene_complete' && onSceneComplete) {
                                onSceneComplete(data.scene_id, data.video_path);
                            } else if (data.type === 'footage_found' && onFootageFound) {
                                onFootageFound(data.scene_id, data);
                            } else if (data.type === 'progress') {
                                onProgress(data.message, data.percentage, data.scene_id);
                            }
                        } catch (e) {
                            // Skip non-JSON
                        }
                        eventType = 'message';
                    }
                }
            }

            function read(): void {
                reader.read().then(({ done, value }) => {
                    if (done) {
                        if (buffer.trim()) processChunk('\n');
                        if (!resolved) {
                            resolved = true;
                            reject(new Error('Assembly stream closed without result'));
                        }
                        return;
                    }
                    processChunk(decoder.decode(value, { stream: true }));
                    read();
                }).catch((err) => {
                    if (!resolved) {
                        resolved = true;
                        reject(err);
                    }
                });
            }
            read();
        });
    },

    // Assemble all scenes into final video
    async assembleAll(sceneVideos: { scene_id: number; video_path: string }[], outputFilename?: string) {
        const response = await api.post('/api/footage/assemble-all', {
            scene_videos: sceneVideos,
            output_filename: outputFilename || 'final_video.mp4',
        }, { timeout: 600000 }); // 10 min timeout
        return response.data;
    },

    // Get download URL for assembled video
    getVideoUrl(filename: string): string {
        return `${API_BASE_URL}/api/footage/download-video/${filename}`;
    },

    // Get currently configured API keys from backend .env
    async getConfig() {
        const response = await api.get('/api/footage/config');
        return response.data;
    },

    // Update API keys for footage sources (Pexels/Pixabay)
    async updateConfig(pexelsKey: string, pixabayKey: string) {
        const params = new URLSearchParams();
        if (pexelsKey) params.append('pexels_key', pexelsKey);
        if (pixabayKey) params.append('pixabay_key', pixabayKey);
        const response = await api.post(`/api/footage/config?${params.toString()}`);
        return response.data;
    },

    // Test a Pexels or Pixabay API key
    async testKey(source: 'pexels' | 'pixabay', apiKey: string) {
        const params = new URLSearchParams({ source, api_key: apiKey });
        const response = await api.post(`/api/footage/test-key?${params.toString()}`);
        return response.data;
    },

    // Delete session folder (video_output/<sessionId>/)
    async cleanupSession(sessionId: string) {
        try {
            const response = await api.delete(`/api/footage/session/${sessionId}`);
            return response.data;
        } catch (e) {
            console.warn('[footageApi] cleanupSession failed (non-blocking):', e);
            return null;
        }
    },
};


// 
// FOOTAGE API KEY POOL MANAGEMENT
// 

export interface FootageKeyInfo {
    id: number;
    source: string;
    api_key: string;
    api_key_masked: string;
    label: string;
    is_active: number;
    request_count: number;
    last_used_at: string | null;
    last_tested_at: string | null;
    test_status: string;
    created_at: string;
}

export const footageKeysApi = {
    // Get all keys for a source
    async getKeys(source: 'pexels' | 'pixabay'): Promise<{ success: boolean; keys: FootageKeyInfo[]; pool_status: any }> {
        const response = await api.get(`/api/footage-keys/${source}`);
        return response.data;
    },

    // Add a new key
    async addKey(source: 'pexels' | 'pixabay', apiKey: string, label: string = ''): Promise<{ success: boolean; key_id?: number; error?: string }> {
        const response = await api.post(`/api/footage-keys/${source}`, { api_key: apiKey, label });
        return response.data;
    },

    // Remove a key
    async removeKey(keyId: number): Promise<{ success: boolean }> {
        const response = await api.delete(`/api/footage-keys/${keyId}`);
        return response.data;
    },

    // Toggle a key active/inactive
    async toggleKey(keyId: number, active: boolean): Promise<{ success: boolean }> {
        const response = await api.patch(`/api/footage-keys/${keyId}/toggle`, { active });
        return response.data;
    },

    // Test a specific key
    async testKey(source: 'pexels' | 'pixabay', apiKey: string): Promise<{ success: boolean; message?: string; error?: string }> {
        const response = await api.post(`/api/footage-keys/${source}/test`, { api_key: apiKey });
        return response.data;
    },

    // Get pool status summary
    async getPoolStatus(): Promise<{ success: boolean; pool: Record<string, { total_keys: number; active_keys: number; total_requests: number }> }> {
        const response = await api.get('/api/footage-keys');
        return response.data;
    },
};


// 
// FREE FOOTAGE API (No API Keys Required)
// 

export interface FreeFootageResult {
    source: string;
    video_id: string;
    title: string;
    thumbnail_url: string;
    thumbnail?: string;
    preview_url: string;
    download_url: string;
    url?: string;
    duration: number;
    width: number;
    height: number;
    license: string;
    attribution: string;
    original_query: string;
    aspect_ratio: string;
    is_hd: boolean;
    is_full_hd: boolean;
    local_preview_url?: string;  // Local API URL for cached video preview
}

export const freeFootageApi = {
    // Get status of free footage sources
    async getStatus(): Promise<{
        success: boolean;
        available: boolean;
        sources: string[];
        source_status?: Record<string, boolean>;
        message?: string;
    }> {
        const response = await api.get('/api/footage/free/status');
        return response.data;
    },

    // Search for a single scene (no API keys needed)
    async searchForScene(params: {
        keyword: string;
        orientation?: string;
        target_duration?: number;
        preferred_sources?: string[];
    }): Promise<{
        success: boolean;
        footage: FreeFootageResult | null;
        source?: string;
        message?: string;
    }> {
        const response = await api.post('/api/footage/free/search', {
            keyword: params.keyword,
            orientation: params.orientation || 'landscape',
            target_duration: params.target_duration || 7.0,
            preferred_sources: params.preferred_sources || null,
        });
        return response.data;
    },

    // Batch search with SSE streaming (no API keys needed)
    async searchBatch(
        params: {
            scenes: { scene_id: number; keyword: string; target_duration?: number }[];
            orientation?: string;
            preferred_sources?: string[];
        },
        onProgress: (message: string, percentage: number, sources?: string[]) => void,
        onSceneResult: (sceneId: number, footage: FreeFootageResult | null) => void,
        signal?: AbortSignal
    ): Promise<{
        success: boolean;
        total: number;
        found: number;
        sources_used: string[];
    }> {
        return new Promise((resolve, reject) => {
            fetch(`${API_BASE_URL}/api/footage/free/search-batch`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    scenes: params.scenes,
                    orientation: params.orientation || 'landscape',
                    preferred_sources: params.preferred_sources || null,
                }),
                signal,
            })
                .then(response => {
                    if (!response.body) throw new Error('No response body');
                    const reader = response.body.getReader();
                    const decoder = new TextDecoder();
                    let buffer = '';
                    let eventType = 'message';

                    function processChunk(chunk: string): void {
                        buffer += chunk;
                        const lines = buffer.split('\n');
                        buffer = lines.pop() || '';

                        for (const line of lines) {
                            if (line.startsWith('event:')) {
                                eventType = line.replace('event:', '').trim();
                            } else if (line.startsWith('data:')) {
                                const dataStr = line.replace('data:', '').trim();
                                try {
                                    const data = JSON.parse(dataStr);

                                    if (eventType === 'result' || data.type === 'result') {
                                        resolve({
                                            success: data.success,
                                            total: data.total,
                                            found: data.found,
                                            sources_used: data.sources_used || [],
                                        });
                                        return;
                                    } else if (eventType === 'error' || data.type === 'error') {
                                        reject(new Error(data.error || 'Search error'));
                                        return;
                                    } else if (data.type === 'scene_result') {
                                        onSceneResult(data.scene_id, data.footage);
                                    } else if (data.type === 'progress') {
                                        onProgress(data.message, data.percentage, data.sources);
                                    }
                                } catch {
                                    // Skip non-JSON
                                }
                                eventType = 'message';
                            }
                        }
                    }

                    function read(): void {
                        reader.read().then(({ done, value }) => {
                            if (done) {
                                if (buffer.trim()) processChunk('\n');
                                return;
                            }
                            processChunk(decoder.decode(value, { stream: true }));
                            read();
                        }).catch(reject);
                    }
                    read();
                })
                .catch(reject);
        });
    },

    // Cache a video on-demand and get preview URL
    async cacheVideo(params: {
        download_url: string;
        video_id: string;
        source: string;
    }): Promise<{
        success: boolean;
        cached_path?: string;
        duration?: number;
        preview_url?: string;
        message?: string;
    }> {
        const response = await api.post('/api/footage/cache/video', params);
        return response.data;
    },
};


// 
// PROJECTS API
// 

export const projectApi = {
    async createProject(name: string, styleId?: number | null, data?: Record<string, any>) {
        const response = await api.post('/api/projects', {
            name,
            style_id: styleId || null,
            data: data || null,
        });
        return response.data;
    },

    async getProjects() {
        const response = await api.get('/api/projects');
        return response.data;
    },

    async getProject(projectId: number) {
        const response = await api.get(`/api/projects/${projectId}`);
        return response.data;
    },

    async updateProject(projectId: number, updates: { name?: string; status?: string; style_id?: number; data?: Record<string, any> }) {
        const response = await api.put(`/api/projects/${projectId}`, updates);
        return response.data;
    },

    async deleteProject(projectId: number) {
        const response = await api.delete(`/api/projects/${projectId}`);
        return response.data;
    },

    /** Save full workflow data to an existing project */
    async saveProjectData(projectId: number, data: Record<string, any>) {
        return projectApi.updateProject(projectId, { data });
    },
};


// ═══════════════════════════════════════════════════════════════════════════════
// EXPORT / PACKAGING API
// ═══════════════════════════════════════════════════════════════════════════════

export interface ExportPackageParams {
    output_dir: string;
    item_id: string;
    folder_name?: string;
    export_options: {
        full_script: boolean;
        split_csv: boolean;
        final_video: boolean;
        voice_zip: boolean;
        footage_zip: boolean;
        keywords_txt?: boolean;
        prompts_txt?: boolean;
        seo_optimize?: boolean;
    };
    full_script: string;
    scenes: { scene_id: number; content: string; keywords?: string[]; image_prompt: string; video_prompt: string }[];
    voice_filenames: string[];
    final_video_path: string;
    scene_video_paths: string[];
    // Production metadata
    project_name?: string;
    original_link?: string;
    description?: string;
    thumbnail?: string;
    keywords?: string;
    upload_platform?: string;
    channel_name?: string;
    preset_name?: string;
    voice_id?: string;
    settings_snapshot?: Record<string, any>;
    // Production metadata from queue items
    original_title?: string;
    original_description?: string;
    thumbnail_url?: string;
    generated_title?: string;
    generated_description?: string;
    generated_thumbnail_prompt?: string;
    // SEO Thô
    seo_data?: Record<string, any>;
}

export const exportApi = {
    async packageResults(params: ExportPackageParams) {
        const response = await api.post('/api/export/package', params, { timeout: 120000 });
        return response.data;
    },
};


// YouTube Extract API
export const youtubeApi = {
    async extractFromUrl(url: string): Promise<{
        success: boolean;
        video_id?: string;
        title?: string;
        description?: string;
        thumbnail_url?: string;
        transcript?: string;
        transcript_segments?: { text: string; start: number; duration: number }[];
        has_transcript: boolean;
        channel_name?: string;
        error?: string;
    }> {
        const response = await api.post('/api/youtube/extract', { url }, { timeout: 60000 });
        return response.data;
    },
};

export default api;


// ═══════════════════════════════════════════════════════════════════════════════
// SEO THÔ API
// ═══════════════════════════════════════════════════════════════════════════════

export interface SEODataPayload {
    main_keyword: string;
    secondary_keywords: string[];
    seo_title: string;
    seo_description: string;
    seo_tags: string[];
    seo_filename: string;
    channel_name: string;
    target_platform: string;
}

export const seoApi = {
    async generate(params: {
        script_content: string;
        language?: string;
        channel_name?: string;
        target_platform?: string;
    }): Promise<{ success: boolean; seo_data: SEODataPayload }> {
        const response = await api.post('/api/seo/generate', {
            script_content: params.script_content,
            language: params.language || 'vi',
            channel_name: params.channel_name || '',
            target_platform: params.target_platform || 'youtube',
        }, { timeout: 60000 });
        return response.data;
    },

    async apply(params: {
        input_path: string;
        output_dir: string;
        seo_data: SEODataPayload;
        create_variant?: boolean;
        variant_method?: string;
    }) {
        const response = await api.post('/api/seo/apply', params, { timeout: 120000 });
        return response.data;
    },

    async readMetadata(filepath: string) {
        const response = await api.post('/api/seo/read-metadata', { filepath });
        return response.data;
    },
};


// 
// PRODUCTIONS API (Production Hub)
// 

export interface Production {
    id: number;
    // 18 Core Fields
    project_name: string;
    sequence_number: number;
    original_link: string;
    title: string;
    description: string;
    thumbnail: string;
    keywords: string;
    script_full: string;
    script_split: string;
    voiceover: string;
    video_footage: string;
    video_final: string;
    upload_platform: string;
    channel_name: string;
    video_status: string;
    prompts_reference: string;
    prompts_scene_builder: string;
    prompts_concept: string;
    prompts_video: string;
    // Original vs Generated metadata
    original_title: string;
    original_description: string;
    thumbnail_url: string;
    generated_title: string;
    generated_description: string;
    generated_thumbnail_prompt: string;
    // Internal
    export_dir: string;
    preset_name: string;
    voice_id: string;
    settings_snapshot: Record<string, any>;
    created_at: string;
    updated_at: string;
}

export interface ProductionFile {
    name: string;
    size_bytes: number;
    path: string;
    extension: string;
}

export const productionApi = {
    async create(data: Partial<Omit<Production, 'id' | 'created_at' | 'updated_at'>>): Promise<{ success: boolean; production: Production }> {
        const response = await api.post('/api/productions', data);
        return response.data;
    },

    async list(search: string = '', limit: number = 100): Promise<{ success: boolean; productions: Production[]; count: number }> {
        const params = new URLSearchParams();
        if (search) params.set('search', search);
        if (limit !== 100) params.set('limit', String(limit));
        const response = await api.get(`/api/productions?${params.toString()}`);
        return response.data;
    },

    async get(id: number): Promise<{ success: boolean; production: Production }> {
        const response = await api.get(`/api/productions/${id}`);
        return response.data;
    },

    async getFiles(id: number): Promise<{ success: boolean; exists: boolean; files: ProductionFile[]; total_size_bytes: number }> {
        const response = await api.get(`/api/productions/${id}/files`);
        return response.data;
    },

    async getStats(): Promise<{ success: boolean; total: number; with_video: number }> {
        const response = await api.get('/api/productions/stats');
        return response.data;
    },

    async update(id: number, data: Partial<Pick<Production, 'project_name' | 'original_link' | 'title' | 'description' | 'thumbnail' | 'upload_platform' | 'channel_name' | 'video_status' | 'prompts_reference' | 'prompts_scene_builder' | 'prompts_concept' | 'prompts_video' | 'script_full' | 'script_split' | 'voiceover' | 'keywords' | 'video_footage' | 'video_final' | 'export_dir' | 'preset_name' | 'voice_id' | 'original_title' | 'original_description' | 'thumbnail_url' | 'generated_title' | 'generated_description' | 'generated_thumbnail_prompt'>>): Promise<{ success: boolean }> {
        const response = await api.put(`/api/productions/${id}`, data);
        return response.data;
    },

    async delete(id: number, deleteFiles: boolean = false): Promise<{ success: boolean; files_deleted: boolean }> {
        const response = await api.delete(`/api/productions/${id}?delete_files=${deleteFiles}`);
        return response.data;
    },

    async openFolder(id: number): Promise<{ success: boolean }> {
        const response = await api.post(`/api/productions/${id}/open`);
        return response.data;
    },

    async openFile(filePath: string): Promise<{ success: boolean; message: string }> {
        const response = await api.post('/api/productions/open-file', { file_path: filePath });
        return response.data;
    },

    async scanImport(): Promise<{ success: boolean; imported_count: number; imported: any[]; message: string }> {
        const response = await api.post('/api/productions/scan-import');
        return response.data;
    },
};
