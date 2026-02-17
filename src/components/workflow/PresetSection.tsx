import { useState, useEffect, useCallback } from 'react';

// 
// TYPES
// 

export interface PresetConfig {
    targetWordCount: number;
    sourceLanguage: string;
    language: string;
    dialect: string;
    enableStorytellingStyle: boolean;
    storytellingStyle: string;
    narrativeVoice: string;
    customNarrativeVoice: string;
    enableAudienceAddress: boolean;
    audienceAddress: string;
    customAudienceAddress: string;
    enableValueType: boolean;
    valueType: string;
    customValue: string;
    addQuiz: boolean;
    country: string;
    voiceLanguage: string;
    selectedVoice: string;
    voiceSpeed: number;
    splitMode: string;
    sceneMode: string;
    footageOrientation: string;
    videoQuality: string;
    enableSubtitles: boolean;
    promptStyle: string;
    mainCharacter: string;
}

export interface AnalysisOptions {
    voiceStyle: boolean;
    title: boolean;
    thumbnail: boolean;
    description: boolean;
    syncCharacter: boolean;
    syncStyle: boolean;
    syncContext: boolean;
    customCta?: string;
}

export interface SeoOptions {
    enabled: boolean;
    mode: 'auto' | 'review';
}

export interface PipelineSelection {
    styleAnalysis: boolean | AnalysisOptions;
    scriptGeneration: boolean;
    voiceGeneration: boolean;
    videoProduction: {
        video_prompts: boolean;
        image_prompts: boolean;
        keywords: boolean;
        footage: boolean;
        image_prompt_mode: 'reference' | 'scene_builder' | 'concept';
        video_prompt_mode: 'character_sync' | 'scene_sync' | 'full_sync';
    };
    seoOptimize: boolean | SeoOptions;
}

export interface WorkflowConfigProps {
    advancedSettings: {
        targetWordCount: number;
        sourceLanguage: string;
        language: string;
        dialect: string;
        enableStorytellingStyle: boolean;
        storytellingStyle: string;
        narrativeVoice: string;
        customNarrativeVoice: string;
        enableAudienceAddress: boolean;
        audienceAddress: string;
        customAudienceAddress: string;
        enableValueType: boolean;
        valueType: string;
        customValue: string;
        country: string;
        addQuiz: boolean;
    };
    setAdvancedSettings: (fn: (s: any) => any) => void;
    voiceLanguage: string;
    setVoiceLanguage: (v: string) => void;
    selectedVoice: string;
    setSelectedVoice: (v: string) => void;
    voiceSpeed: number;
    setVoiceSpeed: (v: number) => void;
    voicesByLanguage: Record<string, { voices: { id: string; name: string; gender: string }[] }>;
    splitMode: string;
    setSplitMode: (v: any) => void;
    sceneMode: string;
    setSceneMode: (v: any) => void;
    footageOrientation: string;
    setFootageOrientation: (v: any) => void;
    videoQuality: string;
    setVideoQuality: (v: string) => void;
    enableSubtitles: boolean;
    setEnableSubtitles: (v: boolean) => void;
    promptStyle: string;
    setPromptStyle: (v: string) => void;
    mainCharacter: string;
    setMainCharacter: (v: string) => void;
    contextDescription: string;
    setContextDescription: (v: string) => void;
    channelName: string;
    setChannelName: (v: string) => void;
}

interface PresetSectionProps {
    config: WorkflowConfigProps;
    onPipelineChange?: (pipeline: PipelineSelection) => void;
    initialPipeline?: Partial<PipelineSelection>;
    analysisLocked?: boolean;
}

// 
// PIPELINE STEPS
// 

interface StepDef {
    id: string;
    label: string;
    desc: string;
    children?: { id: string; label: string }[];
}

const STEPS: StepDef[] = [
    {
        id: 'styleAnalysis', label: 'Phân tích', desc: 'Giọng văn, Title, Thumbnail, Description, Sync',
        children: [
            { id: 'voiceStyle', label: 'Giọng Văn' },
            { id: 'title', label: 'Title' },
            { id: 'thumbnail', label: 'Thumbnail' },
            { id: 'description', label: 'Description' },
            { id: 'syncCharacter', label: 'Sync Nhân Vật' },
            { id: 'syncStyle', label: 'Sync Phong Cách' },
            { id: 'syncContext', label: 'Sync Bối Cảnh' },
        ],
    },
    { id: 'scriptGeneration', label: 'Tạo kịch bản', desc: 'Remake dựa trên nội dung gốc' },
    { id: 'voiceGeneration', label: 'Tạo Voice', desc: 'Giọng đọc AI cho từng scene' },
    {
        id: 'videoProduction', label: 'Dựng Video', desc: 'Hình ảnh & Video',
        children: [
            { id: 'video_prompts', label: 'Tạo Prompts Video' },
            { id: 'image_prompts', label: 'Tạo Prompts Ảnh' },
            { id: 'keywords', label: 'Tạo Keywords' },
            { id: 'footage', label: 'Tìm Video Footage' },
        ],
    },
    { id: 'seoOptimize', label: 'SEO Thô', desc: 'Metadata, title, tags, hash unique' },
];

const STORAGE_KEY = 'renmae_pipeline_selection';

export const DEFAULT_ANALYSIS: AnalysisOptions = { voiceStyle: true, title: false, thumbnail: false, description: false, syncCharacter: false, syncStyle: false, syncContext: false };

export function normalizeAnalysis(val: any): AnalysisOptions {
    if (typeof val === 'boolean') return val ? { ...DEFAULT_ANALYSIS } : { voiceStyle: false, title: false, thumbnail: false, description: false, syncCharacter: false, syncStyle: false, syncContext: false };
    if (typeof val === 'object' && val !== null) return { voiceStyle: !!val.voiceStyle, title: !!val.title, thumbnail: !!val.thumbnail, description: !!val.description, syncCharacter: !!val.syncCharacter, syncStyle: !!val.syncStyle, syncContext: !!val.syncContext, customCta: val.customCta || '' };
    return { ...DEFAULT_ANALYSIS };
}

export function isAnalysisEnabled(val: boolean | AnalysisOptions): boolean {
    if (typeof val === 'boolean') return val;
    return val.voiceStyle || val.title || val.thumbnail || val.description || val.syncCharacter || val.syncStyle || val.syncContext;
}

export function normalizeSeo(val: any): SeoOptions {
    if (typeof val === 'boolean') return { enabled: val, mode: 'auto' };
    if (typeof val === 'object' && val !== null) return { enabled: !!val.enabled, mode: val.mode === 'review' ? 'review' : 'auto' };
    return { enabled: false, mode: 'auto' };
}

export function isSeoEnabled(val: boolean | SeoOptions | undefined): boolean {
    if (!val) return false;
    if (typeof val === 'boolean') return val;
    return val.enabled;
}

function loadPipeline(): PipelineSelection {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        if (raw) {
            const parsed = JSON.parse(raw);
            // Migrate old 'prompts' key to new split keys
            if (parsed.videoProduction && 'prompts' in parsed.videoProduction && !('video_prompts' in parsed.videoProduction)) {
                parsed.videoProduction.video_prompts = parsed.videoProduction.prompts;
                parsed.videoProduction.image_prompts = parsed.videoProduction.prompts;
                delete parsed.videoProduction.prompts;
            }
            // Migrate old boolean styleAnalysis to new object format
            parsed.styleAnalysis = normalizeAnalysis(parsed.styleAnalysis);
            // Migrate old seoOptimize
            if (parsed.seoOptimize !== undefined) {
                parsed.seoOptimize = normalizeSeo(parsed.seoOptimize);
            } else {
                parsed.seoOptimize = { enabled: false, mode: 'auto' };
            }
            // Migrate: add prompt mode defaults
            if (parsed.videoProduction && !parsed.videoProduction.image_prompt_mode) {
                parsed.videoProduction.image_prompt_mode = 'reference';
            }
            if (parsed.videoProduction && !parsed.videoProduction.video_prompt_mode) {
                parsed.videoProduction.video_prompt_mode = 'full_sync';
            }
            return parsed;
        }
    } catch { /* ignore */ }
    return { styleAnalysis: { ...DEFAULT_ANALYSIS }, scriptGeneration: true, voiceGeneration: true, videoProduction: { video_prompts: true, image_prompts: true, keywords: true, footage: true, image_prompt_mode: 'reference', video_prompt_mode: 'full_sync' }, seoOptimize: { enabled: false, mode: 'auto' } };
}

// 
// TOGGLE SWITCH
// 
function Toggle({ checked, onChange, color = '#0EA5E9' }: { checked: boolean; onChange: (v: boolean) => void; color?: string }) {
    return (
        <label style={{ position: 'relative', display: 'inline-block', width: '40px', height: '22px', flexShrink: 0 }}>
            <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} style={{ opacity: 0, width: 0, height: 0 }} />
            <span style={{
                position: 'absolute', cursor: 'pointer', top: 0, left: 0, right: 0, bottom: 0,
                background: checked ? color : 'var(--bg-tertiary)', borderRadius: '11px', transition: 'all 0.3s',
            }}>
                <span style={{
                    position: 'absolute', height: '16px', width: '16px', left: checked ? '21px' : '3px',
                    bottom: '3px', background: 'white', borderRadius: '50%', transition: 'all 0.3s',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.25)',
                }} />
            </span>
        </label>
    );
}

