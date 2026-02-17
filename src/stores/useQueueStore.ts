import { create } from 'zustand';

export type PipelineStep = 'script' | 'scenes' | 'metadata' | 'voice' | 'keywords' | 'video_direction' | 'video_prompts' | 'entity_extraction' | 'reference_prompts' | 'scene_builder' | 'assembly' | 'seo' | 'export';

export interface ExportOptions {
    fullScript: boolean;
    splitCsv: boolean;
    finalVideo: boolean;
    voiceZip: boolean;
    footageZip: boolean;
    keywordsTxt: boolean;
    promptsTxt: boolean;
}

export interface QueueItem {
    id: string;
    scriptText: string;
    presetName: string;
    voiceId?: string;
    status: 'queued' | 'running' | 'done' | 'error';
    progress: number;
    currentStep: string;
    error?: string;
    failedStep?: PipelineStep;
    addedAt: number;
    // Cached data to prevent re-splitting on retry
    cachedScript?: string;
    cachedScenes?: any[];
    // Step-level tracking
    retryFromStep?: PipelineStep;
    completedSteps?: PipelineStep[];
    finalVideoPath?: string;
    // Cached intermediate results for step-level retry
    cachedVoiceResults?: Record<number, { filename: string; duration: number }>;
    cachedKeywordResult?: any;
    cachedPipelineResult?: {
        directions?: any[];
        entities?: any[];
        referencePromptsText?: string;
        sceneBuilderPromptsText?: string;
    };
    // Original YouTube metadata (input from user)
    originalTitle?: string;
    originalDescription?: string;
    thumbnailUrl?: string;
    // YouTube metadata generation results
    generatedTitle?: string;
    generatedDescription?: string;
    generatedThumbnailPrompt?: string;
    // Export result
    exportDir?: string;
    // Production Hub record ID (for incremental updates)
    productionId?: number;
    // SEO Thô data
    seoData?: {
        main_keyword: string;
        secondary_keywords: string[];
        seo_title: string;
        seo_description: string;
        seo_tags: string[];
        seo_filename: string;
        channel_name: string;
        target_platform: string;
    };
}

interface QueueState {
    items: QueueItem[];
    maxConcurrent: number;
    delayBetweenMs: number;
    outputPath: string;
    isQueueRunning: boolean;
    exportOptions: ExportOptions;

    // Actions
    addItem: (scriptText: string, presetName: string, voiceId?: string, metadata?: { originalTitle?: string; originalDescription?: string; thumbnailUrl?: string }) => string;
    removeItem: (id: string) => void;
    retryItem: (id: string) => void;
    retryItemFromStep: (id: string, step: PipelineStep) => void;
    clearCompleted: () => void;
    clearAll: () => void;
    updateItem: (id: string, updates: Partial<QueueItem>) => void;
    setMaxConcurrent: (n: number) => void;
    setDelayBetween: (ms: number) => void;
    setOutputPath: (path: string) => void;
    setIsQueueRunning: (running: boolean) => void;
    setExportOptions: (opts: Partial<ExportOptions>) => void;
    getNextQueued: () => QueueItem | undefined;
    getRunningCount: () => number;
}

function generateId(): string {
    return `q_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
}

export const useQueueStore = create<QueueState>((set, get) => ({
    items: [],
    maxConcurrent: 1,
    delayBetweenMs: 2000,
    outputPath: '',
    isQueueRunning: false,
    exportOptions: {
        fullScript: true,
        splitCsv: true,
        finalVideo: true,
        voiceZip: true,
        footageZip: true,
        keywordsTxt: true,
        promptsTxt: true,
    },

    addItem: (scriptText: string, presetName: string, voiceId?: string, metadata?: { originalTitle?: string; originalDescription?: string; thumbnailUrl?: string }) => {
        const id = generateId();
        set(state => ({
            items: [...state.items, {
                id,
                scriptText,
                presetName,
                voiceId,
                originalTitle: metadata?.originalTitle || undefined,
                originalDescription: metadata?.originalDescription || undefined,
                thumbnailUrl: metadata?.thumbnailUrl || undefined,
                status: 'queued',
                progress: 0,
                currentStep: 'Đang chờ...',
                addedAt: Date.now(),
            }]
        }));
        return id;
    },

    removeItem: (id: string) => {
        set(state => ({
            items: state.items.filter(item => item.id !== id)
        }));
    },

    retryItem: (id: string) => {
        set(state => ({
            items: state.items.map(item =>
                item.id === id && (item.status === 'error' || item.status === 'done')
                    ? { ...item, status: 'queued' as const, progress: 0, currentStep: 'Đang chờ retry...', error: undefined, failedStep: undefined, retryFromStep: undefined }
                    : item
            )
        }));
    },

    retryItemFromStep: (id: string, step: PipelineStep) => {
        set(state => ({
            items: state.items.map(item =>
                item.id === id && (item.status === 'error' || item.status === 'done')
                    ? {
                        ...item,
                        status: 'queued' as const,
                        progress: 0,
                        currentStep: `Đang chờ retry từ bước ${step}...`,
                        error: undefined,
                        failedStep: undefined,
                        retryFromStep: step,
                        finalVideoPath: undefined,
                    }
                    : item
            )
        }));
    },

    clearCompleted: () => {
        set(state => ({
            items: state.items.filter(item => item.status !== 'done')
        }));
    },

    clearAll: () => {
        set(state => ({
            items: state.items.filter(item => item.status === 'running'),
        }));
    },

    updateItem: (id: string, updates: Partial<QueueItem>) => {
        set(state => ({
            items: state.items.map(item =>
                item.id === id ? { ...item, ...updates } : item
            )
        }));
    },

    setMaxConcurrent: (n: number) => set({ maxConcurrent: Math.max(1, Math.min(5, n)) }),
    setDelayBetween: (ms: number) => set({ delayBetweenMs: Math.max(0, ms) }),
    setOutputPath: (path: string) => set({ outputPath: path }),
    setIsQueueRunning: (running: boolean) => set({ isQueueRunning: running }),
    setExportOptions: (opts: Partial<ExportOptions>) => set(state => ({
        exportOptions: { ...state.exportOptions, ...opts },
    })),

    getNextQueued: () => {
        return get().items.find(item => item.status === 'queued');
    },

    getRunningCount: () => {
        return get().items.filter(item => item.status === 'running').length;
    },
}));
