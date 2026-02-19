import { useState, useEffect, useRef, useCallback } from 'react';

import { useScriptWorkflowStore } from '../../stores/useScriptWorkflowStore';

import { useAISettingsStore } from '../../stores/useAISettingsStore';

import { workflowApi, aiApi, voiceApi, footageApi, freeFootageApi, projectApi, exportApi, youtubeApi, seoApi, productionApi } from '../../lib/api';

import PresetSection from './PresetSection';

import type { PipelineSelection, PresetConfig, AnalysisOptions } from './PresetSection';

import { useRealtimeEvent } from '../../contexts/RealtimeSyncContext';

import { normalizeAnalysis, isAnalysisEnabled, DEFAULT_ANALYSIS, isSeoEnabled } from './PresetSection';

import QueueSidebar from './QueueSidebar';

import QueuePanel from './QueuePanel';

import ProductionHub from './ProductionHub';

import { useQueueStore, QueueItem, PipelineStep } from '../../stores/useQueueStore';

import {

    CheckCircle,

    Loader2,

    Zap,

    BookOpen,

    Wand2,

    AlertCircle,

    Plus,

    Trash2,

    XCircle,

    Check,

    Save,

    Link2,

    ExternalLink,

    ChevronDown,

    ChevronRight,

    Package

} from 'lucide-react';



interface ScriptWorkflowProps {

    activeProjectId: string | null;

    setActiveProjectId: (id: string | null) => void;

    onBackToEntry?: () => void;

}



// Auto-detect country from language for legal review
const LANG_TO_COUNTRY: Record<string, string> = {
    vi: 'Vietnam',
    en: 'United States',
    zh: 'China',
    ja: 'Japan',
    ko: 'South Korea',
    es: 'Spain',
    fr: 'France',
    th: 'Thailand',
    de: 'Germany',
    pt: 'Brazil',
    ru: 'Russia',
};