// 
// HELPERS
// 
const LANG_LABELS: Record<string, string> = {
    vi: 'Tiếng Việt', en: 'Tiếng Anh', zh: 'Tiếng Trung', ja: 'Tiếng Nhật',
    ko: 'Tiếng Hàn', es: 'Tiếng Tây Ban Nha', fr: 'Tiếng Pháp', th: 'Tiếng Thái',
    de: 'Tiếng Đức', pt: 'Tiếng Bồ Đào Nha', ru: 'Tiếng Nga',
};
const STYLE_LABELS: Record<string, string> = {
    immersive: 'Nhập vai', documentary: 'Thuyết minh', conversational: 'Đối thoại',
    analytical: 'Phân tích', narrative: 'Kể chuyện',
};
const VOICE_LABELS: Record<string, string> = {
    first_person: 'Ngôi thứ nhất (Tôi)', second_person: 'Ngôi thứ hai (Bạn)', third_person: 'Ngôi thứ ba',
};
const VALUE_LABELS: Record<string, string> = {
    sell: 'Kêu gọi mua hàng', engage: 'Tương tác & Đăng ký',
    community: 'Cộng đồng & Đăng ký',
};
const ORIENT_LABELS: Record<string, string> = { landscape: 'Ngang (16:9)', portrait: 'Dọc (9:16)' };
const MODE_LABELS: Record<string, string> = { footage: 'Footage', concept: 'Concept', storytelling: 'Storytelling', custom: 'Custom' };
const IMAGE_PROMPT_MODE_LABELS: Record<string, string> = {
    reference: 'Tạo ảnh tham chiếu',
    scene_builder: 'Scene builder',
    concept: 'Tạo ảnh theo concept',
};
const VIDEO_PROMPT_MODE_LABELS: Record<string, string> = {
    character_sync: 'Đồng bộ nhân vật',
    scene_sync: 'Đồng bộ phong cách',
    full_sync: 'Đồng bộ nhân vật + bối cảnh',
};

// 
// COMPONENT
// 