export default function ScriptWorkflow({ activeProjectId, setActiveProjectId, onBackToEntry }: ScriptWorkflowProps) {

    const {

        referenceScript,

        referenceScripts,

        styleA,

        isAnalyzingStyle,

        error,

        setReferenceScript,

        setReferenceScripts,

        setStyleA,

        setAnalyzingStyle,

        remakeScript,

        setRemakeScript,

        channelName,

        setChannelName,

        topic,

        setTopic,

        language,

        setLanguage,

        setTemplates,

        setError,

    } = useScriptWorkflowStore();



    const [multiMode] = useState(false);

    const [, setModels] = useState<{ id: string; name: string; description: string }[]>([]);

    const [selectedModel, setSelectedModel] = useState('gpt-5.2-auto');

    const [showPresetGateway, setShowPresetGateway] = useState(true);
    const [isAnalysisLocked, setIsAnalysisLocked] = useState(false);

    const [showEntrySection, setShowEntrySection] = useState(true);

    const [isLoadingProject, setIsLoadingProject] = useState(false);

    const [showProjectNameDialog, setShowProjectNameDialog] = useState(false);

    const [newProjectName, setNewProjectName] = useState('');

    const [pendingStyleId, setPendingStyleId] = useState<number | null>(null);

    const [pendingStyleName, setPendingStyleName] = useState<string | null>(null);

    const [pipelineSelection, setPipelineSelection] = useState<PipelineSelection>(() => {

        try {

            const raw = localStorage.getItem('renmae_pipeline_selection');

            if (raw) {

                const parsed = JSON.parse(raw);

                // Migrate old 'prompts' key to new split keys

                if (parsed.videoProduction && 'prompts' in parsed.videoProduction && !('video_prompts' in parsed.videoProduction)) {

                    parsed.videoProduction.video_prompts = parsed.videoProduction.prompts;

                    parsed.videoProduction.image_prompts = parsed.videoProduction.prompts;

                    delete parsed.videoProduction.prompts;

                }

                return parsed;

            }

        } catch { /* ignore */ }

        return {

            styleAnalysis: { ...DEFAULT_ANALYSIS },

            scriptGeneration: true,

            voiceGeneration: true,

            videoProduction: { video_prompts: true, image_prompts: true, keywords: true, footage: true, image_prompt_mode: 'reference', video_prompt_mode: 'full_sync' },

            seoOptimize: { enabled: false, mode: 'auto' },

        };

    });



    // Progress tracking state

    const [analysisProgress, setAnalysisProgress] = useState<string>('');

    const [analysisTimer, setAnalysisTimer] = useState<number>(0);

    const timerRef = useRef<NodeJS.Timeout | null>(null);



    // Saved styles state

    const [savedStyles, setSavedStyles] = useState<any[]>([]);



    // Saved projects state (for entry section)

    const [savedProjects, setSavedProjects] = useState<any[]>([]);

    const [isLoadingProjects, setIsLoadingProjects] = useState(false);

    const [isProjectsCollapsed, setIsProjectsCollapsed] = useState(false);

    const [isVoicesCollapsed, setIsVoicesCollapsed] = useState(false);

    // Bulk selection state
    const [bulkSelectProjects, setBulkSelectProjects] = useState(false);
    const [selectedProjectIds, setSelectedProjectIds] = useState<Set<number>>(new Set());
    const [bulkSelectStyles, setBulkSelectStyles] = useState(false);
    const [selectedStyleIds, setSelectedStyleIds] = useState<Set<number>>(new Set());
    const [isDeletingBulk, setIsDeletingBulk] = useState(false);

    const [styleName, setStyleName] = useState('');

    const [showSaveDialog, setShowSaveDialog] = useState(false);

    const [isSavingStyle, setIsSavingStyle] = useState(false);

    const [styleSaved, setStyleSaved] = useState<string | null>(null);

    const [selectedStyleId, setSelectedStyleId] = useState<number | null>(null);

    const [renamingStyleId, setRenamingStyleId] = useState<number | null>(null);

    const [renameValue, setRenameValue] = useState('');

    const [isRefreshingStyles, setIsRefreshingStyles] = useState(false);

    const [analysisLanguage, setAnalysisLanguage] = useState('auto'); // Language for analysis prompts (auto = detect from scripts)



    // Individual analysis results (for detailed view)

    const [, setIndividualResults] = useState<any[]>([]);

    const [scriptsAnalyzed, setScriptsAnalyzed] = useState(0);

    // Title/Description/Thumbnail analysis samples
    const [titleSamples, setTitleSamples] = useState<string[]>([]);
    const [titleInput, setTitleInput] = useState('');
    const [descriptionSamples, setDescriptionSamples] = useState<string[]>([]);
    const [descriptionInput, setDescriptionInput] = useState('');
    const [thumbnailFiles, setThumbnailFiles] = useState<{ file: File; preview: string }[]>([]);

    // Collapse states for analysis input sections (collapsed by default)
    const [isVoiceInputExpanded, setIsVoiceInputExpanded] = useState(false);
    const [isTitleInputExpanded, setIsTitleInputExpanded] = useState(false);
    const [isDescInputExpanded, setIsDescInputExpanded] = useState(false);
    const [isThumbInputExpanded, setIsThumbInputExpanded] = useState(false);

    // Metadata style analysis results (title/description/thumbnail)
    const [titleStyleAnalysis, setTitleStyleAnalysis] = useState<any>(null);
    const [descriptionStyleAnalysis, setDescriptionStyleAnalysis] = useState<any>(null);
    const [thumbnailStyleAnalysis, setThumbnailStyleAnalysis] = useState<any>(null);

    // Per-section progress tracking for 4 analysis panels
    interface SectionProgress { pct: number; msg: string; status: 'idle' | 'running' | 'done' | 'error' }
    const defaultProgress: SectionProgress = { pct: 0, msg: '', status: 'idle' };
    const [voiceProgress, setVoiceProgress] = useState<SectionProgress>({ ...defaultProgress });
    const [titleProgress, setTitleProgress] = useState<SectionProgress>({ ...defaultProgress });
    const [descProgress, setDescProgress] = useState<SectionProgress>({ ...defaultProgress });
    const [thumbProgress, setThumbProgress] = useState<SectionProgress>({ ...defaultProgress });
    const [syncProgress, setSyncProgress] = useState<SectionProgress>({ ...defaultProgress });

    // YouTube URL extraction state
    const [youtubeUrlInput, setYoutubeUrlInput] = useState('');
    const [isExtractingYoutube, setIsExtractingYoutube] = useState(false);
    const [youtubeExtractedItems, setYoutubeExtractedItems] = useState<{
        video_id: string;
        title: string;
        description: string;
        thumbnail_url: string;
        transcript: string | null;
        channel_name: string;
    }[]>([]);

    // Computed analysis options from current pipeline
    const analysisOpts = normalizeAnalysis(pipelineSelection.styleAnalysis);



    // Abort controller for cancelling analysis

    const abortControllerRef = useRef<AbortController | null>(null);



    // 

    // ADVANCED REMAKE - 7 STEP WORKFLOW STATE

    // 

    const [advancedStep, setAdvancedStep] = useState(1);  // UI tabs: 1=Style Analysis, 2=Remake Script



    // Clear style analysis results on fresh mount so right panel starts empty

    useEffect(() => {

        setStyleA(null);

        setOriginalAnalysis(null);

    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    const [, setPipelineStep] = useState(0);  // Pipeline progress: 0=idle, 1-7=running steps

    const [isRunningAdvanced, setIsRunningAdvanced] = useState(false);

    const [advancedProgress, setAdvancedProgress] = useState('');



    // Advanced Remake results

    const [originalAnalysis, setOriginalAnalysis] = useState<any>(null);

    const [, setStructureAnalysis] = useState<any>(null);

    const [, setOutlineA] = useState<any>(null);

    const [, setAdvancedDraftSections] = useState<any[]>([]);

    const [similarityReview, setSimilarityReview] = useState<any>(null);

    const [, setRefinedSections] = useState<any[]>([]);

    const [advancedFinalScript, setAdvancedFinalScript] = useState('');



    // Scene splitting state

    const [scenes, setScenes] = useState<{ scene_id: number; content: string; word_count: number; est_duration?: number; audio_duration?: number; voiceExport: boolean; keyword?: string; keywords?: string[]; target_clip_duration?: number; image_prompt?: string; video_prompt?: string }[]>([]);

    const [isSplittingScenes, setIsSplittingScenes] = useState(false);

    const [sceneSplitProgress, setSceneSplitProgress] = useState('');

    const [detectedLanguage, setDetectedLanguage] = useState<string>('');

    const [splitMode, setSplitMode] = useState<'voiceover' | 'footage'>('voiceover'); // Scene split mode: voiceover (5-8s) or footage (3-5s)



    // 

    // VOICE GENERATION STATE

    // 

    const [, setAvailableVoices] = useState<any[]>([]);

    const [voicesByLanguage, setVoicesByLanguage] = useState<any>({});

    const [selectedVoice, setSelectedVoice] = useState('vi-VN-HoaiMyNeural');

    const [voiceLanguage, setVoiceLanguage] = useState('vi');

    const [voiceSpeed, setVoiceSpeed] = useState(1.0);

    const [sceneAudioMap, setSceneAudioMap] = useState<Record<number, { status: 'pending' | 'generating' | 'done' | 'error'; filename?: string; url?: string; error?: string }>>({});

    const [isGeneratingBatch, setIsGeneratingBatch] = useState(false);

    const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, percentage: 0 });

    const [playingSceneId, setPlayingSceneId] = useState<number | null>(null);

    const audioRef = useRef<HTMLAudioElement | null>(null);



    // Stop/Cancel controllers

    const scriptAbortRef = useRef<AbortController | null>(null);

    const voiceAbortRef = useRef<AbortController | null>(null);

    const keywordAbortRef = useRef<AbortController | null>(null);

    const footageAbortRef = useRef<AbortController | null>(null);



    // Total voice duration

    const [totalVoiceDuration, setTotalVoiceDuration] = useState(0);



    // AI Keyword generation

    const [isGeneratingKeywords, setIsGeneratingKeywords] = useState(false);

    const [keywordProgress, setKeywordProgress] = useState('');

    const [editingCell, setEditingCell] = useState<{ sceneId: number; field: 'keyword' | 'image_prompt' | 'video_prompt' } | null>(null);



    // Scene generation mode

    const [sceneMode, setSceneMode] = useState<'footage' | 'concept' | 'storytelling' | 'custom'>('footage');

    const [genOptions, setGenOptions] = useState({

        keyword: true,

        imagePrompt: false,

        videoPrompt: false,

        consistentCharacters: false,

        consistentSettings: false,

    });

    const [sceneContext, setSceneContext] = useState<{ characters?: any[]; settings?: any[] } | null>(null);

    const [isAnalyzingContext, setIsAnalyzingContext] = useState(false);

    const [editValue, setEditValue] = useState('');



    // 

    // 

    // FOOTAGE/VIDEO ASSEMBLY STATE

    // 

    const [sceneFootage, setSceneFootage] = useState<Record<number, any>>({});

    const [isSearchingFootage, setIsSearchingFootage] = useState(false);

    const [footageProgress, setFootageProgress] = useState('');

    const [isAssemblingVideo, setIsAssemblingVideo] = useState(false);

    const [assemblyProgress, setAssemblyProgress] = useState('');

    const [assemblyPercentage, setAssemblyPercentage] = useState(0);

    const [footageOrientation, setFootageOrientation] = useState<'landscape' | 'portrait'>('landscape');

    const [videoQuality, setVideoQuality] = useState<string>('720p');

    const [enableSubtitles, setEnableSubtitles] = useState<boolean>(true);

    const [promptStyle, setPromptStyle] = useState<string>('');
    const [mainCharacter, setMainCharacter] = useState<string>('');
    const [contextDescription, setContextDescription] = useState<string>('');

    // Sync reference images (data URLs)
    const [syncCharacterImages, setSyncCharacterImages] = useState<string[]>([]);
    const [syncStyleImages, setSyncStyleImages] = useState<string[]>([]);
    const [syncContextImages, setSyncContextImages] = useState<string[]>([]);
    const [syncAnalysisResult, setSyncAnalysisResult] = useState<any>(null);

    const [useFreeFootage] = useState(false);

    const [finalVideoPath, setFinalVideoPath] = useState<string | null>(null);

    const [assembledVideos, setAssembledVideos] = useState<Record<string, any>>({});

    // Concept analysis (persisted across workflow steps)

    const [conceptAnalysis, setConceptAnalysis] = useState<any>(null);

    const [isAnalyzingConcept, setIsAnalyzingConcept] = useState(false);

    // One-click footage workflow

    const [isRunningFootageWorkflow, setIsRunningFootageWorkflow] = useState(false);

    const [footageWorkflowStep, setFootageWorkflowStep] = useState<string>('');



    // API keys from settings store

    const { pexelsApiKey, pixabayApiKey } = useAISettingsStore();



    //  Footage: map backend result → UI-friendly format 

    function mapFootageResult(raw: any, keyword?: string) {

        if (!raw) return null;

        return {

            ...raw,

            thumbnail: raw.thumbnail_url || raw.thumbnail || '',

            url: raw.download_url || raw.preview_url || raw.url || '',

            query: raw.query || keyword || '',

        };

    }



    //  Footage: search all scenes (batch) 

    const handleSearchFootageBatch = async () => {

        const scenesWithKeywords = scenes.filter(s => s.keyword || (s.keywords && s.keywords.length > 0));

        if (scenesWithKeywords.length === 0) return;



        setIsSearchingFootage(true);

        setFootageProgress('Đang bắt đầu tìm footage...');

        footageAbortRef.current = new AbortController();



        try {

            await footageApi.searchBatch(

                {

                    scenes: scenesWithKeywords.map(s => ({

                        scene_id: s.scene_id,

                        keyword: s.keyword!,

                        keywords: s.keywords || undefined,  // Multi-keyword list for footage mode

                        target_duration: s.audio_duration || s.est_duration || 7.0,

                        target_clip_duration: s.target_clip_duration || undefined,

                        scene_text: s.content || '',  // Voiceover text for AI Vision

                    })),

                    orientation: footageOrientation,

                    // Key rotation handled by backend pool (get_rotated_footage_api)

                    use_ai_concepts: sceneMode !== 'footage',

                    full_script: advancedFinalScript || '',  // Full script for AI Vision context

                },

                (message, percentage) => {

                    setFootageProgress(message);

                    console.log(`[Footage] ${percentage}% — ${message}`);

                },

                (sceneId, footage, footageList) => {

                    if (footageList && footageList.length > 0) {

                        // Multi-footage mode: store first (best) result as primary footage

                        const mappedList = footageList.map((f: any) => mapFootageResult(f, f.query));

                        setSceneFootage(prev => ({ ...prev, [sceneId]: mappedList[0] }));

                    } else {

                        const mapped = mapFootageResult(footage, scenesWithKeywords.find(s => s.scene_id === sceneId)?.keyword);

                        setSceneFootage(prev => ({ ...prev, [sceneId]: mapped }));

                    }

                },

                footageAbortRef.current.signal,

            );

            setFootageProgress('');

        } catch (err: any) {

            if (err.name === 'AbortError') {

                setFootageProgress('Đã dừng tìm footage.');

            } else {

                console.error('[Footage] Batch search error:', err);

                setFootageProgress(`Lỗi: ${err.message}`);

            }

        } finally {

            setIsSearchingFootage(false);

            footageAbortRef.current = null;

        }

    };



    //  Footage: search a single scene 

    const handleSearchFootageForScene = async (sceneId: number, keyword: string, duration?: number) => {

        try {

            const result = await footageApi.searchForScene(keyword, footageOrientation, duration || 7.0);

            if (result.success && result.footage) {

                const mapped = mapFootageResult(result.footage, keyword);

                setSceneFootage(prev => ({ ...prev, [sceneId]: mapped }));

            }

        } catch (err: any) {

            console.error(`[Footage] Scene #${sceneId} search error:`, err);

        }

    };



    //  Footage: stop batch search 

    const handleStopFootageSearch = () => {

        footageAbortRef.current?.abort();

    };



    //  One-click Footage Workflow: Keywords → Voice → Footage (uses pre-split scenes + concept from state) 

    const handleGenerateVideoFootage = async () => {

        // Validate: scenes must already be split

        if (!scenes || scenes.length === 0) {

            setError('Chưa có scenes. Vui lòng chia kịch bản thành scenes trước (Bước 3).');

            return;

        }

        if (!advancedFinalScript || advancedFinalScript.length < 50) {

            setError('Chưa có kịch bản hoàn chỉnh. Vui lòng hoàn thành Bước 2 trước.');

            return;

        }



        setIsRunningFootageWorkflow(true);

        setError(null);



        // Use concept analysis from state (set during scene splitting in Step 2/3)

        const concept = conceptAnalysis;

        if (concept) {

            console.log(`[Footage Workflow] Using concept: prefix="${concept.concept_prefix || ''}", style="${concept.style_modifier || ''}", subjects=${(concept.allowed_subjects || []).length}, forbidden=${(concept.forbidden_terms || []).length}`);

        } else {

            console.warn('[Footage Workflow] No concept analysis available — keywords will not be concept-anchored');

        }



        // Use scenes from state (already split by user)

        let currentScenes = [...scenes];

        const totalSteps = 3;



        try {

            //  STEP 1/3: Generate Keywords (concept-anchored) 

            setFootageWorkflowStep('Tạo từ khóa AI...');

            setIsGeneratingKeywords(true);



            const keywordController = new AbortController();

            keywordAbortRef.current = keywordController;



            const keywordResult = await workflowApi.advancedRemake.generateSceneKeywords({

                scenes: currentScenes.map(s => ({

                    scene_id: s.scene_id,

                    content: s.content,

                    audio_duration: s.audio_duration,

                })),

                language: detectedLanguage || advancedSettings.language || 'vi',

                model: selectedModel || undefined,

                mode: 'footage',

                concept_analysis: concept || undefined,

            }, (message, _pct) => {

                setFootageWorkflowStep(`Từ khóa: ${message}`);

            }, keywordController.signal);



            if (keywordResult?.success && keywordResult?.keywords) {

                const keywordMap: Record<number, any> = {};

                keywordResult.keywords.forEach((k: any) => {

                    keywordMap[k.scene_id] = k;

                });

                currentScenes = currentScenes.map(s => {

                    const kw = keywordMap[s.scene_id];

                    if (kw) {

                        return {

                            ...s,

                            keyword: kw.keyword || (kw.keywords ? kw.keywords[0] : ''),

                            keywords: kw.keywords || (kw.keyword ? [kw.keyword] : []),

                        };

                    }

                    return s;

                });

                setScenes(currentScenes);

                setKeywordProgress(` Đã tạo ${keywordResult.keywords.length} keywords (concept-anchored)`);

            }



            setIsGeneratingKeywords(false);

            keywordAbortRef.current = null;



            //  STEP 2/3: Generate Voice 

            setFootageWorkflowStep(`Tạo voice: ${currentScenes.length} scenes...`);



            const scenesForVoice = currentScenes;



            setIsGeneratingBatch(true);

            setBatchProgress({ current: 0, total: scenesForVoice.length, percentage: 0 });



            const controller = new AbortController();

            voiceAbortRef.current = controller;



            const initialAudioMap: typeof sceneAudioMap = {};

            scenesForVoice.forEach((s: any) => { initialAudioMap[s.scene_id] = { status: 'generating' }; });

            setSceneAudioMap(prev => ({ ...prev, ...initialAudioMap }));



            const voiceResult = await voiceApi.generateBatch(

                {

                    scenes: scenesForVoice.map((s: any) => ({

                        scene_id: s.scene_id,

                        content: s.content,

                        voiceExport: true,

                    })),

                    voice: selectedVoice,

                    language: voiceLanguage,

                    speed: voiceSpeed,

                },

                (current, total, sceneId, percentage) => {

                    setBatchProgress({ current, total, percentage });

                    setFootageWorkflowStep(`Voice ${current}/${total}`);

                    setSceneAudioMap(prev => ({

                        ...prev,

                        [sceneId]: {

                            status: 'done',

                            filename: `scene_${String(sceneId).padStart(3, '0')}.mp3`,

                            url: voiceApi.getAudioUrl(`scene_${String(sceneId).padStart(3, '0')}.mp3`),

                        }

                    }));

                },

                controller.signal,

                (sceneId, _filename, durationSeconds) => {

                    setScenes(prev => prev.map(s =>

                        s.scene_id === sceneId

                            ? { ...s, audio_duration: Math.round(durationSeconds * 10) / 10, est_duration: Math.round(durationSeconds * 10) / 10 }

                            : s

                    ));

                }

            );



            // Process voice results to update audio durations

            if (voiceResult?.results) {

                const finalMap: typeof sceneAudioMap = {};

                let totalDur = 0;

                voiceResult.results.forEach((r: any) => {

                    finalMap[r.scene_id] = r.success

                        ? { status: 'done', filename: r.filename, url: voiceApi.getAudioUrl(r.filename) }

                        : { status: 'error', error: r.error };

                    if (r.success && r.duration_seconds) {

                        totalDur += r.duration_seconds;

                        currentScenes = currentScenes.map(s =>

                            s.scene_id === r.scene_id

                                ? { ...s, audio_duration: Math.round(r.duration_seconds * 10) / 10, est_duration: Math.round(r.duration_seconds * 10) / 10 }

                                : s

                        );

                    }

                });

                setSceneAudioMap(prev => ({ ...prev, ...finalMap }));

                setScenes(currentScenes);

                setTotalVoiceDuration(Math.round(totalDur));

            }



            setIsGeneratingBatch(false);

            voiceAbortRef.current = null;



            //  STEP 3/3: Search Footage (thumbnail AI + concept) 

            setFootageWorkflowStep('Tìm footage...');



            const scenesWithKeywords = currentScenes.filter(s => s.keyword || (s.keywords && s.keywords.length > 0));



            if (scenesWithKeywords.length > 0) {

                setIsSearchingFootage(true);

                footageAbortRef.current = new AbortController();



                await footageApi.searchBatch(

                    {

                        scenes: scenesWithKeywords.map(s => ({

                            scene_id: s.scene_id,

                            keyword: s.keyword || s.keywords?.[0] || '',

                            keywords: s.keywords || undefined,

                            target_duration: s.audio_duration || s.est_duration || 7.0,

                            target_clip_duration: 4,

                            scene_text: s.content || '',

                        })),

                        orientation: footageOrientation,

                        // Key rotation handled by backend pool (get_rotated_footage_api)

                        use_ai_concepts: false,

                        full_script: advancedFinalScript || '',

                        concept_analysis: concept || undefined,

                    },

                    (message, _percentage) => {

                        setFootageProgress(message);

                        setFootageWorkflowStep(`Footage: ${message}`);

                    },

                    (sceneId, footage, footageList) => {

                        if (footageList && footageList.length > 0) {

                            const mappedList = footageList.map((f: any) => mapFootageResult(f, f.query));

                            setSceneFootage(prev => ({ ...prev, [sceneId]: mappedList[0] }));

                        } else {

                            const mapped = mapFootageResult(footage, scenesWithKeywords.find(s => s.scene_id === sceneId)?.keyword);

                            setSceneFootage(prev => ({ ...prev, [sceneId]: mapped }));

                        }

                    },

                    footageAbortRef.current.signal,

                );



                setIsSearchingFootage(false);

                setFootageProgress('');

                footageAbortRef.current = null;

            }



            setFootageWorkflowStep(' Hoàn tất! Keywords + Voice + Footage đã sẵn sàng.');

        } catch (err: any) {

            if (err.name === 'AbortError') {

                setFootageWorkflowStep(' Đã dừng workflow');

            } else {

                console.error('[Footage Workflow] Error:', err);

                setError(`Lỗi footage workflow: ${err.message}`);

                setFootageWorkflowStep(` Lỗi: ${err.message}`);

            }

        } finally {

            setIsRunningFootageWorkflow(false);

            setIsGeneratingBatch(false);

            setIsGeneratingKeywords(false);

            setIsSearchingFootage(false);

            voiceAbortRef.current = null;

            keywordAbortRef.current = null;

            footageAbortRef.current = null;

        }

    };



    // Unused stubs kept for JSX compatibility

    const handleSearchFreeFootage = () => { console.log('[Footage] Free footage search not available'); };

    const handleAssembleVideo = async () => {

        // Build scene list: include scenes with footage OR with keywords (auto-sync)

        const assembleScenes = scenes

            .filter((s: any) => sceneAudioMap[s.scene_id]?.status === 'done')

            .filter((s: any) => sceneFootage[s.scene_id]?.url || s.keyword || s.keywords)

            .map((s: any) => ({

                scene_id: s.scene_id,

                footage_url: sceneFootage[s.scene_id]?.url || undefined,

                audio_filename: sceneAudioMap[s.scene_id].filename || `scene_${String(s.scene_id).padStart(3, '0')}.mp3`,

                keyword: s.keyword || (s.keywords ? (Array.isArray(s.keywords) ? s.keywords[0] : s.keywords) : undefined),

                subtitle_text: s.content || '',

                video_id: sceneFootage[s.scene_id]?.video_id || undefined,

                source: sceneFootage[s.scene_id]?.source || undefined,

            }));



        if (assembleScenes.length === 0) {

            setError('Không có scene nào có audio và footage/keyword để ghép.');

            return;

        }



        const hasAutoSync = assembleScenes.some((s: any) => !s.footage_url && s.keyword);

        setIsAssemblingVideo(true);

        setAssemblyProgress(hasAutoSync

            ? ` Auto-Sync: đang xử lý ${assembleScenes.length} scenes...`

            : `Bắt đầu ghép ${assembleScenes.length} scenes...`

        );

        setAssemblyPercentage(0);

        setFinalVideoPath(null);

        setError(null);



        try {

            const result = await footageApi.assembleScenes(

                {

                    scenes: assembleScenes,

                    orientation: footageOrientation,

                    transition_duration: 0.5,

                    video_quality: videoQuality,

                    enable_subtitles: enableSubtitles,

                },

                // onProgress

                (message: string, percentage: number) => {

                    setAssemblyProgress(message);

                    setAssemblyPercentage(percentage);

                },

                // onSceneComplete

                (sceneId: number, videoPath: string) => {

                    setAssembledVideos((prev: Record<string, any>) => ({ ...prev, [sceneId]: videoPath }));

                },

                // signal

                undefined,

                // onFootageFound — update sceneFootage when backend auto-selects

                (sceneId: number, footage: any) => {

                    setSceneFootage((prev: Record<number, any>) => ({

                        ...prev,

                        [sceneId]: {

                            url: footage.download_url,

                            video_id: footage.video_id,

                            source: footage.source,

                            duration: footage.duration,

                            thumbnail: footage.thumbnail_url,

                        },

                    }));

                },

            );



            if (result?.success && result?.final_video_path) {

                setFinalVideoPath(result.final_video_path);

                setAssemblyProgress(` Hoàn tất! ${result.scenes_assembled} scenes — ${result.file_size_mb} MB`);

                setAssemblyPercentage(100);

            }

        } catch (err: any) {

            console.error('[Assemble] Error:', err);

            setError(`Lỗi ghép video: ${err.message}`);

            setAssemblyProgress(` Lỗi: ${err.message}`);

        } finally {

            setIsAssemblingVideo(false);

        }

    };



    // Video preview modal state

    const [videoPreviewModal, setVideoPreviewModal] = useState<{

        isOpen: boolean;

        url: string;

        title: string;

        sceneId: number;

    }>({ isOpen: false, url: '', title: '', sceneId: 0 });



    // FREE FOOTAGE STATE (not yet implemented)

    const [freeFootageLoaded] = useState(false);

    const [availableFreeFootageSources] = useState<string[]>([]);



    // StyleA is now managed in store (useScriptWorkflowStore)

    // No local state needed - styleA comes from store

    // User-defined style profile name

    const [styleProfileName, setStyleProfileName] = useState<string>('Phong cách mới');



    // Advanced settings

    const [advancedSettings, setAdvancedSettings] = useState({

        targetWordCount: 1500,

        sourceLanguage: '',  // Default empty - auto-detect

        language: '',  // Default empty - user must select

        dialect: '',   // Default empty - user must select

        // Toggle flags for optional settings

        enableValueType: false,

        enableStorytellingStyle: false,  // Toggle for storytelling style section

        enableAudienceAddress: false,

        // Values when enabled

        country: '',  // Auto-derived from language via LANG_TO_COUNTRY

        addQuiz: false,

        valueType: 'sell' as 'sell' | 'engage' | 'community',

        customValue: '',  // Custom value description text

        // Storytelling style settings (combined)

        storytellingStyle: 'immersive' as 'immersive' | 'documentary' | 'conversational' | 'analytical' | 'narrative',  // Phong cách kể chuyện

        narrativeVoice: 'first_person' as 'first_person' | 'second_person' | 'third_person',  // Ngôi kể

        customNarrativeVoice: '',  // Textarea để user nhập chi tiết cách xưng hô ngôi kể

        audienceAddress: '',  // Empty default - will be resolved by backend based on language

        customAudienceAddress: ''  // Textarea để user nhập chi tiết cách xưng hô khán giả

    });





    // Load saved styles function

    const loadSavedStyles = async () => {

        setIsRefreshingStyles(true);

        try {

            const response = await fetch('http://localhost:8000/api/workflow/styles');

            const data = await response.json();

            if (data.success) {

                setSavedStyles(data.profiles || []);

            }

        } catch (err) {

            console.error('Failed to load saved styles:', err);

        } finally {

            // Brief delay so the spin animation is visible

            setTimeout(() => setIsRefreshingStyles(false), 600);

        }

    };



    // Load saved projects from backend

    const projectsLoadingRef = useRef(false);

    const loadSavedProjects = async () => {

        if (projectsLoadingRef.current) return; // prevent re-entrancy

        projectsLoadingRef.current = true;

        setIsLoadingProjects(true);

        try {

            const controller = new AbortController();

            const timeoutId = setTimeout(() => controller.abort(), 5000);

            const data = await projectApi.getProjects();

            clearTimeout(timeoutId);

            setSavedProjects(data.projects || []);

        } catch (err) {

            console.error('[Projects] Failed to load:', err);

        } finally {

            setIsLoadingProjects(false);

            projectsLoadingRef.current = false;

        }

    };



    // Get AI settings from store

    const { openaiApiKey, openaiBaseUrl, openaiModel } = useAISettingsStore();



    // Load templates and models on mount

    useEffect(() => {

        const loadTemplates = async () => {

            try {

                const data = await workflowApi.getTemplates();

                setTemplates(data);

            } catch (err) {

                console.error('Failed to load templates:', err);

            }

        };



        // Default models list (Feb 2026) - Synced with backend OPENAI_MODELS

        // Primary source of truth for fallback model list

        const defaultModels = [

            // 

            // GPT-5.2 Series (Latest Flagship - Feb 2026)

            // 

            { id: 'gpt-5.2', name: 'GPT-5.2 Auto', description: 'Auto-selects best mode' },

            { id: 'gpt-5.2-pro', name: 'GPT-5.2 Pro', description: 'Research-grade, most powerful' },

            { id: 'gpt-5.2-thinking', name: 'GPT-5.2 Thinking', description: 'Step-by-step reasoning' },

            { id: 'gpt-5.2-instant', name: 'GPT-5.2 Instant', description: 'Ultra-fast responses' },

            // GPT-5.1 Series

            { id: 'gpt-5.1', name: 'GPT-5.1', description: 'Previous flagship' },

            { id: 'gpt-5.1-pro', name: 'GPT-5.1 Pro', description: 'High capability' },

            { id: 'gpt-5.1-thinking', name: 'GPT-5.1 Thinking', description: 'Reasoning mode' },

            { id: 'gpt-5.1-instant', name: 'GPT-5.1 Instant', description: 'Fast responses' },

            // 

            // O-Series Reasoning Models

            // 

            { id: 'o4-mini', name: 'o4-mini', description: 'Lightweight reasoning, STEM optimized' },

            { id: 'o3', name: 'o3', description: 'Advanced reasoning for coding/math' },

            { id: 'o3-pro', name: 'o3-pro', description: 'Extended thinking, best performance' },

            { id: 'o3-mini', name: 'o3-mini', description: 'Fast reasoning, cost-effective' },

            { id: 'o1', name: 'o1', description: 'Advanced reasoning, complex tasks' },

            { id: 'o1-mini', name: 'o1-mini', description: 'Faster reasoning model' },

            { id: 'o1-preview', name: 'o1-preview', description: 'Preview of o1 reasoning' },

            // 

            // GPT-4 Series (Legacy - still available via API)

            // 

            { id: 'gpt-4.5-preview', name: 'GPT-4.5 Preview', description: 'Latest preview model' },

            { id: 'gpt-4.1', name: 'GPT-4.1', description: 'Improved GPT-4 variant' },

            { id: 'gpt-4.1-mini', name: 'GPT-4.1 Mini', description: 'Faster GPT-4.1' },

            { id: 'gpt-4.1-nano', name: 'GPT-4.1 Nano', description: 'Ultra-fast, lightweight' },

            { id: 'gpt-4o', name: 'GPT-4o', description: 'Multimodal model (legacy flagship)' },

            { id: 'gpt-4o-mini', name: 'GPT-4o Mini', description: 'Fast and affordable' },

            { id: 'chatgpt-4o-latest', name: 'ChatGPT-4o Latest', description: 'Dynamic ChatGPT model' },

            { id: 'gpt-4o-audio-preview', name: 'GPT-4o Audio', description: 'Audio input/output' },

            { id: 'gpt-4-turbo', name: 'GPT-4 Turbo', description: 'Previous generation turbo' },

            { id: 'gpt-4-turbo-preview', name: 'GPT-4 Turbo Preview', description: 'Latest GPT-4 preview' },

            { id: 'gpt-4', name: 'GPT-4', description: 'Original GPT-4' },

            { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo', description: 'Fast, budget option' },

        ];



        const loadModels = async () => {

            let finalModels = [...defaultModels];



            // Try to fetch from user's configured provider

            if (openaiApiKey) {

                const baseUrl = openaiBaseUrl || 'https://api.openai.com/v1';

                try {

                    const userModels = await aiApi.fetchModels(baseUrl, openaiApiKey);

                    if (userModels.length > 0) {

                        // Merge: API models + default models not in API

                        const apiModelIds = new Set(userModels.map(m => m.id));

                        const extraDefaults = defaultModels.filter(m => !apiModelIds.has(m.id));

                        finalModels = [...userModels, ...extraDefaults];

                    }

                } catch (err) {

                    console.error('Failed to fetch from user provider:', err);

                }

            }



            // Also try backend's model list

            try {

                const response = await fetch('http://localhost:8000/api/ai/models');

                const data = await response.json();

                if (data.models && data.models.length > 0) {

                    const currentIds = new Set(finalModels.map(m => m.id));

                    const newFromBackend = data.models.filter((m: any) => !currentIds.has(m.id));

                    finalModels = [...finalModels, ...newFromBackend];

                }

            } catch (err) {

                console.error('Failed to load models from backend:', err);

            }



            setModels(finalModels);

            // Set default to user's configured model or first available

            setSelectedModel(openaiModel || finalModels[0]?.id || 'gpt-5.2');

        };



        loadTemplates();

        loadModels();

        loadSavedStyles();

        loadSavedProjects();

    }, [setTemplates, openaiApiKey, openaiBaseUrl, openaiModel]);


    // ── Real-time sync: auto-refresh styles & projects on WS events ──
    const stableLoadStyles = useCallback(() => { loadSavedStyles(); }, []);
    const stableLoadProjects = useCallback(() => { loadSavedProjects(); }, []);
    useRealtimeEvent('styles_updated', stableLoadStyles);
    useRealtimeEvent('projects_updated', stableLoadProjects);


    // ──────────────────────────────────────────

    // Load project data when opening from entry section

    // Only skip entry/gateway if the project already has progress data

    // ──────────────────────────────────────────

    const justCreatedRef = useRef(false);



    // Reset to entry section when activeProjectId is cleared (e.g. back button)

    useEffect(() => {

        if (!activeProjectId) {

            setShowEntrySection(true);

            setShowPresetGateway(true);

        }

    }, [activeProjectId]);



    // Project loading: restore data when opening an existing project
    useEffect(() => {
        if (!activeProjectId) return;
        if (justCreatedRef.current) {
            justCreatedRef.current = false;
            return;
        }
        setShowEntrySection(false);
        // Load project data from backend
        projectApi.getProject(Number(activeProjectId))
            .then(result => {
                if (result?.project?.data && typeof result.project.data === 'object') {
                    const d = result.project.data;
                    console.log('[Project] Loading data for project', activeProjectId, Object.keys(d));
                    // Restore workflow state
                    if (d.styleA) setStyleA(d.styleA);
                    if (d.advancedFinalScript) setAdvancedFinalScript(d.advancedFinalScript);
                    if (d.scenes && Array.isArray(d.scenes)) setScenes(d.scenes);
                    if (d.detectedLanguage) setDetectedLanguage(d.detectedLanguage);
                    if (d.selectedVoice) setSelectedVoice(d.selectedVoice);
                    if (d.voiceSpeed) setVoiceSpeed(d.voiceSpeed);
                    if (d.voiceLanguage) setVoiceLanguage(d.voiceLanguage);
                    if (d.splitMode) setSplitMode(d.splitMode);
                    if (d.sceneMode) setSceneMode(d.sceneMode);
                    if (d.originalAnalysis) setOriginalAnalysis(d.originalAnalysis);
                    if (d.syncAnalysisResult) setSyncAnalysisResult(d.syncAnalysisResult);
                    if (d.sceneContext) setSceneContext(d.sceneContext);
                    if (d.conceptAnalysis) setConceptAnalysis(d.conceptAnalysis);
                    if (d.promptStyle) setPromptStyle(d.promptStyle);
                    if (d.mainCharacter) setMainCharacter(d.mainCharacter);
                    if (d.contextDescription) setContextDescription(d.contextDescription);
                    if (d.advancedStep) setAdvancedStep(d.advancedStep);
                    // Restore store state
                    if (d.referenceScripts) setReferenceScripts(d.referenceScripts);
                    if (d.topic) setTopic(d.topic);
                    if (d.channelName) setChannelName(d.channelName);
                    if (d.language) setLanguage(d.language);
                }
            })
            .catch(err => console.error('[Project] Failed to load data:', err));
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [activeProjectId]);



    // Auto-save project data to backend
    const autoSaveProject = async (extra?: Record<string, any>) => {
        if (!activeProjectId) return;
        try {
            const data: Record<string, any> = {
                // Workflow state from store
                styleA,
                referenceScripts,
                topic,
                channelName,
                language,
                // Local component state
                advancedFinalScript,
                scenes,
                detectedLanguage,
                selectedVoice,
                voiceSpeed,
                voiceLanguage,
                splitMode,
                sceneMode,
                originalAnalysis,
                syncAnalysisResult,
                sceneContext,
                conceptAnalysis,
                promptStyle,
                mainCharacter,
                contextDescription,
                advancedStep,
                // Merge any extra data from caller
                ...extra,
            };
            await projectApi.saveProjectData(Number(activeProjectId), data);
            console.log('[Project] Auto-saved data for project', activeProjectId);
        } catch (err) {
            console.error('[Project] Auto-save failed:', err);
        }
    };

    // Reset all workflow state for a fresh start
    const resetWorkflowState = () => {
        setAdvancedFinalScript('');
        setScenes([]);
        setSceneAudioMap({});
        setSceneFootage({});
        setSceneContext(null);
        setConceptAnalysis(null);
        setFinalVideoPath(null);
        setAssembledVideos({});
        setOriginalAnalysis(null);
        setReferenceScript('');
        setReferenceScripts([]);
        setStyleA(null);
        setDetectedLanguage('');
        setAdvancedStep(1);
        setPlayingSceneId(null);
        setEditingCell(null);
        setTotalVoiceDuration(0);
        setIsAnalysisLocked(false);
        console.log('[Navigation] Workflow state reset for fresh start');
    };



    // 

    // FIX: Reset analysis state on component mount to prevent stale states

    // 

    useEffect(() => {

        // Reset any stale analysis state from previous session

        if (isAnalyzingStyle) {

            console.log('[DEBUG] Resetting stale analysis state on mount');

            setAnalyzingStyle(false);

            if (timerRef.current) {

                clearInterval(timerRef.current);

                timerRef.current = null;

            }

            setAnalysisProgress('');

            setAnalysisTimer(0);

        }

        // eslint-disable-next-line react-hooks/exhaustive-deps

    }, []); // Empty deps = only on mount





    // (REMOVED) Load Free Footage sources - footage feature removed



    // Cleanup timer and abort controller on unmount

    useEffect(() => {

        return () => {

            if (timerRef.current) {

                clearInterval(timerRef.current);

                timerRef.current = null;

            }

            if (abortControllerRef.current) {

                abortControllerRef.current.abort();

                abortControllerRef.current = null;

            }

        };

    }, []);



    // 

    // AUTO-SAVE SESSION TO LOCALSTORAGE

    // 

    const STORAGE_KEYS = {

        scenes: 'renmae_scenes',

        sceneFootage: 'renmae_scene_footage',

        advancedFinalScript: 'renmae_advanced_final_script',

        detectedLanguage: 'renmae_detected_language',

    };



    // Restore session from localStorage on mount

    useEffect(() => {

        try {

            const savedScenes = localStorage.getItem(STORAGE_KEYS.scenes);

            if (savedScenes) {

                const parsed = JSON.parse(savedScenes);

                if (Array.isArray(parsed) && parsed.length > 0) {

                    setScenes(parsed);

                    console.log('[AutoSave] Restored', parsed.length, 'scenes');

                }

            }



            const savedFootage = localStorage.getItem(STORAGE_KEYS.sceneFootage);

            if (savedFootage) {

                const parsed = JSON.parse(savedFootage);

                if (parsed && typeof parsed === 'object') {

                    setSceneFootage(parsed);

                    console.log('[AutoSave] Restored footage for', Object.keys(parsed).length, 'scenes');

                }

            }



            const savedScript = localStorage.getItem(STORAGE_KEYS.advancedFinalScript);

            if (savedScript) {

                setAdvancedFinalScript(savedScript);

                console.log('[AutoSave] Restored final script');

            }



            const savedLang = localStorage.getItem(STORAGE_KEYS.detectedLanguage);

            if (savedLang) {

                setDetectedLanguage(savedLang);

            }

        } catch (err) {

            console.error('[AutoSave] Error restoring session:', err);

        }

        // eslint-disable-next-line react-hooks/exhaustive-deps

    }, []);



    // Auto-save scenes when they change

    useEffect(() => {

        if (scenes.length > 0) {

            localStorage.setItem(STORAGE_KEYS.scenes, JSON.stringify(scenes));

        }

    }, [scenes]);



    // Auto-save footage when it changes

    useEffect(() => {

        if (Object.keys(sceneFootage).length > 0) {

            localStorage.setItem(STORAGE_KEYS.sceneFootage, JSON.stringify(sceneFootage));

        }

    }, [sceneFootage]);



    // Auto-save final script when it changes

    useEffect(() => {

        if (advancedFinalScript) {

            localStorage.setItem(STORAGE_KEYS.advancedFinalScript, advancedFinalScript);

        }

    }, [advancedFinalScript]);



    // Auto-save detected language

    useEffect(() => {

        if (detectedLanguage) {

            localStorage.setItem(STORAGE_KEYS.detectedLanguage, detectedLanguage);

        }

    }, [detectedLanguage]);



    // Save style function

    const handleSaveStyle = async () => {

        if (!styleName.trim() || !styleA) {

            setError('Vui lòng nhập tên style');

            return;

        }



        setIsSavingStyle(true);

        try {

            const response = await fetch('http://localhost:8000/api/workflow/styles/save', {

                method: 'POST',

                headers: { 'Content-Type': 'application/json' },

                body: JSON.stringify({

                    name: styleName.trim(),

                    profile: styleA,

                    source_scripts_count: multiMode ? referenceScripts.length : 1

                })

            });

            const data = await response.json();

            if (data.success) {

                await loadSavedStyles();

                loadSavedProjects();

                setShowSaveDialog(false);

                setStyleSaved(styleName.trim());

                setStyleName('');

                // Auto hide success message after 5 seconds

                setTimeout(() => setStyleSaved(null), 5000);

            } else {

                setError(data.detail || 'Lỗi lưu style');

            }

        } catch (err: any) {

            setError(err.message || 'Lỗi kết nối');

        } finally {

            setIsSavingStyle(false);

        }

    };



    // Load saved style

    const handleLoadStyle = async (profileId: number) => {

        try {

            const response = await fetch(`http://localhost:8000/api/workflow/styles/${profileId}`);

            const data = await response.json();

            if (data.success && data.profile?.raw_profile) {

                setStyleA(data.profile.raw_profile);

                // Set the style profile name from saved style

                if (data.profile.name) {

                    setStyleProfileName(data.profile.name);

                }

            }

        } catch (err: any) {

            setError(err.message || 'Lỗi tải style');

        }

    };



    // Delete saved style

    const handleDeleteStyle = async (profileId: number, styleName: string) => {

        if (!confirm(`Bạn có chắc muốn xóa giọng văn "${styleName}"?`)) {

            return;

        }



        try {

            const response = await fetch(`http://localhost:8000/api/workflow/styles/${profileId}`, {

                method: 'DELETE'

            });

            const data = await response.json();

            if (data.success) {

                await loadSavedStyles(); // Reload the list

                loadSavedProjects();

            } else {

                setError(data.detail || 'Lỗi xóa style');

            }

        } catch (err: any) {

            setError(err.message || 'Lỗi kết nối');

        }

    };



    // Rename saved style

    const handleRenameStyle = async (profileId: number) => {

        if (!renameValue.trim()) {

            setError('Tên giọng văn không được để trống');

            return;

        }



        try {

            const response = await fetch(`http://localhost:8000/api/workflow/styles/${profileId}`, {

                method: 'PUT',

                headers: { 'Content-Type': 'application/json' },

                body: JSON.stringify({ name: renameValue.trim() })

            });

            const data = await response.json();

            if (data.success) {

                await loadSavedStyles();

                setRenamingStyleId(null);

                setRenameValue('');

            } else {

                setError(data.detail || 'Lỗi đổi tên');

            }

        } catch (err: any) {

            setError(err.message || 'Lỗi kết nối');

        }

    };



    // ── YouTube URL Extraction Handler ──────────────────────────────────
    const handleExtractYoutubeUrl = async () => {
        const url = youtubeUrlInput.trim();
        if (!url) return;

        setIsExtractingYoutube(true);
        setError(null);

        try {
            const result = await youtubeApi.extractFromUrl(url);

            if (!result.success) {
                setError(result.error || 'Không thể lấy dữ liệu từ YouTube URL');
                return;
            }

            const newItem = {
                video_id: result.video_id || '',
                title: result.title || '',
                description: result.description || '',
                thumbnail_url: result.thumbnail_url || `https://i.ytimg.com/vi/${result.video_id}/maxresdefault.jpg`,
                transcript: result.transcript || null,
                channel_name: result.channel_name || '',
            };

            // Add to YouTube extracted items list
            setYoutubeExtractedItems(prev => [...prev, newItem]);

            // Auto-populate voice analysis (transcript → referenceScripts)
            // Note: setReferenceScripts is from Zustand store (not useState), so no callback pattern
            if (newItem.transcript && newItem.transcript.length >= 50 && referenceScripts.length < 20) {
                setReferenceScripts([...referenceScripts, newItem.transcript]);
            }

            // Auto-populate title analysis
            if (newItem.title) {
                setTitleSamples(prev => {
                    if (prev.length < 20) return [...prev, newItem.title];
                    return prev;
                });
            }

            // Auto-populate description analysis
            if (newItem.description && newItem.description.length >= 30) {
                setDescriptionSamples(prev => {
                    if (prev.length < 20) return [...prev, newItem.description];
                    return prev;
                });
            }

            // Auto-populate thumbnail analysis (download via backend proxy to avoid CORS)
            if (newItem.thumbnail_url && thumbnailFiles.length < 10) {
                try {
                    const proxyUrl = `http://localhost:8000/api/youtube/thumbnail-proxy?url=${encodeURIComponent(newItem.thumbnail_url)}`;
                    const thumbResp = await fetch(proxyUrl);
                    if (thumbResp.ok) {
                        const blob = await thumbResp.blob();
                        const fileName = `youtube_thumb_${newItem.video_id || Date.now()}.jpg`;
                        const file = new File([blob], fileName, { type: blob.type || 'image/jpeg' });
                        const preview = URL.createObjectURL(blob);
                        setThumbnailFiles(prev => [...prev, { file, preview }]);
                        console.log(`[YouTube] Thumbnail auto-added: ${fileName}`);
                    }
                } catch (thumbErr) {
                    console.warn('[YouTube] Failed to auto-download thumbnail:', thumbErr);
                }
            }

            // Clear input for next URL
            setYoutubeUrlInput('');

            console.log(`[YouTube] Extracted: "${newItem.title}" | transcript: ${newItem.transcript ? 'yes' : 'no'} | desc: ${newItem.description.length} chars`);

        } catch (err: any) {
            setError(err.message || 'Lỗi kết nối đến server');
        } finally {
            setIsExtractingYoutube(false);
        }
    };

    // Remove a YouTube extracted item and clean up corresponding data
    const handleRemoveYoutubeItem = (idx: number) => {
        const item = youtubeExtractedItems[idx];
        if (!item) return;

        // Remove from YouTube items list
        setYoutubeExtractedItems(prev => prev.filter((_, i) => i !== idx));

        // Remove from referenceScripts (find matching transcript)
        // Note: setReferenceScripts is from Zustand store (not useState), so no callback pattern
        if (item.transcript) {
            const matchIdx = referenceScripts.findIndex(s => s === item.transcript);
            if (matchIdx >= 0) {
                setReferenceScripts(referenceScripts.filter((_, i) => i !== matchIdx));
            }
        }

        // Remove from titleSamples
        if (item.title) {
            setTitleSamples(prev => {
                const matchIdx = prev.findIndex(t => t === item.title);
                if (matchIdx >= 0) return prev.filter((_, i) => i !== matchIdx);
                return prev;
            });
        }

        // Remove from descriptionSamples
        if (item.description) {
            setDescriptionSamples(prev => {
                const matchIdx = prev.findIndex(d => d === item.description);
                if (matchIdx >= 0) return prev.filter((_, i) => i !== matchIdx);
                return prev;
            });
        }
    };


    // Step 1: Analyze multiple styles (5-20 scripts)

    const handleAnalyzeMultipleStyles = async () => {
        // Check if ANY section has data
        const hasVoiceData = referenceScripts.length >= 1;
        const hasTitleData = analysisOpts.title && titleSamples.length > 0;
        const hasDescData = analysisOpts.description && descriptionSamples.length > 0;
        const hasThumbData = analysisOpts.thumbnail && thumbnailFiles.length > 0;
        const hasSyncData = (analysisOpts.syncCharacter && (mainCharacter.trim() || syncCharacterImages.length > 0))
            || (analysisOpts.syncStyle && (promptStyle.trim() || syncStyleImages.length > 0))
            || (analysisOpts.syncContext && (contextDescription.trim() || syncContextImages.length > 0));

        if (!hasVoiceData && !hasTitleData && !hasDescData && !hasThumbData && !hasSyncData) {
            setError('Vui lòng thêm ít nhất 1 loại mẫu để phân tích');
            return;
        }

        setAnalyzingStyle(true);
        setError(null);
        setAnalysisProgress('[0%] Đang khởi tạo phân tích...');

        // Create AbortController for cancellation
        const controller = new AbortController();
        abortControllerRef.current = controller;

        // Reset per-section progress
        setVoiceProgress(hasVoiceData ? { pct: 0, msg: 'Đang chờ...', status: 'running' } : { ...defaultProgress });
        setTitleProgress(hasTitleData ? { pct: 0, msg: 'Đang chờ...', status: 'running' } : { ...defaultProgress });
        setDescProgress(hasDescData ? { pct: 0, msg: 'Đang chờ...', status: 'running' } : { ...defaultProgress });
        setThumbProgress(hasThumbData ? { pct: 0, msg: 'Đang chờ...', status: 'running' } : { ...defaultProgress });
        setSyncProgress(hasSyncData ? { pct: 0, msg: 'Đang chờ...', status: 'running' } : { ...defaultProgress });

        // Clear previous results
        setStyleA(null);
        setOriginalAnalysis(null);
        setIndividualResults([]);
        setScriptsAnalyzed(0);
        setAnalysisTimer(0);
        setTitleStyleAnalysis(null);
        setDescriptionStyleAnalysis(null);
        setThumbnailStyleAnalysis(null);
        setSyncAnalysisResult(null);

        // Start timer
        const startTime = Date.now();
        timerRef.current = setInterval(() => {
            const elapsed = Math.floor((Date.now() - startTime) / 1000);
            setAnalysisTimer(elapsed);
        }, 1000);

        try {
            // Build parallel promises
            const promises: Promise<any>[] = [];
            const promiseLabels: string[] = [];

            // 1) Voice analysis (if voice data exists)
            if (hasVoiceData) {
                console.log(`[PARALLEL] Starting voice analysis with ${referenceScripts.length} scripts`);
                promises.push(
                    workflowApi.analyzeToStyleAStream(
                        referenceScripts,
                        selectedModel,
                        (_step, percentage, message) => {
                            // Strip emojis and STEP X: prefix from message
                            const cleanMsg = message
                                .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2702}-\u{27B0}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}]/gu, '')
                                .replace(/STEP\s*\d+\s*:\s*/gi, '')
                                .trim();
                            setAnalysisProgress(`[${percentage}%] ${cleanMsg}`);
                            setVoiceProgress({ pct: percentage, msg: cleanMsg, status: 'running' });
                        },
                        analysisLanguage,
                        advancedSettings.language,
                        controller.signal
                    ).then(data => ({ type: 'voice', data }))
                );
                promiseLabels.push('voice');
            }

            // 2) Metadata analysis (title + description + thumbnail)
            if (hasTitleData || hasDescData || hasThumbData) {
                // Convert thumbnails to base64 data URIs for Vision API
                const thumbBase64: string[] = [];
                if (hasThumbData) {
                    for (const t of thumbnailFiles) {
                        try {
                            const dataUri = await new Promise<string>((resolve, reject) => {
                                const reader = new FileReader();
                                reader.onload = () => resolve(reader.result as string);
                                reader.onerror = reject;
                                reader.readAsDataURL(t.file);
                            });
                            thumbBase64.push(dataUri);
                        } catch (err) {
                            console.warn(`[PARALLEL] Failed to convert thumbnail to base64:`, err);
                        }
                    }
                }
                const thumbDescs = hasThumbData
                    ? thumbnailFiles.map((t, i) => `Thumbnail ${i + 1}: ${t.file.name}`)
                    : [];

                console.log(`[PARALLEL] Starting metadata analysis: ${hasTitleData ? titleSamples.length + ' titles' : ''} ${hasDescData ? descriptionSamples.length + ' descs' : ''} ${hasThumbData ? thumbBase64.length + ' thumb images' : ''}`);
                promises.push(
                    workflowApi.analyzeMetadataStylesStream(
                        hasTitleData ? titleSamples : [],
                        hasDescData ? descriptionSamples : [],
                        thumbDescs,
                        selectedModel,
                        (_step, percentage, message) => {
                            // Strip emojis from message
                            const cleanMsg = message
                                .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2702}-\u{27B0}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{2714}\u{2713}\u{2705}\u{2611}]/gu, '')
                                .replace(/[✓✔]/g, '')
                                .trim();
                            // Set status to 'done' when step ends with _done
                            const isDone = _step.endsWith('_done');
                            if (_step.startsWith('title')) {
                                setTitleProgress({ pct: Math.min(percentage, 100), msg: cleanMsg, status: isDone ? 'done' : 'running' });
                            } else if (_step.startsWith('desc')) {
                                setDescProgress({ pct: Math.min(percentage, 100), msg: cleanMsg, status: isDone ? 'done' : 'running' });
                            } else if (_step.startsWith('thumb')) {
                                setThumbProgress({ pct: Math.min(percentage, 100), msg: cleanMsg, status: isDone ? 'done' : 'running' });
                            }
                        },
                        thumbBase64,
                        controller.signal,
                        advancedSettings.language
                    ).then(data => ({ type: 'metadata', data }))
                );
                promiseLabels.push('metadata');
            }

            // 3) Sync reference analysis (character/style/context)
            if (hasSyncData) {
                console.log(`[PARALLEL] Starting sync reference analysis`);
                promises.push(
                    workflowApi.analyzeSyncReferencesStream(
                        analysisOpts.syncCharacter ? mainCharacter : '',
                        analysisOpts.syncStyle ? promptStyle : '',
                        analysisOpts.syncContext ? contextDescription : '',
                        analysisOpts.syncCharacter ? syncCharacterImages : [],
                        analysisOpts.syncStyle ? syncStyleImages : [],
                        analysisOpts.syncContext ? syncContextImages : [],
                        selectedModel,
                        (_step, percentage, message) => {
                            const cleanMsg = message
                                .replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2702}-\u{27B0}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}]/gu, '')
                                .trim();
                            const isDone = _step.endsWith('_done');
                            setSyncProgress({ pct: Math.min(percentage, 100), msg: cleanMsg, status: isDone ? 'done' : 'running' });
                        },
                        controller.signal,
                        advancedSettings.language
                    ).then(data => ({ type: 'sync', data }))
                );
                promiseLabels.push('sync');
            }

            // Run all in parallel
            console.log(`[PARALLEL] Running ${promises.length} analysis streams in parallel: [${promiseLabels.join(', ')}]`);
            const results = await Promise.allSettled(promises);

            // Process results
            for (const result of results) {
                if (result.status === 'fulfilled') {
                    const { type, data } = result.value;
                    if (type === 'voice' && data.success) {
                        if (data.style_a) {
                            setStyleA(data.style_a);
                            setVoiceProgress(p => ({ ...p, pct: 100, status: 'done' }));
                            console.log('[PARALLEL] Voice StyleA set:', data.style_a);
                            autoSaveProject({ styleAnalysis: data.style_a, currentStep: 1 });
                        }
                        if (data.individual_analyses) {
                            setIndividualResults(data.individual_analyses);
                            setScriptsAnalyzed(data.scripts_analyzed || data.individual_analyses.length);
                        }
                    } else if (type === 'metadata' && data.success) {
                        if (data.title_style) {
                            setTitleStyleAnalysis(data.title_style);
                            setTitleProgress(p => ({ ...p, pct: 100, status: 'done' }));
                            console.log('[PARALLEL] Title style set:', data.title_style);
                        }
                        if (data.description_style) {
                            setDescriptionStyleAnalysis(data.description_style);
                            setDescProgress(p => ({ ...p, pct: 100, status: 'done' }));
                            console.log('[PARALLEL] Description style set:', data.description_style);
                        }
                        if (data.thumbnail_style) {
                            setThumbnailStyleAnalysis(data.thumbnail_style);
                            setThumbProgress(p => ({ ...p, pct: 100, status: 'done' }));
                            console.log('[PARALLEL] Thumbnail style set:', data.thumbnail_style);
                        }
                    } else if (type === 'sync' && data.success) {
                        setSyncAnalysisResult(data);
                        // Update text fields with AI-enhanced descriptions
                        if (data.sync_character_analysis) {
                            setMainCharacter(data.sync_character_analysis);
                        }
                        if (data.sync_style_analysis) {
                            setPromptStyle(data.sync_style_analysis);
                        }
                        if (data.sync_context_analysis) {
                            setContextDescription(data.sync_context_analysis);
                        }
                        setSyncProgress(p => ({ ...p, pct: 100, status: 'done' }));
                        console.log('[PARALLEL] Sync analysis done:', data);
                    } else if (!data.success) {
                        console.warn(`[PARALLEL] ${type} analysis returned error:`, data.error);
                    }
                } else {
                    console.error(`[PARALLEL] Analysis stream failed:`, result.reason);
                }
            }

            setAnalysisProgress('');

        } catch (err: any) {
            // Ignore abort errors (user clicked Stop)
            if (err.name === 'AbortError') return;
            setError(err.message || 'Lỗi kết nối');
        } finally {
            if (timerRef.current) {
                clearInterval(timerRef.current);
                timerRef.current = null;
            }
            setAnalyzingStyle(false);
            setAnalysisProgress('');
        }
    };



    // Stop/Cancel analysis

    const handleStopAnalysis = () => {

        if (abortControllerRef.current) {

            abortControllerRef.current.abort();

            abortControllerRef.current = null;

        }

        if (timerRef.current) {

            clearInterval(timerRef.current);

            timerRef.current = null;

        }

        setAnalyzingStyle(false);

        setAnalysisProgress('');
        setVoiceProgress({ ...defaultProgress });
        setTitleProgress({ ...defaultProgress });
        setDescProgress({ ...defaultProgress });
        setThumbProgress({ ...defaultProgress });
        setSyncProgress({ ...defaultProgress });

        setError('Đã dừng phân tích');

    };





    // 

    // ADVANCED REMAKE - SINGLE CONVERSATION PIPELINE (AI remembers context)

    // 

    const handleAdvancedRemakeConversation = async () => {

        if (!remakeScript || remakeScript.length < 50) {

            setError('Vui lòng nhập kịch bản gốc (ít nhất 50 ký tự)');

            return;

        }



        // Validate required fields

        if (!advancedSettings.language) {

            setError('Vui lòng chọn ngôn ngữ output');

            return;

        }

        if (!advancedSettings.dialect) {

            setError('Vui lòng chọn giọng/dialect');

            return;

        }



        setIsRunningAdvanced(true);

        setError(null);

        setAdvancedProgress('[0%] Đang khởi tạo conversation pipeline...');

        setPipelineStep(1);



        // Create AbortController for cancellation

        const controller = new AbortController();

        scriptAbortRef.current = controller;



        try {

            console.log('[ConversationPipeline] Starting with SSE streaming progress...');



            // Call the SSE streaming conversation API

            const result = await workflowApi.advancedRemake.fullPipelineConversationStream(

                {

                    original_script: remakeScript,
                    target_word_count: advancedSettings.targetWordCount,
                    source_language: advancedSettings.sourceLanguage || '',
                    language: advancedSettings.language,

                    dialect: advancedSettings.dialect,

                    channel_name: channelName,

                    country: LANG_TO_COUNTRY[advancedSettings.language] || '',

                    add_quiz: advancedSettings.addQuiz,

                    value_type: advancedSettings.enableValueType ? advancedSettings.valueType : '',

                    custom_value: advancedSettings.enableValueType ? advancedSettings.customValue : '',

                    storytelling_style: advancedSettings.enableStorytellingStyle ? advancedSettings.storytellingStyle : '',

                    narrative_voice: advancedSettings.enableStorytellingStyle ? advancedSettings.narrativeVoice : '',

                    audience_address: advancedSettings.enableAudienceAddress ? advancedSettings.audienceAddress : '',

                    custom_narrative_voice: advancedSettings.enableStorytellingStyle ? advancedSettings.customNarrativeVoice : '',

                    custom_audience_address: advancedSettings.enableAudienceAddress ? advancedSettings.customAudienceAddress : '',

                    style_profile: styleA || originalAnalysis || undefined,

                    model: selectedModel || undefined,

                },

                (_step, percentage, message) => {

                    // Real-time progress from backend

                    setAdvancedProgress(`[${percentage}%] ${message}`);

                },

                controller.signal

            );



            if (!result.success) {

                throw new Error(result.error || 'Pipeline failed');

            }



            console.log('[ConversationPipeline] Completed! Word count:', result.word_count);



            // Set results

            if (result.original_analysis) setOriginalAnalysis(result.original_analysis);

            if (result.structure_analysis) setStructureAnalysis(result.structure_analysis);

            if (result.outline_a) setOutlineA(result.outline_a);

            if (result.draft_sections) setAdvancedDraftSections(result.draft_sections);

            if (result.refined_sections) setRefinedSections(result.refined_sections);

            if (result.similarity_review) setSimilarityReview(result.similarity_review);



            setAdvancedFinalScript(result.final_script);

            // Build completion message with similarity info
            let completionMsg = `[100%] Hoàn thành! ${result.word_count} từ`;
            if (result.similarity_review) {
                const sr = result.similarity_review;
                const score = sr.similarity_score || sr.score || '';
                const verdict = sr.verdict || sr.rating || '';
                if (score || verdict) {
                    completionMsg += ` | Similarity: ${score}${verdict ? ` (${verdict})` : ''}`;
                }
                console.log('[ConversationPipeline] Similarity review:', sr);
            }
            setAdvancedProgress(completionMsg);

            // Auto-save script to project

            autoSaveProject({ script: result.final_script, currentStep: 2 });



        } catch (err: any) {

            if (err.name === 'AbortError') {

                setAdvancedProgress('Đã dừng tạo kịch bản');

                setError('Đã dừng tạo kịch bản');

            } else {

                console.error('[ConversationPipeline] Failed:', err);

                setError(`Lỗi: ${err.message || 'Lỗi kết nối'}`);

            }

        } finally {

            scriptAbortRef.current = null;

            setIsRunningAdvanced(false);

            setPipelineStep(0);

        }

    };



    // Stop/Cancel script generation

    const handleStopScriptGeneration = () => {

        if (scriptAbortRef.current) {

            scriptAbortRef.current.abort();

            scriptAbortRef.current = null;

        }

    };



    // Copy Advanced script

    const handleCopyAdvanced = () => {

        navigator.clipboard.writeText(advancedFinalScript);

        alert('Đã copy kịch bản vào clipboard!');

    };



    // Download Advanced script

    const handleDownloadAdvanced = () => {

        const blob = new Blob([advancedFinalScript], { type: 'text/plain' });

        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');

        a.href = url;

        a.download = `advanced_remake_${Date.now()}.txt`;

        a.click();

        URL.revokeObjectURL(url);

    };



    // 

    // STEP 3: SPLIT SCRIPT TO SCENES

    // 

    const handleSplitToScenes = async () => {

        if (!advancedFinalScript || advancedFinalScript.length < 50) {

            setError('Chưa có kịch bản hoàn chỉnh. Vui lòng hoàn thành Bước 2 trước.');

            return;

        }



        setIsSplittingScenes(true);

        const modeLabel = splitMode === 'footage' ? ' Footage (3-5s)' : ' Voiceover (5-8s)';

        setSceneSplitProgress(` Đang chia kịch bản [${modeLabel}]...`);

        setError(null);



        try {

            //  Auto Concept Analysis (runs in parallel with scene splitting) 

            const conceptPromise = (async () => {

                try {

                    setIsAnalyzingConcept(true);

                    const conceptResult = await workflowApi.advancedRemake.analyzeConcept({

                        script: advancedFinalScript,

                        model: selectedModel || undefined,

                    });

                    if (conceptResult?.success && conceptResult?.concept) {

                        setConceptAnalysis(conceptResult.concept);

                        console.log(`[ConceptAnalysis] Done: theme="${conceptResult.concept.theme || ''}", prefix="${conceptResult.concept.concept_prefix || ''}"`);

                    } else {

                        console.warn('[ConceptAnalysis] Failed, continuing without concept');

                    }

                } catch (err: any) {

                    console.warn('[ConceptAnalysis] Error:', err.message);

                } finally {

                    setIsAnalyzingConcept(false);

                }

            })();



            //  Split scenes 

            const splitPromise = workflowApi.advancedRemake.splitScriptToScenes(

                advancedFinalScript,

                selectedModel,

                advancedSettings.language || undefined,

                splitMode

            );



            // Run both in parallel

            const [, result] = await Promise.all([conceptPromise, splitPromise]);



            if (!result.success) {

                throw new Error(result.error || 'Chia scene thất bại');

            }



            if (result.detected_language) {

                setDetectedLanguage(result.detected_language);

            }



            const scenesWithExport = result.scenes.map((s: any) => ({

                ...s,

                voiceExport: true,

            }));



            setScenes(scenesWithExport);

            const estDur = result.est_total_duration ? ` · ~${Math.floor(result.est_total_duration / 60)}:${String(Math.round(result.est_total_duration % 60)).padStart(2, '0')}` : '';

            const estPages = result.est_pages ? ` · ~${result.est_pages} trang` : '';

            const modeDone = splitMode === 'footage' ? 'footage (3-5s)' : 'voiceover (5-8s)';

            setSceneSplitProgress(` Đã chia ${result.scene_count} scenes [${modeDone}] (${result.detected_language || 'auto'})${estDur}${estPages}`);

            // Auto-save scenes to project

            autoSaveProject({ scenes: scenesWithExport, scenesCount: scenesWithExport.length, currentStep: 3 });

        } catch (err: any) {

            console.error('[SplitScenes] Failed:', err);

            setError(`Lỗi chia scene: ${err.message || 'Lỗi kết nối'}`);

        } finally {

            setIsSplittingScenes(false);

        }

    };



    // 

    // RESET SCENES HANDLER - Clear all scenes back to initial state

    // 

    const handleResetScenes = () => {

        if (scenes.length === 0) return;



        if (confirm('Bạn có chắc muốn xóa tất cả scenes và bắt đầu lại từ đầu?')) {

            setScenes([]);

            setSceneAudioMap({});

            setDetectedLanguage('');

            setSceneSplitProgress('');

        }

    };



    const handleToggleVoiceExport = (sceneId: number) => {

        setScenes(prev => prev.map(s =>

            s.scene_id === sceneId ? { ...s, voiceExport: !s.voiceExport } : s

        ));

    };



    const handleCopyScenes = () => {

        const text = scenes.map(s => `Scene ${s.scene_id}: ${s.content}`).join('\n');

        navigator.clipboard.writeText(text);

        alert('Đã copy tất cả scenes!');

    };



    const handleDownloadScenesCsv = () => {

        const header = 'STT,Nội dung,Số chữ,Xuất Voice\n';

        const rows = scenes.map(s =>

            `${s.scene_id},"${s.content.replace(/"/g, '""')}",${s.word_count},${s.voiceExport ? 'Có' : 'Không'}`

        ).join('\n');

        const csv = '\uFEFF' + header + rows; // BOM for Vietnamese

        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });

        const url = URL.createObjectURL(blob);

        const a = document.createElement('a');

        a.href = url;

        a.download = `scenes_${Date.now()}.csv`;

        a.click();

        URL.revokeObjectURL(url);

    };





    // (REMOVED) FREE FOOTAGE SEARCH handlers - footage feature removed



    // 

    // AI KEYWORD & PROMPT GENERATION (MODE-BASED)

    // 



    const handleModeChange = (mode: 'footage' | 'concept' | 'storytelling' | 'custom') => {

        setSceneMode(mode);

        if (mode === 'footage') {

            setGenOptions({ keyword: true, imagePrompt: false, videoPrompt: false, consistentCharacters: false, consistentSettings: false });

        } else if (mode === 'concept') {

            setGenOptions({ keyword: true, imagePrompt: true, videoPrompt: false, consistentCharacters: false, consistentSettings: false });

        } else if (mode === 'storytelling') {

            setGenOptions({ keyword: true, imagePrompt: true, videoPrompt: true, consistentCharacters: true, consistentSettings: true });

        }

        // 'custom' — keep current options

    };



    const handleToggleOption = (key: keyof typeof genOptions) => {

        if (sceneMode !== 'custom' || key === 'keyword') return;

        setGenOptions(prev => ({ ...prev, [key]: !prev[key] }));

    };



    const handleAnalyzeContext = async () => {

        setIsAnalyzingContext(true);

        setError(null);

        try {

            const fullScript = scenes.map(s => s.content).join('\n');

            const result = await workflowApi.advancedRemake.analyzeSceneContext({

                script: fullScript,

                language: detectedLanguage || advancedSettings.language || 'vi',

                model: selectedModel || undefined,

            });

            if (result?.success) {

                setSceneContext({ characters: result.characters, settings: result.settings });

                setKeywordProgress(` Đã phân tích: ${result.characters?.length || 0} nhân vật, ${result.settings?.length || 0} bối cảnh`);

            } else {

                setError(`Lỗi phân tích bối cảnh: ${result?.error || 'Unknown'}`);

            }

        } catch (err: any) {

            setError(`Lỗi phân tích: ${err.message}`);

        } finally {

            setIsAnalyzingContext(false);

        }

    };



    const handleGenerateKeywords = async () => {

        if (scenes.length === 0) {

            setError('Chưa có scene nào');

            return;

        }



        // Footage mode: check if audio exists (need audio_duration for keyword count)

        if (sceneMode === 'footage') {

            const hasAudio = scenes.some(s => s.audio_duration && s.audio_duration > 0);

            if (!hasAudio) {

                setError(' Cần tạo audio trước để đo thời lượng chính xác cho footage keywords. Vui lòng tạo voice trước.');

                return;

            }

        }



        // Auto-analyze context if needed and not done yet

        const needsContext = genOptions.consistentCharacters || genOptions.consistentSettings;

        if (needsContext && !sceneContext) {

            setKeywordProgress(' Đang phân tích nhân vật & bối cảnh...');

            setIsGeneratingKeywords(true);

            try {

                const fullScript = scenes.map(s => s.content).join('\n');

                const ctxResult = await workflowApi.advancedRemake.analyzeSceneContext({

                    script: fullScript,

                    language: detectedLanguage || advancedSettings.language || 'vi',

                    model: selectedModel || undefined,

                });

                if (ctxResult?.success) {

                    setSceneContext({ characters: ctxResult.characters, settings: ctxResult.settings });

                }

            } catch {

                // Continue without context

            }

        }



        setIsGeneratingKeywords(true);

        setKeywordProgress(' Đang khởi tạo phân tích...');

        setError(null);



        const controller = new AbortController();

        keywordAbortRef.current = controller;



        try {

            const result = await workflowApi.advancedRemake.generateSceneKeywords(

                {

                    scenes: scenes.map(s => ({

                        scene_id: s.scene_id,

                        content: s.content,

                        audio_duration: s.audio_duration || undefined,

                    })),

                    language: detectedLanguage || advancedSettings.language || 'vi',

                    model: selectedModel || undefined,

                    mode: sceneMode,

                    generate_image_prompt: genOptions.imagePrompt,

                    generate_video_prompt: genOptions.videoPrompt,

                    consistent_characters: genOptions.consistentCharacters,

                    consistent_settings: genOptions.consistentSettings,

                    scene_context: sceneContext,

                    prompt_style: promptStyle || undefined,

                    main_character: mainCharacter || undefined,

                    context_description: contextDescription || undefined,

                    image_prompt_mode: pipelineSelection?.videoProduction?.image_prompt_mode || undefined,

                    video_prompt_mode: pipelineSelection?.videoProduction?.video_prompt_mode || undefined,

                },

                (message, percentage) => {

                    setKeywordProgress(`[${percentage}%] ${message}`);

                },

                controller.signal

            );



            if (result?.success && result?.keywords) {

                setScenes(prev => prev.map(scene => {

                    const kw = result.keywords.find((k: any) => k.scene_id === scene.scene_id);

                    if (kw) {

                        return {

                            ...scene,

                            keyword: kw.keyword,

                            keywords: kw.keywords || undefined,  // Multi-keyword list for footage mode

                            target_clip_duration: kw.target_clip_duration || undefined,

                            image_prompt: kw.image_prompt ?? scene.image_prompt,

                            video_prompt: kw.video_prompt ?? scene.video_prompt,

                        };

                    }

                    return scene;

                }));

                const keywordInfo = sceneMode === 'footage' ? ' (multi-keyword)' : '';

                setKeywordProgress(` Đã tạo từ khóa cho ${result.total} scenes [${(result.mode || sceneMode).toUpperCase()}]${keywordInfo}`);

            }

        } catch (err: any) {

            if (err.name === 'AbortError') {

                setKeywordProgress(' Đã dừng tạo từ khóa');

            } else {

                console.error('[Keywords] Error:', err);

                setError(`Lỗi tạo từ khóa: ${err.message}`);

            }

        } finally {

            keywordAbortRef.current = null;

            setIsGeneratingKeywords(false);

        }

    };





    const handleStopKeywordGeneration = () => {

        if (keywordAbortRef.current) {

            keywordAbortRef.current.abort();

            keywordAbortRef.current = null;

        }

    };



    // Cell editing helpers for keywords/prompts

    const handleStartEdit = (sceneId: number, field: 'keyword' | 'image_prompt' | 'video_prompt', currentValue: string) => {

        setEditingCell({ sceneId, field });

        setEditValue(currentValue || '');

    };



    const handleFinishEdit = () => {

        if (editingCell) {

            setScenes(prev => prev.map(s =>

                s.scene_id === editingCell.sceneId

                    ? { ...s, [editingCell.field]: editValue }

                    : s

            ));

        }

        setEditingCell(null);

        setEditValue('');

    };



    const handleCancelEdit = () => {

        setEditingCell(null);

        setEditValue('');

    };



    // 

    // VOICE GENERATION HANDLERS

    // 



    // Load available voices on mount

    useEffect(() => {

        const loadVoices = async () => {

            try {

                const data = await voiceApi.getVoices();

                if (data.success) {

                    setAvailableVoices(data.voices || []);

                    setVoicesByLanguage(data.voices_by_language || {});

                }

            } catch (err) {

                console.error('Failed to load voices:', err);

            }

        };

        loadVoices();

    }, []);



    // Update selected voice when language changes — only if current voice isn't valid for new language

    useEffect(() => {

        if (voicesByLanguage[voiceLanguage]) {

            const voicesInLang = voicesByLanguage[voiceLanguage].voices || [];

            // Only auto-select first voice if current selectedVoice is NOT in the new language's list
            const currentVoiceValid = voicesInLang.some((v: any) => v.id === selectedVoice);
            if (!currentVoiceValid) {
                const firstVoice = voicesInLang[0];
                if (firstVoice) {
                    console.log(`[Voice] Language changed to ${voiceLanguage}, auto-selecting: ${firstVoice.id}`);
                    setSelectedVoice(firstVoice.id);
                }
            }

        }

    }, [voiceLanguage, voicesByLanguage, selectedVoice]);



    // Auto-sync voice language: output language takes priority over detected language

    useEffect(() => {

        // Priority: advancedSettings.language (output) > detectedLanguage (input auto-detect)

        const lang = advancedSettings.language || detectedLanguage;

        if (lang && voicesByLanguage[lang]) {

            setVoiceLanguage(lang);

        }

    }, [detectedLanguage, advancedSettings.language, voicesByLanguage]);



    // Generate voice for a single scene

    const handleGenerateVoice = async (sceneId: number, content: string) => {

        setSceneAudioMap(prev => ({ ...prev, [sceneId]: { status: 'generating' } }));



        try {

            const result = await voiceApi.generateVoice({

                text: content,

                voice: selectedVoice,

                language: voiceLanguage,

                speed: voiceSpeed,

                scene_id: sceneId,

            });



            if (result.success) {

                setSceneAudioMap(prev => ({

                    ...prev,

                    [sceneId]: {

                        status: 'done',

                        filename: result.filename,

                        url: voiceApi.getAudioUrl(result.filename),

                    }

                }));

            }

        } catch (err: any) {

            console.error(`[Voice] Error scene ${sceneId}:`, err);

            setSceneAudioMap(prev => ({

                ...prev,

                [sceneId]: { status: 'error', error: err.message }

            }));

        }

    };



    // Generate voice for ALL selected scenes

    const handleGenerateBatchVoice = async () => {

        const exportScenes = scenes.filter(s => s.voiceExport);

        if (exportScenes.length === 0) {

            setError('Chưa chọn scene nào để xuất voice');

            return;

        }



        setIsGeneratingBatch(true);

        setBatchProgress({ current: 0, total: exportScenes.length, percentage: 0 });



        // Create AbortController for cancellation

        const controller = new AbortController();

        voiceAbortRef.current = controller;



        // Mark all export scenes as generating

        const initialMap: typeof sceneAudioMap = {};

        exportScenes.forEach(s => { initialMap[s.scene_id] = { status: 'generating' }; });

        setSceneAudioMap(prev => ({ ...prev, ...initialMap }));



        try {

            const result = await voiceApi.generateBatch(

                {

                    scenes: exportScenes.map(s => ({

                        scene_id: s.scene_id,

                        content: s.content,

                        voiceExport: s.voiceExport,

                    })),

                    voice: selectedVoice,

                    language: voiceLanguage,

                    speed: voiceSpeed,

                },

                (current, total, sceneId, percentage) => {

                    setBatchProgress({ current, total, percentage });

                    // Mark current scene as done

                    setSceneAudioMap(prev => ({

                        ...prev,

                        [sceneId]: {

                            status: 'done',

                            filename: `scene_${String(sceneId).padStart(3, '0')}.mp3`,

                            url: voiceApi.getAudioUrl(`scene_${String(sceneId).padStart(3, '0')}.mp3`),

                        }

                    }));

                },

                controller.signal,

                // onSceneDone: update audio_duration on each scene in real-time

                (sceneId, _filename, durationSeconds) => {

                    setScenes(prev => prev.map(s =>

                        s.scene_id === sceneId

                            ? { ...s, audio_duration: Math.round(durationSeconds * 10) / 10, est_duration: Math.round(durationSeconds * 10) / 10 }

                            : s

                    ));

                }

            );



            if (result?.results) {

                const finalMap: typeof sceneAudioMap = {};

                let totalDur = 0;

                const durationMap: Record<number, number> = {};

                result.results.forEach((r: any) => {

                    finalMap[r.scene_id] = r.success

                        ? { status: 'done', filename: r.filename, url: voiceApi.getAudioUrl(r.filename) }

                        : { status: 'error', error: r.error };

                    if (r.success && r.duration_seconds) {

                        totalDur += r.duration_seconds;

                        durationMap[r.scene_id] = r.duration_seconds;

                    }

                });

                setSceneAudioMap(prev => ({ ...prev, ...finalMap }));

                setTotalVoiceDuration(Math.round(totalDur));



                // Update audio_duration and est_duration with actual measured duration from audio files

                if (Object.keys(durationMap).length > 0) {

                    setScenes(prev => prev.map(s =>

                        durationMap[s.scene_id] !== undefined

                            ? { ...s, audio_duration: Math.round(durationMap[s.scene_id] * 10) / 10, est_duration: Math.round(durationMap[s.scene_id] * 10) / 10 }

                            : s

                    ));

                }

            }



            setBatchProgress({ current: exportScenes.length, total: exportScenes.length, percentage: 100 });

        } catch (err: any) {

            if (err.name === 'AbortError') {

                setError('Đã dừng tạo voice');

            } else {

                console.error('[Voice Batch] Error:', err);

                setError(`Lỗi tạo voice: ${err.message}`);

            }

        } finally {

            voiceAbortRef.current = null;

            setIsGeneratingBatch(false);

        }

    };



    // Stop/Cancel batch voice generation

    const handleStopVoiceGeneration = () => {

        if (voiceAbortRef.current) {

            voiceAbortRef.current.abort();

            voiceAbortRef.current = null;

        }

    };



    // Retry all failed voice scenes

    const handleRetryFailedVoices = async () => {

        const failedSceneIds = Object.entries(sceneAudioMap)

            .filter(([, a]) => a.status === 'error')

            .map(([id]) => parseInt(id));



        const failedScenes = scenes.filter(s => failedSceneIds.includes(s.scene_id) && s.voiceExport);



        if (failedScenes.length === 0) {

            setError('Không có scene lỗi nào để thử lại');

            return;

        }



        setIsGeneratingBatch(true);

        setBatchProgress({ current: 0, total: failedScenes.length, percentage: 0 });



        const controller = new AbortController();

        voiceAbortRef.current = controller;



        // Mark failed scenes as generating

        const retryMap: typeof sceneAudioMap = {};

        failedScenes.forEach(s => { retryMap[s.scene_id] = { status: 'generating' }; });

        setSceneAudioMap(prev => ({ ...prev, ...retryMap }));



        try {

            const result = await voiceApi.generateBatch(

                {

                    scenes: failedScenes.map(s => ({

                        scene_id: s.scene_id,

                        content: s.content,

                        voiceExport: true,

                    })),

                    voice: selectedVoice,

                    language: voiceLanguage,

                    speed: voiceSpeed,

                },

                (current, total, sceneId, percentage) => {

                    setBatchProgress({ current, total, percentage });

                    setSceneAudioMap(prev => ({

                        ...prev,

                        [sceneId]: {

                            status: 'done',

                            filename: `scene_${String(sceneId).padStart(3, '0')}.mp3`,

                            url: voiceApi.getAudioUrl(`scene_${String(sceneId).padStart(3, '0')}.mp3`),

                        }

                    }));

                },

                controller.signal,

                // onSceneDone: update audio_duration for retried scenes

                (sceneId, _filename, durationSeconds) => {

                    setScenes(prev => prev.map(s =>

                        s.scene_id === sceneId

                            ? { ...s, audio_duration: Math.round(durationSeconds * 10) / 10, est_duration: Math.round(durationSeconds * 10) / 10 }

                            : s

                    ));

                }

            );



            if (result?.results) {

                const finalMap: typeof sceneAudioMap = {};

                result.results.forEach((r: any) => {

                    finalMap[r.scene_id] = r.success

                        ? { status: 'done', filename: r.filename, url: voiceApi.getAudioUrl(r.filename) }

                        : { status: 'error', error: r.error };

                });

                setSceneAudioMap(prev => ({ ...prev, ...finalMap }));

            }



            setBatchProgress({ current: failedScenes.length, total: failedScenes.length, percentage: 100 });

        } catch (err: any) {

            if (err.name === 'AbortError') {

                setError('Đã dừng retry voice');

            } else {

                console.error('[Voice Retry] Error:', err);

                setError(`Lỗi retry voice: ${err.message}`);

            }

        } finally {

            voiceAbortRef.current = null;

            setIsGeneratingBatch(false);

        }

    };



    // Download all generated voice files as zip

    const handleDownloadAllVoices = async () => {

        const filenames = Object.values(sceneAudioMap)

            .filter(a => a.status === 'done' && a.filename)

            .map(a => a.filename!);



        if (filenames.length === 0) {

            setError('Chưa có file voice nào để download');

            return;

        }



        try {

            await voiceApi.downloadAll(filenames);

        } catch (err: any) {

            setError(`Lỗi download: ${err.message}`);

        }

    };



    // Play/pause audio for a scene

    const handlePlayScene = (sceneId: number) => {

        const audio = sceneAudioMap[sceneId];

        if (!audio?.url) return;



        if (playingSceneId === sceneId) {

            // Stop playing

            audioRef.current?.pause();

            setPlayingSceneId(null);

            return;

        }



        // Play new scene

        if (audioRef.current) {

            audioRef.current.pause();

        }

        const newAudio = new Audio(audio.url);

        newAudio.onended = () => setPlayingSceneId(null);

        newAudio.play();

        audioRef.current = newAudio;

        setPlayingSceneId(sceneId);

    };





    // 

    // FOOTAGE SEARCH & VIDEO ASSEMBLY HANDLERS

    // 



    // Search footage for ALL scenes using their keywords

    // (REMOVED) PAID FOOTAGE SEARCH and VIDEO ASSEMBLY handlers - footage feature removed



    // 

    // PRESET HANDLING (auto-load active preset on mount)

    // 

    const handleApplyPreset = (config: PresetConfig) => {

        setAdvancedSettings(s => ({

            ...s,

            targetWordCount: config.targetWordCount,

            sourceLanguage: config.sourceLanguage || '',

            language: config.language,

            dialect: config.dialect,

            enableStorytellingStyle: config.enableStorytellingStyle,

            storytellingStyle: config.storytellingStyle as any,

            narrativeVoice: config.narrativeVoice as any,

            customNarrativeVoice: config.customNarrativeVoice,

            enableAudienceAddress: config.enableAudienceAddress,

            audienceAddress: config.audienceAddress,

            customAudienceAddress: config.customAudienceAddress,

            enableValueType: config.enableValueType,

            valueType: config.valueType as any,

            customValue: config.customValue,

            // country is auto-derived from language, no need to load from preset

        }));

        setSplitMode(config.splitMode as any);

        setSceneMode(config.sceneMode as any);

        setSelectedVoice(config.selectedVoice);

        setVoiceLanguage(config.voiceLanguage);

        setVoiceSpeed(config.voiceSpeed);

        setFootageOrientation(config.footageOrientation as any);

        setVideoQuality(config.videoQuality);

        setEnableSubtitles(config.enableSubtitles);

        if (config.promptStyle !== undefined) setPromptStyle(config.promptStyle);
        if (config.mainCharacter !== undefined) setMainCharacter(config.mainCharacter);

    };



    // Auto-load active preset on mount

    useEffect(() => {

        try {

            const activePresetId = localStorage.getItem('renmae_active_preset');

            if (!activePresetId) return;



            // Try user presets first

            const stored = localStorage.getItem('renmae_workflow_presets');

            const userPresets = stored ? JSON.parse(stored) : [];

            let preset = userPresets.find((p: any) => p.id === activePresetId);



            if (!preset) {

                // Check built-in presets (mirror of PresetSection's BUILT_IN_PRESETS IDs)

                // Built-in presets are handled by PresetSection, we just apply on first load

                return;

            }



            if (preset?.config) {

                console.log('[Preset] Auto-loading active preset:', preset.name);

                handleApplyPreset(preset.config);

            }

        } catch (err) {

            console.error('[Preset] Error loading active preset:', err);

        }

        // eslint-disable-next-line react-hooks/exhaustive-deps

    }, []);



    // 

    // ADVANCED REMAKE - 7 STEP WORKFLOW UI

    // 



    //  Entry Section: show project selection + guide before pipeline config 

    if (showEntrySection) {

        return (

            <div className="workflow-step advanced-remake-section">

                <div className="entry-section">

                    {/* LEFT: Project Selection */}

                    <div className="entry-left">

                        <h3 className="entry-section-title">Bắt đầu Podcast Remake</h3>

                        <p className="entry-section-subtitle">Chọn cách bạn muốn tiếp tục</p>



                        {/* Option 1: New Project */}

                        <button

                            className="entry-card"

                            onClick={() => {

                                resetWorkflowState();

                                setPendingStyleId(null);

                                setPendingStyleName(null);

                                setNewProjectName(`Project ${new Date().toLocaleDateString('vi-VN')} ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`);

                                setShowProjectNameDialog(true);

                            }}

                        >

                            <div className="entry-card-info">

                                <span className="entry-card-title">Tạo Project Mới</span>

                                <span className="entry-card-desc">

                                    Bắt đầu từ đầu — nhập kịch bản mẫu, phân tích phong cách, tạo kịch bản mới và dựng video.

                                </span>

                            </div>

                            <span className="entry-card-arrow">→</span>

                        </button>



                        {/* Option 2: Saved Projects */}

                        <div className={`entry-saved-section ${isProjectsCollapsed ? 'collapsed' : ''}`}>

                            <div className="entry-saved-header">

                                <div className="entry-saved-header-left"

                                    onClick={() => setIsProjectsCollapsed(!isProjectsCollapsed)}

                                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}

                                >

                                    <span style={{

                                        display: 'inline-block',

                                        transition: 'transform 0.2s',

                                        transform: isProjectsCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',

                                        fontSize: 12,

                                    }}>▼</span>

                                    <span>Project Đã Tạo</span>

                                    {savedProjects.length > 0 && (

                                        <span style={{ color: 'rgba(255,215,0,0.6)', fontSize: 12, marginLeft: 4 }}>({savedProjects.length})</span>

                                    )}

                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                    {savedProjects.length > 0 && !isProjectsCollapsed && (
                                        <button
                                            className="entry-refresh-btn"
                                            onClick={() => {
                                                setBulkSelectProjects(!bulkSelectProjects);
                                                setSelectedProjectIds(new Set());
                                            }}
                                            title={bulkSelectProjects ? 'Hủy chọn' : 'Chọn hàng loạt'}
                                            style={bulkSelectProjects ? { color: '#FFD700', background: 'rgba(255,215,0,0.15)' } : {}}
                                        >
                                            {bulkSelectProjects ? '✕' : '☐'}
                                        </button>
                                    )}
                                    <button

                                        className="entry-refresh-btn"

                                        onClick={loadSavedProjects}

                                        disabled={isLoadingProjects}

                                        title="Làm mới"

                                    >

                                        <span className={isLoadingProjects ? 'spinning' : ''}>↻</span>

                                    </button>
                                </div>

                            </div>



                            {!isProjectsCollapsed && (savedProjects.length === 0 ? (

                                <div className="entry-saved-empty">

                                    <span>Chưa có project nào</span>

                                    <span className="entry-saved-empty-hint">

                                        Tạo project mới ở trên để bắt đầu.

                                    </span>

                                </div>

                            ) : (

                                <div className="entry-saved-list">

                                    {savedProjects.map((proj: any) => (

                                        <div key={proj.id} className="entry-saved-item">

                                            {bulkSelectProjects && (
                                                <label
                                                    className="entry-bulk-checkbox"
                                                    onClick={e => e.stopPropagation()}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedProjectIds.has(proj.id)}
                                                        onChange={() => {
                                                            setSelectedProjectIds(prev => {
                                                                const next = new Set(prev);
                                                                if (next.has(proj.id)) next.delete(proj.id);
                                                                else next.add(proj.id);
                                                                return next;
                                                            });
                                                        }}
                                                    />
                                                </label>
                                            )}

                                            <button

                                                className="entry-saved-item-btn"

                                                onClick={() => {

                                                    if (bulkSelectProjects) {
                                                        setSelectedProjectIds(prev => {
                                                            const next = new Set(prev);
                                                            if (next.has(proj.id)) next.delete(proj.id);
                                                            else next.add(proj.id);
                                                            return next;
                                                        });
                                                        return;
                                                    }

                                                    resetWorkflowState();

                                                    setActiveProjectId(proj.id);

                                                    setShowEntrySection(false);

                                                    setShowPresetGateway(false);

                                                    setAdvancedStep(2);

                                                    // Load linked style if available (only if no data.styleA from project)

                                                    if (proj.style_id && (!proj.data || !proj.data.styleA)) {

                                                        handleLoadStyle(proj.style_id);

                                                        setPipelineSelection(prev => ({ ...prev, styleAnalysis: { voiceStyle: false, title: false, thumbnail: false, description: false, syncCharacter: false, syncStyle: false, syncContext: false } }));

                                                        setIsAnalysisLocked(true);

                                                    }

                                                    // If project has saved data, lock analysis

                                                    if (proj.data && proj.data.styleA) {

                                                        setIsAnalysisLocked(true);

                                                    }

                                                }}

                                            >

                                                <div className="entry-saved-item-info">

                                                    <span className="entry-saved-item-name">{proj.name}</span>

                                                    <span className="entry-saved-item-date">

                                                        {proj.status === 'in-progress' ? 'Đang xử lý' : proj.status === 'completed' ? 'Hoàn thành' : 'Bản nháp'}

                                                        {proj.updatedAt ? ` · ${new Date(proj.updatedAt).toLocaleDateString('vi-VN')}` : ''}

                                                    </span>

                                                </div>

                                                <span className="entry-card-arrow">→</span>

                                            </button>

                                            {!bulkSelectProjects && (
                                                <button

                                                    className="entry-saved-delete-btn"

                                                    title={`Xóa "${proj.name}"`}

                                                    onClick={async (e) => {

                                                        e.stopPropagation();

                                                        if (!confirm(`Xóa project "${proj.name}"? Dữ liệu sẽ bị xóa vĩnh viễn.`)) return;

                                                        try {

                                                            await projectApi.deleteProject(proj.id);

                                                        } catch (err) {

                                                            console.error('[Projects] Failed to delete:', err);

                                                        }

                                                        setSavedProjects(prev => prev.filter((p: any) => p.id !== proj.id));

                                                    }}

                                                >

                                                    ✕

                                                </button>
                                            )}

                                        </div>

                                    ))}

                                    {bulkSelectProjects && (
                                        <div className="entry-bulk-actions">
                                            <button
                                                className="entry-bulk-select-all"
                                                onClick={() => {
                                                    if (selectedProjectIds.size === savedProjects.length) {
                                                        setSelectedProjectIds(new Set());
                                                    } else {
                                                        setSelectedProjectIds(new Set(savedProjects.map((p: any) => p.id)));
                                                    }
                                                }}
                                            >
                                                {selectedProjectIds.size === savedProjects.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
                                            </button>
                                            {selectedProjectIds.size > 0 && (
                                                <button
                                                    className="entry-bulk-delete-btn"
                                                    disabled={isDeletingBulk}
                                                    onClick={async () => {
                                                        if (!confirm(`Xóa ${selectedProjectIds.size} project? Dữ liệu sẽ bị xóa vĩnh viễn.`)) return;
                                                        setIsDeletingBulk(true);
                                                        try {
                                                            await Promise.all(
                                                                Array.from(selectedProjectIds).map(id => projectApi.deleteProject(id))
                                                            );
                                                            setSavedProjects(prev => prev.filter((p: any) => !selectedProjectIds.has(p.id)));
                                                            setSelectedProjectIds(new Set());
                                                            setBulkSelectProjects(false);
                                                        } catch (err) {
                                                            console.error('[Projects] Bulk delete failed:', err);
                                                        }
                                                        setIsDeletingBulk(false);
                                                    }}
                                                >
                                                    {isDeletingBulk ? 'Đang xóa...' : `Xóa (${selectedProjectIds.size})`}
                                                </button>
                                            )}
                                        </div>
                                    )}

                                </div>

                            ))}

                        </div>



                        {/* Option 3: Saved Voices */}

                        <div className={`entry-saved-section ${isVoicesCollapsed ? 'collapsed' : ''}`}>

                            <div className="entry-saved-header">

                                <div className="entry-saved-header-left"

                                    onClick={() => setIsVoicesCollapsed(!isVoicesCollapsed)}

                                    style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6 }}

                                >

                                    <span style={{

                                        display: 'inline-block',

                                        transition: 'transform 0.2s',

                                        transform: isVoicesCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)',

                                        fontSize: 12,

                                    }}>▼</span>

                                    <span>Giọng Văn Đã Lưu</span>

                                    {savedStyles.length > 0 && (

                                        <span style={{ color: 'rgba(255,215,0,0.6)', fontSize: 12, marginLeft: 4 }}>({savedStyles.length})</span>

                                    )}

                                </div>

                                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                                    {savedStyles.length > 0 && !isVoicesCollapsed && (
                                        <button
                                            className="entry-refresh-btn"
                                            onClick={() => {
                                                setBulkSelectStyles(!bulkSelectStyles);
                                                setSelectedStyleIds(new Set());
                                            }}
                                            title={bulkSelectStyles ? 'Hủy chọn' : 'Chọn hàng loạt'}
                                            style={bulkSelectStyles ? { color: '#FFD700', background: 'rgba(255,215,0,0.15)' } : {}}
                                        >
                                            {bulkSelectStyles ? '✕' : '☐'}
                                        </button>
                                    )}
                                    <button

                                        className="entry-refresh-btn"

                                        onClick={loadSavedStyles}

                                        disabled={isRefreshingStyles}

                                        title="Làm mới"

                                    >

                                        <span className={isRefreshingStyles ? 'spinning' : ''}>↻</span>

                                    </button>
                                </div>

                            </div>



                            {!isVoicesCollapsed && (savedStyles.length === 0 ? (

                                <div className="entry-saved-empty">

                                    <span>Chưa có giọng văn nào được lưu</span>

                                    <span className="entry-saved-empty-hint">

                                        Phân tích phong cách trong project mới, sau đó lưu lại để tái sử dụng.

                                    </span>

                                </div>

                            ) : (

                                <div className="entry-saved-list">

                                    {savedStyles.map((style: any) => (

                                        <div key={style.id} className="entry-saved-item">

                                            {bulkSelectStyles && (
                                                <label
                                                    className="entry-bulk-checkbox"
                                                    onClick={e => e.stopPropagation()}
                                                >
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedStyleIds.has(style.id)}
                                                        onChange={() => {
                                                            setSelectedStyleIds(prev => {
                                                                const next = new Set(prev);
                                                                if (next.has(style.id)) next.delete(style.id);
                                                                else next.add(style.id);
                                                                return next;
                                                            });
                                                        }}
                                                    />
                                                </label>
                                            )}

                                            <button

                                                className="entry-saved-item-btn"

                                                onClick={() => {

                                                    if (bulkSelectStyles) {
                                                        setSelectedStyleIds(prev => {
                                                            const next = new Set(prev);
                                                            if (next.has(style.id)) next.delete(style.id);
                                                            else next.add(style.id);
                                                            return next;
                                                        });
                                                        return;
                                                    }

                                                    resetWorkflowState();

                                                    setPendingStyleId(style.id);

                                                    setPendingStyleName(style.name);

                                                    setPipelineSelection(prev => ({ ...prev, styleAnalysis: false }));

                                                    setIsAnalysisLocked(true);

                                                    setNewProjectName(`${style.name} — ${new Date().toLocaleDateString('vi-VN')}`);

                                                    setShowProjectNameDialog(true);

                                                }}

                                            >

                                                <div className="entry-saved-item-info">

                                                    <span className="entry-saved-item-name">{style.name}</span>

                                                    <span className="entry-saved-item-date">

                                                        {style.created_at ? new Date(style.created_at).toLocaleDateString('vi-VN') : ''}

                                                    </span>

                                                </div>

                                                <span className="entry-card-arrow">→</span>

                                            </button>

                                            {!bulkSelectStyles && (
                                                <button

                                                    className="entry-saved-delete-btn"

                                                    title={`Xóa "${style.name}"`}

                                                    onClick={(e) => {

                                                        e.stopPropagation();

                                                        handleDeleteStyle(style.id, style.name);

                                                    }}

                                                >

                                                    ✕

                                                </button>
                                            )}

                                        </div>

                                    ))}

                                    {bulkSelectStyles && (
                                        <div className="entry-bulk-actions">
                                            <button
                                                className="entry-bulk-select-all"
                                                onClick={() => {
                                                    if (selectedStyleIds.size === savedStyles.length) {
                                                        setSelectedStyleIds(new Set());
                                                    } else {
                                                        setSelectedStyleIds(new Set(savedStyles.map((s: any) => s.id)));
                                                    }
                                                }}
                                            >
                                                {selectedStyleIds.size === savedStyles.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
                                            </button>
                                            {selectedStyleIds.size > 0 && (
                                                <button
                                                    className="entry-bulk-delete-btn"
                                                    disabled={isDeletingBulk}
                                                    onClick={async () => {
                                                        if (!confirm(`Xóa ${selectedStyleIds.size} giọng văn? Dữ liệu sẽ bị xóa vĩnh viễn.`)) return;
                                                        setIsDeletingBulk(true);
                                                        try {
                                                            for (const id of Array.from(selectedStyleIds)) {
                                                                await fetch(`http://localhost:8000/api/workflow/styles/${id}`, { method: 'DELETE' });
                                                            }
                                                            await loadSavedStyles();
                                                            loadSavedProjects();
                                                            setSelectedStyleIds(new Set());
                                                            setBulkSelectStyles(false);
                                                        } catch (err) {
                                                            console.error('[Styles] Bulk delete failed:', err);
                                                        }
                                                        setIsDeletingBulk(false);
                                                    }}
                                                >
                                                    {isDeletingBulk ? 'Đang xóa...' : `Xóa (${selectedStyleIds.size})`}
                                                </button>
                                            )}
                                        </div>
                                    )}

                                </div>

                            ))}

                        </div>

                    </div>



                    {/* RIGHT: Guide Frame */}

                    <div className="entry-right">

                        <div className="entry-guide">

                            <div className="entry-guide-header">

                                <span>Hướng Dẫn Sử Dụng</span>

                            </div>



                            <div className="entry-guide-scroll">

                                {/* 1. Mục đích */}

                                <div className="guide-block">

                                    <div className="guide-block-title">

                                        <span>Mục đích</span>

                                    </div>

                                    <p className="guide-text">

                                        Podcast Remake giúp bạn biến nội dung gốc (podcast, bài viết, video YouTube) thành <strong>video hoàn chỉnh</strong> với kịch bản mới, giọng đọc AI, footage tự động, phụ đề, và metadata SEO — tất cả chỉ với <strong>một cú click</strong>.

                                    </p>

                                </div>



                                {/* 2. Workflow */}

                                <div className="guide-block">

                                    <div className="guide-block-title">

                                        <span>Quy trình làm việc</span>

                                    </div>

                                    <div className="guide-steps">

                                        <div className="guide-step">

                                            <div className="guide-step-num">1</div>

                                            <div className="guide-step-content">

                                                <strong>Nhập nội dung gốc</strong>

                                                <span>Dán link YouTube để tự động trích xuất transcript, hoặc paste nội dung trực tiếp.</span>

                                            </div>

                                        </div>

                                        <div className="guide-step">

                                            <div className="guide-step-num">2</div>

                                            <div className="guide-step-content">

                                                <strong>Phân tích phong cách</strong>

                                                <span>AI phân tích giọng văn, title, thumbnail, description từ kịch bản mẫu + đồng bộ nhân vật & bối cảnh.</span>

                                            </div>

                                        </div>

                                        <div className="guide-step">

                                            <div className="guide-step-num">3</div>

                                            <div className="guide-step-content">

                                                <strong>Tạo kịch bản</strong>

                                                <span>AI remake nội dung gốc theo phong cách đã phân tích, tự động chia scenes và điều chỉnh số từ.</span>

                                            </div>

                                        </div>

                                        <div className="guide-step">

                                            <div className="guide-step-num">4</div>

                                            <div className="guide-step-content">

                                                <strong>Tạo Voice AI</strong>

                                                <span>Giọng đọc AI cho từng scene, hỗ trợ 11 ngôn ngữ với nhiều giọng nam/nữ và tùy chỉnh tốc độ.</span>

                                            </div>

                                        </div>

                                        <div className="guide-step">

                                            <div className="guide-step-num">5</div>

                                            <div className="guide-step-content">

                                                <strong>Tạo Prompts & Keywords</strong>

                                                <span>AI tạo video prompts, image prompts, và keywords cho từng scene với 3 chế độ đồng bộ.</span>

                                            </div>

                                        </div>

                                        <div className="guide-step">

                                            <div className="guide-step-num">6</div>

                                            <div className="guide-step-content">

                                                <strong>Dựng Video</strong>

                                                <span>Tìm footage Pexels/Pixabay → AI Vision xếp hạng → ghép video với phụ đề và voice.</span>

                                            </div>

                                        </div>

                                        <div className="guide-step">

                                            <div className="guide-step-num">7</div>

                                            <div className="guide-step-content">

                                                <strong>SEO Thô</strong>

                                                <span>Tự động inject metadata SEO (title, tags, hash unique) vào video output.</span>

                                            </div>

                                        </div>

                                    </div>

                                </div>



                                {/* 3. Tips */}

                                <div className="guide-block">

                                    <div className="guide-block-title">

                                        <span>Mẹo sử dụng</span>

                                    </div>

                                    <ul className="guide-tips">

                                        <li>Càng nhiều kịch bản mẫu → AI phân tích phong cách chính xác hơn <em>(tối ưu: 10–15 bài)</em>.</li>

                                        <li>Bật <strong>Sync Nhân Vật + Bối Cảnh</strong> trong Phân tích để video prompts giữ nhất quán hình ảnh.</li>

                                        <li>Dùng <strong>Queue</strong> để xếp hàng nhiều project chạy pipeline tự động liên tục.</li>

                                        <li>Lưu giọng văn sau khi phân tích để <strong>tái sử dụng</strong> cho nhiều project khác nhau.</li>

                                        <li>Video ngang <strong>(16:9)</strong> cho YouTube dài, video dọc <strong>(9:16)</strong> cho Shorts/TikTok.</li>

                                    </ul>

                                </div>



                                {/* 4. Key Features */}

                                <div className="guide-block">

                                    <div className="guide-block-title">

                                        <span>Tính năng nổi bật</span>

                                    </div>

                                    <div className="guide-features">

                                        <div className="guide-feature-chip">One-click Pipeline</div>

                                        <div className="guide-feature-chip">11 Ngôn ngữ</div>

                                        <div className="guide-feature-chip">AI Vision Ranking</div>

                                        <div className="guide-feature-chip">Sync Nhân Vật & Bối Cảnh</div>

                                        <div className="guide-feature-chip">3 Chế độ Prompt</div>

                                        <div className="guide-feature-chip">Phụ đề tự động</div>

                                        <div className="guide-feature-chip">SEO Metadata</div>

                                        <div className="guide-feature-chip">Queue & Production Hub</div>

                                        <div className="guide-feature-chip">YouTube Extraction</div>

                                        <div className="guide-feature-chip">Pexels & Pixabay</div>

                                    </div>

                                </div>



                                {/* 5. Requirements */}

                                <div className="guide-block">

                                    <div className="guide-block-title">

                                        <span>Yêu cầu trước khi bắt đầu</span>

                                    </div>

                                    <ul className="guide-requirements">

                                        <li>

                                            <span>Cấu hình AI model (Gemini, GPT, Claude...) trong <strong>Cấu Hình AI</strong>.</span>

                                        </li>

                                        <li>

                                            <span>API key <strong>Pexels</strong> và/hoặc <strong>Pixabay</strong> (cho footage tự động).</span>

                                        </li>

                                        <li>

                                            <span>Chuẩn bị kịch bản mẫu <strong>(5–20 bài)</strong> cho bước phân tích giọng văn.</span>

                                        </li>

                                        <li>

                                            <span>Nội dung gốc: link YouTube hoặc văn bản podcast/bài viết.</span>

                                        </li>

                                    </ul>

                                </div>

                            </div>

                        </div>

                    </div>

                </div>



                <style>{`

                    /* ===== ENTRY SECTION ===== */

                    .entry-section {

                        display: flex;

                        gap: 1.25rem;

                        min-height: 520px;

                        animation: entryFadeIn 0.4s ease;

                    }

                    @keyframes entryFadeIn {

                        from { opacity: 0; transform: translateY(12px); }

                        to { opacity: 1; transform: translateY(0); }

                    }



                    /* LEFT COLUMN */

                    .entry-left {

                        flex: 1;

                        display: flex;

                        flex-direction: column;

                        gap: 0.75rem;

                        min-width: 0;

                    }

                    .entry-section-title {

                        font-family: 'Fredoka', sans-serif;

                        font-size: 1.35rem;

                        font-weight: 700;

                        margin: 0;

                        background: linear-gradient(135deg, #FFD700, #F59E0B);

                        -webkit-background-clip: text;

                        -webkit-text-fill-color: transparent;

                        background-clip: text;

                    }

                    .entry-section-subtitle {

                        font-size: 0.82rem;

                        color: var(--text-secondary);

                        margin: -0.25rem 0 0.5rem;

                    }



                    /* New Project Card */

                    .entry-card {

                        display: flex;

                        align-items: center;

                        gap: 1rem;

                        padding: 1.1rem 1.25rem;

                        background: linear-gradient(160deg, rgba(26, 26, 26, 0.95) 0%, rgba(18, 18, 18, 0.98) 100%);

                        border: 1.5px solid rgba(167, 139, 250, 0.25);

                        border-radius: 16px;

                        cursor: pointer;

                        transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);

                        text-align: left;

                        width: 100%;

                        font-family: inherit;

                        color: inherit;

                    }

                    .entry-card:hover {

                        border-color: rgba(167, 139, 250, 0.5);

                        transform: translateY(-2px);

                        box-shadow: 0 8px 30px rgba(167, 139, 250, 0.12);

                    }

                    .entry-card:active { transform: translateY(0) scale(0.99); }



                    .entry-card-info {

                        flex: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0;

                    }

                    .entry-card-title {

                        font-weight: 700; font-size: 0.95rem; color: var(--text-primary);

                        font-family: 'Fredoka', sans-serif;

                    }

                    .entry-card-desc {

                        font-size: 0.78rem; color: var(--text-secondary); line-height: 1.5;

                    }

                    .entry-card-arrow {

                        color: var(--text-secondary); flex-shrink: 0;

                        transition: transform 0.2s;

                    }

                    .entry-card:hover .entry-card-arrow {

                        transform: translateX(4px); color: #A78BFA;

                    }



                    /* Saved Styles Section */

                    .entry-saved-section {

                        flex: 1;

                        display: flex;

                        flex-direction: column;

                        background: var(--bg-secondary);

                        border: 1px solid var(--border-color);

                        border-radius: 14px;

                        overflow: hidden;

                        min-height: 200px;

                        transition: min-height 0.25s ease, flex 0.25s ease;

                    }

                    .entry-saved-section.collapsed {

                        flex: 0 0 auto;

                        min-height: 0;

                    }

                    .entry-saved-section.collapsed .entry-saved-header {

                        border-bottom: none;

                    }

                    .entry-saved-header {

                        display: flex;

                        align-items: center;

                        justify-content: space-between;

                        padding: 0.7rem 1rem;

                        border-bottom: 1px solid var(--border-color);

                        background: rgba(255, 215, 0, 0.03);

                    }

                    .entry-saved-header-left {

                        display: flex; align-items: center; gap: 0.5rem;

                        font-weight: 600; font-size: 0.85rem;

                        font-family: 'Fredoka', sans-serif;

                    }

                    .entry-refresh-btn {

                        background: none; border: 1px solid var(--border-color);

                        border-radius: 8px; padding: 4px 6px;

                        cursor: pointer; color: var(--text-secondary);

                        transition: all 0.2s; display: flex; align-items: center;

                    }

                    .entry-refresh-btn:hover {

                        border-color: #FFD700; color: #FFD700;

                        background: rgba(255, 215, 0, 0.06);

                    }

                    .entry-refresh-btn .spinning {

                        animation: spin 0.6s linear infinite;

                    }

                    @keyframes spin { to { transform: rotate(360deg); } }



                    .entry-saved-empty {

                        flex: 1; display: flex; flex-direction: column;

                        align-items: center; justify-content: center;

                        gap: 0.5rem; padding: 2rem 1rem;

                        color: #525252; font-size: 0.82rem;

                    }

                    .entry-saved-empty-hint {

                        font-size: 0.72rem; color: #404040;

                        text-align: center; max-width: 260px; line-height: 1.5;

                    }



                    .entry-saved-list {

                        display: flex; flex-direction: column;

                        overflow-y: auto; max-height: 280px;

                        padding: 0.3rem;

                    }

                    .entry-saved-item {

                        display: flex; align-items: center; gap: 0;

                        border: 1.5px solid transparent;

                        border-radius: 10px;

                        transition: all 0.2s; width: 100%;

                    }

                    .entry-saved-item:hover {

                        background: rgba(255, 215, 0, 0.05);

                        border-color: rgba(255, 215, 0, 0.2);

                    }

                    .entry-saved-item-btn {

                        flex: 1; display: flex; align-items: center; gap: 0.65rem;

                        padding: 0.65rem 0.75rem;

                        background: none; border: none;

                        border-radius: 10px; cursor: pointer;

                        text-align: left; font-family: inherit; color: inherit;

                        min-width: 0;

                    }

                    .entry-saved-delete-btn {

                        width: 28px; height: 28px;

                        background: none; border: 1px solid transparent;

                        border-radius: 7px; cursor: pointer;

                        color: #525252; font-size: 0.8rem;

                        display: flex; align-items: center; justify-content: center;

                        transition: all 0.2s; flex-shrink: 0;

                        margin-right: 0.5rem;

                        opacity: 0;

                    }

                    .entry-saved-item:hover .entry-saved-delete-btn {

                        opacity: 1;

                    }

                    .entry-saved-delete-btn:hover {

                        color: #ef4444; border-color: rgba(239, 68, 68, 0.3);

                        background: rgba(239, 68, 68, 0.08);

                    }

                    .entry-bulk-checkbox {
                        display: flex; align-items: center; justify-content: center;
                        padding: 0 4px 0 8px; cursor: pointer; flex-shrink: 0;
                    }
                    .entry-bulk-checkbox input[type="checkbox"] {
                        width: 16px; height: 16px; accent-color: #FFD700; cursor: pointer;
                    }
                    .entry-bulk-actions {
                        display: flex; align-items: center; justify-content: space-between;
                        padding: 8px 10px; margin-top: 4px;
                        border-top: 1px solid rgba(255,255,255,0.06);
                    }
                    .entry-bulk-select-all {
                        background: none; border: 1px solid rgba(255,215,0,0.25);
                        color: rgba(255,215,0,0.8); font-size: 0.72rem; font-weight: 500;
                        padding: 4px 10px; border-radius: 6px; cursor: pointer;
                        transition: all 0.2s;
                    }
                    .entry-bulk-select-all:hover {
                        background: rgba(255,215,0,0.08); border-color: rgba(255,215,0,0.4);
                    }
                    .entry-bulk-delete-btn {
                        background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3);
                        color: #ef4444; font-size: 0.72rem; font-weight: 600;
                        padding: 4px 12px; border-radius: 6px; cursor: pointer;
                        transition: all 0.2s;
                    }
                    .entry-bulk-delete-btn:hover:not(:disabled) {
                        background: rgba(239, 68, 68, 0.2); border-color: rgba(239, 68, 68, 0.5);
                    }
                    .entry-bulk-delete-btn:disabled {
                        opacity: 0.5; cursor: not-allowed;
                    }

                    .entry-saved-item-info {

                        flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0;

                    }

                    .entry-saved-item-name {

                        font-weight: 600; font-size: 0.82rem;

                        color: var(--text-primary);

                        white-space: nowrap; overflow: hidden; text-overflow: ellipsis;

                    }

                    .entry-saved-item-date {

                        font-size: 0.7rem; color: var(--text-secondary);

                    }



                    /* RIGHT COLUMN — Guide */

                    .entry-right {

                        width: 380px; flex-shrink: 0;

                    }

                    .entry-guide {

                        background: var(--bg-secondary);

                        border: 1px solid var(--border-color);

                        border-radius: 14px;

                        overflow: hidden;

                        height: 100%;

                        display: flex;

                        flex-direction: column;

                    }

                    .entry-guide-header {

                        display: flex; align-items: center; gap: 0.5rem;

                        padding: 0.75rem 1rem;

                        border-bottom: 1px solid var(--border-color);

                        background: linear-gradient(135deg, rgba(255,215,0,0.06), rgba(245,158,11,0.03));

                        font-weight: 700; font-size: 0.9rem;

                        font-family: 'Fredoka', sans-serif;

                    }

                    .entry-guide-scroll {

                        flex: 1; overflow-y: auto;

                        padding: 0.75rem 1rem;

                        display: flex; flex-direction: column; gap: 1rem;

                    }



                    /* Guide Blocks */

                    .guide-block {

                        display: flex; flex-direction: column; gap: 0.4rem;

                    }

                    .guide-block-title {

                        display: flex; align-items: center; gap: 0.4rem;

                        font-weight: 700; font-size: 0.82rem;

                        color: var(--text-primary);

                    }



                    .guide-text {

                        font-size: 0.78rem; color: var(--text-secondary);

                        line-height: 1.6; margin: 0;

                    }

                    .guide-text strong { color: #FFD700; font-weight: 600; }



                    /* Workflow Steps */

                    .guide-steps {

                        display: flex; flex-direction: column; gap: 0.15rem;

                    }

                    .guide-step {

                        display: flex; align-items: flex-start; gap: 0.6rem;

                        padding: 0.45rem 0.5rem;

                        border-radius: 8px;

                        transition: background 0.15s;

                    }

                    .guide-step:hover { background: rgba(255,255,255,0.02); }

                    .guide-step-num {

                        width: 22px; height: 22px;

                        background: linear-gradient(135deg, #A78BFA33, #8B5CF622);

                        border: 1px solid rgba(167,139,250,0.3);

                        border-radius: 7px;

                        display: flex; align-items: center; justify-content: center;

                        font-size: 0.72rem; font-weight: 700;

                        color: #A78BFA; flex-shrink: 0;

                        margin-top: 1px;

                    }

                    .guide-step-content {

                        display: flex; flex-direction: column; gap: 2px;

                    }

                    .guide-step-content strong {

                        font-size: 0.78rem; color: var(--text-primary);

                    }

                    .guide-step-content span {

                        font-size: 0.72rem; color: var(--text-secondary); line-height: 1.45;

                    }



                    /* Tips */

                    .guide-tips {

                        margin: 0; padding: 0 0 0 1.1rem;

                        list-style: none;

                    }

                    .guide-tips li {

                        font-size: 0.76rem; color: var(--text-secondary);

                        line-height: 1.5; margin-bottom: 0.3rem;

                        position: relative;

                    }

                    .guide-tips li::before {

                        content: '•'; position: absolute; left: -0.9rem;

                        color: #FFD700; font-weight: 700;

                    }

                    .guide-tips li strong { color: #FFD700; }

                    .guide-tips li em { color: #737373; font-style: normal; }



                    /* Feature Chips */

                    .guide-features {

                        display: flex; flex-wrap: wrap; gap: 0.35rem;

                    }

                    .guide-feature-chip {

                        font-size: 0.7rem; font-weight: 600;

                        padding: 0.25rem 0.65rem;

                        background: linear-gradient(135deg, rgba(255,215,0,0.08), rgba(245,158,11,0.04));

                        border: 1px solid rgba(255,215,0,0.18);

                        border-radius: 20px;

                        color: #FBBF24;

                    }



                    /* Requirements */

                    .guide-requirements {

                        margin: 0; padding: 0;

                        list-style: none;

                        display: flex; flex-direction: column; gap: 0.35rem;

                    }

                    .guide-requirements li {

                        display: flex; align-items: flex-start; gap: 0.45rem;

                        font-size: 0.76rem; color: var(--text-secondary);

                        line-height: 1.5;

                    }



                    .guide-requirements li strong { color: #FFD700; }



                    /* ===== PROJECT NAME DIALOG ===== */

                    .project-name-overlay {

                        position: fixed;

                        top: 0; left: 0; right: 0; bottom: 0;

                        background: rgba(0, 0, 0, 0.65);

                        backdrop-filter: blur(6px);

                        display: flex;

                        align-items: center;

                        justify-content: center;

                        z-index: 9999;

                        animation: overlayFadeIn 0.2s ease;

                    }

                    @keyframes overlayFadeIn {

                        from { opacity: 0; }

                        to { opacity: 1; }

                    }

                    .project-name-dialog {

                        background: linear-gradient(160deg, #1a1a1a 0%, #111 100%);

                        border: 1.5px solid rgba(255, 215, 0, 0.25);

                        border-radius: 18px;

                        padding: 2rem;

                        width: 420px;

                        max-width: 90vw;

                        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5), 0 0 40px rgba(255, 215, 0, 0.08);

                        animation: dialogSlideUp 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);

                    }

                    @keyframes dialogSlideUp {

                        from { opacity: 0; transform: translateY(20px) scale(0.95); }

                        to { opacity: 1; transform: translateY(0) scale(1); }

                    }

                    .project-name-dialog h3 {

                        font-family: 'Fredoka', sans-serif;

                        font-size: 1.15rem;

                        font-weight: 700;

                        color: #FFD700;

                        margin: 0 0 0.5rem;

                    }

                    .project-name-dialog p {

                        font-size: 0.82rem;

                        color: var(--text-tertiary);

                        margin: 0 0 1.25rem;

                        line-height: 1.5;

                    }

                    .project-name-input {

                        width: 100%;

                        padding: 0.75rem 1rem;

                        background: rgba(255, 255, 255, 0.04);

                        border: 1.5px solid rgba(255, 215, 0, 0.2);

                        border-radius: 12px;

                        color: var(--text-primary);

                        font-size: 0.95rem;

                        font-family: 'Fredoka', sans-serif;

                        outline: none;

                        transition: border-color 0.2s;

                        box-sizing: border-box;

                    }

                    .project-name-input:focus {

                        border-color: rgba(255, 215, 0, 0.5);

                        box-shadow: 0 0 12px rgba(255, 215, 0, 0.1);

                    }

                    .project-name-actions {

                        display: flex;

                        justify-content: flex-end;

                        gap: 0.75rem;

                        margin-top: 1.25rem;

                    }

                    .project-name-cancel {

                        padding: 0.6rem 1.5rem;

                        background: rgba(255, 255, 255, 0.04);

                        border: 1px solid rgba(255, 255, 255, 0.1);

                        border-radius: 10px;

                        color: var(--text-secondary);

                        font-size: 0.85rem;

                        cursor: pointer;

                        transition: all 0.2s;

                    }

                    .project-name-cancel:hover {

                        background: rgba(255, 255, 255, 0.08);

                        color: var(--text-primary);

                    }

                    .project-name-confirm {

                        padding: 0.6rem 1.5rem;

                        background: linear-gradient(135deg, #FFD700, #F59E0B);

                        border: none;

                        border-radius: 10px;

                        color: #000;

                        font-size: 0.85rem;

                        font-weight: 700;

                        font-family: 'Fredoka', sans-serif;

                        cursor: pointer;

                        transition: all 0.2s;

                    }

                    .project-name-confirm:hover {

                        transform: translateY(-1px);

                        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);

                    }

                    .project-name-confirm:disabled {

                        opacity: 0.5;

                        cursor: not-allowed;

                        transform: none;

                        box-shadow: none;

                    }

                `}</style>



                {/* Project Name Dialog */}

                {showProjectNameDialog && (

                    <div className="project-name-overlay" onClick={() => setShowProjectNameDialog(false)}>

                        <div className="project-name-dialog" onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>

                            <h3>Đặt tên Project</h3>

                            <p>Nhập tên cho project mới của bạn{pendingStyleName ? ` (giọng văn: ${pendingStyleName})` : ''}.</p>

                            <input

                                className="project-name-input"

                                type="text"

                                value={newProjectName}

                                onChange={e => setNewProjectName(e.target.value)}

                                placeholder="Tên project..."

                                autoFocus

                                onKeyDown={e => {

                                    if (e.key === 'Enter' && newProjectName.trim()) {

                                        setShowProjectNameDialog(false);

                                        justCreatedRef.current = true;

                                        setShowEntrySection(false);

                                        // Fire-and-forget: persist to backend

                                        projectApi.createProject(newProjectName.trim(), pendingStyleId)

                                            .then(result => { if (result.project) setActiveProjectId(String(result.project.id)); })

                                            .catch(err => console.error('[Projects] Failed to create:', err));

                                        if (pendingStyleId) {

                                            handleLoadStyle(pendingStyleId);

                                        }

                                    }

                                }}

                            />

                            <div className="project-name-actions">

                                <button className="project-name-cancel" onClick={() => setShowProjectNameDialog(false)}>

                                    Hủy

                                </button>

                                <button

                                    className="project-name-confirm"

                                    disabled={!newProjectName.trim()}

                                    onClick={() => {

                                        setShowProjectNameDialog(false);

                                        justCreatedRef.current = true;

                                        setShowEntrySection(false);

                                        // Fire-and-forget: persist to backend

                                        projectApi.createProject(newProjectName.trim(), pendingStyleId)

                                            .then(result => { if (result.project) setActiveProjectId(String(result.project.id)); })

                                            .catch(err => console.error('[Projects] Failed to create:', err));

                                        if (pendingStyleId) {

                                            handleLoadStyle(pendingStyleId);

                                        }

                                    }}

                                >

                                    Tạo Project

                                </button>

                            </div>

                        </div>

                    </div>

                )}

            </div>

        );

    }



    //  Gateway: show PresetSection first 

    if (showPresetGateway) {

        return (

            <div className="workflow-step advanced-remake-section">

                <PresetSection

                    onPipelineChange={setPipelineSelection}

                    initialPipeline={pipelineSelection}

                    analysisLocked={isAnalysisLocked}

                    config={{

                        advancedSettings,

                        setAdvancedSettings,

                        voiceLanguage,

                        setVoiceLanguage,

                        selectedVoice,

                        setSelectedVoice,

                        voiceSpeed,

                        setVoiceSpeed,

                        voicesByLanguage,

                        splitMode,

                        setSplitMode,

                        sceneMode,

                        setSceneMode,

                        footageOrientation,

                        setFootageOrientation,

                        videoQuality,

                        setVideoQuality,

                        enableSubtitles,

                        setEnableSubtitles,

                        promptStyle,

                        setPromptStyle,

                        mainCharacter,

                        setMainCharacter,

                        contextDescription,

                        setContextDescription,

                        channelName,

                        setChannelName,

                    }}

                />



                {/* Continue button */}

                <div style={{

                    display: 'flex',

                    justifyContent: 'center',

                    gap: '1rem',

                    marginTop: '1.5rem',

                }}>

                    <button

                        className="btn btn-primary"

                        onClick={() => {

                            setShowPresetGateway(false);

                            // Route to first enabled step based on pipeline selection

                            if (isAnalysisEnabled(pipelineSelection.styleAnalysis)) {

                                setAdvancedStep(1);

                            } else if (pipelineSelection.scriptGeneration) {

                                setAdvancedStep(2);

                            } else if (pipelineSelection.voiceGeneration) {

                                setAdvancedStep(3);

                            } else {

                                setAdvancedStep(4);

                            }

                        }}

                        style={{

                            padding: '12px 40px',

                            fontSize: '1rem',

                            fontFamily: "'Fredoka', sans-serif",

                            fontWeight: 600,

                            background: 'linear-gradient(135deg, #FFD700, #F59E0B)',

                            color: '#000',

                            border: 'none',

                            borderRadius: '14px',

                            cursor: 'pointer',

                            transition: 'all 0.3s',

                            boxShadow: '0 4px 20px rgba(255, 215, 0, 0.3)',

                        }}

                        onMouseEnter={e => {

                            (e.target as HTMLButtonElement).style.transform = 'translateY(-2px) scale(1.02)';

                            (e.target as HTMLButtonElement).style.boxShadow = '0 8px 30px rgba(255, 215, 0, 0.4)';

                        }}

                        onMouseLeave={e => {

                            (e.target as HTMLButtonElement).style.transform = '';

                            (e.target as HTMLButtonElement).style.boxShadow = '0 4px 20px rgba(255, 215, 0, 0.3)';

                        }}

                    >

                        {isAnalysisEnabled(pipelineSelection.styleAnalysis) ? 'Tiếp tục phân tích →' : 'Tiếp tục tạo kịch bản →'}

                    </button>

                </div>

            </div>

        );

    }



    return (

        <div className="workflow-step advanced-remake-section">





            {/*  */}

            {/* STEP 1: STYLE ANALYSIS (OPTIONAL) */}

            {/*  */}

            {advancedStep === 1 && (

                <div className="step-content glass-card" style={{ padding: '1.5rem' }}>

                    {/* Two-Panel Layout */}

                    <div style={{

                        display: 'flex',

                        gap: '1.5rem',

                        alignItems: 'stretch'

                    }}>

                        {/* LEFT PANEL: Script Input & Analysis Controls */}

                        <div style={{

                            flex: '1 1 50%',

                            minWidth: 0

                        }}>

                            {/* ═══ YOUTUBE URL EXTRACTION FRAME ═══ */}
                            <div className="style-analysis-section glass-card" style={{
                                padding: '1.5rem',
                                marginBottom: '1.5rem',
                                border: '1px solid rgba(239, 68, 68, 0.35)',
                                borderRadius: '16px',
                                background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.04), rgba(220, 38, 38, 0.02))',
                            }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                    <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                                        <Link2 size={18} style={{ color: '#EF4444' }} />
                                        YouTube Auto-Extract
                                        <span className="badge" style={{
                                            background: 'linear-gradient(135deg, #EF4444, #DC2626)',
                                            color: '#fff',
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '20px',
                                            fontSize: '0.7rem',
                                            fontWeight: 600
                                        }}>
                                            {youtubeExtractedItems.length} LINK
                                        </span>
                                    </h3>
                                </div>
                                <p style={{ color: 'var(--text-secondary)', marginBottom: '0.75rem', fontSize: '0.85rem', lineHeight: 1.5 }}>
                                    Dán link YouTube → tự động lấy kịch bản, tiêu đề, mô tả, thumbnail.
                                </p>

                                {/* URL Input */}
                                <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                    <input
                                        type="text"
                                        placeholder="https://youtube.com/watch?v=... hoặc youtu.be/..."
                                        value={youtubeUrlInput}
                                        onChange={(e) => setYoutubeUrlInput(e.target.value)}
                                        disabled={isExtractingYoutube}
                                        style={{
                                            flex: 1,
                                            background: 'var(--bg-tertiary)',
                                            color: 'var(--text-primary)',
                                            border: '1px solid var(--border-color)',
                                            borderRadius: '10px',
                                            padding: '0.6rem 0.8rem',
                                            fontSize: '0.9rem',
                                            outline: 'none'
                                        }}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter' && youtubeUrlInput.trim() && !isExtractingYoutube) {
                                                handleExtractYoutubeUrl();
                                            }
                                        }}
                                    />
                                    <button
                                        className="btn btn-primary"
                                        onClick={handleExtractYoutubeUrl}
                                        disabled={!youtubeUrlInput.trim() || isExtractingYoutube}
                                        style={{
                                            background: isExtractingYoutube ? 'rgba(239, 68, 68, 0.3)' : 'linear-gradient(135deg, #EF4444, #DC2626)',
                                            border: 'none',
                                            padding: '0.6rem 1.2rem',
                                            borderRadius: '10px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.4rem',
                                            whiteSpace: 'nowrap' as const,
                                        }}
                                    >
                                        {isExtractingYoutube ? (
                                            <><Loader2 size={16} className="spin" /> Đang lấy...</>
                                        ) : (
                                            <><Plus size={16} /> Thêm link</>
                                        )}
                                    </button>
                                </div>

                                {/* Extracted items list */}
                                {youtubeExtractedItems.length > 0 && (
                                    <div style={{ maxHeight: '200px', overflowY: 'auto', background: 'var(--bg-tertiary)', borderRadius: '10px', padding: '0.5rem' }}>
                                        {youtubeExtractedItems.map((item, idx) => (
                                            <div key={item.video_id + '-' + idx} style={{
                                                display: 'flex',
                                                gap: '0.75rem',
                                                alignItems: 'center',
                                                padding: '0.5rem',
                                                borderBottom: idx < youtubeExtractedItems.length - 1 ? '1px solid var(--border-color)' : 'none',
                                            }}>
                                                <img
                                                    src={item.thumbnail_url}
                                                    alt={item.title}
                                                    style={{ width: '80px', height: '45px', borderRadius: '6px', objectFit: 'cover', flexShrink: 0, border: '1px solid var(--border-color)' }}
                                                    onError={(e) => { (e.target as HTMLImageElement).src = `https://i.ytimg.com/vi/${item.video_id}/hqdefault.jpg`; }}
                                                />
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <div style={{ fontSize: '0.85rem', fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
                                                        {item.title}
                                                    </div>
                                                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', display: 'flex', gap: '0.75rem', marginTop: '0.2rem' }}>
                                                        <span>{item.channel_name || 'Unknown'}</span>
                                                        <span style={{ color: item.transcript ? '#10B981' : '#EF4444' }}>
                                                            {item.transcript ? '✓ Transcript' : '✗ No transcript'}
                                                        </span>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={() => handleRemoveYoutubeItem(idx)}
                                                    style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', borderRadius: '6px', padding: '0.3rem 0.4rem', cursor: 'pointer', flexShrink: 0 }}
                                                    title="Xóa link này"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            {/*  */}

                            {/* COMPREHENSIVE STYLE ANALYSIS - 5-20 Scripts Support */}

                            {/*  */}

                            {analysisOpts.voiceStyle && (
                                <div className="style-analysis-section glass-card" style={{
                                    padding: isVoiceInputExpanded ? '1.5rem' : '1rem 1.5rem',
                                    marginBottom: '1.5rem',
                                    border: '1px solid var(--border-color)',
                                    borderRadius: '16px',
                                    display: 'flex',
                                    flexDirection: 'column' as const,
                                }}>
                                    <div
                                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: isVoiceInputExpanded ? '1rem' : 0 }}
                                        onClick={() => setIsVoiceInputExpanded(!isVoiceInputExpanded)}
                                    >
                                        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                                            {isVoiceInputExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                            Phân tích giọng văn
                                        </h3>
                                        <span className="badge" style={{
                                            background: 'var(--gradient-primary)',
                                            color: '#0a0a0a',
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '20px',
                                            fontSize: '0.75rem'
                                        }}>
                                            {referenceScripts.length}/20 mẫu
                                        </span>
                                    </div>

                                    {isVoiceInputExpanded && <>
                                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.9rem' }}>
                                            Nhập 5-20 kịch bản mẫu để AI phân tích sâu: Core Angle, INSIGHT, HOOK, Retention Engine, CTA...
                                        </p>





                                        {/* Multi-script input area */}

                                        <div className="multi-script-input" style={{ marginBottom: '1rem' }}>

                                            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>

                                                <textarea

                                                    className="script-textarea"

                                                    placeholder="Paste kịch bản mẫu vào đây... (tối thiểu 50 ký tự)"

                                                    value={referenceScript}

                                                    onChange={(e) => setReferenceScript(e.target.value)}

                                                    rows={4}

                                                    style={{

                                                        flex: 1,

                                                        background: 'var(--bg-tertiary)',

                                                        color: 'var(--text-primary)',

                                                        border: '1px solid var(--border-color)',

                                                        borderRadius: '12px',

                                                        padding: '0.75rem 1rem',

                                                        fontSize: '0.9rem',

                                                        resize: 'vertical',

                                                        outline: 'none',

                                                        transition: 'border-color 0.2s'

                                                    }}

                                                />

                                            </div>

                                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>

                                                <button

                                                    className="btn btn-secondary"

                                                    onClick={() => {

                                                        if (referenceScript.length >= 50 && referenceScripts.length < 20) {

                                                            setReferenceScripts([...referenceScripts, referenceScript]);

                                                            setReferenceScript('');

                                                        }

                                                    }}

                                                    disabled={referenceScript.length < 50 || referenceScripts.length >= 20}

                                                >

                                                    <Plus size={16} /> Thêm mẫu ({referenceScripts.length}/20)

                                                </button>

                                                <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>

                                                    {referenceScript.length.toLocaleString()} ký tự

                                                </span>

                                            </div>

                                        </div>



                                        {/* Added scripts list */}

                                        {referenceScripts.length > 0 && (

                                            <div className="scripts-list" style={{

                                                marginBottom: '1rem',

                                                maxHeight: '150px',

                                                overflowY: 'auto',

                                                background: 'var(--bg-tertiary)',

                                                borderRadius: '8px',

                                                padding: '0.5rem'

                                            }}>

                                                {referenceScripts.map((script, idx) => (

                                                    <div key={idx} style={{

                                                        display: 'flex',

                                                        justifyContent: 'space-between',

                                                        alignItems: 'center',

                                                        padding: '0.5rem',

                                                        borderBottom: idx < referenceScripts.length - 1 ? '1px solid var(--border-color)' : 'none'

                                                    }}>

                                                        <span style={{ fontSize: '0.85rem' }}>

                                                            Mẫu {idx + 1}: {script.substring(0, 60)}...

                                                            <span style={{ color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>

                                                                ({script.length} ký tự)

                                                            </span>

                                                        </span>

                                                        <button

                                                            onClick={() => setReferenceScripts(referenceScripts.filter((_, i) => i !== idx))}

                                                            style={{

                                                                background: 'rgba(239, 68, 68, 0.15)',

                                                                border: '1px solid rgba(239, 68, 68, 0.3)',

                                                                color: '#ef4444',

                                                                borderRadius: '8px',

                                                                padding: '0.35rem 0.5rem',

                                                                cursor: 'pointer',

                                                                display: 'flex',

                                                                alignItems: 'center',

                                                                justifyContent: 'center',

                                                                flexShrink: 0,

                                                            }}

                                                            title="Xóa kịch bản"

                                                        >

                                                            <Trash2 size={14} />

                                                        </button>

                                                    </div>

                                                ))}

                                            </div>

                                        )}
                                    </>}

                                </div>
                            )}

                            {/* ═══ TITLE ANALYSIS SECTION ═══ */}
                            {analysisOpts.title && (
                                <div className="style-analysis-section glass-card" style={{
                                    padding: isTitleInputExpanded ? '1.5rem' : '1rem 1.5rem',
                                    marginBottom: '1.5rem',
                                    border: '1px solid rgba(59, 130, 246, 0.3)',
                                    borderRadius: '16px',
                                    display: 'flex',
                                    flexDirection: 'column' as const,
                                }}>
                                    <div
                                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: isTitleInputExpanded ? '0.5rem' : 0 }}
                                        onClick={() => setIsTitleInputExpanded(!isTitleInputExpanded)}
                                    >
                                        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                                            {isTitleInputExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                            Phân tích Title
                                        </h3>
                                        <span className="badge" style={{
                                            background: 'linear-gradient(135deg, #3B82F6, #2563EB)',
                                            color: '#fff',
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '20px',
                                            fontSize: '0.75rem'
                                        }}>
                                            {titleSamples.length}/20 mẫu
                                        </span>
                                    </div>
                                    {isTitleInputExpanded && <>
                                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                                            Nhập 5-20 title YouTube mẫu để AI phân tích phong cách đặt tiêu đề.
                                        </p>
                                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                            <input
                                                type="text"
                                                placeholder="Paste title mẫu vào đây..."
                                                value={titleInput}
                                                onChange={(e) => setTitleInput(e.target.value)}
                                                style={{
                                                    flex: 1,
                                                    background: 'var(--bg-tertiary)',
                                                    color: 'var(--text-primary)',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '10px',
                                                    padding: '0.6rem 0.8rem',
                                                    fontSize: '0.9rem',
                                                    outline: 'none'
                                                }}
                                                onKeyDown={(e) => {
                                                    if (e.key === 'Enter' && titleInput.trim().length >= 5 && titleSamples.length < 20) {
                                                        setTitleSamples([...titleSamples, titleInput.trim()]);
                                                        setTitleInput('');
                                                    }
                                                }}
                                            />
                                            <button
                                                className="btn btn-secondary"
                                                onClick={() => {
                                                    if (titleInput.trim().length >= 5 && titleSamples.length < 20) {
                                                        setTitleSamples([...titleSamples, titleInput.trim()]);
                                                        setTitleInput('');
                                                    }
                                                }}
                                                disabled={titleInput.trim().length < 5 || titleSamples.length >= 20}
                                            >
                                                <Plus size={16} /> Thêm
                                            </button>
                                        </div>
                                        {titleSamples.length > 0 && (
                                            <div style={{ maxHeight: '120px', overflowY: 'auto', background: 'var(--bg-tertiary)', borderRadius: '8px', padding: '0.5rem' }}>
                                                {titleSamples.map((t, idx) => (
                                                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0.5rem', borderBottom: idx < titleSamples.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                                                        <span style={{ fontSize: '0.85rem' }}>{idx + 1}. {t}</span>
                                                        <button onClick={() => setTitleSamples(titleSamples.filter((_, i) => i !== idx))} style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', borderRadius: '6px', padding: '0.2rem 0.4rem', cursor: 'pointer', flexShrink: 0 }}>
                                                            <Trash2 size={12} />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </>}
                                </div>
                            )}

                            {/* ═══ DESCRIPTION ANALYSIS SECTION ═══ */}
                            {analysisOpts.description && (
                                <div className="style-analysis-section glass-card" style={{
                                    padding: isDescInputExpanded ? '1.5rem' : '1rem 1.5rem',
                                    marginBottom: '1.5rem',
                                    border: '1px solid rgba(16, 185, 129, 0.3)',
                                    borderRadius: '16px',
                                    display: 'flex',
                                    flexDirection: 'column' as const,
                                }}>
                                    <div
                                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: isDescInputExpanded ? '0.5rem' : 0 }}
                                        onClick={() => setIsDescInputExpanded(!isDescInputExpanded)}
                                    >
                                        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                                            {isDescInputExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                            Phân tích Description
                                        </h3>
                                        <span className="badge" style={{
                                            background: 'linear-gradient(135deg, #10B981, #059669)',
                                            color: '#fff',
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '20px',
                                            fontSize: '0.75rem'
                                        }}>
                                            {descriptionSamples.length}/20 mẫu
                                        </span>
                                    </div>
                                    {isDescInputExpanded && <>
                                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                                            Nhập 5-20 description YouTube mẫu để AI phân tích cấu trúc mô tả.
                                        </p>
                                        <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
                                            <textarea
                                                placeholder="Paste description mẫu vào đây... (tối thiểu 30 ký tự)"
                                                value={descriptionInput}
                                                onChange={(e) => setDescriptionInput(e.target.value)}
                                                rows={3}
                                                style={{
                                                    flex: 1,
                                                    background: 'var(--bg-tertiary)',
                                                    color: 'var(--text-primary)',
                                                    border: '1px solid var(--border-color)',
                                                    borderRadius: '10px',
                                                    padding: '0.6rem 0.8rem',
                                                    fontSize: '0.9rem',
                                                    resize: 'vertical',
                                                    outline: 'none'
                                                }}
                                            />
                                        </div>
                                        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                                            <button
                                                className="btn btn-secondary"
                                                onClick={() => {
                                                    if (descriptionInput.trim().length >= 30 && descriptionSamples.length < 20) {
                                                        setDescriptionSamples([...descriptionSamples, descriptionInput.trim()]);
                                                        setDescriptionInput('');
                                                    }
                                                }}
                                                disabled={descriptionInput.trim().length < 30 || descriptionSamples.length >= 20}
                                            >
                                                <Plus size={16} /> Thêm mẫu ({descriptionSamples.length}/20)
                                            </button>
                                            <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
                                                {descriptionInput.length} ký tự
                                            </span>
                                        </div>
                                        {descriptionSamples.length > 0 && (
                                            <div style={{ maxHeight: '120px', overflowY: 'auto', background: 'var(--bg-tertiary)', borderRadius: '8px', padding: '0.5rem', marginTop: '0.75rem' }}>
                                                {descriptionSamples.map((d, idx) => (
                                                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0.5rem', borderBottom: idx < descriptionSamples.length - 1 ? '1px solid var(--border-color)' : 'none' }}>
                                                        <span style={{ fontSize: '0.85rem' }}>Mẫu {idx + 1}: {d.substring(0, 60)}... <span style={{ color: 'var(--text-secondary)' }}>({d.length} ký tự)</span></span>
                                                        <button onClick={() => setDescriptionSamples(descriptionSamples.filter((_, i) => i !== idx))} style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', color: '#ef4444', borderRadius: '6px', padding: '0.2rem 0.4rem', cursor: 'pointer', flexShrink: 0 }}>
                                                            <Trash2 size={12} />
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </>}
                                </div>
                            )}

                            {/* ═══ THUMBNAIL ANALYSIS SECTION ═══ */}
                            {analysisOpts.thumbnail && (
                                <div className="style-analysis-section glass-card" style={{
                                    padding: isThumbInputExpanded ? '1.5rem' : '1rem 1.5rem',
                                    marginBottom: '1.5rem',
                                    border: '1px solid rgba(168, 85, 247, 0.3)',
                                    borderRadius: '16px',
                                    display: 'flex',
                                    flexDirection: 'column' as const,
                                }}>
                                    <div
                                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer', marginBottom: isThumbInputExpanded ? '0.5rem' : 0 }}
                                        onClick={() => setIsThumbInputExpanded(!isThumbInputExpanded)}
                                    >
                                        <h3 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                                            {isThumbInputExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                                            Phân tích Thumbnail
                                        </h3>
                                        <span className="badge" style={{
                                            background: 'linear-gradient(135deg, #A855F7, #7C3AED)',
                                            color: '#fff',
                                            padding: '0.25rem 0.75rem',
                                            borderRadius: '20px',
                                            fontSize: '0.75rem'
                                        }}>
                                            {thumbnailFiles.length}/10 ảnh
                                        </span>
                                    </div>
                                    {isThumbInputExpanded && <>
                                        <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem', fontSize: '0.85rem' }}>
                                            Upload 3-10 thumbnail YouTube mẫu để AI phân tích phong cách hình ảnh.
                                        </p>
                                        <div
                                            style={{
                                                border: '2px dashed rgba(168, 85, 247, 0.3)',
                                                borderRadius: '12px',
                                                padding: '1.5rem',
                                                textAlign: 'center',
                                                cursor: 'pointer',
                                                transition: 'all 0.2s',
                                                background: 'rgba(168, 85, 247, 0.05)'
                                            }}
                                            onClick={() => {
                                                const input = document.createElement('input');
                                                input.type = 'file';
                                                input.accept = 'image/*';
                                                input.multiple = true;
                                                input.onchange = (e) => {
                                                    const files = Array.from((e.target as HTMLInputElement).files || []);
                                                    const remaining = 10 - thumbnailFiles.length;
                                                    const newFiles = files.slice(0, remaining).map(f => ({
                                                        file: f,
                                                        preview: URL.createObjectURL(f)
                                                    }));
                                                    setThumbnailFiles(prev => [...prev, ...newFiles]);
                                                };
                                                input.click();
                                            }}
                                        >
                                            <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📷</div>
                                            <p style={{ color: 'var(--text-secondary)', margin: 0, fontSize: '0.85rem' }}>
                                                Click để upload thumbnail mẫu (PNG, JPG)
                                            </p>
                                        </div>
                                        {thumbnailFiles.length > 0 && (
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '1rem' }}>
                                                {thumbnailFiles.map((thumb, idx) => (
                                                    <div key={idx} style={{ position: 'relative', width: '100px', height: '56px', borderRadius: '8px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
                                                        <img src={thumb.preview} alt={`Thumbnail ${idx + 1}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                URL.revokeObjectURL(thumb.preview);
                                                                setThumbnailFiles(thumbnailFiles.filter((_, i) => i !== idx));
                                                            }}
                                                            style={{
                                                                position: 'absolute', top: 2, right: 2,
                                                                background: 'rgba(0,0,0,0.6)', border: 'none',
                                                                color: '#fff', borderRadius: '50%',
                                                                width: '18px', height: '18px',
                                                                cursor: 'pointer', fontSize: '0.65rem',
                                                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                                                            }}
                                                        >
                                                            ✕
                                                        </button>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </>}
                                </div>
                            )}

                            {/* ═══ SYNC MODE ANALYSIS PANELS ═══ */}
                            {(() => {
                                const showCharacterPanel = analysisOpts.syncCharacter;
                                const showStylePanel = analysisOpts.syncStyle;
                                const showContextPanel = analysisOpts.syncContext;
                                const vMode = pipelineSelection?.videoProduction?.video_prompt_mode;
                                if (!showCharacterPanel && !showStylePanel && !showContextPanel) return null;

                                // Drag-and-drop handler factory
                                function handleImageDrop(e: React.DragEvent, setter: React.Dispatch<React.SetStateAction<string[]>>) {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    const files = Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/'));
                                    files.forEach(file => {
                                        const reader = new FileReader();
                                        reader.onload = () => setter(prev => [...prev, reader.result as string]);
                                        reader.readAsDataURL(file);
                                    });
                                }
                                function handleImageInput(e: React.ChangeEvent<HTMLInputElement>, setter: React.Dispatch<React.SetStateAction<string[]>>) {
                                    const files = Array.from(e.target.files || []).filter(f => f.type.startsWith('image/'));
                                    files.forEach(file => {
                                        const reader = new FileReader();
                                        reader.onload = () => setter(prev => [...prev, reader.result as string]);
                                        reader.readAsDataURL(file);
                                    });
                                    e.target.value = '';
                                }
                                function renderImageDropZone(
                                    images: string[],
                                    setter: React.Dispatch<React.SetStateAction<string[]>>,
                                    inputId: string,
                                ) {
                                    return (
                                        <div style={{ marginTop: '0.5rem' }}>
                                            <div
                                                onDragOver={e => { e.preventDefault(); e.stopPropagation(); }}
                                                onDrop={e => handleImageDrop(e, setter)}
                                                onClick={() => document.getElementById(inputId)?.click()}
                                                style={{
                                                    border: '2px dashed rgba(168, 85, 247, 0.3)',
                                                    borderRadius: '10px',
                                                    padding: images.length > 0 ? '0.5rem' : '1rem',
                                                    textAlign: 'center',
                                                    cursor: 'pointer',
                                                    background: 'rgba(168, 85, 247, 0.03)',
                                                    transition: 'border-color 0.2s, background 0.2s',
                                                    minHeight: images.length > 0 ? 'auto' : '60px',
                                                    display: 'flex',
                                                    flexDirection: 'column' as const,
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    gap: '0.5rem',
                                                }}
                                            >
                                                <input
                                                    id={inputId}
                                                    type="file"
                                                    accept="image/*"
                                                    multiple
                                                    style={{ display: 'none' }}
                                                    onChange={e => handleImageInput(e, setter)}
                                                />
                                                {images.length === 0 && (
                                                    <span style={{ color: 'var(--text-tertiary)', fontSize: '0.78rem' }}>
                                                        Kéo thả ảnh tham chiếu vào đây hoặc click để chọn
                                                    </span>
                                                )}
                                                {images.length > 0 && (
                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center' }}>
                                                        {images.map((src, idx) => (
                                                            <div key={idx} style={{ position: 'relative', width: '72px', height: '72px' }}>
                                                                <img src={src} alt={`ref-${idx}`} style={{
                                                                    width: '100%', height: '100%', objectFit: 'cover',
                                                                    borderRadius: '8px', border: '1px solid rgba(168, 85, 247, 0.3)',
                                                                }} />
                                                                <button
                                                                    onClick={e => { e.stopPropagation(); setter(prev => prev.filter((_, i) => i !== idx)); }}
                                                                    style={{
                                                                        position: 'absolute', top: '-6px', right: '-6px',
                                                                        width: '18px', height: '18px', borderRadius: '50%',
                                                                        background: 'rgba(239, 68, 68, 0.9)', color: '#fff',
                                                                        border: 'none', cursor: 'pointer', fontSize: '0.6rem',
                                                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                                        lineHeight: 1,
                                                                    }}
                                                                >
                                                                    ✕
                                                                </button>
                                                            </div>
                                                        ))}
                                                        <div
                                                            style={{
                                                                width: '72px', height: '72px', borderRadius: '8px',
                                                                border: '2px dashed rgba(168, 85, 247, 0.25)',
                                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                                color: 'rgba(168, 85, 247, 0.5)', fontSize: '1.2rem',
                                                            }}
                                                        >
                                                            +
                                                        </div>
                                                    </div>
                                                )}
                                            </div>
                                        </div>
                                    );
                                }

                                return (
                                    <div className="style-analysis-section glass-card" style={{
                                        padding: '1.5rem',
                                        marginTop: '1.5rem',
                                        border: '1px solid rgba(168, 85, 247, 0.35)',
                                        borderRadius: '16px',
                                        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.04), rgba(139, 92, 246, 0.02))',
                                    }}>
                                        <h3 style={{ margin: '0 0 0.75rem', fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                                            Sync Analysis
                                            <span style={{
                                                marginLeft: '0.5rem', fontSize: '0.7rem', fontWeight: 600,
                                                background: 'rgba(168, 85, 247, 0.15)', color: '#A855F7',
                                                padding: '0.2rem 0.6rem', borderRadius: '20px',
                                                border: '1px solid rgba(168, 85, 247, 0.3)',
                                            }}>
                                                {vMode === 'character_sync' ? 'Character' : vMode === 'scene_sync' ? 'Style' : 'Full'}
                                            </span>
                                        </h3>
                                        <p style={{ color: 'var(--text-secondary)', margin: '0 0 1rem', fontSize: '0.82rem', lineHeight: 1.5 }}>
                                            {vMode === 'character_sync' && 'Mô tả nhân vật chính. AI sẽ lặp lại mô tả này trong mọi prompt (Identity Layer).'}
                                            {vMode === 'scene_sync' && 'Mô tả phong cách hình ảnh. Sẽ áp dụng đồng nhất cho mọi scene.'}
                                            {vMode === 'full_sync' && 'Mô tả nhân vật, phong cách và bối cảnh. AI đảm bảo nhất quán toàn bộ.'}
                                        </p>

                                        {/* Character Panel */}
                                        {showCharacterPanel && (
                                            <div style={{ marginBottom: showStylePanel || showContextPanel ? '1rem' : 0 }}>
                                                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: '0.4rem' }}>
                                                    Phân tích nhân vật
                                                </label>
                                                <textarea
                                                    value={mainCharacter}
                                                    onChange={e => setMainCharacter(e.target.value)}
                                                    placeholder="VD: Phụ nữ Việt Nam 28 tuổi, tóc đen dài ngang vai, mắt nâu ấm, mặc áo lụa kem. Hoặc: 40-year-old fisherman with salt-and-pepper beard, faded yellow raincoat..."
                                                    style={{
                                                        width: '100%', minHeight: '80px', padding: '0.6rem 0.8rem', borderRadius: '10px',
                                                        border: '1px solid rgba(168, 85, 247, 0.3)', background: 'var(--bg-tertiary)',
                                                        color: 'var(--text-primary)', fontSize: '0.82rem', lineHeight: 1.5,
                                                        resize: 'vertical', fontFamily: 'inherit',
                                                    }}
                                                />
                                                {renderImageDropZone(syncCharacterImages, setSyncCharacterImages, 'sync-char-upload')}
                                            </div>
                                        )}

                                        {/* Style Panel */}
                                        {showStylePanel && (
                                            <div style={{ marginBottom: showContextPanel ? '1rem' : 0 }}>
                                                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: '0.4rem' }}>
                                                    Phân tích phong cách
                                                </label>
                                                <textarea
                                                    value={promptStyle}
                                                    onChange={e => setPromptStyle(e.target.value)}
                                                    placeholder="VD: Cinematic photorealism, golden hour warm lighting, 35mm lens, shallow depth of field, warm amber tones, film grain..."
                                                    style={{
                                                        width: '100%', minHeight: '80px', padding: '0.6rem 0.8rem', borderRadius: '10px',
                                                        border: '1px solid rgba(168, 85, 247, 0.3)', background: 'var(--bg-tertiary)',
                                                        color: 'var(--text-primary)', fontSize: '0.82rem', lineHeight: 1.5,
                                                        resize: 'vertical', fontFamily: 'inherit',
                                                    }}
                                                />
                                                {renderImageDropZone(syncStyleImages, setSyncStyleImages, 'sync-style-upload')}
                                            </div>
                                        )}

                                        {/* Context Panel */}
                                        {showContextPanel && (
                                            <div>
                                                <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)', display: 'block', marginBottom: '0.4rem' }}>
                                                    Phân tích bối cảnh
                                                </label>
                                                <textarea
                                                    value={contextDescription}
                                                    onChange={e => setContextDescription(e.target.value)}
                                                    placeholder="VD: Hành lang bệnh viện hiện đại, ánh đèn LED trắng lạnh, sàn gạch bóng. Hoặc: Sun-drenched Victorian study, dust motes in shafts of light through bay windows..."
                                                    style={{
                                                        width: '100%', minHeight: '80px', padding: '0.6rem 0.8rem', borderRadius: '10px',
                                                        border: '1px solid rgba(168, 85, 247, 0.3)', background: 'var(--bg-tertiary)',
                                                        color: 'var(--text-primary)', fontSize: '0.82rem', lineHeight: 1.5,
                                                        resize: 'vertical', fontFamily: 'inherit',
                                                    }}
                                                />
                                                {renderImageDropZone(syncContextImages, setSyncContextImages, 'sync-ctx-upload')}
                                            </div>
                                        )}
                                    </div>
                                );
                            })()}

                        </div>

                        {/* RIGHT PANEL: Analysis Results */}

                        <div style={{

                            flex: '1 1 50%',

                            minWidth: 0,

                            borderRadius: '16px',

                            display: 'flex',

                            flexDirection: 'column' as const,

                            gap: '0.75rem',

                        }}>

                            {/* ═══ UPPER PANEL: Voice / Title / Desc / Thumbnail ═══ */}
                            <div style={{
                                minHeight: 0,
                                flex: 1,
                                overflowY: 'auto',
                                display: 'flex',
                                flexDirection: 'column' as const,
                                background: 'var(--bg-secondary)',
                                borderRadius: '12px',
                                padding: '1rem',
                                border: '1px solid var(--border-color)',
                            }}>

                                {(styleA || originalAnalysis) && (

                                    <div className="analysis-results" style={{

                                        background: 'var(--bg-tertiary)',

                                        borderRadius: '12px',

                                        padding: '1rem',

                                        flex: 1,

                                    }}>

                                        <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>
                                            Kết quả phân tích
                                        </h4>



                                        <div style={{ display: 'grid', gap: '1rem' }}>



                                            {/*  PHONG C??CH VĂN A - StyleA Display - 2 GROUPS  */}

                                            {styleA && (

                                                <div style={{

                                                    background: 'linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(245, 158, 11, 0.1))',

                                                    borderRadius: '12px',

                                                    padding: '1rem',

                                                    border: '2px solid rgba(255, 215, 0, 0.3)'

                                                }}>





                                                    {/*  */}

                                                    {/* GROUP 1: DNA CỐ ĐỊNH - Không thay đổi theo kịch bản */}

                                                    {/*  */}

                                                    <div style={{

                                                        marginBottom: '1rem',

                                                        padding: '1rem',

                                                        background: 'rgba(99, 102, 241, 0.05)',

                                                        borderRadius: '12px',

                                                        border: '1px solid rgba(99, 102, 241, 0.2)'

                                                    }}>

                                                        <h5 style={{

                                                            margin: '0 0 1rem 0',

                                                            display: 'flex',

                                                            alignItems: 'center',

                                                            gap: '0.5rem',

                                                            color: 'var(--primary)',

                                                            fontSize: '0.95rem'

                                                        }}>

                                                            ĐẶC TRƯNG CỐ ĐỊNH

                                                            <span style={{

                                                                fontSize: '0.7rem',

                                                                fontWeight: 'normal',

                                                                opacity: 0.7

                                                            }}>(DNA của style - áp dụng cho mọi kịch bản)</span>

                                                        </h5>



                                                        <div style={{ display: 'grid', gap: '0.75rem' }}>

                                                            {/* Voice Description */}

                                                            {styleA.voice_description && (

                                                                <div style={{

                                                                    padding: '0.75rem',

                                                                    background: 'rgba(99, 102, 241, 0.1)',

                                                                    borderRadius: '8px',

                                                                    borderLeft: '4px solid #6366f1'

                                                                }}>

                                                                    <strong> Giọng văn:</strong>

                                                                    <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>{styleA.voice_description}</p>

                                                                </div>

                                                            )}



                                                            {/* Storytelling Approach */}

                                                            {styleA.storytelling_approach && (

                                                                <div style={{

                                                                    padding: '0.75rem',

                                                                    background: 'rgba(168, 85, 247, 0.1)',

                                                                    borderRadius: '8px',

                                                                    borderLeft: '4px solid #a855f7'

                                                                }}>

                                                                    <strong> Cách dẫn chuyện:</strong>

                                                                    <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>{styleA.storytelling_approach}</p>

                                                                </div>

                                                            )}



                                                            {/* Author's Soul */}

                                                            {styleA.authors_soul && (

                                                                <div style={{

                                                                    padding: '0.75rem',

                                                                    background: 'linear-gradient(135deg, rgba(234, 179, 8, 0.1), rgba(249, 115, 22, 0.1))',

                                                                    borderRadius: '8px',

                                                                    borderLeft: '4px solid #f59e0b'

                                                                }}>

                                                                    <strong> HỒN VĂN (Author's Soul):</strong>

                                                                    <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>{styleA.authors_soul}</p>

                                                                </div>

                                                            )}



                                                            {/* Technical Patterns Grid - CONSOLIDATED */}

                                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.5rem' }}>

                                                                {styleA.common_hook_types?.length > 0 && (

                                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>

                                                                        <strong style={{ fontSize: '0.8rem' }}> HOOK patterns:</strong>

                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.25rem' }}>

                                                                            {styleA.common_hook_types.map((h: string, i: number) => (

                                                                                <span key={i} style={{

                                                                                    fontSize: '0.75rem',

                                                                                    background: 'rgba(234, 179, 8, 0.2)',

                                                                                    padding: '0.15rem 0.4rem',

                                                                                    borderRadius: '4px'

                                                                                }}>{h}</span>

                                                                            ))}

                                                                        </div>

                                                                    </div>

                                                                )}



                                                                {styleA.retention_techniques?.length > 0 && (

                                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>

                                                                        <strong style={{ fontSize: '0.8rem' }}> Retention patterns:</strong>

                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.25rem' }}>

                                                                            {styleA.retention_techniques.map((r: string, i: number) => (

                                                                                <span key={i} style={{

                                                                                    fontSize: '0.75rem',

                                                                                    background: 'rgba(34, 197, 94, 0.2)',

                                                                                    padding: '0.15rem 0.4rem',

                                                                                    borderRadius: '4px'

                                                                                }}>{r}</span>

                                                                            ))}

                                                                        </div>

                                                                    </div>

                                                                )}



                                                                {styleA.cta_patterns?.length > 0 && (

                                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>

                                                                        <strong style={{ fontSize: '0.8rem' }}> CTA patterns:</strong>

                                                                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.25rem' }}>

                                                                            {styleA.cta_patterns.map((c: string, i: number) => (

                                                                                <span key={i} style={{

                                                                                    fontSize: '0.75rem',

                                                                                    background: 'rgba(59, 130, 246, 0.2)',

                                                                                    padding: '0.15rem 0.4rem',

                                                                                    borderRadius: '4px'

                                                                                }}>{c}</span>

                                                                            ))}

                                                                        </div>

                                                                    </div>

                                                                )}

                                                            </div>



                                                            {/* Style Characteristics - DNA only (no narrative voice/audience) */}

                                                            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '0.5rem', fontSize: '0.85rem' }}>

                                                                {styleA.tone_spectrum && (

                                                                    <div><strong> Tone:</strong> {styleA.tone_spectrum}</div>

                                                                )}

                                                                {styleA.vocabulary_signature && (

                                                                    <div><strong> Từ vựng:</strong> {styleA.vocabulary_signature}</div>

                                                                )}

                                                                {styleA.emotional_palette && (

                                                                    <div><strong> Cảm xúc:</strong> {styleA.emotional_palette}</div>

                                                                )}

                                                                {styleA.script_structure && (

                                                                    <div style={{ marginTop: '0.5rem', padding: '0.5rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '6px' }}>

                                                                        <strong> Nhịp văn/Cấu trúc:</strong>

                                                                        <div style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>

                                                                            {styleA.script_structure.avg_word_count > 0 && <div>• Số từ trung bình: {styleA.script_structure.avg_word_count}</div>}

                                                                            {styleA.script_structure.hook_duration && <div>• Hook: {styleA.script_structure.hook_duration}</div>}

                                                                            {styleA.script_structure.structure_breakdown?.intro?.segments > 0 && <div>• Mở bài: {styleA.script_structure.structure_breakdown.intro.segments} đoạn - {styleA.script_structure.structure_breakdown.intro.purpose}</div>}

                                                                            {styleA.script_structure.structure_breakdown?.body?.segments > 0 && <div>• Thân bài: {styleA.script_structure.structure_breakdown.body.segments} đoạn - {styleA.script_structure.structure_breakdown.body.purpose}</div>}

                                                                            {styleA.script_structure.structure_breakdown?.conclusion?.segments > 0 && <div>• Kết bài: {styleA.script_structure.structure_breakdown.conclusion.segments} đoạn - {styleA.script_structure.structure_breakdown.conclusion.purpose}</div>}

                                                                            {styleA.script_structure.climax_position && <div>• Cao trào: {styleA.script_structure.climax_position}</div>}

                                                                        </div>

                                                                    </div>

                                                                )}

                                                            </div>



                                                            {/* Signature Phrases */}

                                                            {styleA.signature_phrases?.length > 0 && (

                                                                <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>

                                                                    <strong style={{ fontSize: '0.85rem' }}> Cụm từ đặc trưng:</strong>

                                                                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.25rem', marginTop: '0.25rem' }}>

                                                                        {styleA.signature_phrases.map((p: string, i: number) => (

                                                                            <span key={i} style={{

                                                                                fontSize: '0.8rem',

                                                                                background: 'rgba(99, 102, 241, 0.2)',

                                                                                padding: '0.2rem 0.5rem',

                                                                                borderRadius: '4px',

                                                                                fontStyle: 'italic'

                                                                            }}>"{p}"</span>

                                                                        ))}

                                                                    </div>

                                                                </div>

                                                            )}

                                                        </div>

                                                    </div>

                                                </div>

                                            )}



                                            {/*  */}

                                            {/* CONTENT-SPECIFIC ANALYSIS - Only show if originalAnalysis exists */}

                                            {/*  */}

                                            {originalAnalysis && (originalAnalysis.core_angle || originalAnalysis.viewer_insight || originalAnalysis.main_ideas?.length > 0) && (

                                                <div style={{

                                                    padding: '1rem',

                                                    background: 'rgba(34, 197, 94, 0.05)',

                                                    borderRadius: '12px',

                                                    border: '1px solid rgba(34, 197, 94, 0.2)'

                                                }}>

                                                    <h5 style={{

                                                        margin: '0 0 1rem 0',

                                                        display: 'flex',

                                                        alignItems: 'center',

                                                        gap: '0.5rem',

                                                        color: 'var(--accent-cyan)',

                                                        fontSize: '0.95rem'

                                                    }}>

                                                        PHÂN TÍCH NỘI DUNG

                                                        <span style={{

                                                            fontSize: '0.7rem',

                                                            fontWeight: 'normal',

                                                            opacity: 0.7

                                                        }}>(Từ các kịch bản mẫu)</span>

                                                    </h5>



                                                    <div style={{ display: 'grid', gap: '0.75rem' }}>

                                                        {/* Core Angle */}

                                                        {originalAnalysis.core_angle && (

                                                            <div style={{

                                                                padding: '0.75rem',

                                                                background: 'rgba(99, 102, 241, 0.1)',

                                                                borderRadius: '8px',

                                                                borderLeft: '4px solid #6366f1'

                                                            }}>

                                                                <strong> Core Angle (Góc nhìn cốt lõi):</strong>

                                                                <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>{originalAnalysis.core_angle}</p>

                                                            </div>

                                                        )}



                                                        {/* Viewer Insight */}

                                                        {originalAnalysis.viewer_insight && (

                                                            <div style={{

                                                                padding: '0.75rem',

                                                                background: 'rgba(168, 85, 247, 0.1)',

                                                                borderRadius: '8px',

                                                                borderLeft: '4px solid #a855f7'

                                                            }}>

                                                                <strong> INSIGHT người xem:</strong>

                                                                <p style={{ margin: '0.5rem 0 0', fontSize: '0.9rem' }}>{originalAnalysis.viewer_insight}</p>

                                                            </div>

                                                        )}



                                                        {/* Main Ideas */}

                                                        {originalAnalysis.main_ideas?.length > 0 && (

                                                            <div style={{ padding: '0.75rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>

                                                                <strong> Ý chính quan trọng:</strong>

                                                                <ul style={{ margin: '0.5rem 0 0', paddingLeft: '1.5rem', fontSize: '0.9rem' }}>

                                                                    {originalAnalysis.main_ideas.map((idea: string, i: number) => (

                                                                        <li key={i}>{idea}</li>

                                                                    ))}

                                                                </ul>

                                                            </div>

                                                        )}

                                                    </div>

                                                </div>

                                            )}

                                        </div>

                                    </div>

                                )}

                                {/* ═══ TITLE STYLE ANALYSIS RESULT ═══ */}
                                {titleStyleAnalysis && (
                                    <div style={{
                                        background: 'linear-gradient(135deg, rgba(6, 182, 212, 0.08), rgba(59, 130, 246, 0.08))',
                                        borderRadius: '12px',
                                        padding: '1rem',
                                        border: '1px solid rgba(6, 182, 212, 0.3)',
                                        marginTop: '1rem'
                                    }}>
                                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', color: '#06b6d4', fontWeight: 600 }}>
                                            Phong cách Tiêu đề
                                        </h4>
                                        <div style={{ display: 'grid', gap: '0.6rem' }}>
                                            {titleStyleAnalysis.style_summary && (
                                                <div style={{ padding: '0.6rem', background: 'rgba(6, 182, 212, 0.1)', borderRadius: '8px', borderLeft: '3px solid #06b6d4' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Tóm tắt:</strong>
                                                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem' }}>{titleStyleAnalysis.style_summary}</p>
                                                </div>
                                            )}
                                            {titleStyleAnalysis.title_formulas?.length > 0 && (
                                                <div style={{ padding: '0.6rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Công thức Title:</strong>
                                                    <ul style={{ margin: '0.3rem 0 0', paddingLeft: '1.25rem', fontSize: '0.85rem' }}>
                                                        {titleStyleAnalysis.title_formulas.map((f: string, i: number) => (
                                                            <li key={i}>{f}</li>
                                                        ))}
                                                    </ul>
                                                </div>
                                            )}
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                                {titleStyleAnalysis.dominant_hooks?.map((h: string, i: number) => (
                                                    <span key={i} style={{ fontSize: '0.75rem', background: 'rgba(6, 182, 212, 0.15)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: '#06b6d4' }}>{h}</span>
                                                ))}
                                                {titleStyleAnalysis.power_words?.map((w: string, i: number) => (
                                                    <span key={`pw-${i}`} style={{ fontSize: '0.75rem', background: 'rgba(59, 130, 246, 0.15)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: '#3b82f6' }}>{w}</span>
                                                ))}
                                            </div>
                                            {titleStyleAnalysis.emotional_tone && (
                                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                    <strong>Tone:</strong> {titleStyleAnalysis.emotional_tone}
                                                    {titleStyleAnalysis.avg_length && <> · <strong>Avg:</strong> {titleStyleAnalysis.avg_length} ký tự</>}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* ═══ DESCRIPTION STYLE ANALYSIS RESULT ═══ */}
                                {descriptionStyleAnalysis && (
                                    <div style={{
                                        background: 'linear-gradient(135deg, rgba(34, 197, 94, 0.08), rgba(16, 185, 129, 0.08))',
                                        borderRadius: '12px',
                                        padding: '1rem',
                                        border: '1px solid rgba(34, 197, 94, 0.3)',
                                        marginTop: '1rem'
                                    }}>
                                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', color: '#22c55e', fontWeight: 600 }}>
                                            Phong cách Mô tả
                                        </h4>
                                        <div style={{ display: 'grid', gap: '0.6rem' }}>
                                            {descriptionStyleAnalysis.style_summary && (
                                                <div style={{ padding: '0.6rem', background: 'rgba(34, 197, 94, 0.1)', borderRadius: '8px', borderLeft: '3px solid #22c55e' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Tóm tắt:</strong>
                                                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem' }}>{descriptionStyleAnalysis.style_summary}</p>
                                                </div>
                                            )}
                                            {descriptionStyleAnalysis.hook_style && (
                                                <div style={{ padding: '0.6rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Hook Style:</strong>
                                                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem' }}>{descriptionStyleAnalysis.hook_style}</p>
                                                </div>
                                            )}
                                            {descriptionStyleAnalysis.structure_template && (
                                                <div style={{ padding: '0.6rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Cấu trúc mẫu:</strong>
                                                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem', whiteSpace: 'pre-line' }}>{descriptionStyleAnalysis.structure_template}</p>
                                                </div>
                                            )}
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                {descriptionStyleAnalysis.body_style?.writing_approach && (
                                                    <span>{descriptionStyleAnalysis.body_style.writing_approach}</span>
                                                )}
                                                {descriptionStyleAnalysis.uses_timestamps !== undefined && (
                                                    <span>{descriptionStyleAnalysis.uses_timestamps ? 'Có timestamps' : 'Không timestamps'}</span>
                                                )}
                                                {descriptionStyleAnalysis.cta_position && (
                                                    <span>CTA: {descriptionStyleAnalysis.cta_position}</span>
                                                )}
                                                {descriptionStyleAnalysis.hashtag_strategy?.avg_count && (
                                                    <span>~{descriptionStyleAnalysis.hashtag_strategy.avg_count} hashtags</span>
                                                )}
                                            </div>
                                            {descriptionStyleAnalysis.brand_voice?.tone && (
                                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                                                    <strong>Brand Voice:</strong> {descriptionStyleAnalysis.brand_voice.tone}
                                                    {descriptionStyleAnalysis.brand_voice.addressing && <> · Xưng hô: {descriptionStyleAnalysis.brand_voice.addressing}</>}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                )}

                                {/* ═══ THUMBNAIL STYLE ANALYSIS RESULT ═══ */}
                                {thumbnailStyleAnalysis && (
                                    <div style={{
                                        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.08), rgba(139, 92, 246, 0.08))',
                                        borderRadius: '12px',
                                        padding: '1rem',
                                        border: '1px solid rgba(168, 85, 247, 0.3)',
                                        marginTop: '1rem'
                                    }}>
                                        <h4 style={{ margin: '0 0 0.75rem', fontSize: '0.95rem', color: '#a855f7', fontWeight: 600 }}>
                                            Phong cách Thumbnail
                                        </h4>
                                        <div style={{ display: 'grid', gap: '0.6rem' }}>
                                            {thumbnailStyleAnalysis.style_summary && (
                                                <div style={{ padding: '0.6rem', background: 'rgba(168, 85, 247, 0.1)', borderRadius: '8px', borderLeft: '3px solid #a855f7' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Tóm tắt:</strong>
                                                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem' }}>{thumbnailStyleAnalysis.style_summary}</p>
                                                </div>
                                            )}
                                            {thumbnailStyleAnalysis.thumbnail_formula && (
                                                <div style={{ padding: '0.6rem', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
                                                    <strong style={{ fontSize: '0.8rem' }}>Công thức Thumbnail:</strong>
                                                    <p style={{ margin: '0.3rem 0 0', fontSize: '0.85rem' }}>{thumbnailStyleAnalysis.thumbnail_formula}</p>
                                                </div>
                                            )}
                                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem' }}>
                                                {thumbnailStyleAnalysis.composition?.layout && (
                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem' }}>
                                                        <strong>Bố cục:</strong> {thumbnailStyleAnalysis.composition.layout}
                                                    </div>
                                                )}
                                                {thumbnailStyleAnalysis.color_scheme?.contrast_style && (
                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem' }}>
                                                        <strong>Tương phản:</strong> {thumbnailStyleAnalysis.color_scheme.contrast_style}
                                                    </div>
                                                )}
                                                {thumbnailStyleAnalysis.overall_style && (
                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem' }}>
                                                        <strong>Style:</strong> {thumbnailStyleAnalysis.overall_style}
                                                    </div>
                                                )}
                                                {thumbnailStyleAnalysis.emotional_signals?.dominant_emotion && (
                                                    <div style={{ padding: '0.5rem', background: 'var(--bg-secondary)', borderRadius: '6px', fontSize: '0.8rem' }}>
                                                        <strong>Emotion:</strong> {thumbnailStyleAnalysis.emotional_signals.dominant_emotion}
                                                    </div>
                                                )}
                                            </div>
                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                                {thumbnailStyleAnalysis.color_scheme?.dominant_colors?.map((c: string, i: number) => (
                                                    <span key={i} style={{ fontSize: '0.75rem', background: 'rgba(168, 85, 247, 0.15)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: '#a855f7' }}>{c}</span>
                                                ))}
                                                {thumbnailStyleAnalysis.storytelling_techniques?.map((t: string, i: number) => (
                                                    <span key={`st-${i}`} style={{ fontSize: '0.75rem', background: 'rgba(139, 92, 246, 0.15)', padding: '0.2rem 0.5rem', borderRadius: '6px', color: '#8b5cf6' }}>{t}</span>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                )}



                                {/* 4-Panel Analysis Progress Display */}
                                {(() => {
                                    const hasAnyResult = styleA || originalAnalysis || titleStyleAnalysis || descriptionStyleAnalysis || thumbnailStyleAnalysis || syncAnalysisResult;
                                    const isRunning = isAnalyzingStyle;
                                    const hasAnyProgress = voiceProgress.status !== 'idle' || titleProgress.status !== 'idle' || descProgress.status !== 'idle' || thumbProgress.status !== 'idle' || syncProgress.status !== 'idle';

                                    // Show panel grid when: analysis is running, OR initial empty state (no results)
                                    // Hide when results are available (after analysis completes) to show detailed results instead
                                    if (isRunning || (!hasAnyResult && !isRunning)) {
                                        // Panel configuration
                                        const panels = [
                                            { key: 'voice', label: 'Giọng văn', color: '#FFD700', bgFrom: 'rgba(255, 215, 0, 0.06)', bgTo: 'rgba(245, 158, 11, 0.06)', borderColor: 'rgba(255, 215, 0, 0.3)', progress: voiceProgress, result: styleA },
                                            { key: 'title', label: 'Tiêu đề', color: '#3B82F6', bgFrom: 'rgba(59, 130, 246, 0.06)', bgTo: 'rgba(96, 165, 250, 0.06)', borderColor: 'rgba(59, 130, 246, 0.3)', progress: titleProgress, result: titleStyleAnalysis },
                                            { key: 'desc', label: 'Mô tả', color: '#22C55E', bgFrom: 'rgba(34, 197, 94, 0.06)', bgTo: 'rgba(74, 222, 128, 0.06)', borderColor: 'rgba(34, 197, 94, 0.3)', progress: descProgress, result: descriptionStyleAnalysis },
                                            { key: 'thumb', label: 'Thumbnail', color: '#A855F7', bgFrom: 'rgba(168, 85, 247, 0.06)', bgTo: 'rgba(192, 132, 252, 0.06)', borderColor: 'rgba(168, 85, 247, 0.3)', progress: thumbProgress, result: thumbnailStyleAnalysis },
                                            ...(syncProgress.status !== 'idle' || (analysisOpts.syncCharacter || analysisOpts.syncStyle || analysisOpts.syncContext) ? [{ key: 'sync', label: 'Sync', color: '#EC4899', bgFrom: 'rgba(236, 72, 153, 0.06)', bgTo: 'rgba(244, 114, 182, 0.06)', borderColor: 'rgba(236, 72, 153, 0.3)', progress: syncProgress, result: syncAnalysisResult }] : []),
                                        ];

                                        return (
                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1 }}>
                                                {/* Timer row */}
                                                {isRunning && (
                                                    <div style={{ textAlign: 'center', fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '0.25rem 0' }}>
                                                        Đang phân tích... {analysisTimer}s
                                                    </div>
                                                )}
                                                {panels.map(p => {
                                                    const { status, pct, msg } = p.progress;
                                                    const isIdle = status === 'idle';
                                                    const isDone = status === 'done';
                                                    const isActive = status === 'running';

                                                    return (
                                                        <div key={p.key} style={{
                                                            background: isIdle
                                                                ? 'var(--bg-tertiary)'
                                                                : `linear-gradient(135deg, ${p.bgFrom} 0%, ${p.bgTo} 100%)`,
                                                            border: `1px solid ${isIdle ? 'rgba(255,255,255,0.06)' : p.borderColor}`,
                                                            borderRadius: '10px',
                                                            padding: '0.6rem 0.75rem',
                                                            opacity: isIdle ? 0.5 : 1,
                                                            transition: 'all 0.3s ease',
                                                            flex: isActive ? '1.2' : '1',
                                                            minHeight: 0,
                                                            display: 'flex',
                                                            flexDirection: 'column',
                                                            justifyContent: 'center',
                                                        }}>
                                                            {/* Header row */}
                                                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: isActive ? '0.4rem' : 0 }}>
                                                                <span style={{ fontSize: '0.8rem', fontWeight: 600, color: isIdle ? 'var(--text-secondary)' : p.color }}>
                                                                    {p.label}
                                                                </span>
                                                                <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
                                                                    {isDone && <CheckCircle size={14} style={{ color: p.color }} />}
                                                                    {isActive && <Loader2 size={14} className="spin" style={{ color: p.color }} />}
                                                                    {isIdle && !isRunning && 'Chưa có dữ liệu'}
                                                                    {isIdle && isRunning && '—'}
                                                                </span>
                                                            </div>
                                                            {/* Progress bar */}
                                                            {isActive && (
                                                                <>
                                                                    <div style={{ height: '4px', background: 'rgba(255,255,255,0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                                                                        <div style={{
                                                                            height: '100%',
                                                                            width: `${pct}%`,
                                                                            background: `linear-gradient(90deg, ${p.color}, ${p.color}cc)`,
                                                                            borderRadius: '2px',
                                                                            transition: 'width 0.4s ease',
                                                                        }} />
                                                                    </div>
                                                                    <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '0.3rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                                        {msg.replace(/[\u{1F300}-\u{1F9FF}\u{2600}-\u{27BF}\u{1F600}-\u{1F64F}\u{1F680}-\u{1F6FF}\u{2702}-\u{27B0}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}]/gu, '').trim()}
                                                                    </div>
                                                                </>
                                                            )}
                                                            {/* Done summary */}
                                                            {isDone && (
                                                                <div style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', marginTop: '0.2rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                                                    {p.result?.style_summary || msg || (p.key === 'voice' ? 'Phân tích hoàn tất' : 'Hoàn tất')}
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        );
                                    }
                                    return null;
                                })()}

                            </div>

                            {/* ═══ LOWER PANEL: Sync Analysis Summary ═══ */}
                            {(() => {
                                const hasSync = analysisOpts.syncCharacter || analysisOpts.syncStyle || analysisOpts.syncContext;
                                if (!hasSync) return null;
                                const vMode = pipelineSelection?.videoProduction?.video_prompt_mode;
                                const badgeLabel = vMode === 'character_sync' ? 'Character' : vMode === 'scene_sync' ? 'Style' : 'Full Sync';

                                const syncSections = [
                                    { key: 'character', label: 'Nhân vật', enabled: analysisOpts.syncCharacter, text: mainCharacter, images: syncCharacterImages },
                                    { key: 'style', label: 'Phong cách', enabled: analysisOpts.syncStyle, text: promptStyle, images: syncStyleImages },
                                    { key: 'context', label: 'Bối cảnh', enabled: analysisOpts.syncContext, text: contextDescription, images: syncContextImages },
                                ];

                                return (
                                    <div style={{
                                        background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.08), rgba(139, 92, 246, 0.04))',
                                        borderRadius: '12px', padding: '1rem',
                                        border: '1px solid rgba(168, 85, 247, 0.25)',
                                    }}>
                                        <h4 style={{ margin: '0 0 0.75rem', fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
                                            Sync Analysis
                                            <span style={{
                                                marginLeft: '0.4rem', fontSize: '0.65rem',
                                                background: 'rgba(168, 85, 247, 0.15)', color: '#A855F7',
                                                padding: '0.15rem 0.5rem', borderRadius: '12px',
                                            }}>
                                                {badgeLabel}
                                            </span>
                                        </h4>
                                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                                            {syncSections.filter(s => s.enabled).map(s => {
                                                const hasContent = s.text || s.images.length > 0;
                                                const sectionId = `sync-expand-${s.key}`;
                                                return (
                                                    <div key={s.key} style={{
                                                        background: hasContent ? 'rgba(255,255,255,0.03)' : 'var(--bg-tertiary)',
                                                        borderRadius: '8px', padding: '0.6rem 0.8rem',
                                                        border: hasContent ? 'none' : '1px solid rgba(255,255,255,0.06)',
                                                        opacity: hasContent ? 1 : 0.6,
                                                    }}>
                                                        <div
                                                            style={{
                                                                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                                                                cursor: hasContent ? 'pointer' : 'default',
                                                            }}
                                                            onClick={() => {
                                                                if (!hasContent) return;
                                                                const contentEl = document.getElementById(sectionId);
                                                                if (contentEl) {
                                                                    const wasExpanded = contentEl.style.maxHeight !== '0px';
                                                                    contentEl.style.maxHeight = wasExpanded ? '0px' : '2000px';
                                                                    contentEl.style.opacity = wasExpanded ? '0' : '1';
                                                                    contentEl.style.marginTop = wasExpanded ? '0' : '0.25rem';
                                                                    // Toggle chevron
                                                                    const chevron = contentEl.previousElementSibling?.querySelector('.sync-chevron') as HTMLElement;
                                                                    if (chevron) chevron.style.transform = wasExpanded ? 'rotate(-90deg)' : 'rotate(0deg)';
                                                                }
                                                            }}
                                                        >
                                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                                                                {hasContent && (
                                                                    <span className="sync-chevron" style={{ fontSize: '0.65rem', color: '#A855F7', transition: 'transform 0.2s', display: 'inline-block' }}>▼</span>
                                                                )}
                                                                <div style={{ fontSize: '0.7rem', fontWeight: 600, color: '#A855F7', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{s.label}</div>
                                                            </div>
                                                            {!hasContent && (
                                                                <span style={{ fontSize: '0.7rem', color: 'var(--text-tertiary)' }}>Chưa nhập dữ liệu</span>
                                                            )}
                                                        </div>
                                                        <div id={sectionId} style={{
                                                            maxHeight: '2000px', overflow: 'hidden',
                                                            transition: 'max-height 0.3s ease, opacity 0.3s ease, margin-top 0.2s ease',
                                                            opacity: 1, marginTop: hasContent ? '0.25rem' : '0',
                                                        }}>
                                                            {s.text && <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.4, whiteSpace: 'pre-wrap' }}>{s.text}</div>}
                                                            {s.images.length > 0 && (
                                                                <div style={{ display: 'flex', gap: '0.3rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
                                                                    {s.images.map((src, i) => <img key={i} src={src} alt={`${s.key}-${i}`} style={{ width: '40px', height: '40px', objectFit: 'cover', borderRadius: '6px', border: '1px solid rgba(168,85,247,0.3)' }} />)}
                                                                </div>
                                                            )}
                                                        </div>
                                                    </div>
                                                );
                                            })}
                                        </div>
                                    </div>
                                );
                            })()}

                        </div>



                    </div>

                    {/* Navigation Buttons */}

                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem', paddingTop: '1rem', borderTop: '1px solid var(--border-color)' }}>

                        {/* Save Voice Style Button — hide after saved */}

                        {!styleSaved && (

                            <button

                                type="button"

                                className="btn btn-secondary"

                                onClick={() => setShowSaveDialog(true)}

                                disabled={!styleA && !originalAnalysis}

                                style={{

                                    display: 'flex',

                                    alignItems: 'center',

                                    gap: '0.5rem',

                                    padding: '0.6rem 1.25rem',

                                    borderRadius: '12px',

                                    border: '1px solid rgba(34, 197, 94, 0.4)',

                                    background: 'rgba(34, 197, 94, 0.1)',

                                    color: '#22c55e',

                                    cursor: (!styleA && !originalAnalysis) ? 'not-allowed' : 'pointer',

                                    fontWeight: 600,

                                    fontSize: '0.9rem',

                                    opacity: (!styleA && !originalAnalysis) ? 0.5 : 1,

                                    transition: 'all 0.3s',

                                }}

                            >

                                <Save size={16} /> Lưu giọng văn

                            </button>

                        )}

                        {/* Stop button - shown during analysis, next to Save */}
                        {isAnalyzingStyle && (
                            <button
                                className="btn btn-danger btn-sm"
                                onClick={handleStopAnalysis}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem',
                                    padding: '0.6rem 1.25rem',
                                    borderRadius: '12px',
                                    background: 'linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)',
                                    color: '#fff',
                                    fontWeight: 600,
                                    fontSize: '0.9rem',
                                    border: 'none',
                                    cursor: 'pointer',
                                }}
                            >
                                <XCircle size={16} /> Dừng
                            </button>
                        )}



                        {/* Success indicator */}

                        {styleSaved && (

                            <span style={{

                                display: 'flex',

                                alignItems: 'center',

                                gap: '0.35rem',

                                color: '#22c55e',

                                fontSize: '0.85rem',

                                fontWeight: 600,

                            }}>

                                <CheckCircle size={14} /> Đã lưu "{styleSaved}"

                            </span>

                        )}



                        {(() => {
                            const voiceCount = referenceScripts.length + (referenceScript.length >= 50 ? 1 : 0);
                            const titleCount = analysisOpts.title ? titleSamples.length : 0;
                            const descCount = analysisOpts.description ? descriptionSamples.length : 0;
                            const thumbCount = analysisOpts.thumbnail ? thumbnailFiles.length : 0;
                            const hasAnySamples = voiceCount > 0 || titleCount > 0 || descCount > 0 || thumbCount > 0;

                            // Build summary chips
                            const chips: string[] = [];
                            if (voiceCount > 0) chips.push(`${voiceCount} giọng văn`);
                            if (titleCount > 0) chips.push(`${titleCount} title`);
                            if (descCount > 0) chips.push(`${descCount} desc`);
                            if (thumbCount > 0) chips.push(`${thumbCount} ảnh`);

                            if (isAnalyzingStyle) return (
                                <button type="button" className="btn btn-primary" disabled style={{ background: 'var(--gradient-primary)', color: '#0a0a0a', fontWeight: 700, opacity: 0.9, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '2px', padding: '0.5rem 1.5rem' }}>
                                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                        <Loader2 size={16} className="spin" /> Đang phân tích ({analysisTimer}s)...
                                    </span>
                                    {analysisProgress && <span style={{ fontSize: '0.7rem', opacity: 0.8 }}>{analysisProgress}</span>}
                                </button>
                            );
                            if (styleA || originalAnalysis || titleStyleAnalysis || descriptionStyleAnalysis || thumbnailStyleAnalysis) return (
                                <>
                                    <button
                                        type="button"
                                        className="btn btn-secondary"
                                        onClick={() => {
                                            if (referenceScript.length >= 50) {
                                                setReferenceScripts([...referenceScripts, referenceScript]);
                                                setReferenceScript('');
                                            }
                                            handleAnalyzeMultipleStyles();
                                        }}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.5rem',
                                            padding: '0.6rem 1.25rem',
                                            borderRadius: '12px',
                                            border: '1px solid rgba(245, 158, 11, 0.4)',
                                            background: 'rgba(245, 158, 11, 0.1)',
                                            color: '#f59e0b',
                                            cursor: 'pointer',
                                            fontWeight: 600,
                                            fontSize: '0.9rem',
                                            transition: 'all 0.3s',
                                        }}
                                    >
                                        <Zap size={16} /> Phân tích lại
                                    </button>
                                    <button type="button" className="btn btn-primary" onClick={() => setAdvancedStep(2)} style={{ background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', color: '#fff', fontWeight: 700 }}>
                                        <CheckCircle size={16} /> Tiếp tục bước tiếp theo
                                    </button>
                                </>
                            );
                            return (
                                <button
                                    type="button"
                                    className="btn btn-primary"
                                    onClick={() => {
                                        if (referenceScript.length >= 50) {
                                            setReferenceScripts([...referenceScripts, referenceScript]);
                                            setReferenceScript('');
                                        }
                                        handleAnalyzeMultipleStyles();
                                    }}
                                    disabled={!hasAnySamples}
                                    style={{ background: 'var(--gradient-primary)', color: '#0a0a0a', fontWeight: 700 }}
                                >
                                    {hasAnySamples
                                        ? `Phân tích toàn bộ (${chips.join(', ')})`
                                        : 'Phân tích toàn bộ'}
                                </button>
                            );
                        })()}

                    </div>



                    {/* Save Voice Style Dialog */}

                    {showSaveDialog && (

                        <div style={{

                            position: 'fixed',

                            inset: 0,

                            background: 'rgba(0,0,0,0.6)',

                            display: 'flex',

                            alignItems: 'center',

                            justifyContent: 'center',

                            zIndex: 9999,

                        }}

                            onClick={() => setShowSaveDialog(false)}

                        >

                            <div

                                style={{

                                    background: 'var(--bg-primary)',

                                    borderRadius: '16px',

                                    padding: '1.5rem',

                                    width: '400px',

                                    maxWidth: '90vw',

                                    boxShadow: '0 20px 60px rgba(0,0,0,0.4)',

                                    border: '1px solid var(--border-color)',

                                }}

                                onClick={e => e.stopPropagation()}

                            >

                                <h3 style={{ margin: '0 0 1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>

                                    <Save size={20} /> Lưu giọng văn

                                </h3>

                                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', margin: '0 0 1rem' }}>

                                    Đặt tên cho giọng văn đã phân tích để sử dụng lại sau này

                                </p>

                                <input

                                    type="text"

                                    className="input"

                                    placeholder="VD: Giọng văn podcast công nghệ..."

                                    value={styleName}

                                    onChange={e => setStyleName(e.target.value)}

                                    onKeyDown={e => e.key === 'Enter' && handleSaveStyle()}

                                    autoFocus

                                    style={{

                                        width: '100%',

                                        padding: '0.75rem 1rem',

                                        borderRadius: '10px',

                                        border: '1px solid var(--border-color)',

                                        background: 'var(--bg-secondary)',

                                        color: 'var(--text-primary)',

                                        fontSize: '0.9rem',

                                        marginBottom: '1rem',

                                    }}

                                />

                                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>

                                    <button

                                        type="button"

                                        onClick={() => { setShowSaveDialog(false); setStyleName(''); }}

                                        style={{

                                            padding: '0.6rem 1.25rem',

                                            borderRadius: '10px',

                                            border: '1px solid var(--border-color)',

                                            background: 'var(--bg-secondary)',

                                            color: 'var(--text-secondary)',

                                            cursor: 'pointer',

                                            fontWeight: 600,

                                        }}

                                    >

                                        Hủy

                                    </button>

                                    <button

                                        type="button"

                                        onClick={handleSaveStyle}

                                        disabled={!styleName.trim() || isSavingStyle}

                                        style={{

                                            padding: '0.6rem 1.25rem',

                                            borderRadius: '10px',

                                            border: 'none',

                                            background: isSavingStyle ? 'var(--bg-tertiary)' : 'linear-gradient(135deg, #22c55e, #16a34a)',

                                            color: 'white',

                                            cursor: (!styleName.trim() || isSavingStyle) ? 'not-allowed' : 'pointer',

                                            fontWeight: 600,

                                            display: 'flex',

                                            alignItems: 'center',

                                            gap: '0.4rem',

                                            opacity: (!styleName.trim() || isSavingStyle) ? 0.6 : 1,

                                        }}

                                    >

                                        {isSavingStyle ? (

                                            <><Loader2 size={14} className="spin" /> Đang lưu...</>

                                        ) : (

                                            <><Save size={14} /> Lưu</>

                                        )}

                                    </button>

                                </div>

                            </div>

                        </div>

                    )}

                </div>

            )}





            {/*  */}

            {/* STEPS 2+: QUEUE VIEW (Sidebar + Panel) */}

            {/*  */}

            {advancedStep >= 2 && (

                <QueueView

                    styleA={styleA}

                    originalAnalysis={originalAnalysis}

                    advancedSettings={advancedSettings}

                    splitMode={splitMode}

                    sceneMode={sceneMode}

                    selectedVoice={selectedVoice}

                    voiceLanguage={voiceLanguage}

                    voiceSpeed={voiceSpeed}

                    selectedModel={selectedModel}

                    pipelineSelection={pipelineSelection}

                    footageOrientation={footageOrientation}

                    videoQuality={videoQuality}

                    enableSubtitles={enableSubtitles}

                    promptStyle={promptStyle}

                    mainCharacter={mainCharacter}

                    contextDescription={contextDescription}

                    setAdvancedStep={setAdvancedStep}

                    setError={setError}

                    activeProjectId={activeProjectId}

                    titleSamples={titleSamples}

                    descriptionSamples={descriptionSamples}

                    titleStyleAnalysis={titleStyleAnalysis}

                    descriptionStyleAnalysis={descriptionStyleAnalysis}

                    thumbnailStyleAnalysis={thumbnailStyleAnalysis}

                    syncAnalysisResult={syncAnalysisResult}

                />

            )}

        </div >

    );

}

// ──────────────────────────────────────────

// Queue View Component (replaces Steps 2-3 wizard)

// ──────────────────────────────────────────

function QueueView({

    styleA,

    originalAnalysis,

    advancedSettings,

    splitMode,

    sceneMode,

    selectedVoice,

    voiceLanguage,

    voiceSpeed,

    selectedModel,

    pipelineSelection,

    footageOrientation,

    videoQuality,

    enableSubtitles,

    promptStyle,

    mainCharacter,

    contextDescription,

    setAdvancedStep,

    setError,

    activeProjectId,

    titleSamples,

    descriptionSamples,

    titleStyleAnalysis,

    descriptionStyleAnalysis,

    thumbnailStyleAnalysis,

    syncAnalysisResult,

}: {

    styleA: any;

    originalAnalysis: any;

    advancedSettings: any;

    splitMode: string;

    sceneMode: string;

    selectedVoice: string;

    voiceLanguage: string;

    voiceSpeed: number;

    selectedModel: string;

    pipelineSelection: any;

    footageOrientation: string;

    videoQuality: string;

    enableSubtitles: boolean;

    promptStyle: string;

    mainCharacter: string;

    contextDescription: string;

    setAdvancedStep: (step: number) => void;

    setError: (error: string) => void;

    activeProjectId: string | null;

    titleSamples: string[];

    descriptionSamples: string[];

    titleStyleAnalysis: any;

    descriptionStyleAnalysis: any;

    thumbnailStyleAnalysis: any;

    syncAnalysisResult: any;

}) {

    const queueStore = useQueueStore();
    const { channelName: storeChannelName } = useScriptWorkflowStore();

    const abortControllersRef = useRef<Map<string, AbortController>>(new Map());

    const [isPresetOpen, setIsPresetOpen] = useState(false);
    const handlePresetToggle = () => setIsPresetOpen(prev => !prev);
    const [activeRightTab, setActiveRightTab] = useState<'queue' | 'productions'>('queue');

    // Get active preset name from localStorage

    const activePresetName = (() => {

        try {

            const id = localStorage.getItem('renmae_active_preset');

            if (!id) return 'Mặc định';

            const stored = localStorage.getItem('renmae_workflow_presets');

            const presets = stored ? JSON.parse(stored) : [];

            const found = presets.find((p: any) => p.id === id);

            return found?.name || 'Mặc định';

        } catch { return 'Mặc định'; }

    })();



    // voiceId resolver disabled
    const [activeVoiceId, setActiveVoiceId] = useState<string | undefined>(undefined);

    // Queue execution engine

    const executeQueueItem = async (item: QueueItem) => {
        const controller = new AbortController();
        abortControllersRef.current.set(item.id, controller);

        // Determine which step to start from
        const stepOrder: PipelineStep[] = ['script', 'scenes', 'metadata', 'voice', 'keywords', 'video_direction', 'video_prompts', 'entity_extraction', 'reference_prompts', 'scene_builder', 'assembly', 'seo', 'export'];
        const startFrom = item.retryFromStep || 'script';
        const startIdx = stepOrder.indexOf(startFrom);
        const completedSteps: PipelineStep[] = [...(item.completedSteps || [])].filter(s => stepOrder.indexOf(s) < startIdx);

        let productionId: number | undefined = item.productionId;

        try {
            // Read channelName directly from store to avoid closure/HMR issues
            const channelNameLocal = useScriptWorkflowStore.getState().channelName || '';

            queueStore.updateItem(item.id, {
                status: 'running',
                progress: 0,
                currentStep: startIdx > 0 ? `Retry: ${startFrom}` : 'Generating script',
                retryFromStep: undefined,
            });

            // ── Step 1: Remake Script (0-30%) — use cached if available ──
            let finalScript: string;
            let scenesArray: any[];

            if (startIdx <= 0) {
                if (item.cachedScript && item.cachedScenes?.length && startFrom !== 'script') {
                    finalScript = item.cachedScript;
                    scenesArray = item.cachedScenes;
                    console.log(`[Queue] Using cached script (${finalScript.split(/\s+/).length} words) and ${scenesArray.length} scenes`);
                    queueStore.updateItem(item.id, { progress: 38, currentStep: `Cache: ${scenesArray.length} scenes` });
                    completedSteps.push('script', 'scenes');
                } else {
                    const pipelineResult = await workflowApi.advancedRemake.fullPipelineConversationStream(
                        {
                            original_script: item.scriptText,
                            target_word_count: advancedSettings.targetWordCount || 1200,
                            source_language: advancedSettings.sourceLanguage || '',
                            language: advancedSettings.language || 'vi',
                            dialect: advancedSettings.dialect || '',
                            channel_name: channelNameLocal,
                            country: LANG_TO_COUNTRY[advancedSettings.language] || '',
                            add_quiz: advancedSettings.addQuiz,
                            storytelling_style: advancedSettings.enableStorytellingStyle ? advancedSettings.storytellingStyle : '',
                            narrative_voice: advancedSettings.enableStorytellingStyle ? advancedSettings.narrativeVoice : '',
                            audience_address: advancedSettings.enableAudienceAddress ? advancedSettings.audienceAddress : '',
                            value_type: advancedSettings.enableValueType ? advancedSettings.valueType : '',
                            custom_value: advancedSettings.enableValueType ? advancedSettings.customValue : '',
                            custom_narrative_voice: advancedSettings.enableStorytellingStyle ? advancedSettings.customNarrativeVoice : '',
                            custom_audience_address: advancedSettings.enableAudienceAddress ? advancedSettings.customAudienceAddress : '',
                            style_profile: styleA || originalAnalysis || undefined,
                            model: selectedModel,
                        },
                        (_step: any, percentage: number, message: string) => {
                            const mappedProgress = Math.round(percentage * 0.30);
                            queueStore.updateItem(item.id, {
                                progress: mappedProgress,
                                currentStep: message || 'Processing',
                            });
                        },
                        controller.signal
                    );

                    if (!pipelineResult?.final_script) {
                        throw new Error('Không tạo được kịch bản');
                    }
                    finalScript = pipelineResult.final_script;
                    completedSteps.push('script');

                    // ── Step 2: Split to Scenes (30-38%) ──
                    queueStore.updateItem(item.id, { progress: 30, currentStep: 'Splitting scenes' });
                    const scenesResult = await workflowApi.advancedRemake.splitScriptToScenes(
                        finalScript,
                        selectedModel,
                        advancedSettings.language || 'vi',
                        splitMode as 'voiceover' | 'footage'
                    );

                    if (!scenesResult?.scenes?.length) {
                        throw new Error('Không chia được scenes');
                    }
                    scenesArray = scenesResult.scenes;
                    completedSteps.push('scenes');

                    queueStore.updateItem(item.id, {
                        cachedScript: finalScript,
                        cachedScenes: scenesArray,
                    });
                    console.log(`[Queue] Cached ${scenesArray.length} scenes for item ${item.id}`);
                }
            } else if (startIdx === 1) {
                // Retry from scenes — reuse cached script, re-split
                finalScript = item.cachedScript || item.scriptText;
                completedSteps.push('script');
                queueStore.updateItem(item.id, { progress: 30, currentStep: 'Re-splitting scenes' });
                const scenesResult = await workflowApi.advancedRemake.splitScriptToScenes(
                    finalScript,
                    selectedModel,
                    advancedSettings.language || 'vi',
                    splitMode as 'voiceover' | 'footage'
                );
                if (!scenesResult?.scenes?.length) {
                    throw new Error('Không chia được scenes');
                }
                scenesArray = scenesResult.scenes;
                completedSteps.push('scenes');
                queueStore.updateItem(item.id, { cachedScenes: scenesArray });
            } else {
                // Retry from voice/keywords/assembly — reuse cached script + scenes
                finalScript = item.cachedScript || item.scriptText;
                scenesArray = item.cachedScenes || [];
                if (!scenesArray.length) {
                    throw new Error('Không có scenes cache. Vui lòng retry từ đầu.');
                }
                completedSteps.push('script', 'scenes');
                queueStore.updateItem(item.id, { progress: 38, currentStep: `Cache: ${scenesArray.length} scenes` });
            }

            // ── Production Hub: Create record early (or reuse existing) ──
            productionId = item.productionId;
            let productionSeqNum: number | undefined;
            // Fetch actual project name from activeProjectId
            let actualProjectName = activePresetName || '';
            if (activeProjectId) {
                try {
                    const proj = await projectApi.getProject(Number(activeProjectId));
                    if (proj?.project?.name) actualProjectName = proj.project.name;
                } catch (e) { /* fallback to preset name */ }
            }
            if (!productionId) {
                try {
                    const prodTitle = item.generatedTitle || item.originalTitle || `Project ${new Date().toLocaleDateString('vi-VN')} ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`;
                    const csvContent = scenesArray.length > 0
                        ? scenesArray.map((s: any) => `Scene ${s.scene_id}: ${(s.content || '').replace(/\n/g, ' ').substring(0, 200)}`).join('\n')
                        : '';
                    const createResult = await productionApi.create({
                        project_name: actualProjectName,
                        original_link: (item as any).originalLink || '',
                        title: item.originalTitle || prodTitle,
                        description: item.originalDescription || '',
                        thumbnail: '',
                        original_title: item.originalTitle || '',
                        original_description: item.originalDescription || '',
                        thumbnail_url: item.thumbnailUrl || '',
                        script_full: finalScript || '',
                        script_split: csvContent,
                        video_status: 'draft',
                        preset_name: activePresetName,
                        voice_id: selectedVoice,
                        settings_snapshot: {
                            language: advancedSettings.language,
                            dialect: advancedSettings.dialect,
                            storytelling_style: advancedSettings.storytellingStyle,
                            narrative_voice: advancedSettings.narrativeVoice,
                            target_word_count: advancedSettings.targetWordCount,
                            voice: selectedVoice,
                            voice_language: voiceLanguage,
                            voice_speed: voiceSpeed,
                            model: selectedModel,
                            split_mode: splitMode,
                            footage_orientation: footageOrientation,
                            video_quality: videoQuality,
                            enable_subtitles: enableSubtitles,
                        },
                    });
                    productionId = createResult?.production?.id;
                    productionSeqNum = createResult?.production?.sequence_number;
                    if (productionId) {
                        queueStore.updateItem(item.id, { productionId });
                        console.log(`[Queue][Production] Created early record #${productionId} (seq ${productionSeqNum}) for: ${prodTitle}`);
                    }
                } catch (prodErr: any) {
                    console.error('[Queue][Production] Failed to create early record (non-blocking):', prodErr);
                }
            }

            // ── Production Hub: Sync script after retry (script may have changed) ──
            if (productionId && finalScript) {
                try {
                    const csvContent = scenesArray.length > 0
                        ? scenesArray.map((s: any) => `Scene ${s.scene_id}: ${(s.content || '').replace(/\n/g, ' ').substring(0, 200)}`).join('\n')
                        : '';
                    const scriptUpdate: Record<string, string> = { script_full: finalScript };
                    if (csvContent) scriptUpdate.script_split = csvContent;
                    await productionApi.update(productionId, scriptUpdate);
                    console.log(`[Queue][Production] Synced script to #${productionId} (${finalScript.length} chars, ${scenesArray.length} scenes)`);
                } catch (e) { console.error('[Queue][Production] script sync failed:', e); }
            }

            // ── Metadata options (used later after voice) ──
            const queueAnalysisOpts = normalizeAnalysis(pipelineSelection?.styleAnalysis);
            const analysisHasTitle = queueAnalysisOpts.title;
            const analysisHasDescription = queueAnalysisOpts.description;
            const analysisHasThumbnail = queueAnalysisOpts.thumbnail;
            let metadataResult: any = null;

            // ── Step 3: Generate Voice (38-55%) — capture filenames ──
            const voiceResults: Record<number, { filename: string; duration: number }> = {};

            if (startIdx <= 3) {
                if (startIdx < 3 && item.cachedVoiceResults && Object.keys(item.cachedVoiceResults).length > 0) {
                    // Reuse cached voice results if not explicitly retrying voice
                    Object.assign(voiceResults, item.cachedVoiceResults);
                    completedSteps.push('voice');
                    console.log(`[Queue] Using cached voice results: ${Object.keys(voiceResults).length} scenes`);
                } else if (pipelineSelection?.voiceGeneration === true) {
                    queueStore.updateItem(item.id, { progress: 45, currentStep: 'Generating voice' });
                    const voiceScenes = scenesArray
                        .filter((s: any) => s.content?.trim())
                        .map((s: any) => ({
                            scene_id: s.scene_id,
                            content: s.content,
                            voiceExport: true,
                        }));

                    // Warn if voice language doesn't match script output language
                    if (voiceLanguage && advancedSettings.language && voiceLanguage !== advancedSettings.language) {
                        console.warn(
                            `⚠️ Voice language mismatch: TTS voice is set to "${voiceLanguage}" but script was generated in "${advancedSettings.language}". ` +
                            `This may produce garbled audio. Consider matching voice language to output language.`
                        );
                        queueStore.updateItem(item.id, {
                            currentStep: `Voice: ${voiceLanguage} / Script: ${advancedSettings.language}`,
                        });
                        // Brief delay so user can see the warning
                        await new Promise(r => setTimeout(r, 2000));
                    }

                    await voiceApi.generateBatch(
                        {
                            scenes: voiceScenes,
                            voice: selectedVoice,
                            language: voiceLanguage,
                            speed: voiceSpeed,
                            session_id: item.id,
                        },
                        (current: number, total: number, _sceneId: number, _percentage: number) => {
                            const voiceProgress = 45 + Math.round((current / total) * 17);
                            queueStore.updateItem(item.id, {
                                progress: voiceProgress,
                                currentStep: `Voice ${current}/${total}`,
                            });
                        },
                        controller.signal,
                        (sceneId: number, filename: string, durationSeconds: number) => {
                            voiceResults[sceneId] = { filename, duration: durationSeconds };
                        }
                    );
                    completedSteps.push('voice');
                    // Cache voice results for future retries
                    queueStore.updateItem(item.id, { cachedVoiceResults: { ...voiceResults } });

                    // ── Production Hub: Update voiceover ──
                    if (productionId) {
                        try {
                            const voiceFilesList = Object.values(voiceResults).map((v: any) => v.filename).filter(Boolean).join(', ');
                            await productionApi.update(productionId, { voiceover: voiceFilesList });
                            console.log(`[Queue][Production] Updated #${productionId} with voice data`);
                        } catch (e) { console.error('[Queue][Production] voice update failed:', e); }
                    }
                }
            } else {
                // Retry from keywords/assembly — reuse cached voice
                if (item.cachedVoiceResults) {
                    Object.assign(voiceResults, item.cachedVoiceResults);
                }
                completedSteps.push('voice');
            }

            // ── Step 3.5: Generate YouTube Metadata (with voice timestamps) ──
            if (analysisHasTitle || analysisHasDescription || analysisHasThumbnail) {
                queueStore.updateItem(item.id, {
                    progress: 55,
                    currentStep: 'Generating metadata',
                });

                // Build timestamps from voice results
                const voiceTimestamps: Array<{ scene_id: number; timestamp: string; content: string; duration: number }> = [];
                let totalSeconds = 0;

                if (Object.keys(voiceResults).length > 0) {
                    const sortedSceneIds = Object.keys(voiceResults).map(Number).sort((a, b) => a - b);
                    let cumulativeSeconds = 0;

                    for (const sceneId of sortedSceneIds) {
                        const minutes = Math.floor(cumulativeSeconds / 60);
                        const seconds = Math.floor(cumulativeSeconds % 60);
                        const timeStr = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

                        const scene = scenesArray.find((s: any) => s.scene_id === sceneId);
                        const sceneContent = scene?.content || scene?.title || '';

                        voiceTimestamps.push({
                            scene_id: sceneId,
                            timestamp: timeStr,
                            content: sceneContent,
                            duration: voiceResults[sceneId]?.duration || 0,
                        });

                        cumulativeSeconds += voiceResults[sceneId]?.duration || 0;
                    }
                    totalSeconds = cumulativeSeconds;
                }

                const totalMinutes = Math.floor(totalSeconds / 60);
                const totalSecs = Math.floor(totalSeconds % 60);
                const totalDuration = `${String(totalMinutes).padStart(2, '0')}:${String(totalSecs).padStart(2, '0')}`;

                try {
                    metadataResult = await workflowApi.advancedRemake.generateYoutubeMetadata({
                        script: finalScript,
                        style_profile: styleA || originalAnalysis || undefined,
                        title_samples: titleSamples.length > 0 ? titleSamples : undefined,
                        description_samples: descriptionSamples.length > 0 ? descriptionSamples : undefined,
                        title_style_analysis: analysisHasTitle ? titleStyleAnalysis : undefined,
                        description_style_analysis: analysisHasDescription ? descriptionStyleAnalysis : undefined,
                        thumbnail_style_analysis: analysisHasThumbnail ? thumbnailStyleAnalysis : undefined,
                        generate_title: analysisHasTitle,
                        generate_description: analysisHasDescription,
                        generate_thumbnail_prompt: analysisHasThumbnail,
                        model: selectedModel,
                        custom_cta: queueAnalysisOpts.customCta || undefined,
                        sync_analysis: syncAnalysisResult || undefined,
                        voice_timestamps: voiceTimestamps.length > 0 ? voiceTimestamps : undefined,
                        total_duration: totalSeconds > 0 ? totalDuration : undefined,
                        language: advancedSettings.language || 'vi',
                    });

                    if (metadataResult?.success) {
                        queueStore.updateItem(item.id, {
                            generatedTitle: metadataResult.title || undefined,
                            generatedDescription: metadataResult.description || undefined,
                            generatedThumbnailPrompt: metadataResult.thumbnail_prompt || undefined,
                        });
                        completedSteps.push('metadata');
                        console.log('[Queue] YouTube metadata generated (post-voice):', {
                            title: metadataResult.title?.slice(0, 60),
                            descLen: metadataResult.description?.length,
                            thumbLen: metadataResult.thumbnail_prompt?.length,
                            timestampCount: voiceTimestamps.length,
                        });
                    }
                } catch (metaErr: any) {
                    console.error('[Queue] YouTube metadata generation failed:', metaErr);
                }

                queueStore.updateItem(item.id, { progress: 62, currentStep: 'Metadata done' });

                // ── Production Hub: Update metadata ──
                if (productionId) {
                    try {
                        const updatedTitle = metadataResult?.title || item.originalTitle || '';
                        await productionApi.update(productionId, {
                            title: updatedTitle,
                            description: metadataResult?.description || item.originalDescription || '',
                            thumbnail: metadataResult?.thumbnail_prompt || '',
                            generated_title: metadataResult?.title || '',
                            generated_description: metadataResult?.description || '',
                            generated_thumbnail_prompt: metadataResult?.thumbnail_prompt || '',
                        });
                        console.log(`[Queue][Production] Updated #${productionId} with metadata (title="${updatedTitle.slice(0, 40)}", timestamps=${voiceTimestamps.length})`);
                    } catch (e) { console.error('[Queue][Production] metadata update failed:', e); }
                }
            }

            // ── Step 4: Generate Keywords ONLY (62-70%) ──
            // stepOrder index: 4 (keywords) — generates search keywords for stock footage, NO prompts
            let keywordResult: any = null;

            if (startIdx <= 4) {
                if (startIdx < 4 && item.cachedKeywordResult) {
                    // Reuse cached keywords if not explicitly retrying
                    keywordResult = item.cachedKeywordResult;
                    completedSteps.push('keywords');
                    console.log('[Queue] Using cached keyword results');
                    // Re-merge cached keywords into scenesArray
                    const cachedKwScenes = keywordResult?.keywords || keywordResult?.scenes || [];
                    if (cachedKwScenes.length > 0) {
                        for (const kwScene of cachedKwScenes) {
                            const target = scenesArray.find((s: any) => s.scene_id === kwScene.scene_id);
                            if (target) {
                                target.keyword = kwScene.keyword || target.keyword;
                                target.keywords = kwScene.keywords || target.keywords;
                                if (kwScene.image_prompt) target.image_prompt = kwScene.image_prompt;
                            }
                        }
                    }
                } else {
                    const vp = pipelineSelection?.videoProduction;
                    const shouldGenerateKeywords = vp?.keywords === true;
                    const isConceptMode = vp?.image_prompts === true && vp?.image_prompt_mode === 'concept';

                    if (shouldGenerateKeywords || isConceptMode) {
                        queueStore.updateItem(item.id, { progress: 62, currentStep: 'Generating keywords' });
                        const keywordScenes = scenesArray.map((s: any) => ({
                            scene_id: s.scene_id,
                            content: s.content,
                            audio_duration: voiceResults[s.scene_id]?.duration || s.audio_duration || s.est_duration || 5,
                        }));

                        keywordResult = await workflowApi.advancedRemake.generateSceneKeywords(
                            {
                                scenes: keywordScenes,
                                language: advancedSettings.language || 'vi',
                                model: selectedModel,
                                mode: isConceptMode ? 'concept' : 'custom',
                                generate_video_prompt: false,
                                generate_image_prompt: isConceptMode,
                                generate_keywords: shouldGenerateKeywords,
                            },
                            (message: string, percentage: number) => {
                                const kwProgress = Math.min(70, 62 + Math.round(percentage * 0.08));
                                queueStore.updateItem(item.id, {
                                    progress: kwProgress,
                                    currentStep: message || 'Generating keywords',
                                });
                            },
                            controller.signal
                        );

                        const kwScenes = keywordResult?.keywords || keywordResult?.scenes || [];
                        if (kwScenes.length > 0) {
                            for (const kwScene of kwScenes) {
                                const target = scenesArray.find((s: any) => s.scene_id === kwScene.scene_id);
                                if (target) {
                                    target.keyword = kwScene.keyword || target.keyword;
                                    target.keywords = kwScene.keywords || target.keywords;
                                    target.target_clip_duration = kwScene.target_clip_duration || target.target_clip_duration;
                                    if (isConceptMode && kwScene.image_prompt) target.image_prompt = kwScene.image_prompt;
                                }
                            }
                        }
                        // Cache keyword results
                        queueStore.updateItem(item.id, { cachedKeywordResult: keywordResult });

                        completedSteps.push('keywords');

                        // ── Production Hub: Save keywords immediately (use keywordResult directly for all scenes) ──
                        if (productionId) {
                            try {
                                const allKwScenes = keywordResult?.keywords || keywordResult?.scenes || [];
                                const kwText = allKwScenes
                                    .map((s: any) => {
                                        const kws = s.keywords || (s.keyword ? [s.keyword] : []);
                                        return kws.length > 0 ? `Scene ${s.scene_id}: ${kws.join(', ')}` : '';
                                    })
                                    .filter(Boolean)
                                    .join('\n');
                                if (kwText) {
                                    await productionApi.update(productionId, { keywords: kwText });
                                    console.log(`[Queue][Production] Updated #${productionId} with keywords (${allKwScenes.length} scenes from API, ${kwText.split('\n').length} non-empty)`);
                                } else {
                                    console.warn(`[Queue][Production] No keyword text generated from ${allKwScenes.length} scenes`);
                                }
                            } catch (e) { console.error('[Queue][Production] keywords update failed:', e); }
                        }
                    } else {
                        console.log('[Queue] Skipping keywords — not selected in pipeline');
                    }
                }
            } else {
                // Retry from later step — reuse cached keywords
                const retryKwScenes = item.cachedKeywordResult?.keywords || item.cachedKeywordResult?.scenes || [];
                if (retryKwScenes.length > 0) {
                    for (const kwScene of retryKwScenes) {
                        const target = scenesArray.find((s: any) => s.scene_id === kwScene.scene_id);
                        if (target) {
                            target.keyword = kwScene.keyword || target.keyword;
                            target.keywords = kwScene.keywords || target.keywords;
                            if (kwScene.image_prompt) target.image_prompt = kwScene.image_prompt;
                        }
                    }
                }
                completedSteps.push('keywords');
            }

            // ── Step 5: Video Direction Analysis (71-76%) ──
            // stepOrder index: 5 (video_direction)
            let pipelineDirections: any[] = item.cachedPipelineResult?.directions || [];
            let pipelineEntities: any[] = item.cachedPipelineResult?.entities || [];
            let pipelineRefPromptsText = item.cachedPipelineResult?.referencePromptsText || '';
            let pipelineSbPromptsText = item.cachedPipelineResult?.sceneBuilderPromptsText || '';

            const vp = pipelineSelection?.videoProduction;
            const wantsPrompts = vp?.video_prompts === true || vp?.image_prompts === true;

            if (wantsPrompts && startIdx <= 5) {
                if (startIdx < 5 && pipelineDirections.length > 0) {
                    // Reuse cached directions
                    console.log('[Queue][Pipeline] Using cached directions');
                    for (const dir of pipelineDirections) {
                        const target = scenesArray.find((s: any) => s.scene_id === dir.scene_id);
                        if (target) target.direction_notes = dir.direction_notes || '';
                    }
                    completedSteps.push('video_direction');
                } else if (startIdx <= 5) {
                    queueStore.updateItem(item.id, { progress: 71, currentStep: 'Analyzing direction' });
                    try {
                        const directionResult = await workflowApi.advancedRemake.analyzeVideoDirection(
                            {
                                scenes: scenesArray.map((s: any) => ({ scene_id: s.scene_id, content: s.content })),
                                language: advancedSettings.language || 'vi',
                                model: selectedModel,
                                prompt_style: promptStyle || undefined,
                                main_character: mainCharacter || undefined,
                                context_description: contextDescription || undefined,
                                sync_analysis: syncAnalysisResult || undefined,
                            },
                            (msg: string, pct: number) => {
                                queueStore.updateItem(item.id, { progress: Math.min(76, 71 + Math.round(pct * 0.05)), currentStep: msg });
                            },
                            controller.signal
                        );
                        pipelineDirections = directionResult?.directions || [];
                        for (const dir of pipelineDirections) {
                            const target = scenesArray.find((s: any) => s.scene_id === dir.scene_id);
                            if (target) target.direction_notes = dir.direction_notes || '';
                        }
                        queueStore.updateItem(item.id, {
                            cachedPipelineResult: { ...item.cachedPipelineResult, directions: pipelineDirections },
                        });
                        completedSteps.push('video_direction');
                    } catch (dirErr: any) {
                        console.error('[Queue][Pipeline] Direction error:', dirErr.message);
                        queueStore.updateItem(item.id, { failedStep: 'video_direction' });
                        throw new Error(`Lỗi phân tích đạo diễn: ${dirErr.message}`);
                    }
                }
            } else if (wantsPrompts && pipelineDirections.length > 0) {
                // Retry from later step — reuse cached
                for (const dir of pipelineDirections) {
                    const target = scenesArray.find((s: any) => s.scene_id === dir.scene_id);
                    if (target) target.direction_notes = dir.direction_notes || '';
                }
                completedSteps.push('video_direction');
            }

            // ── Step 6: Generate Video Prompts (77-82%) ──
            // stepOrder index: 6 (video_prompts) — uses direction notes from step 5
            const wantsVideoPrompts = vp?.video_prompts === true;

            if (wantsVideoPrompts && startIdx <= 6) {
                const hasCachedVideoPrompts = scenesArray.some((s: any) => s.video_prompt);
                if (startIdx < 6 && hasCachedVideoPrompts) {
                    console.log('[Queue][Pipeline] Using cached video prompts');
                    completedSteps.push('video_prompts');
                } else if (startIdx <= 6) {
                    queueStore.updateItem(item.id, { progress: 77, currentStep: 'Generating video prompts' });

                    try {
                        const vpResult = await workflowApi.advancedRemake.generateVideoPrompts(
                            {
                                scenes: scenesArray.map((s: any) => ({
                                    scene_id: s.scene_id,
                                    content: s.content,
                                    direction_notes: s.direction_notes || pipelineDirections.find((d: any) => d.scene_id === s.scene_id)?.direction_notes || '',
                                    audio_duration: voiceResults[s.scene_id]?.duration || s.audio_duration || s.est_duration || 5,
                                })),
                                language: advancedSettings.language || 'vi',
                                model: selectedModel,
                                prompt_style: promptStyle || undefined,
                                main_character: mainCharacter || undefined,
                                context_description: contextDescription || undefined,
                                video_prompt_mode: (vp as any)?.video_prompt_mode || undefined,
                                sync_analysis: syncAnalysisResult || undefined,
                            },
                            (message: string, percentage: number) => {
                                const pProgress = Math.min(82, 77 + Math.round(percentage * 0.05));
                                queueStore.updateItem(item.id, {
                                    progress: pProgress,
                                    currentStep: message || 'Generating video prompts',
                                });
                            },
                            controller.signal
                        );

                        const vpScenes = vpResult?.video_prompts || [];
                        if (vpScenes.length > 0) {
                            for (const vps of vpScenes) {
                                const target = scenesArray.find((s: any) => s.scene_id === vps.scene_id);
                                if (target) {
                                    target.video_prompt = vps.video_prompt || target.video_prompt;
                                }
                            }
                        }

                        // Update cached result with video prompts
                        queueStore.updateItem(item.id, {
                            cachedKeywordResult: {
                                ...item.cachedKeywordResult,
                                keywords: scenesArray.map((s: any) => ({
                                    scene_id: s.scene_id,
                                    keyword: s.keyword || '',
                                    keywords: s.keywords || [],
                                    video_prompt: s.video_prompt || '',
                                    image_prompt: s.image_prompt || '',
                                })),
                            },
                        });
                        completedSteps.push('video_prompts');

                        // ── Production Hub: Update prompts_video ──
                        if (productionId) {
                            try {
                                const updatedVideoPrompts = scenesArray.map((s: any) => s.video_prompt || '').filter(Boolean).join('\n');
                                await productionApi.update(productionId, {
                                    prompts_video: updatedVideoPrompts,
                                });
                                console.log(`[Queue][Production] Updated #${productionId} with ${updatedVideoPrompts.split('\n').length} video prompts`);
                            } catch (e) { console.error('[Queue][Production] video prompts update failed:', e); }
                        }
                    } catch (vpErr: any) {
                        console.error('[Queue][Pipeline] Video prompt generation error:', vpErr.message);
                        queueStore.updateItem(item.id, { failedStep: 'video_prompts' });
                        throw new Error(`Lỗi tạo video prompts: ${vpErr.message}`);
                    }
                }
            } else if (wantsVideoPrompts && startIdx > 6) {
                // Retry from later step — reuse cached video prompts
                const retryVpScenes = item.cachedKeywordResult?.keywords || item.cachedKeywordResult?.scenes || [];
                if (retryVpScenes.length > 0) {
                    for (const vps of retryVpScenes) {
                        const target = scenesArray.find((s: any) => s.scene_id === vps.scene_id);
                        if (target) {
                            target.video_prompt = vps.video_prompt || target.video_prompt;
                        }
                    }
                }
                completedSteps.push('video_prompts');
            } else if (!wantsVideoPrompts) {
                completedSteps.push('video_prompts');
            }

            // Recompute hasVideoPrompts AFTER Step 6 has populated scenesArray
            const hasVideoPrompts = scenesArray.some((s: any) => s.video_prompt);

            // ── Step 7: Entity Extraction (83-86%) ──
            // stepOrder index: 7 (entity_extraction)
            if (hasVideoPrompts && startIdx <= 7) {
                if (startIdx < 7 && pipelineEntities.length > 0) {
                    console.log('[Queue][Pipeline] Using cached entities');
                    completedSteps.push('entity_extraction');
                } else if (startIdx <= 7) {
                    queueStore.updateItem(item.id, { progress: 83, currentStep: 'Extracting entities' });
                    try {
                        const entityResult = await workflowApi.advancedRemake.extractEntities(
                            {
                                video_prompts: scenesArray.map((s: any) => ({ scene_id: s.scene_id, video_prompt: s.video_prompt || '' })),
                                language: advancedSettings.language || 'vi',
                                model: selectedModel,
                                script_scenes: scenesArray.map((s: any) => ({ scene_id: s.scene_id, content: s.content })),
                            },
                            (msg: string, pct: number) => {
                                queueStore.updateItem(item.id, { progress: Math.min(86, 83 + Math.round(pct * 0.03)), currentStep: msg });
                            },
                            controller.signal
                        );
                        pipelineEntities = entityResult?.entities || [];
                        console.log(`[Queue][Pipeline] Extracted ${pipelineEntities.length} entities`);
                        queueStore.updateItem(item.id, {
                            cachedPipelineResult: { ...item.cachedPipelineResult, directions: pipelineDirections, entities: pipelineEntities },
                        });
                        completedSteps.push('entity_extraction');
                    } catch (entErr: any) {
                        console.error('[Queue][Pipeline] Entity extraction error:', entErr.message);
                        queueStore.updateItem(item.id, { failedStep: 'entity_extraction' });
                        throw new Error(`Lỗi trích xuất entities: ${entErr.message}`);
                    }
                }
            } else if (hasVideoPrompts && pipelineEntities.length > 0) {
                completedSteps.push('entity_extraction');
            }

            // ── Step 8: Reference Image Prompts (87-89%) ──
            // stepOrder index: 8 (reference_prompts)
            if (hasVideoPrompts && pipelineEntities.length > 0 && startIdx <= 8) {
                if (startIdx < 8 && pipelineRefPromptsText) {
                    console.log('[Queue][Pipeline] Using cached reference prompts');
                    (scenesArray as any).__pipeline_reference_prompts = pipelineRefPromptsText;
                    (scenesArray as any).__pipeline_entities = pipelineEntities;
                    completedSteps.push('reference_prompts');
                } else if (startIdx <= 8) {
                    queueStore.updateItem(item.id, { progress: 87, currentStep: 'Reference prompts' });
                    try {
                        const refResult = await workflowApi.advancedRemake.generateReferencePrompts(
                            {
                                entities: pipelineEntities,
                                model: selectedModel,
                                prompt_style: promptStyle || undefined,
                                sync_analysis: syncAnalysisResult || undefined,
                            },
                            (msg: string, pct: number) => {
                                queueStore.updateItem(item.id, { progress: Math.min(89, 87 + Math.round(pct * 0.02)), currentStep: msg });
                            },
                            controller.signal
                        );
                        const entitiesHeader = refResult?.entities_header || pipelineEntities.map((e: any) => `[${e.name}]`).join(', ');
                        const refPrompts = refResult?.reference_prompts || [];
                        pipelineRefPromptsText = `=== ENTITIES ===\n${entitiesHeader}\n\n=== REFERENCE PROMPTS ===\n`;
                        for (const rp of refPrompts) {
                            for (const p of (rp.prompts || [])) {
                                pipelineRefPromptsText += `[${rp.entity_name}] ${p.angle}: ${p.prompt}\n`;
                            }
                        }
                        pipelineRefPromptsText = pipelineRefPromptsText.trim();
                        (scenesArray as any).__pipeline_reference_prompts = pipelineRefPromptsText;
                        (scenesArray as any).__pipeline_entities = pipelineEntities;
                        queueStore.updateItem(item.id, {
                            cachedPipelineResult: { ...item.cachedPipelineResult, directions: pipelineDirections, entities: pipelineEntities, referencePromptsText: pipelineRefPromptsText },
                        });
                        completedSteps.push('reference_prompts');

                        // ── Production Hub: Save reference prompts immediately ──
                        if (productionId && pipelineRefPromptsText) {
                            try {
                                await productionApi.update(productionId, {
                                    prompts_reference: pipelineRefPromptsText,
                                });
                                console.log(`[Queue][Production] Updated #${productionId} with reference prompts`);
                            } catch (e) { console.error('[Queue][Production] ref prompts update failed:', e); }
                        }
                    } catch (refErr: any) {
                        console.error('[Queue][Pipeline] Reference prompts error:', refErr.message);
                        queueStore.updateItem(item.id, { failedStep: 'reference_prompts' });
                        throw new Error(`Lỗi tạo ảnh tham chiếu: ${refErr.message}`);
                    }
                }
            } else if (hasVideoPrompts && pipelineRefPromptsText) {
                (scenesArray as any).__pipeline_reference_prompts = pipelineRefPromptsText;
                (scenesArray as any).__pipeline_entities = pipelineEntities;
                completedSteps.push('reference_prompts');
            }

            // ── Step 9: Scene Builder Image Prompts (90-92%) ──
            // stepOrder index: 9 (scene_builder)
            if (hasVideoPrompts && pipelineEntities.length > 0 && startIdx <= 9) {
                if (startIdx < 9 && pipelineSbPromptsText) {
                    console.log('[Queue][Pipeline] Using cached scene builder prompts');
                    (scenesArray as any).__pipeline_scene_builder_prompts = pipelineSbPromptsText;
                    completedSteps.push('scene_builder');
                } else if (startIdx <= 9) {
                    queueStore.updateItem(item.id, { progress: 90, currentStep: 'Scene builder' });
                    try {
                        const sbResult = await workflowApi.advancedRemake.generateSceneBuilderPrompts(
                            {
                                video_prompts: scenesArray.map((s: any) => ({ scene_id: s.scene_id, video_prompt: s.video_prompt || '' })),
                                entities: pipelineEntities,
                                directions: pipelineDirections,
                                model: selectedModel,
                                prompt_style: promptStyle || undefined,
                                sync_analysis: syncAnalysisResult || undefined,
                            },
                            (msg: string, pct: number) => {
                                queueStore.updateItem(item.id, { progress: Math.min(92, 90 + Math.round(pct * 0.02)), currentStep: msg });
                            },
                            controller.signal
                        );
                        const sbPrompts = sbResult?.scene_builder_prompts || [];
                        for (const sb of sbPrompts) {
                            const target = scenesArray.find((s: any) => s.scene_id === sb.scene_id);
                            if (target) target.scene_builder_prompt = sb.scene_builder_prompt || '';
                        }
                        pipelineSbPromptsText = sbPrompts.map((sb: any) => sb.scene_builder_prompt || '').filter(Boolean).join('\n');
                        (scenesArray as any).__pipeline_scene_builder_prompts = pipelineSbPromptsText;
                        queueStore.updateItem(item.id, {
                            cachedPipelineResult: { directions: pipelineDirections, entities: pipelineEntities, referencePromptsText: pipelineRefPromptsText, sceneBuilderPromptsText: pipelineSbPromptsText },
                        });
                        completedSteps.push('scene_builder');
                        console.log(`[Queue][Pipeline] ✅ Pipeline complete: ${pipelineEntities.length} entities, ref prompts: ${pipelineRefPromptsText ? 'yes' : 'no'}, scene builders: ${sbPrompts.length}`);

                        // ── Production Hub: Update image prompts ──
                        if (productionId) {
                            try {
                                const perSceneImagePrompts = scenesArray.map((s: any) => s.image_prompt || '').filter(Boolean).join('\n');
                                const imgPromptMode = pipelineSelection?.videoProduction?.image_prompt_mode || 'reference';
                                await productionApi.update(productionId, {
                                    prompts_reference: pipelineRefPromptsText || (imgPromptMode === 'reference' ? perSceneImagePrompts : ''),
                                    prompts_scene_builder: pipelineSbPromptsText || (imgPromptMode === 'scene_builder' ? perSceneImagePrompts : ''),
                                    prompts_concept: imgPromptMode === 'concept' ? perSceneImagePrompts : '',
                                });
                                console.log(`[Queue][Production] Updated #${productionId} with image prompts`);
                            } catch (e) { console.error('[Queue][Production] image prompts update failed:', e); }
                        }
                    } catch (sbErr: any) {
                        console.error('[Queue][Pipeline] Scene builder error:', sbErr.message);
                        queueStore.updateItem(item.id, { failedStep: 'scene_builder' });
                        throw new Error(`Lỗi tạo scene builder: ${sbErr.message}`);
                    }
                }
            } else if (hasVideoPrompts && pipelineSbPromptsText) {
                (scenesArray as any).__pipeline_scene_builder_prompts = pipelineSbPromptsText;
                completedSteps.push('scene_builder');
            }

            // ── Merge voice results into scenesArray ──
            for (const [sceneIdStr, voiceData] of Object.entries(voiceResults)) {
                const sceneId = Number(sceneIdStr);
                const target = scenesArray.find((s: any) => s.scene_id === sceneId);
                if (target) {
                    target.audio_duration = (voiceData as any).duration;
                    target.voice_filename = (voiceData as any).filename;
                }
            }

            // ── Step 5: Video Assembly (75-90%) ──
            let finalVideoPath: string | null = null;
            let assemblyError: string | null = null;

            // ── DEBUG: Log all assembly decision factors ──
            console.log('[Queue][Assembly DEBUG] ── Assembly Decision ──');
            console.log('[Queue][Assembly DEBUG] pipelineSelection:', JSON.stringify(pipelineSelection, null, 2));
            console.log('[Queue][Assembly DEBUG] pipelineSelection?.videoProduction:', pipelineSelection?.videoProduction);
            console.log('[Queue][Assembly DEBUG] pipelineSelection?.videoProduction?.footage:', pipelineSelection?.videoProduction?.footage);
            console.log('[Queue][Assembly DEBUG] voiceResults keys:', Object.keys(voiceResults));
            console.log('[Queue][Assembly DEBUG] voiceResults count:', Object.keys(voiceResults).length);
            console.log('[Queue][Assembly DEBUG] scenesArray count:', scenesArray.length);
            console.log('[Queue][Assembly DEBUG] scenesArray scene_ids:', scenesArray.map((s: any) => s.scene_id));

            const shouldAssembleVideo = pipelineSelection?.videoProduction?.footage === true &&
                Object.keys(voiceResults).length > 0;

            console.log('[Queue][Assembly DEBUG] shouldAssembleVideo:', shouldAssembleVideo);

            if (!shouldAssembleVideo) {
                console.warn('[Queue][Assembly DEBUG] ⚠️ SKIPPING assembly because:');
                if (!pipelineSelection?.videoProduction) console.warn('  → pipelineSelection.videoProduction is falsy');
                if (pipelineSelection?.videoProduction?.footage === false) console.warn('  → videoProduction.footage === false');
                if (Object.keys(voiceResults).length === 0) console.warn('  → voiceResults is empty (no voice files)');
            }

            if (shouldAssembleVideo) {
                queueStore.updateItem(item.id, { progress: 75, currentStep: 'Assembling video' });

                const assembleSceneList = scenesArray
                    .filter((s: any) => voiceResults[s.scene_id])
                    .map((s: any) => ({
                        scene_id: s.scene_id,
                        audio_filename: voiceResults[s.scene_id].filename,
                        keyword: s.keyword || (Array.isArray(s.keywords) ? s.keywords[0] : s.keywords) || '',
                        keywords: Array.isArray(s.keywords) ? s.keywords : undefined,
                        target_clip_duration: s.target_clip_duration || undefined,
                        subtitle_text: s.content || '',
                    }));

                console.log('[Queue][Assembly DEBUG] assembleSceneList.length:', assembleSceneList.length);
                console.log('[Queue][Assembly DEBUG] assembleSceneList:', JSON.stringify(assembleSceneList.slice(0, 3), null, 2), assembleSceneList.length > 3 ? `... +${assembleSceneList.length - 3} more` : '');

                if (assembleSceneList.length === 0) {
                    console.error('[Queue][Assembly DEBUG] ⚠️ assembleSceneList is EMPTY!');
                    console.error('[Queue][Assembly DEBUG] voiceResults keys (type check):', Object.entries(voiceResults).map(([k, v]) => `${k} (${typeof k}): ${JSON.stringify(v)}`));
                    console.error('[Queue][Assembly DEBUG] scenesArray scene_ids (type check):', scenesArray.map((s: any) => `${s.scene_id} (${typeof s.scene_id})`));
                    assemblyError = 'assembleSceneList is empty — voice/scene ID mismatch';
                }

                if (assembleSceneList.length > 0) {
                    try {
                        console.log('[Queue][Assembly DEBUG] 🚀 Calling footageApi.assembleScenes with:', {
                            scenesCount: assembleSceneList.length,
                            orientation: footageOrientation,
                            video_quality: videoQuality,
                            enable_subtitles: enableSubtitles,
                        });
                        const assembleResult = await footageApi.assembleScenes(
                            {
                                scenes: assembleSceneList,
                                orientation: footageOrientation,
                                video_quality: videoQuality,
                                enable_subtitles: enableSubtitles,
                                session_id: item.id,
                            },
                            (msg: string, pct: number) => {
                                console.log(`[Queue][Assembly DEBUG] SSE progress: ${pct}% — ${msg}`);
                                const assembleProgress = 75 + Math.round(pct * 0.15);
                                queueStore.updateItem(item.id, {
                                    progress: assembleProgress,
                                    currentStep: msg || 'Assembling video',
                                });
                            },
                            undefined,
                            controller.signal
                        );
                        console.log('[Queue][Assembly DEBUG] ✅ assembleResult:', JSON.stringify(assembleResult, null, 2));
                        finalVideoPath = assembleResult?.final_video_path || null;
                        console.log('[Queue][Assembly DEBUG] finalVideoPath:', finalVideoPath);
                    } catch (assembleErr: any) {
                        console.error('[Queue][Assembly DEBUG] ❌ Video assembly FAILED:', assembleErr);
                        console.error('[Queue][Assembly DEBUG] Error name:', assembleErr?.name);
                        console.error('[Queue][Assembly DEBUG] Error message:', assembleErr?.message);
                        console.error('[Queue][Assembly DEBUG] Error stack:', assembleErr?.stack);
                        assemblyError = assembleErr?.message || 'Unknown assembly error';
                    }
                }
            }
            if ((shouldAssembleVideo || startFrom === 'assembly') && !assemblyError) {
                completedSteps.push('assembly');

                // ── Production Hub: Save assembly result immediately ──
                if (productionId && finalVideoPath) {
                    try {
                        await productionApi.update(productionId, {
                            video_final: finalVideoPath,
                        });
                        console.log(`[Queue][Production] Updated #${productionId} with video_final`);
                    } catch (e) { console.error('[Queue][Production] assembly update failed:', e); }
                }
            }

            // ── Step 6: SEO Data (90-93%) ──
            let seoData: Record<string, any> | undefined;

            if (isSeoEnabled(pipelineSelection?.seoOptimize)) {
                const seoMode = (typeof pipelineSelection?.seoOptimize === 'object' && pipelineSelection.seoOptimize)
                    ? (pipelineSelection.seoOptimize as any).mode : 'auto';

                if (seoMode === 'review') {
                    // 'review' mode: skip auto-generation, user reviews manually
                    console.log('[Queue][SEO] Mode = review — skipping auto-generation');
                    queueStore.updateItem(item.id, { progress: 93, currentStep: 'Skip SEO (review mode)' });
                } else {
                    queueStore.updateItem(item.id, { progress: 90, currentStep: 'Generating SEO' });

                    try {
                        const seoResult = await seoApi.generate({
                            script_content: finalScript.substring(0, 3000),
                            language: advancedSettings.language || 'vi',
                            channel_name: channelNameLocal,
                            target_platform: 'youtube',
                        });

                        if (seoResult?.success && seoResult.seo_data && seoResult.seo_data.main_keyword) {
                            seoData = seoResult.seo_data;
                            queueStore.updateItem(item.id, {
                                seoData: seoResult.seo_data,
                                currentStep: `SEO: ${seoResult.seo_data.main_keyword}`,
                            });
                            console.log('[Queue][SEO] Generated SEO data:', seoResult.seo_data.main_keyword);
                        } else {
                            console.warn('[Queue][SEO] SEO returned empty/invalid data, skipping:', seoResult);
                        }
                    } catch (seoErr: any) {
                        console.error('[Queue][SEO] SEO generation failed (non-blocking):', seoErr);
                    }
                }
                completedSteps.push('seo');
            }

            // ── Step 7: Export Results (93-99%) ──
            let exportDir: string | undefined;
            const queueOutputPath = queueStore.outputPath;
            const queueExportOptions = queueStore.exportOptions;
            const hasAnyExport = queueOutputPath && (
                queueExportOptions.fullScript ||
                queueExportOptions.splitCsv ||
                queueExportOptions.finalVideo ||
                queueExportOptions.voiceZip ||
                queueExportOptions.footageZip ||
                queueExportOptions.keywordsTxt ||
                queueExportOptions.promptsTxt
            );

            if (hasAnyExport) {
                queueStore.updateItem(item.id, { progress: 93, currentStep: 'Exporting results' });

                try {
                    // Collect scene data with prompts
                    const exportScenes = scenesArray.map((s: any) => ({
                        scene_id: s.scene_id,
                        content: s.content || '',
                        keywords: s.keywords || (s.keyword ? [s.keyword] : []),
                        image_prompt: s.image_prompt || '',
                        video_prompt: s.video_prompt || '',
                    }));

                    // Collect voice filenames
                    const voiceFilenames = Object.values(voiceResults)
                        .map((v: any) => v.filename)
                        .filter(Boolean);

                    // Collect scene video paths from video_output directory
                    const sceneVideoPaths = scenesArray
                        .map((s: any) => s.scene_video_path)
                        .filter(Boolean);

                    // Build folder path: [project_name]/[sequence_number] when available
                    const exportFolderName = (actualProjectName && productionSeqNum)
                        ? `${actualProjectName}/${productionSeqNum}`
                        : undefined; // fallback to default timestamp-based name

                    const exportResult = await exportApi.packageResults({
                        output_dir: queueOutputPath,
                        item_id: item.id,
                        folder_name: exportFolderName || '',
                        export_options: {
                            full_script: queueExportOptions.fullScript && completedSteps.includes('script'),
                            split_csv: queueExportOptions.splitCsv && completedSteps.includes('scenes'),
                            final_video: queueExportOptions.finalVideo && completedSteps.includes('assembly'),
                            voice_zip: queueExportOptions.voiceZip && completedSteps.includes('voice'),
                            footage_zip: queueExportOptions.footageZip && completedSteps.includes('assembly'),
                            keywords_txt: queueExportOptions.keywordsTxt && completedSteps.includes('keywords'),
                            prompts_txt: queueExportOptions.promptsTxt && (completedSteps.includes('video_prompts') || completedSteps.includes('keywords')),
                            seo_optimize: completedSteps.includes('seo') && !!seoData,
                        },
                        full_script: finalScript,
                        scenes: exportScenes,
                        voice_filenames: voiceFilenames,
                        final_video_path: finalVideoPath || '',
                        scene_video_paths: sceneVideoPaths,
                        // Production metadata — forwarded to auto-create production record
                        preset_name: activePresetName,
                        voice_id: selectedVoice,
                        keywords: scenesArray
                            .map((s: any) => {
                                const kws = s.keywords || (s.keyword ? [s.keyword] : []);
                                return kws.length > 0 ? `Scene ${s.scene_id}: ${kws.join(', ')}` : '';
                            })
                            .filter(Boolean)
                            .join('\n'),
                        original_title: item.originalTitle || '',
                        original_description: item.originalDescription || '',
                        thumbnail_url: item.thumbnailUrl || '',
                        generated_title: item.generatedTitle || '',
                        generated_description: item.generatedDescription || '',
                        generated_thumbnail_prompt: item.generatedThumbnailPrompt || '',
                        settings_snapshot: {
                            language: advancedSettings.language,
                            dialect: advancedSettings.dialect,
                            storytelling_style: advancedSettings.storytellingStyle,
                            narrative_voice: advancedSettings.narrativeVoice,
                            target_word_count: advancedSettings.targetWordCount,
                            voice: selectedVoice,
                            voice_language: voiceLanguage,
                            voice_speed: voiceSpeed,
                            model: selectedModel,
                            split_mode: splitMode,
                            footage_orientation: footageOrientation,
                            video_quality: videoQuality,
                            enable_subtitles: enableSubtitles,
                        },
                        // SEO Thô data
                        seo_data: seoData,
                    });

                    exportDir = exportResult?.export_dir;
                    console.log('[Queue][Export] Results packaged:', exportResult);
                    completedSteps.push('export');
                    queueStore.updateItem(item.id, { progress: 99, currentStep: `Exported ${exportResult?.total_exported || 0} files` });

                    // ── Production Hub: Update export + video ──
                    if (productionId) {
                        try {
                            await productionApi.update(productionId, {
                                export_dir: exportDir || '',
                                video_final: finalVideoPath || '',
                            });
                            console.log(`[Queue][Production] Updated #${productionId} with export dir`);
                        } catch (e) { console.error('[Queue][Production] export update failed:', e); }
                    }
                } catch (exportErr: any) {
                    console.error('[Queue][Export] Error:', exportErr);
                    // Don't fail the whole queue item for export errors
                }
            }

            // ── Final Production Hub sync — safety net: persist ALL data ──
            if (productionId) {
                try {
                    // Re-read fresh item from store — item closure may be stale
                    const freshItem = queueStore.getState().items.find((i: any) => i.id === item.id) || item;
                    const finalDesc = freshItem.generatedDescription || freshItem.originalDescription || '';
                    const finalVideoPromptsText = scenesArray.map((s: any) => s.video_prompt || '').filter(Boolean).join('\n');
                    const finalKeywordsText = scenesArray
                        .map((s: any) => {
                            const kws = s.keywords || (s.keyword ? [s.keyword] : []);
                            return kws.length > 0 ? `Scene ${s.scene_id}: ${kws.join(', ')}` : '';
                        })
                        .filter(Boolean)
                        .join('\n');

                    // Build final update — only include non-empty values to avoid overwriting with blanks
                    const finalUpdate: Record<string, string> = {};
                    const finalTitle = freshItem.generatedTitle || freshItem.originalTitle || '';
                    const finalThumbnail = freshItem.generatedThumbnailPrompt || '';
                    if (finalTitle) finalUpdate.title = finalTitle;
                    if (finalDesc) finalUpdate.description = finalDesc;
                    if (finalThumbnail) finalUpdate.thumbnail = finalThumbnail;
                    if (finalVideoPath) finalUpdate.video_final = finalVideoPath;
                    if (exportDir) finalUpdate.export_dir = exportDir;
                    if (finalScript) finalUpdate.script_full = finalScript;
                    if (finalVideoPromptsText) finalUpdate.prompts_video = finalVideoPromptsText;
                    if (pipelineRefPromptsText) finalUpdate.prompts_reference = pipelineRefPromptsText;
                    if (pipelineSbPromptsText) finalUpdate.prompts_scene_builder = pipelineSbPromptsText;
                    if (finalKeywordsText) finalUpdate.keywords = finalKeywordsText;
                    // Concept image prompts
                    const finalConceptPrompts = scenesArray.map((s: any) => s.image_prompt || '').filter(Boolean).join('\n');
                    if (finalConceptPrompts && pipelineSelection?.videoProduction?.image_prompt_mode === 'concept') finalUpdate.prompts_concept = finalConceptPrompts;
                    // Original + generated metadata fields
                    if (freshItem.generatedTitle) finalUpdate.generated_title = freshItem.generatedTitle;
                    if (freshItem.generatedDescription) finalUpdate.generated_description = freshItem.generatedDescription;
                    if (freshItem.generatedThumbnailPrompt) finalUpdate.generated_thumbnail_prompt = freshItem.generatedThumbnailPrompt;
                    if (freshItem.originalTitle) finalUpdate.original_title = freshItem.originalTitle;
                    if (freshItem.originalDescription) finalUpdate.original_description = freshItem.originalDescription;
                    if (freshItem.thumbnailUrl) finalUpdate.thumbnail_url = freshItem.thumbnailUrl;

                    // Only call API if there's something to update
                    if (Object.keys(finalUpdate).length > 0) {
                        await productionApi.update(productionId, finalUpdate);
                    }
                    console.log(`[Queue][Production] Final sync #${productionId} — fields=${Object.keys(finalUpdate).join(',')}, prompts_video=${finalVideoPromptsText ? 'yes' : 'no'}, ref=${pipelineRefPromptsText ? 'yes' : 'no'}, sb=${pipelineSbPromptsText ? 'yes' : 'no'}`);
                } catch (prodErr: any) {
                    console.error('[Queue][Production] Final sync failed (non-blocking):', prodErr);
                }
            }

            // ── Cleanup session cache (non-blocking) ──
            try {
                const cleanupPromises: Promise<any>[] = [];
                cleanupPromises.push(voiceApi.cleanupSession(item.id));
                if (shouldAssembleVideo) {
                    cleanupPromises.push(footageApi.cleanupSession(item.id));
                }
                Promise.all(cleanupPromises).then((results) => {
                    console.log(`[Queue][Cleanup] Session ${item.id} cleaned:`, results);
                }).catch(() => { /* non-blocking */ });
            } catch { /* non-blocking */ }

            // ── Done — detect missing output ──
            const hasVoice = Object.keys(voiceResults).length > 0;
            const exportFailed = hasAnyExport && !exportDir;
            queueStore.updateItem(item.id, {
                status: 'done',
                progress: 100,
                currentStep: exportFailed
                    ? '⚠️ Hoàn tất nhưng xuất file thất bại'
                    : exportDir
                        ? `Hoàn tất! Tải xuống → ${exportDir.split(/[/\\]/).pop()}`
                        : finalVideoPath
                            ? `Hoàn tất! Tải xuống → ${finalVideoPath.split(/[/\\]/).pop()}`
                            : assemblyError
                                ? `⚠️ Lỗi ghép video: ${assemblyError}`
                                : hasVoice
                                    ? '⚠️ Hoàn tất nhưng KHÔNG có video đầu ra'
                                    : '⚠️ Hoàn tất nhưng KHÔNG có voice/video',
                finalVideoPath: finalVideoPath || undefined,
                exportDir,
                completedSteps,
            });

        } catch (err: any) {
            // Derive which step failed from completedSteps
            const stepOrder2: PipelineStep[] = ['script', 'scenes', 'metadata', 'voice', 'keywords', 'video_direction', 'video_prompts', 'entity_extraction', 'reference_prompts', 'scene_builder', 'assembly', 'seo', 'export'];
            // Prefer the failedStep already set by individual catch blocks; only derive if not set
            const alreadySetFailedStep = useQueueStore.getState().items.find(i => i.id === item.id)?.failedStep;
            const derivedFailedStep = alreadySetFailedStep || stepOrder2.find(s => !completedSteps.includes(s)) || 'script';

            if (err.name === 'AbortError') {
                queueStore.updateItem(item.id, {
                    status: 'error',
                    error: 'Đã dừng bởi người dùng',
                    completedSteps,
                    failedStep: derivedFailedStep,
                });
            } else {
                queueStore.updateItem(item.id, {
                    status: 'error',
                    error: err.message || 'Lỗi không xác định',
                    completedSteps,
                    failedStep: derivedFailedStep,
                });
            }

            // ── Sync any generated data to production even on stop/error ──
            if (productionId) {
                try {
                    const currentItem = useQueueStore.getState().items.find(i => i.id === item.id);
                    const errUpdate: Record<string, string> = {};
                    if (currentItem?.generatedTitle) {
                        errUpdate.title = currentItem.generatedTitle;
                        errUpdate.generated_title = currentItem.generatedTitle;
                    }
                    if (currentItem?.generatedDescription) {
                        errUpdate.description = currentItem.generatedDescription;
                        errUpdate.generated_description = currentItem.generatedDescription;
                    }
                    if (currentItem?.generatedThumbnailPrompt) {
                        errUpdate.thumbnail = currentItem.generatedThumbnailPrompt;
                        errUpdate.generated_thumbnail_prompt = currentItem.generatedThumbnailPrompt;
                    }
                    if (finalScript) errUpdate.script_full = finalScript;
                    if (Object.keys(errUpdate).length > 0) {
                        await productionApi.update(productionId, errUpdate);
                        console.log(`[Queue][Production] Error-sync #${productionId} — saved: ${Object.keys(errUpdate).join(',')}`);
                    }
                } catch { /* non-blocking */ }
            }
        } finally {
            abortControllersRef.current.delete(item.id);
        }

    };



    // Queue runner effect

    const executingItemsRef = useRef<Set<string>>(new Set());

    useEffect(() => {
        console.log('[Queue][Effect] isQueueRunning changed to:', queueStore.isQueueRunning);
        if (!queueStore.isQueueRunning) return;



        const runNext = async () => {

            const runningCount = queueStore.getRunningCount();

            if (runningCount >= queueStore.maxConcurrent) return;



            const next = queueStore.getNextQueued();
            console.log('[Queue][runNext] runningCount:', runningCount, 'next:', next?.id, 'status:', next?.status, 'retryFromStep:', next?.retryFromStep);

            if (!next) {

                // No more items to run

                if (runningCount === 0) {
                    console.log('[Queue][runNext] No items left, stopping queue');
                    queueStore.setIsQueueRunning(false);
                    executingItemsRef.current.clear();

                }

                return;

            }

            // Guard: prevent duplicate execution of the same item
            if (executingItemsRef.current.has(next.id)) return;
            executingItemsRef.current.add(next.id);

            // Delay between thread starts
            if (queueStore.delayBetweenMs > 0) {
                await new Promise(r => setTimeout(r, queueStore.delayBetweenMs));
                // Re-check concurrency after delay (another thread may have started)
                if (queueStore.getRunningCount() >= queueStore.maxConcurrent) {
                    executingItemsRef.current.delete(next.id);
                    return;
                }
            }

            executeQueueItem(next);

        };



        runNext();

        const interval = setInterval(runNext, 2000);

        return () => clearInterval(interval);

        // eslint-disable-next-line react-hooks/exhaustive-deps

    }, [queueStore.isQueueRunning]);



    // Stop all on unmount or when queue stops

    useEffect(() => {

        if (!queueStore.isQueueRunning) {

            abortControllersRef.current.forEach(controller => controller.abort());

            abortControllersRef.current.clear();

        }

    }, [queueStore.isQueueRunning]);



    const handleRetryItem = (item: QueueItem) => {
        console.log('[Queue][RetryItem] Triggered:', { itemId: item.id });
        executingItemsRef.current.delete(item.id);
        queueStore.retryItem(item.id);
        queueStore.setIsQueueRunning(true);
        // Directly execute after a micro-delay to ensure store state is committed
        setTimeout(() => {
            const freshItem = useQueueStore.getState().items.find(i => i.id === item.id);
            if (freshItem && freshItem.status === 'queued') {
                console.log('[Queue][RetryItem] Directly executing:', freshItem.id);
                executingItemsRef.current.add(freshItem.id);
                executeQueueItem(freshItem);
            } else {
                console.warn('[Queue][RetryItem] Item not in queued state after retry:', freshItem?.status);
            }
        }, 100);
    };

    const handleRetryFromStep = (item: QueueItem, step: PipelineStep) => {
        console.log('[Queue][RetryFromStep] Triggered:', { itemId: item.id, step });
        executingItemsRef.current.delete(item.id);
        queueStore.retryItemFromStep(item.id, step);
        queueStore.setIsQueueRunning(true);
        // Directly execute after a micro-delay to ensure store state is committed
        setTimeout(() => {
            const freshItem = useQueueStore.getState().items.find(i => i.id === item.id);
            if (freshItem && freshItem.status === 'queued') {
                console.log('[Queue][RetryFromStep] Directly executing:', freshItem.id, 'from step:', freshItem.retryFromStep);
                executingItemsRef.current.add(freshItem.id);
                executeQueueItem(freshItem);
            } else {
                console.warn('[Queue][RetryFromStep] Item not in queued state after retry:', freshItem?.status);
            }
        }, 100);
    };





    const handleSelectOutputPath = async () => {
        try {
            let dir: string | null = null;
            if (window.electron?.selectDirectory) {
                // Electron mode: native dialog
                dir = await window.electron.selectDirectory();
            } else {
                // Web mode: prompt for path
                dir = prompt('Nhập đường dẫn thư mục xuất (ví dụ: C:\\Users\\Output)');
            }
            if (dir) queueStore.setOutputPath(dir);
        } catch (err) {
            console.error('[Queue] Failed to select folder:', err);
        }
    };



    return (

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

            {/* Back to Step 1 button */}

            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>

                <button

                    onClick={() => setAdvancedStep(1)}

                    style={{

                        display: 'flex',

                        alignItems: 'center',

                        gap: '0.4rem',

                        padding: '0.5rem 1rem',

                        borderRadius: '10px',

                        border: '1px solid var(--border-color)',

                        background: 'var(--bg-secondary)',

                        color: 'var(--text-secondary)',

                        cursor: 'pointer',

                        fontSize: '0.85rem',

                        fontWeight: 600,

                    }}

                >

                    Để Quay lại Style Analysis

                </button>

                <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>

                    <Zap size={18} style={{ color: '#FFD700' }} /> Hàng đợi tự động

                </h3>

                {/* Tab toggle: Queue / Productions */}
                <div style={{ marginLeft: 'auto', display: 'flex', borderRadius: '8px', border: '1px solid var(--border-color)', overflow: 'hidden', background: 'var(--bg-secondary)' }}>
                    <button
                        onClick={() => setActiveRightTab('queue')}
                        style={{
                            padding: '0.35rem 0.75rem',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            border: 'none',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            transition: 'all 0.2s',
                            background: activeRightTab === 'queue' ? 'rgba(255, 215, 0, 0.12)' : 'transparent',
                            color: activeRightTab === 'queue' ? '#FFD700' : 'var(--text-secondary)',
                            borderBottom: activeRightTab === 'queue' ? '2px solid #FFD700' : '2px solid transparent',
                        }}
                    >
                        <Zap size={12} /> Hàng đợi
                    </button>
                    <button
                        onClick={() => setActiveRightTab('productions')}
                        style={{
                            padding: '0.35rem 0.75rem',
                            fontSize: '0.78rem',
                            fontWeight: 600,
                            border: 'none',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            transition: 'all 0.2s',
                            background: activeRightTab === 'productions' ? 'rgba(255, 215, 0, 0.12)' : 'transparent',
                            color: activeRightTab === 'productions' ? '#FFD700' : 'var(--text-secondary)',
                            borderBottom: activeRightTab === 'productions' ? '2px solid #FFD700' : '2px solid transparent',
                        }}
                    >
                        <Package size={12} /> Productions
                    </button>
                </div>

            </div>



            {/* Sidebar + Queue Panel Layout */}

            <div style={{

                display: 'flex',

                gap: '1rem',

                minHeight: '500px',

                alignItems: 'stretch',

            }}>

                <QueueSidebar

                    activePresetName={activePresetName}

                    onSelectOutputPath={handleSelectOutputPath}

                    isPresetOpen={isPresetOpen}

                    onPresetToggle={handlePresetToggle}

                    activeVoiceId={activeVoiceId}

                    currentConfig={{
                        advancedSettings,
                        splitMode,
                        sceneMode,
                        selectedVoice,
                        voiceLanguage,
                        voiceSpeed,
                        selectedModel,
                        footageOrientation,
                        videoQuality,
                        enableSubtitles,
                        pipelineSelection,
                        channelName: storeChannelName,
                        promptStyle,
                        mainCharacter,
                        contextDescription,
                    }}

                />

                {activeRightTab === 'queue' ? (
                    <QueuePanel
                        onRetryItem={handleRetryItem}
                        onRetryFromStep={handleRetryFromStep}
                        onPresetClick={handlePresetToggle}
                    />
                ) : (
                    <ProductionHub />
                )}

            </div>

        </div>

    );

}