export default function PresetSection({ config, onPipelineChange, initialPipeline, analysisLocked = false }: PresetSectionProps) {
    const [pipeline, setPipeline] = useState<PipelineSelection>(() => {
        const base = loadPipeline();
        if (initialPipeline) {
            return { ...base, ...initialPipeline };
        }
        return base;
    });
    const [expandedStep, setExpandedStep] = useState<string>('scriptGeneration');

    const { advancedSettings: as_, setAdvancedSettings } = config;

    useEffect(() => {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(pipeline));
        onPipelineChange?.(pipeline);
    }, [pipeline, onPipelineChange]);

    // Determine which steps are locked by dependencies
    const isStepLocked = useCallback((id: string): string | false => {
        if (id === 'scriptGeneration') {
            if (pipeline.voiceGeneration) return 'Tạo Voice cần kịch bản';
            if (isEnabled('videoProduction')) return 'Dựng Video cần kịch bản';
            if (isSeoEnabled(pipeline.seoOptimize)) return 'SEO cần kịch bản';
        }
        return false;
    }, [pipeline]);

    const isSubLocked = useCallback((subId: string): string | false => {
        if (subId === 'keywords' && pipeline.videoProduction.footage) return 'Footage cần keywords';
        if (subId === 'footage' && isSeoEnabled(pipeline.seoOptimize)) return 'SEO cần footage';
        if (subId === 'image_prompts' && pipeline.videoProduction.video_prompts && (pipeline.videoProduction.video_prompt_mode === 'character_sync' || pipeline.videoProduction.video_prompt_mode === 'full_sync')) return 'Đồng bộ cần ảnh tham chiếu';
        // Sync checkboxes: locked by video/image prompt modes (only when those features are enabled)
        const vMode = pipeline.videoProduction.video_prompt_mode;
        const iMode = pipeline.videoProduction.image_prompt_mode;
        const vOn = pipeline.videoProduction.video_prompts;
        const iOn = pipeline.videoProduction.image_prompts;
        if (subId === 'syncCharacter') {
            const reasons: string[] = [];
            if (vOn && vMode === 'character_sync') reasons.push('Đồng bộ nhân vật');
            if (vOn && vMode === 'full_sync') reasons.push('Đồng bộ NV+BC');
            if (iOn && iMode === 'reference') reasons.push('Ảnh tham chiếu');
            if (iOn && iMode === 'scene_builder') reasons.push('Scene builder');
            if (reasons.length > 0) return reasons.join(' + ');
        }
        if (subId === 'syncStyle') {
            const reasons: string[] = [];
            if (vOn && vMode === 'scene_sync') reasons.push('Đồng bộ phong cách');
            if (vOn && vMode === 'full_sync') reasons.push('Đồng bộ NV+BC');
            if (iOn && iMode === 'scene_builder') reasons.push('Scene builder');
            if (reasons.length > 0) return reasons.join(' + ');
        }
        if (subId === 'syncContext') {
            const reasons: string[] = [];
            if (vOn && vMode === 'full_sync') reasons.push('Đồng bộ NV+BC');
            if (iOn && iMode === 'reference') reasons.push('Ảnh tham chiếu');
            if (iOn && iMode === 'scene_builder') reasons.push('Scene builder');
            if (reasons.length > 0) return reasons.join(' + ');
        }
        return false;
    }, [pipeline]);

    const toggleStep = useCallback((id: string) => {
        setPipeline(p => {
            if (id === 'videoProduction') {
                const allOn = p.videoProduction.video_prompts && p.videoProduction.image_prompts && p.videoProduction.keywords && p.videoProduction.footage;
                const newState = { ...p, videoProduction: { ...p.videoProduction, video_prompts: !allOn, image_prompts: !allOn, keywords: !allOn, footage: !allOn } };
                // If enabling video, auto-enable script
                if (!allOn) newState.scriptGeneration = true;
                return newState;
            }
            if (id === 'styleAnalysis') {
                if (analysisLocked) return p;
                const analysis = normalizeAnalysis(p.styleAnalysis);
                const allOn = analysis.voiceStyle && analysis.title && analysis.thumbnail && analysis.description;
                const newVal = { voiceStyle: !allOn, title: !allOn, thumbnail: !allOn, description: !allOn, syncCharacter: analysis.syncCharacter, syncStyle: analysis.syncStyle, syncContext: analysis.syncContext };
                return { ...p, styleAnalysis: newVal };
            }
            if (id === 'seoOptimize') {
                const seo = normalizeSeo(p.seoOptimize);
                const newState = { ...p, seoOptimize: { ...seo, enabled: !seo.enabled } };
                // If enabling SEO, auto-enable script + footage + keywords
                if (!seo.enabled) {
                    newState.scriptGeneration = true;
                    newState.videoProduction = { ...newState.videoProduction, footage: true, keywords: true };
                }
                return newState;
            }
            if (id === 'voiceGeneration') {
                const newState = { ...p, voiceGeneration: !p.voiceGeneration };
                // If enabling voice, auto-enable script
                if (!p.voiceGeneration) newState.scriptGeneration = true;
                return newState;
            }
            return { ...p, [id]: !p[id as keyof PipelineSelection] };
        });
    }, []);

    const toggleSub = useCallback((subId: string, parentId?: string) => {
        // Sync checkboxes are auto-determined, not user-toggleable
        if (['syncCharacter', 'syncStyle', 'syncContext'].includes(subId)) return;
        setPipeline(p => {
            if (parentId === 'styleAnalysis') {
                if (analysisLocked) return p; // Locked — do not toggle
                const analysis = normalizeAnalysis(p.styleAnalysis);
                const newAnalysis = { ...analysis, [subId]: !analysis[subId as keyof AnalysisOptions] };
                return { ...p, styleAnalysis: newAnalysis };
            }
            const newVP = { ...p.videoProduction, [subId]: !p.videoProduction[subId as keyof typeof p.videoProduction] };
            // Auto-tick keywords when footage is enabled
            if (subId === 'footage' && !p.videoProduction.footage) {
                newVP.keywords = true;
            }
            return { ...p, videoProduction: newVP };
        });
    }, []);

    // Auto-set sync checkbox values based on video/image prompt modes
    useEffect(() => {
        const vMode = pipeline.videoProduction.video_prompt_mode;
        const iMode = pipeline.videoProduction.image_prompt_mode;
        const vOn = pipeline.videoProduction.video_prompts;
        const iOn = pipeline.videoProduction.image_prompts;
        const syncCharacter = (vOn && (vMode === 'character_sync' || vMode === 'full_sync')) || (iOn && (iMode === 'reference' || iMode === 'scene_builder'));
        const syncStyle = (vOn && (vMode === 'scene_sync' || vMode === 'full_sync')) || (iOn && iMode === 'scene_builder');
        const syncContext = (vOn && vMode === 'full_sync') || (iOn && (iMode === 'reference' || iMode === 'scene_builder'));
        setPipeline(p => {
            const analysis = normalizeAnalysis(p.styleAnalysis);
            if (analysis.syncCharacter === syncCharacter && analysis.syncStyle === syncStyle && analysis.syncContext === syncContext) return p;
            return { ...p, styleAnalysis: { ...analysis, syncCharacter, syncStyle, syncContext } };
        });
    }, [pipeline.videoProduction.video_prompt_mode, pipeline.videoProduction.image_prompt_mode, pipeline.videoProduction.video_prompts, pipeline.videoProduction.image_prompts]);

    function isEnabled(id: string): boolean {
        if (id === 'videoProduction') return pipeline.videoProduction.video_prompts || pipeline.videoProduction.image_prompts || pipeline.videoProduction.keywords || pipeline.videoProduction.footage;
        if (id === 'styleAnalysis') return isAnalysisEnabled(pipeline.styleAnalysis);
        if (id === 'seoOptimize') return isSeoEnabled(pipeline.seoOptimize);
        return !!pipeline[id as keyof PipelineSelection];
    }

    const analysisOpts = normalizeAnalysis(pipeline.styleAnalysis);
    const seoOpts = normalizeSeo(pipeline.seoOptimize);
    const enabledCount = [isAnalysisEnabled(pipeline.styleAnalysis), pipeline.scriptGeneration, pipeline.voiceGeneration, isEnabled('videoProduction'), isSeoEnabled(pipeline.seoOptimize)].filter(Boolean).length;

    // 
    // LEFT PANEL: Accordion steps with inline controls
    // 

    function renderScriptControls() {
        return (
            <div className="step-controls">
                <div className="sc-row">
                    <div className="sc-field" style={{ flex: 1 }}>
                        <label>Tên kênh</label>
                        <input type="text" className="sc-input" value={config.channelName}
                            onChange={e => config.setChannelName(e.target.value)}
                            placeholder="VD: Tri thức TV, Sáng Tạo Lab..." />
                    </div>
                    <div className="sc-field">
                        <label>Số từ</label>
                        <input type="number" className="sc-input" value={as_.targetWordCount}
                            onChange={e => setAdvancedSettings((s: any) => ({ ...s, targetWordCount: parseInt(e.target.value) || 1500 }))}
                            min={500} max={5000} />
                    </div>
                    {as_.language && (
                        <div className="sc-field">
                            <label>Giọng</label>
                            <select className="sc-input" value={as_.dialect}
                                onChange={e => setAdvancedSettings((s: any) => ({ ...s, dialect: e.target.value }))}>
                                <option value="">-- Chọn --</option>
                                {as_.language === 'vi' && <><option value="Northern">Bắc</option><option value="Central">Trung</option><option value="Southern">Nam</option></>}
                                {as_.language === 'en' && <><option value="American">Mỹ</option><option value="British">Anh</option><option value="Australian">Úc</option></>}
                                {as_.language === 'zh' && <><option value="Mandarin">Phổ thông</option><option value="Cantonese">Quảng Đông</option><option value="Traditional">Phồn thể (Đài Loan)</option></>}
                                {as_.language === 'ja' && <><option value="Standard">Chuẩn (標準語)</option><option value="Kansai">Kansai (関西弁)</option></>}
                                {as_.language === 'ko' && <><option value="Standard">Chuẩn (표준어)</option><option value="Busan">Busan (부산 사투리)</option></>}
                                {as_.language === 'es' && <><option value="Spain">Tây Ban Nha</option><option value="LatinAmerica">Mỹ Latinh</option><option value="Mexican">Mexico</option></>}
                                {as_.language === 'fr' && <><option value="France">Pháp</option><option value="Canadian">Canada</option><option value="Belgian">Bỉ</option></>}
                                {as_.language === 'th' && <><option value="Standard">Chuẩn (ภาษากลาง)</option><option value="Isan">Isan (อีสาน)</option></>}
                                {as_.language === 'de' && <><option value="Germany">Đức</option><option value="Austria">Áo</option><option value="Swiss">Thụy Sĩ</option></>}
                                {as_.language === 'pt' && <><option value="Brazil">Brazil</option><option value="Portugal">Bồ Đào Nha</option></>}
                                {as_.language === 'ru' && <><option value="Standard">Chuẩn (Стандартный)</option></>}
                            </select>
                        </div>
                    )}
                </div>
                <div className="sc-toggles">
                    <div className={`sc-toggle ${as_.enableStorytellingStyle ? 'on' : ''}`}>
                        <div className="sc-toggle-head">
                            <span>Dẫn chuyện</span>
                            <Toggle checked={as_.enableStorytellingStyle} onChange={v => setAdvancedSettings((s: any) => ({ ...s, enableStorytellingStyle: v }))} color="linear-gradient(90deg, #a855f7, #8b5cf6)" />
                        </div>
                        {as_.enableStorytellingStyle && (
                            <div className="sc-toggle-body">
                                <select className="sc-input" value={as_.storytellingStyle} onChange={e => setAdvancedSettings((s: any) => ({ ...s, storytellingStyle: e.target.value }))}>
                                    <option value="immersive">Nhập vai</option><option value="documentary">Thuyết minh</option><option value="conversational">Đối thoại</option><option value="analytical">Phân tích</option><option value="narrative">Kể chuyện</option>
                                </select>
                                <select className="sc-input" value={as_.narrativeVoice} onChange={e => setAdvancedSettings((s: any) => ({ ...s, narrativeVoice: e.target.value }))}>
                                    <option value="first_person">Ngôi 1 (Tôi)</option><option value="second_person">Ngôi 2 (Bạn)</option><option value="third_person">Ngôi 3</option>
                                </select>
                                <textarea className="sc-input" placeholder="Chi tiết xưng hô..." value={as_.customNarrativeVoice}
                                    onChange={e => setAdvancedSettings((s: any) => ({ ...s, customNarrativeVoice: e.target.value }))} rows={2} />
                            </div>
                        )}
                    </div>
                    <div className={`sc-toggle ${as_.enableAudienceAddress ? 'on' : ''}`}>
                        <div className="sc-toggle-head">
                            <span>Xưng hô</span>
                            <Toggle checked={as_.enableAudienceAddress} onChange={v => setAdvancedSettings((s: any) => ({ ...s, enableAudienceAddress: v }))} color="linear-gradient(90deg, #06B6D4, #14B8A6)" />
                        </div>
                        {as_.enableAudienceAddress && (
                            <div className="sc-toggle-body">
                                <select className="sc-input" value={as_.audienceAddress} onChange={e => setAdvancedSettings((s: any) => ({ ...s, audienceAddress: e.target.value }))}>
                                    {as_.language === 'en'
                                        ? <><option value="you">you</option><option value="you all">you all</option><option value="dear viewers">dear viewers</option></>
                                        : as_.language === 'ja'
                                            ? <><option value="あなた">あなた</option><option value="皆さん">皆さん</option><option value="視聴者の皆様">視聴者の皆様</option></>
                                            : as_.language === 'ko'
                                                ? <><option value="여러분">여러분</option><option value="당신">당신</option><option value="시청자 여러분">시청자 여러분</option></>
                                                : as_.language === 'zh'
                                                    ? <><option value="你">你</option><option value="大家">大家</option><option value="观众朋友们">观众朋友们</option></>
                                                    : as_.language === 'es'
                                                        ? <><option value="tú">tú</option><option value="ustedes">ustedes</option><option value="queridos espectadores">queridos espectadores</option></>
                                                        : as_.language === 'fr'
                                                            ? <><option value="tu">tu</option><option value="vous">vous</option><option value="chers spectateurs">chers spectateurs</option></>
                                                            : as_.language === 'th'
                                                                ? <><option value="คุณ">คุณ</option><option value="ท่านผู้ชม">ท่านผู้ชม</option></>
                                                                : as_.language === 'de'
                                                                    ? <><option value="du">du</option><option value="Sie">Sie</option><option value="liebe Zuschauer">liebe Zuschauer</option></>
                                                                    : as_.language === 'pt'
                                                                        ? <><option value="você">você</option><option value="vocês">vocês</option><option value="queridos espectadores">queridos espectadores</option></>
                                                                        : as_.language === 'ru'
                                                                            ? <><option value="ты">ты</option><option value="вы">вы</option><option value="уважаемые зрители">уважаемые зрители</option></>
                                                                            : <><option value="bạn">bạn</option><option value="các bạn">các bạn</option><option value="anh chị">anh/chị</option><option value="quý vị">quý vị</option></>}
                                </select>
                                <textarea className="sc-input" placeholder="Chi tiết cách xưng hô, ví dụ: Xưng 'mình' gọi 'các bạn', giọng thân mật gần gũi..."
                                    value={as_.customAudienceAddress}
                                    onChange={e => setAdvancedSettings((s: any) => ({ ...s, customAudienceAddress: e.target.value }))} rows={2} />
                            </div>
                        )}
                    </div>
                    <div className={`sc-toggle ${as_.enableValueType ? 'on' : ''}`}>
                        <div className="sc-toggle-head">
                            <span>Đúc kết & CTA</span>
                            <Toggle checked={as_.enableValueType} onChange={v => setAdvancedSettings((s: any) => ({ ...s, enableValueType: v }))} color="linear-gradient(90deg, #f97316, #ea580c)" />
                        </div>
                        {as_.enableValueType && (
                            <div className="sc-toggle-body">
                                <select className="sc-input" value={as_.valueType} onChange={e => setAdvancedSettings((s: any) => ({ ...s, valueType: e.target.value }))}>
                                    <option value="sell">Đúc kết + Kêu gọi mua hàng</option>
                                    <option value="engage">Đúc kết + Tương tác & Đăng ký</option>
                                    <option value="community">Đúc kết + Cộng đồng & Đăng ký</option>
                                </select>
                                <div className="cta-preview">
                                    {as_.valueType === 'sell' && (
                                        <p className="cta-desc">
                                            Giai đoạn 6-8: Viết đúc kết 300-400 từ → bài học sâu sắc → liên hệ nội dung với khóa học → kêu gọi mua.
                                        </p>
                                    )}
                                    {as_.valueType === 'engage' && (
                                        <p className="cta-desc">
                                            Giai đoạn 6-8: Viết đúc kết 300-500 từ → bài học sâu sắc → tạo câu hỏi tương tác → kêu gọi comment + đăng ký kênh.
                                        </p>
                                    )}
                                    {as_.valueType === 'community' && (
                                        <p className="cta-desc">
                                            Giai đoạn 6-8: Viết đúc kết 300-500 từ → bài học sâu sắc → kêu gọi tham gia cộng đồng + đăng ký kênh.
                                        </p>
                                    )}
                                </div>
                                <textarea className="sc-input" rows={3}
                                    placeholder={
                                        as_.valueType === 'sell'
                                            ? 'Nhập thông tin khóa học: tên, giá, ưu đãi, lợi ích, nỗi đau nếu không mua...'
                                            : as_.valueType === 'community'
                                                ? 'Nhập tên cộng đồng, link, lĩnh vực kiến thức...'
                                                : 'Thêm chi tiết tùy chỉnh (tùy chọn)...'
                                    }
                                    value={as_.customValue}
                                    onChange={e => setAdvancedSettings((s: any) => ({ ...s, customValue: e.target.value }))} />
                            </div>
                        )}
                    </div>

                    <div className={`sc-toggle ${as_.addQuiz ? 'on' : ''}`}>
                        <div className="sc-toggle-head">
                            <span>Câu hỏi A/B</span>
                            <Toggle checked={as_.addQuiz} onChange={v => setAdvancedSettings((s: any) => ({ ...s, addQuiz: v }))} color="linear-gradient(90deg, #ec4899, #db2777)" />
                        </div>
                        {as_.addQuiz && (
                            <p style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0', lineHeight: 1.4 }}>
                                Tạo câu hỏi A/B sau hook để khán giả comment lựa chọn, tăng tương tác.
                            </p>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    function renderVoiceControls() {
        const langVoices = config.voicesByLanguage[config.voiceLanguage]?.voices || [];
        return (
            <div className="step-controls">
                <div className="sc-row" style={{ flexWrap: 'nowrap' }}>
                    <div className="sc-field" style={{ flex: 1, minWidth: 0 }}>
                        <label>Ngôn ngữ</label>
                        <select className="sc-input" value={config.voiceLanguage} disabled
                            style={{ opacity: 0.7, cursor: 'not-allowed' }}>
                            <option value="">Tự nhận diện</option>
                            {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                        </select>
                    </div>
                    <div className="sc-field" style={{ flex: 1.5, minWidth: 0 }}>
                        <label>Giọng đọc</label>
                        <select className="sc-input" value={config.selectedVoice} onChange={e => config.setSelectedVoice(e.target.value)}>
                            {langVoices.length === 0 && <option value="">Không có voice</option>}
                            {langVoices.map((v: { id: string; name: string; gender: string }) => (
                                <option key={v.id} value={v.id}>{v.gender === 'Female' ? 'F' : 'M'} {v.name}</option>
                            ))}
                        </select>
                    </div>
                </div>
                <div className="sc-field" style={{ marginTop: '0.3rem' }}>
                    <label>Tốc độ: {config.voiceSpeed}x</label>
                    <input type="range" min={0.5} max={2} step={0.1} value={config.voiceSpeed}
                        onChange={e => config.setVoiceSpeed(parseFloat(e.target.value))} style={{ accentColor: '#FFD700' }} />
                </div>
            </div>
        );
    }

    function renderVideoControls() {
        return (
            <div className="step-controls">
                <div className="sc-row">
                    <div className="sc-field">
                        <label>Hướng video</label>
                        <select className="sc-input" value={config.footageOrientation} onChange={e => config.setFootageOrientation(e.target.value)}>
                            <option value="landscape">Ngang (16:9)</option><option value="portrait">Dọc (9:16)</option>
                        </select>
                    </div>
                    <div className="sc-field">
                        <label>Chất lượng</label>
                        <select className="sc-input" value={config.videoQuality} onChange={e => config.setVideoQuality(e.target.value)}>
                            <option value="720p">720p HD</option><option value="1080p">1080p Full HD</option><option value="4k">4K Ultra HD</option>
                        </select>
                    </div>
                    <div className="sc-field">
                        <label>Phụ đề</label>
                        <div style={{ paddingTop: '0.2rem' }}>
                            <Toggle checked={config.enableSubtitles} onChange={config.setEnableSubtitles} color="linear-gradient(90deg, #FFD700, #F59E0B)" />
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    function renderStyleControls() {
        return (
            <div className="step-controls">
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.78rem', margin: 0, lineHeight: 1.5 }}>
                    {analysisOpts.voiceStyle && 'Giọng văn: Nhập 5-20 kịch bản mẫu. '}
                    {analysisOpts.title && 'Title: Nhập mẫu title YouTube. '}
                    {analysisOpts.thumbnail && 'Thumbnail: Upload ảnh thumbnail mẫu. '}
                    {analysisOpts.description && 'Description: Nhập mẫu mô tả YouTube. '}
                    {!analysisOpts.voiceStyle && !analysisOpts.title && !analysisOpts.thumbnail && !analysisOpts.description && 'Chọn ít nhất 1 mục để phân tích.'}
                </p>
                {analysisOpts.description && (
                    <div style={{ marginTop: '0.6rem' }}>
                        <label style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.3rem' }}>
                            CTA / Footer Template
                        </label>
                        <p style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', margin: '0 0 0.4rem', lineHeight: 1.4 }}>
                            Nhập phần CTA cá nhân (link kênh, social, tagline). AI sẽ dùng chính xác nội dung này khi sinh description.
                        </p>
                        <textarea
                            value={analysisOpts.customCta || ''}
                            onChange={e => setPipeline(p => ({
                                ...p,
                                styleAnalysis: { ...normalizeAnalysis(p.styleAnalysis), customCta: e.target.value },
                            }))}
                            placeholder={`Ví dụ:\n━━━━━━━━━━━━━━━━━━\n- Đăng ký kênh: [LINK]\n- Follow Tiktok: @your_handle\n- Hợp tác: email@example.com\n#hashtag1 #hashtag2`}
                            style={{
                                width: '100%', minHeight: '90px', padding: '0.5rem 0.6rem', borderRadius: '8px',
                                border: '1px solid var(--border-color)', background: 'var(--bg-tertiary)',
                                color: 'var(--text-primary)', fontSize: '0.75rem', lineHeight: 1.5,
                                resize: 'vertical', fontFamily: 'inherit',
                            }}
                        />
                    </div>
                )}


            </div>
        );
    }

    function renderSeoControls() {
        return (
            <div className="step-controls">
                <div style={{ display: 'flex', gap: '0.4rem', marginBottom: '0.5rem' }}>
                    <button
                        onClick={() => setPipeline(p => ({ ...p, seoOptimize: { ...normalizeSeo(p.seoOptimize), mode: 'auto' } }))}
                        style={{
                            flex: 1, padding: '0.4rem 0.6rem', borderRadius: '8px', border: '1px solid',
                            borderColor: seoOpts.mode === 'auto' ? 'rgba(16, 185, 129, 0.5)' : 'var(--border-color)',
                            background: seoOpts.mode === 'auto' ? 'rgba(16, 185, 129, 0.15)' : 'transparent',
                            color: seoOpts.mode === 'auto' ? '#10B981' : 'var(--text-secondary)',
                            cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, transition: 'all 0.2s',
                        }}
                    >
                        ⚡ AI Tự Động
                    </button>
                    <button
                        onClick={() => setPipeline(p => ({ ...p, seoOptimize: { ...normalizeSeo(p.seoOptimize), mode: 'review' } }))}
                        style={{
                            flex: 1, padding: '0.4rem 0.6rem', borderRadius: '8px', border: '1px solid',
                            borderColor: seoOpts.mode === 'review' ? 'rgba(168, 85, 247, 0.5)' : 'var(--border-color)',
                            background: seoOpts.mode === 'review' ? 'rgba(168, 85, 247, 0.15)' : 'transparent',
                            color: seoOpts.mode === 'review' ? '#A855F7' : 'var(--text-secondary)',
                            cursor: 'pointer', fontSize: '0.75rem', fontWeight: 600, transition: 'all 0.2s',
                        }}
                    >
                        👁 Duyệt Trước
                    </button>
                </div>
                <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', margin: 0, lineHeight: 1.4 }}>
                    {seoOpts.mode === 'auto'
                        ? 'AI tự động sinh metadata SEO và inject vào video khi export.'
                        : 'AI sinh metadata SEO → hiển thị popup để bạn chỉnh sửa trước khi inject.'}
                </p>
            </div>
        );
    }

    function renderExpandedControls(stepId: string) {
        switch (stepId) {
            case 'scriptGeneration': return renderScriptControls();
            case 'voiceGeneration': return renderVoiceControls();
            case 'videoProduction': return renderVideoControls();
            case 'styleAnalysis': return renderStyleControls();
            case 'seoOptimize': return renderSeoControls();
            default: return null;
        }
    }

    // 
    // RIGHT PANEL: Detailed overview of each enabled step
    // 

    function renderDetailedOverview() {
        return (
            <div className="overview">
                {/* Pipeline flow */}
                <div className="ov-flow">
                    <h4 className="ov-section-title">Quy trình sẽ thực hiện</h4>
                    <div className="ov-timeline">
                        {STEPS.filter(step => isEnabled(step.id)).map((step, i, enabledSteps) => (
                            <div key={step.id} className="ov-tl-item on">
                                <div className="ov-tl-indicator">
                                    <div className="ov-tl-dot active">
                                        {i + 1}
                                    </div>
                                    {i < enabledSteps.length - 1 && <div className="ov-tl-line active" />}
                                </div>
                                <div className="ov-tl-content">
                                    <div className="ov-tl-header">

                                        <span className="ov-tl-label">{step.label}</span>
                                        <span className="ov-tl-status on">Bật</span>
                                    </div>
                                    {renderStepDetail(step.id)}
                                    {step.children && (
                                        <div className="ov-tl-subs">
                                            {step.children.map(sub => {
                                                const subOn = step.id === 'styleAnalysis'
                                                    ? analysisOpts[sub.id as keyof AnalysisOptions]
                                                    : pipeline.videoProduction[sub.id as keyof typeof pipeline.videoProduction];
                                                return (
                                                    <span key={sub.id} className={`ov-sub-chip ${subOn ? 'on' : 'off'}`}>
                                                        {sub.label}
                                                    </span>
                                                );
                                            })}
                                        </div>
                                    )}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Config summary at bottom */}
                <div className="ov-config-summary">
                    <h4 className="ov-section-title">Tóm tắt cấu hình</h4>
                    <div className="ov-config-grid">
                        {pipeline.scriptGeneration && (
                            <div className="ov-config-card">
                                <div className="ov-config-info">
                                    <span className="ov-config-label">Kịch bản</span>
                                    <span className="ov-config-val">
                                        {as_.targetWordCount} từ • {as_.language ? LANG_LABELS[as_.language] : 'Tự nhận diện'}
                                        {as_.dialect ? ` • Giọng ${as_.dialect}` : ''}
                                    </span>
                                    {as_.enableStorytellingStyle && (
                                        <span className="ov-config-val">
                                            Dẫn chuyện: {STYLE_LABELS[as_.storytellingStyle]} • {VOICE_LABELS[as_.narrativeVoice]}
                                        </span>
                                    )}
                                    {as_.enableAudienceAddress && as_.audienceAddress && (
                                        <span className="ov-config-val">Xưng hô: "{as_.audienceAddress}"</span>
                                    )}
                                    {as_.enableValueType && (
                                        <span className="ov-config-val">
                                            CTA: {VALUE_LABELS[as_.valueType]}{as_.customValue ? ' • Có chi tiết' : ''}
                                        </span>
                                    )}
                                    {as_.addQuiz && (
                                        <span className="ov-config-val">Câu hỏi A/B sau hook</span>
                                    )}
                                </div>
                            </div>
                        )}
                        {pipeline.voiceGeneration && (
                            <div className="ov-config-card">
                                <div className="ov-config-info">
                                    <span className="ov-config-label">Voice</span>
                                    <span className="ov-config-val">
                                        {config.voiceLanguage ? (config.selectedVoice || '—') : 'Tự nhận diện (tự chọn voice theo ngôn ngữ kịch bản)'} • Tốc độ {config.voiceSpeed}x
                                    </span>
                                    <span className="ov-config-val">
                                        Split: {config.splitMode === 'voiceover' ? 'Voiceover (5-8s)' : 'Footage (3-5s)'}
                                        {' • Scene: '}{MODE_LABELS[config.sceneMode]}
                                    </span>
                                    {config.voiceLanguage && (
                                        <span className="ov-config-val">Ngôn ngữ: {LANG_LABELS[config.voiceLanguage]}</span>
                                    )}
                                </div>
                            </div>
                        )}
                        {isEnabled('videoProduction') && (
                            <div className="ov-config-card">
                                <div className="ov-config-info">
                                    <span className="ov-config-label">Video</span>
                                    <span className="ov-config-val">
                                        {ORIENT_LABELS[config.footageOrientation] || config.footageOrientation} • {config.videoQuality}
                                        {config.enableSubtitles ? ' • Phụ đề bật' : ''}
                                    </span>
                                    <span className="ov-config-val">
                                        {[
                                            pipeline.videoProduction.video_prompts && 'Prompts Video',
                                            pipeline.videoProduction.image_prompts && 'Prompts Ảnh',
                                            pipeline.videoProduction.keywords && 'Keywords',
                                            pipeline.videoProduction.footage && 'Footage',
                                        ].filter(Boolean).join(' • ')}
                                    </span>
                                    {pipeline.videoProduction.image_prompts && (
                                        <span className="ov-config-val">Ảnh: {IMAGE_PROMPT_MODE_LABELS[pipeline.videoProduction.image_prompt_mode] || pipeline.videoProduction.image_prompt_mode}</span>
                                    )}
                                    {pipeline.videoProduction.video_prompts && (
                                        <span className="ov-config-val">Video: {VIDEO_PROMPT_MODE_LABELS[pipeline.videoProduction.video_prompt_mode] || pipeline.videoProduction.video_prompt_mode}</span>
                                    )}
                                </div>
                            </div>
                        )}
                        {isSeoEnabled(pipeline.seoOptimize) && (
                            <div className="ov-config-card">
                                <div className="ov-config-info">
                                    <span className="ov-config-label">SEO Thô</span>
                                    <span className="ov-config-val">
                                        {seoOpts.mode === 'auto' ? '⚡ AI Tự Động' : '👁 Duyệt Trước'}
                                        • Metadata • Title • Tags • Hash
                                    </span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div >
        );
    }

    function renderStepDetail(stepId: string) {
        switch (stepId) {
            case 'styleAnalysis': {
                const activeAnalysis: string[] = [];
                if (analysisOpts.voiceStyle) activeAnalysis.push('Giọng văn');
                if (analysisOpts.title) activeAnalysis.push('Title SEO');
                if (analysisOpts.thumbnail) activeAnalysis.push('Thumbnail');
                if (analysisOpts.description) activeAnalysis.push('Description SEO');
                return (
                    <div className="ov-tl-detail-block">
                        <p className="ov-tl-detail">
                            AI phân tích phong cách dựa trên mẫu bạn cung cấp, sau đó tự động tạo output theo phong cách đã học.
                        </p>
                        {activeAnalysis.length > 0 && (
                            <div className="ov-detail-chips">
                                {activeAnalysis.map((a, i) => <span key={i} className="ov-chip">{a}</span>)}
                            </div>
                        )}
                    </div>
                );
            }
            case 'scriptGeneration': {
                const features: string[] = [];
                features.push(`${as_.targetWordCount} từ`);
                features.push(as_.language ? LANG_LABELS[as_.language] : 'Tự nhận diện');
                if (as_.dialect) features.push(as_.dialect);
                if (as_.enableStorytellingStyle) features.push(STYLE_LABELS[as_.storytellingStyle]);
                if (as_.enableStorytellingStyle) features.push(VOICE_LABELS[as_.narrativeVoice]);
                if (as_.enableAudienceAddress && as_.audienceAddress) features.push(`"${as_.audienceAddress}"`);
                if (as_.enableValueType) features.push(VALUE_LABELS[as_.valueType]);
                if (as_.addQuiz) features.push('Câu hỏi A/B sau hook');
                return (
                    <div className="ov-tl-detail-block">
                        <p className="ov-tl-detail">
                            AI sẽ phân tích nội dung gốc, tạo outline, viết kịch bản mới theo phong cách đã phân tích, rồi kiểm tra tính tương đồng để đảm bảo chất lượng.
                        </p>
                        <div className="ov-detail-chips">
                            {features.map((f, i) => <span key={i} className="ov-chip">{f}</span>)}
                        </div>
                    </div>
                );
            }
            case 'voiceGeneration':
                return (
                    <div className="ov-tl-detail-block">
                        <p className="ov-tl-detail">
                            Kịch bản sẽ được chia thành từng scene rồi tạo giọng đọc AI tự động. Mỗi scene tạo ra 1 file audio riêng.
                        </p>
                        <div className="ov-detail-chips">
                            <span className="ov-chip">{config.voiceLanguage ? LANG_LABELS[config.voiceLanguage] : 'Tự nhận diện'}</span>
                            <span className="ov-chip">{config.voiceSpeed}x</span>
                            <span className="ov-chip">{config.splitMode === 'voiceover' ? 'Voiceover 5-8s' : 'Footage 3-5s'}</span>
                            <span className="ov-chip">{MODE_LABELS[config.sceneMode]}</span>
                        </div>
                    </div>
                );
            case 'videoProduction':
                return (
                    <div className="ov-tl-detail-block">
                        <p className="ov-tl-detail">
                            Tạo prompts cho từng scene, tìm kiếm video footage phù hợp từ Pexels/Pixabay, rồi ghép thành video hoàn chỉnh có phụ đề.
                        </p>
                        <div className="ov-detail-chips">
                            <span className="ov-chip">{ORIENT_LABELS[config.footageOrientation]}</span>
                            <span className="ov-chip">{config.videoQuality}</span>
                            <span className="ov-chip">{config.enableSubtitles ? 'Phụ đề bật' : 'Phụ đề tắt'}</span>
                        </div>
                    </div>
                );
            case 'seoOptimize':
                return (
                    <div className="ov-tl-detail-block">
                        <p className="ov-tl-detail">
                            AI tự động sinh keywords, title SEO, tags, filename, và inject metadata + hash unique vào video.
                        </p>
                        <div className="ov-detail-chips">
                            <span className="ov-chip">{seoOpts.mode === 'auto' ? '⚡ Tự Động' : '👁 Duyệt Trước'}</span>
                            <span className="ov-chip">Metadata</span>
                            <span className="ov-chip">SEO Title</span>
                            <span className="ov-chip">Tags</span>
                            <span className="ov-chip">Hash Unique</span>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    }

    return (
        <div className="pipeline-section">
            <div className="pipe-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>

                    <h3 className="pipe-title">Chọn quy trình & cấu hình</h3>
                </div>
                <span className="pipe-badge">{enabledCount}/5 bước</span>
            </div>

            <div className="pipe-panels">
                {/*  LEFT: Steps + Controls  */}
                <div className="pipe-left">
                    {/* Language Selection Bar */}
                    <div className="lang-bar">
                        <div className="lang-bar-header">
                            <span className="lang-bar-title">Ngôn ngữ</span>
                        </div>
                        <div className="lang-bar-selects">
                            <div className="lang-bar-field">
                                <label>Đầu vào</label>
                                <select value="" disabled
                                    style={{ opacity: 0.7, cursor: 'not-allowed' }}>
                                    <option value="">Tự nhận diện</option>
                                </select>
                            </div>
                            <span className="lang-bar-arrow">→</span>
                            <div className="lang-bar-field">
                                <label>Đầu ra</label>
                                <select value={as_.language}
                                    onChange={e => {
                                        const newLang = e.target.value;
                                        setAdvancedSettings((s: any) => ({ ...s, language: newLang, dialect: '' }));
                                        // Auto-sync voice language to match output language
                                        config.setVoiceLanguage(newLang);
                                        const voices = config.voicesByLanguage[newLang]?.voices || [];
                                        config.setSelectedVoice(voices.length > 0 ? voices[0].id : '');
                                    }}>
                                    <option value="">= Đầu vào</option>
                                    {Object.entries(LANG_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                                </select>
                            </div>
                        </div>
                        {as_.sourceLanguage && as_.language && as_.sourceLanguage !== as_.language && (
                            <div className="lang-bar-badge">
                                🔄 Dịch {LANG_LABELS[as_.sourceLanguage] || as_.sourceLanguage} → {LANG_LABELS[as_.language] || as_.language}
                            </div>
                        )}
                    </div>
                    {STEPS.map(step => {
                        const on = isEnabled(step.id);
                        const expanded = expandedStep === step.id;
                        return (
                            <div key={step.id} className="pipe-step-block">
                                <div className={`pipe-step ${expanded ? 'expanded' : ''} ${on ? '' : 'disabled'}`}
                                    onClick={() => setExpandedStep(expanded ? '' : step.id)}>
                                    <label className="pipe-check" onClick={e => e.stopPropagation()}>
                                        <input type="checkbox" checked={on || !!isStepLocked(step.id)} onChange={() => toggleStep(step.id)}
                                            disabled={(step.id === 'styleAnalysis' && analysisLocked) || !!isStepLocked(step.id)} />
                                        <span className="pipe-mark" />
                                    </label>
                                    <div className="pipe-step-info">
                                        <span className="pipe-step-label">
                                            {step.label}
                                            {step.id === 'styleAnalysis' && analysisLocked && (
                                                <span style={{ marginLeft: 6, fontSize: '0.7rem', color: 'rgba(255,215,0,0.7)' }}>🔒 Đã phân tích</span>
                                            )}
                                            {isStepLocked(step.id) && (
                                                <span style={{ marginLeft: 6, fontSize: '0.65rem', color: 'rgba(255,215,0,0.6)' }}>🔒</span>
                                            )}
                                        </span>
                                        <span className="pipe-step-desc">{step.desc}</span>
                                    </div>
                                    <span className={`pipe-chevron ${expanded ? 'open' : ''}`}></span>
                                </div>

                                {step.children && expanded && (
                                    <div className="pipe-subs">
                                        {step.children.map(sub => {
                                            const subOn: boolean = step.id === 'styleAnalysis'
                                                ? !!analysisOpts[sub.id as keyof AnalysisOptions]
                                                : !!pipeline.videoProduction[sub.id as keyof typeof pipeline.videoProduction];
                                            return (
                                                <div key={sub.id}>
                                                    <div className={`pipe-sub ${(subOn || !!isSubLocked(sub.id)) ? '' : 'disabled'}`}>
                                                        <label className="pipe-check" onClick={e => e.stopPropagation()}>
                                                            <input type="checkbox" checked={subOn || !!isSubLocked(sub.id)}
                                                                onChange={() => toggleSub(sub.id, step.id)}
                                                                disabled={!!isSubLocked(sub.id)} />
                                                            <span className="pipe-mark sm" />
                                                        </label>
                                                        <span className="pipe-sub-label">
                                                            {sub.label}
                                                            {isSubLocked(sub.id) && <span style={{ marginLeft: 4, fontSize: '0.6rem', color: 'rgba(255,215,0,0.6)' }}>🔒</span>}
                                                        </span>
                                                    </div>
                                                    {/* Sub-option radios for image_prompts */}
                                                    {sub.id === 'image_prompts' && subOn && step.id === 'videoProduction' && (() => {
                                                        const vMode = pipeline.videoProduction.video_prompt_mode;
                                                        const lockedModes: string[] = pipeline.videoProduction.video_prompts && (vMode === 'full_sync')
                                                            ? ['reference', 'scene_builder']
                                                            : pipeline.videoProduction.video_prompts && (vMode === 'character_sync') ? ['reference'] : [];
                                                        return (
                                                            <div className="pipe-sub-modes">
                                                                {Object.entries(IMAGE_PROMPT_MODE_LABELS).map(([mode, label]) => {
                                                                    const isLocked = lockedModes.includes(mode);
                                                                    const isActive = isLocked || pipeline.videoProduction.image_prompt_mode === mode;
                                                                    return (
                                                                        <label key={mode} className={`pipe-mode-radio ${isActive ? 'active' : ''} ${isLocked ? 'locked' : ''}`}
                                                                            onClick={e => e.stopPropagation()}>
                                                                            <input type="radio" name="image_prompt_mode" value={mode}
                                                                                checked={isActive}
                                                                                disabled={isLocked}
                                                                                onChange={() => setPipeline(p => ({ ...p, videoProduction: { ...p.videoProduction, image_prompt_mode: mode as any } }))} />
                                                                            <span className="pipe-mode-dot" />
                                                                            <span>{label}{isLocked && ' 🔒'}</span>
                                                                        </label>
                                                                    );
                                                                })}
                                                            </div>
                                                        );
                                                    })()}
                                                    {sub.id === 'video_prompts' && subOn && step.id === 'videoProduction' && (
                                                        <>
                                                            <div className="pipe-sub-modes">
                                                                {Object.entries(VIDEO_PROMPT_MODE_LABELS).map(([mode, label]) => (
                                                                    <label key={mode} className={`pipe-mode-radio ${pipeline.videoProduction.video_prompt_mode === mode ? 'active' : ''}`}
                                                                        onClick={e => e.stopPropagation()}>
                                                                        <input type="radio" name="video_prompt_mode" value={mode}
                                                                            checked={pipeline.videoProduction.video_prompt_mode === mode}
                                                                            onChange={() => {
                                                                                const newMode = mode as any;
                                                                                setPipeline(p => {
                                                                                    const updated = { ...p.videoProduction, video_prompt_mode: newMode };
                                                                                    // Auto-lock image mode based on video mode
                                                                                    if (newMode === 'character_sync' || newMode === 'full_sync') {
                                                                                        updated.image_prompt_mode = 'reference';
                                                                                        updated.image_prompts = true;
                                                                                    }
                                                                                    return { ...p, videoProduction: updated };
                                                                                });
                                                                            }} />
                                                                        <span className="pipe-mode-dot" />
                                                                        <span>{label}</span>
                                                                    </label>
                                                                ))}
                                                            </div>
                                                            {/* Mode-specific info text */}
                                                            <p style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', margin: '0.35rem 0 0', lineHeight: 1.4, paddingLeft: '0.2rem' }}>
                                                                {pipeline.videoProduction.video_prompt_mode === 'character_sync' && 'Panel phân tích nhân vật sẽ hiện ở bước Phân tích'}
                                                                {pipeline.videoProduction.video_prompt_mode === 'scene_sync' && 'Panel phân tích phong cách sẽ hiện ở bước Phân tích'}
                                                                {pipeline.videoProduction.video_prompt_mode === 'full_sync' && 'Panel phân tích nhân vật + phong cách + bối cảnh sẽ hiện ở bước Phân tích'}
                                                            </p>
                                                        </>
                                                    )}
                                                    {/* Warning: Footage needs Voice */}
                                                    {sub.id === 'footage' && subOn && !pipeline.voiceGeneration && (
                                                        <p style={{ fontSize: '0.68rem', color: '#f59e0b', margin: '0.35rem 0 0', lineHeight: 1.4, paddingLeft: '0.2rem' }}>
                                                            ⚠️ Footage cần Voice để ghép video. Bật Voice hoặc tắt Footage.
                                                        </p>
                                                    )}
                                                </div>
                                            );
                                        })}
                                    </div>
                                )}

                                {expanded && on && (
                                    <div className="pipe-controls-area">
                                        {renderExpandedControls(step.id)}
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/*  RIGHT: Detailed Overview  */}
                <div className="pipe-right">
                    <div className="pr-head">
                        <span>Tổng quan quy trình</span>
                    </div>
                    <div className="pr-body">
                        {renderDetailedOverview()}
                    </div>
                </div>
            </div>

            <style>{`
                .pipeline-section { margin-bottom: 0; }

                .pipe-header {
                    display: flex; align-items: center; justify-content: space-between;
                    margin-bottom: 0.75rem; padding: 0.65rem 1rem;
                    background: linear-gradient(135deg, rgba(255,215,0,0.08), rgba(245,158,11,0.04));
                    border: 1px solid rgba(255,215,0,0.12); border-radius: 12px;
                }
                .pipe-title { margin: 0; font-family: 'Fredoka', sans-serif; font-size: 0.95rem; font-weight: 600; }
                .pipe-badge {
                    font-size: 0.72rem; color: #FFD700; background: rgba(255,215,0,0.1);
                    padding: 0.2rem 0.65rem; border-radius: 20px; border: 1px solid rgba(255,215,0,0.2); font-weight: 600;
                }

                .pipe-panels { display: flex; gap: 0.75rem; }

                /*  LEFT  */
                .pipe-left {
                    width: 320px; flex-shrink: 0; background: var(--bg-secondary);
                    border: 1px solid var(--border-color); border-radius: 14px;
                    padding: 0.5rem; display: flex; flex-direction: column; gap: 0.2rem;
                    overflow-y: auto; max-height: 560px;
                }

                .pipe-step-block { border-bottom: 1px solid rgba(255,255,255,0.04); }
                .pipe-step-block:last-child { border-bottom: none; }

                .pipe-step {
                    display: flex; align-items: center; gap: 0.5rem;
                    padding: 0.55rem 0.6rem; border-radius: 10px; cursor: pointer;
                    transition: all 0.15s; border: 1.5px solid transparent;
                }
                .pipe-step:hover { background: rgba(255,255,255,0.03); }
                .pipe-step.expanded { background: rgba(255,215,0,0.06); border-color: rgba(255,215,0,0.18); }
                .pipe-step.disabled .pipe-step-label { opacity: 0.4; text-decoration: line-through; }
                .pipe-step.disabled .pipe-emoji { opacity: 0.3; }

                .pipe-check { position: relative; display: flex; align-items: center; cursor: pointer; flex-shrink: 0; }
                .pipe-check input { position: absolute; opacity: 0; width: 0; height: 0; }
                .pipe-mark {
                    width: 20px; height: 20px; border: 2px solid rgba(255,215,0,0.3); border-radius: 6px;
                    background: rgba(255,255,255,0.03); transition: all 0.2s;
                    display: flex; align-items: center; justify-content: center;
                }
                .pipe-mark.sm { width: 16px; height: 16px; border-radius: 4px; }
                .pipe-mark::after { content: ''; font-size: 11px; font-weight: 700; color: #000; opacity: 0; transition: opacity 0.15s; }
                .pipe-check input:checked + .pipe-mark {
                    background: linear-gradient(135deg, #FFD700, #F59E0B); border-color: #FFD700;
                    box-shadow: 0 2px 6px rgba(255,215,0,0.25);
                }
                .pipe-check input:checked + .pipe-mark::after { opacity: 1; }

                .pipe-emoji { font-size: 1.05rem; flex-shrink: 0; }
                .pipe-step-info { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
                .pipe-step-label { font-weight: 600; font-size: 0.82rem; color: var(--text-primary); }
                .pipe-step-desc { font-size: 0.66rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

                .pipe-chevron {
                    font-size: 0.85rem; color: var(--text-secondary); transition: transform 0.2s; flex-shrink: 0;
                }
                .pipe-chevron.open { transform: rotate(180deg); color: #FFD700; }

                .pipe-subs {
                    margin: 0 0 0 2rem; padding: 0.2rem 0 0.3rem 0.7rem;
                    border-left: 2px solid rgba(255,215,0,0.12);
                    display: flex; flex-direction: column; gap: 0.1rem;
                }
                .pipe-sub { display: flex; align-items: center; gap: 0.35rem; padding: 0.25rem 0.4rem; border-radius: 6px; }
                .pipe-sub:hover { background: rgba(255,255,255,0.02); }
                .pipe-sub.disabled .pipe-sub-label { opacity: 0.4; text-decoration: line-through; }
                .pipe-sub-label { font-size: 0.76rem; color: var(--text-primary); font-weight: 500; }

                .pipe-sub-modes {
                    margin: 0.15rem 0 0.25rem 2.2rem; padding: 0.25rem 0;
                    display: flex; flex-direction: column; gap: 0.1rem;
                    animation: slideDown 0.15s ease;
                }
                .pipe-mode-radio {
                    display: flex; align-items: center; gap: 0.4rem;
                    padding: 0.2rem 0.5rem; border-radius: 6px; cursor: pointer;
                    font-size: 0.72rem; color: var(--text-secondary); transition: all 0.15s;
                }
                .pipe-mode-radio:hover { background: rgba(255,255,255,0.03); color: var(--text-primary); }
                .pipe-mode-radio.active { color: #FFD700; }
                .pipe-mode-radio input { position: absolute; opacity: 0; width: 0; height: 0; }
                .pipe-mode-dot {
                    width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;
                    border: 2px solid rgba(255,215,0,0.25); background: transparent; transition: all 0.2s;
                }
                .pipe-mode-radio.active .pipe-mode-dot {
                    border-color: #FFD700; background: #FFD700;
                    box-shadow: inset 0 0 0 2px var(--bg-secondary), 0 0 6px rgba(255,215,0,0.3);
                }
                .pipe-mode-radio.locked {
                    cursor: not-allowed; opacity: 0.7;
                    pointer-events: none;
                }
                .pipe-mode-radio.locked .pipe-mode-dot {
                    border-color: rgba(255,215,0,0.5); background: rgba(255,215,0,0.5);
                    box-shadow: inset 0 0 0 2px var(--bg-secondary);
                }

                .pipe-controls-area {
                    margin: 0 0.3rem 0.5rem 0.3rem; padding: 0.6rem 0.7rem;
                    background: rgba(255,215,0,0.03); border: 1px solid rgba(255,215,0,0.1);
                    border-radius: 10px; animation: slideDown 0.2s ease;
                }
                @keyframes slideDown { from { opacity: 0; max-height: 0; } to { opacity: 1; max-height: 500px; } }

                .step-controls { display: flex; flex-direction: column; gap: 0.4rem; }
                .sc-row { display: flex; gap: 0.5rem; flex-wrap: wrap; }
                .sc-field { display: flex; flex-direction: column; gap: 0.2rem; flex: 1; min-width: 100px; }
                .sc-field label { font-size: 0.7rem; font-weight: 600; color: var(--text-secondary); }
                .sc-input {
                    font-size: 0.76rem; padding: 0.32rem 0.45rem; background: var(--bg-tertiary);
                    border: 1px solid var(--border-color); border-radius: 6px; color: var(--text-primary);
                    width: 100%; box-sizing: border-box; font-family: inherit;
                }
                select.sc-input { cursor: pointer; }
                textarea.sc-input { resize: vertical; min-height: 34px; }

                .sc-toggles {
                    display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.35rem;
                    margin-top: 0.3rem;
                }
                .sc-toggle {
                    background: var(--bg-tertiary); border: 1px solid var(--border-color);
                    border-radius: 7px; padding: 0.4rem; transition: all 0.2s;
                }
                .sc-toggle.on { border-color: rgba(255,215,0,0.25); background: rgba(255,215,0,0.03); }
                .sc-toggle-head {
                    display: flex; justify-content: space-between; align-items: center;
                    font-size: 0.75rem; font-weight: 600;
                }
                .sc-toggle-body { display: flex; flex-direction: column; gap: 0.3rem; margin-top: 0.35rem; }

                .cta-preview { margin: 0.1rem 0; }
                .cta-desc {
                    font-size: 0.7rem; color: var(--text-secondary); margin: 0;
                    line-height: 1.45; padding: 0.35rem 0.5rem;
                    background: rgba(255,215,0,0.04); border-radius: 6px;
                    border-left: 2px solid rgba(245,158,11,0.35);
                }

                /*  RIGHT (wider)  */
                .pipe-right {
                    flex: 1; background: var(--bg-secondary); border: 1px solid var(--border-color);
                    border-radius: 14px; display: flex; flex-direction: column; min-height: 560px;
                }
                .pr-head {
                    display: flex; align-items: center; gap: 0.4rem; font-weight: 600; font-size: 0.88rem;
                    padding: 0.65rem 1rem; border-bottom: 1px solid var(--border-color); flex-shrink: 0;
                }
                .pr-body { flex: 1; padding: 0.85rem 1rem; overflow-y: auto; display: flex; flex-direction: column; }

                /* Overview */
                .overview { display: flex; flex-direction: column; flex: 1; gap: 0; }
                .ov-section-title {
                    margin: 0 0 0.6rem; font-size: 0.82rem; font-weight: 700; color: var(--text-primary);
                    display: flex; align-items: center; gap: 0.3rem;
                }
                .ov-flow { flex: 1; }

                /* Timeline */
                .ov-timeline { display: flex; flex-direction: column; gap: 0; }
                .ov-tl-item { display: flex; gap: 0.65rem; }
                .ov-tl-indicator { display: flex; flex-direction: column; align-items: center; flex-shrink: 0; width: 28px; }
                .ov-tl-dot {
                    width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
                    font-size: 0.68rem; font-weight: 700; border: 2px solid var(--border-color);
                    background: var(--bg-tertiary); color: var(--text-secondary); transition: all 0.2s; flex-shrink: 0;
                }
                .ov-tl-dot.active {
                    background: linear-gradient(135deg, #FFD700, #F59E0B); border-color: #FFD700;
                    color: #000; box-shadow: 0 2px 8px rgba(255,215,0,0.3);
                }
                .ov-tl-line { width: 2px; flex: 1; min-height: 8px; background: var(--border-color); }
                .ov-tl-item.on .ov-tl-line { background: rgba(255,215,0,0.25); }

                .ov-tl-content { flex: 1; padding-bottom: 0.65rem; min-width: 0; }
                .ov-tl-header { display: flex; align-items: center; gap: 0.35rem; margin-bottom: 0.15rem; }
                .ov-tl-emoji { font-size: 0.95rem; }
                .ov-tl-label { font-weight: 600; font-size: 0.82rem; color: var(--text-primary); }
                .ov-tl-label.disabled { opacity: 0.4; text-decoration: line-through; }
                .ov-tl-status {
                    margin-left: auto; font-size: 0.62rem; font-weight: 600;
                    padding: 0.1rem 0.45rem; border-radius: 4px;
                }
                .ov-tl-status.on { background: rgba(52,211,153,0.12); color: #34d399; }
                .ov-tl-status.off { background: rgba(255,255,255,0.04); color: var(--text-secondary); }

                .ov-tl-detail {
                    font-size: 0.74rem; color: var(--text-secondary); line-height: 1.5;
                    margin: 0.15rem 0 0.3rem; padding: 0;
                }
                .ov-tl-detail-block { display: flex; flex-direction: column; gap: 0.2rem; }

                .ov-detail-chips { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.1rem; }
                .ov-chip {
                    font-size: 0.65rem; padding: 0.15rem 0.5rem; border-radius: 5px;
                    background: rgba(255,215,0,0.07); border: 1px solid rgba(255,215,0,0.15);
                    color: var(--text-primary); white-space: nowrap;
                }

                .ov-tl-subs { display: flex; flex-wrap: wrap; gap: 0.25rem; margin-top: 0.2rem; }
                .ov-sub-chip {
                    font-size: 0.66rem; padding: 0.12rem 0.45rem; border-radius: 4px;
                    background: var(--bg-tertiary); border: 1px solid var(--border-color);
                }
                .ov-sub-chip.on { border-color: rgba(52,211,153,0.2); }
                .ov-sub-chip.off { opacity: 0.4; text-decoration: line-through; }

                /* Config summary cards */
                .ov-config-summary {
                    margin-top: auto; padding-top: 0.75rem;
                    border-top: 1px solid var(--border-color);
                }
                .ov-config-grid { display: flex; flex-direction: column; gap: 0.4rem; }
                .ov-config-card {
                    display: flex; align-items: center; gap: 0.6rem; padding: 0.55rem 0.7rem;
                    background: linear-gradient(135deg, rgba(255,215,0,0.04), rgba(255,255,255,0.02));
                    border: 1px solid rgba(255,215,0,0.1); border-radius: 10px;
                    transition: all 0.15s;
                }
                .ov-config-card:hover { border-color: rgba(255,215,0,0.25); }
                .ov-config-icon { font-size: 1.1rem; flex-shrink: 0; }
                .ov-config-info { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
                .ov-config-label { font-size: 0.7rem; font-weight: 700; color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.3px; }
                .ov-config-val { font-size: 0.78rem; color: var(--text-primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

                /* Language Selection Bar */
                .lang-bar {
                    padding: 0.5rem 0.6rem;
                    background: linear-gradient(135deg, rgba(59,130,246,0.06), rgba(139,92,246,0.04));
                    border: 1px solid rgba(59,130,246,0.15);
                    border-radius: 10px;
                    display: flex; flex-direction: column; gap: 0.35rem;
                    margin-bottom: 0.25rem;
                }
                .lang-bar-header {
                    display: flex; align-items: center; gap: 0.35rem;
                }
                .lang-bar-icon { font-size: 0.9rem; }
                .lang-bar-title {
                    font-size: 0.76rem; font-weight: 700; color: var(--text-primary);
                    letter-spacing: 0.2px;
                }
                .lang-bar-selects {
                    display: flex; align-items: flex-end; gap: 0.4rem;
                }
                .lang-bar-field {
                    flex: 1; display: flex; flex-direction: column; gap: 0.15rem;
                }
                .lang-bar-field label {
                    font-size: 0.62rem; font-weight: 600; color: var(--text-secondary);
                    text-transform: uppercase; letter-spacing: 0.5px;
                }
                .lang-bar-field select {
                    font-size: 0.76rem; padding: 0.3rem 0.45rem;
                    background: var(--bg-tertiary); border: 1px solid var(--border-color);
                    border-radius: 7px; color: var(--text-primary);
                    cursor: pointer; font-family: inherit; width: 100%;
                }
                .lang-bar-field select:focus {
                    border-color: rgba(59,130,246,0.4);
                    outline: none; box-shadow: 0 0 0 2px rgba(59,130,246,0.1);
                }
                .lang-bar-arrow {
                    font-size: 0.9rem; color: var(--text-secondary);
                    padding-bottom: 0.3rem; flex-shrink: 0; font-weight: 600;
                }
                .lang-bar-badge {
                    font-size: 0.68rem; padding: 0.2rem 0.55rem;
                    background: rgba(139,92,246,0.1); border: 1px solid rgba(139,92,246,0.2);
                    border-radius: 6px; color: #a78bfa;
                    font-weight: 600; text-align: center;
                    animation: fadeIn 0.3s ease;
                }
                @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
            `}</style>
        </div >
    );
}
