import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// Types

// Script Structure - Nhịp văn/Cấu trúc kịch bản (tổng quan)
export interface ScriptStructure {
    avg_word_count: number;              // Số từ trung bình
    hook_duration: string;               // Hook chiếm bao lâu
    structure_breakdown: {               // Cấu trúc đoạn
        intro: { segments: number; purpose: string };
        body: { segments: number; purpose: string };
        conclusion: { segments: number; purpose: string };
    };
    climax_position: string;             // Cao trào/payoff nằm ở đâu
}

// StyleA - Unified style profile structure
export interface StyleA {
    // 
    // NHÓM 1: DNA CỐ ĐỊNH (không đổi theo kịch bản)
    // 
    voice_description: string;           //  Giọng văn
    storytelling_approach: string;       //  Cách dẫn chuyện
    authors_soul: string;                //  HỒN VĂN
    character_embodiment: string;        //  Cách nhập vai
    common_hook_types: string[];         //  HOOK patterns
    retention_techniques: string[];      //  Retention patterns
    cta_patterns: string[];              //  CTA patterns
    signature_phrases: string[];         //  Cụm từ đặc trưng
    unique_patterns: string[];           //  Pattern độc đáo
    tone_spectrum: string;               //  Tone (DNA)
    vocabulary_signature: string;        //  Từ vựng (DNA)
    emotional_palette: string;           //  Cảm xúc (DNA)
    script_structure: ScriptStructure;   //  Nhịp văn/Cấu trúc (DNA)

    // 
    // NHÓM 2: TÙY BIẾN (từ phân tích kịch bản gốc, ghép vào Giọng Văn A)
    // 
    core_angle: string;                  //  Core Angle (từ kịch bản gốc)
    viewer_insight: string;              //  INSIGHT người xem
    main_ideas: string[];                //  Những ý quan trọng
    narrative_perspective: string;       //  Ngôi kể
    audience_address: string;            //  Xưng hô khán giả
    cultural_markers: string;            //  Văn hóa vùng miền/quốc gia

    // 
    // METADATA
    // 
    source_scripts_count: number;        // Số kịch bản đã phân tích
    confidence_score: number;            // Độ tin cậy (0-1)
}

// Legacy alias for backward compatibility
export type StyleProfile = StyleA;

export interface Section {
    id: string;
    title: string;
    description: string;
    order: number;
    estimated_duration: number;
    keywords: string[];
}

export interface DraftSection {
    section_id: string;
    content: string;
    version: number;
    word_count: number;
    status: 'draft' | 'refined' | 'final' | 'error';
}

export interface ScriptResult {
    topic: string;
    style_profile: StyleProfile | null;
    outline: Section[];
    sections: DraftSection[];
    final_script: string;
    total_duration: number;
    word_count: number;
    created_at: string;
}

export interface Template {
    id: string;
    name: string;
    description: string;
    structure: string[];
}

interface ScriptWorkflowState {
    // Current step in wizard (1-4)
    currentStep: number;

    // Step 1: Reference scripts for style cloning (5-20 scripts)
    referenceScript: string;  // Single script (backward compat)
    referenceScripts: string[];  // Multiple scripts (5-20)
    styleA: StyleA | null;
    isAnalyzingStyle: boolean;

    // Step 2: Topic and outline
    topic: string;
    targetDuration: number; // seconds
    selectedTemplate: string | null;
    outline: Section[];
    isGeneratingOutline: boolean;

    // Channel & Language
    channelName: string;
    language: string;

    // Custom outline structure
    useCustomOutline: boolean;
    customOutlineStructure: string;

    // Remake mode
    remakeMode: boolean;
    remakeScript: string;

    // Step 3: Writing sections
    draftSections: DraftSection[];
    currentSectionIndex: number;
    isWritingSection: boolean;

    // Step 4: Final result
    finalScript: string;
    result: ScriptResult | null;
    isRunningPipeline: boolean;

    // Templates
    templates: Template[];

    // Error handling
    error: string | null;

    // Actions
    setStep: (step: number) => void;
    nextStep: () => void;
    prevStep: () => void;

    // Step 1 actions
    setReferenceScript: (script: string) => void;
    setReferenceScripts: (scripts: string[]) => void;
    addReferenceScript: (script: string) => void;
    removeReferenceScript: (index: number) => void;
    setStyleA: (profile: StyleA | null) => void;
    setAnalyzingStyle: (isAnalyzing: boolean) => void;

    // Step 2 actions
    setTopic: (topic: string) => void;
    setTargetDuration: (duration: number) => void;
    setSelectedTemplate: (templateId: string | null) => void;
    setOutline: (outline: Section[]) => void;
    setGeneratingOutline: (isGenerating: boolean) => void;
    updateSection: (sectionId: string, updates: Partial<Section>) => void;

    // Remake actions
    setRemakeMode: (mode: boolean) => void;
    setRemakeScript: (script: string) => void;

    // Channel & Language actions
    setChannelName: (name: string) => void;
    setLanguage: (lang: string) => void;

    // Custom outline actions
    setUseCustomOutline: (use: boolean) => void;
    setCustomOutlineStructure: (structure: string) => void;
    removeOutlineSection: (sectionId: string) => void;
    addOutlineSection: (section: Section) => void;
    reorderOutlineSections: (fromIndex: number, toIndex: number) => void;

    // Step 3 actions
    setDraftSections: (sections: DraftSection[]) => void;
    updateDraftSection: (sectionId: string, content: string) => void;
    setCurrentSectionIndex: (index: number) => void;
    setWritingSection: (isWriting: boolean) => void;

    // Step 4 actions
    setFinalScript: (script: string) => void;
    setResult: (result: ScriptResult | null) => void;
    setRunningPipeline: (isRunning: boolean) => void;

    // Templates
    setTemplates: (templates: Template[]) => void;

    // Error
    setError: (error: string | null) => void;

    // Reset
    reset: () => void;
}

const initialState = {
    currentStep: 1,
    referenceScript: '',
    referenceScripts: [] as string[],
    styleA: null,
    isAnalyzingStyle: false,
    topic: '',
    targetDuration: 180,
    selectedTemplate: null,
    outline: [],
    isGeneratingOutline: false,
    channelName: '',
    language: 'vi',
    useCustomOutline: false,
    customOutlineStructure: '',
    remakeMode: false,
    remakeScript: '',
    draftSections: [],
    currentSectionIndex: 0,
    isWritingSection: false,
    finalScript: '',
    result: null,
    isRunningPipeline: false,
    templates: [],
    error: null,
};

export const useScriptWorkflowStore = create<ScriptWorkflowState>()(
    persist(
        (set) => ({
            ...initialState,

            // Navigation
            setStep: (step) => set({ currentStep: step, error: null }),
            nextStep: () => set((state) => ({
                currentStep: Math.min(state.currentStep + 1, 4),
                error: null
            })),
            prevStep: () => set((state) => ({
                currentStep: Math.max(state.currentStep - 1, 1),
                error: null
            })),

            // Step 1: Style
            setReferenceScript: (script) => set({ referenceScript: script }),
            setReferenceScripts: (scripts) => set({ referenceScripts: scripts }),
            addReferenceScript: (script) => set((state) => ({
                referenceScripts: [...state.referenceScripts, script]
            })),
            removeReferenceScript: (index) => set((state) => ({
                referenceScripts: state.referenceScripts.filter((_, i) => i !== index)
            })),
            setStyleA: (profile) => set({ styleA: profile }),
            setAnalyzingStyle: (isAnalyzing) => set({ isAnalyzingStyle: isAnalyzing }),

            // Step 2: Outline
            setTopic: (topic) => set({ topic }),
            setTargetDuration: (duration) => set({ targetDuration: duration }),
            setSelectedTemplate: (templateId) => set({ selectedTemplate: templateId }),
            setOutline: (outline) => set({ outline }),
            setGeneratingOutline: (isGenerating) => set({ isGeneratingOutline: isGenerating }),
            updateSection: (sectionId, updates) => set((state) => ({
                outline: state.outline.map((s) =>
                    s.id === sectionId ? { ...s, ...updates } : s
                )
            })),

            // Remake
            setRemakeMode: (mode) => set({ remakeMode: mode }),
            setRemakeScript: (script) => set({ remakeScript: script }),

            // Channel & Language
            setChannelName: (name) => set({ channelName: name }),
            setLanguage: (lang) => set({ language: lang }),

            // Custom outline
            setUseCustomOutline: (use) => set({ useCustomOutline: use }),
            setCustomOutlineStructure: (structure) => set({ customOutlineStructure: structure }),
            removeOutlineSection: (sectionId) => set((state) => ({
                outline: state.outline
                    .filter((s) => s.id !== sectionId)
                    .map((s, idx) => ({ ...s, order: idx + 1 }))
            })),
            addOutlineSection: (section) => set((state) => ({
                outline: [...state.outline, { ...section, order: state.outline.length + 1 }]
            })),
            reorderOutlineSections: (fromIndex, toIndex) => set((state) => {
                const newOutline = [...state.outline];
                const [removed] = newOutline.splice(fromIndex, 1);
                newOutline.splice(toIndex, 0, removed);
                return { outline: newOutline.map((s, idx) => ({ ...s, order: idx + 1 })) };
            }),

            // Step 3: Writing
            setDraftSections: (sections) => set({ draftSections: sections }),
            updateDraftSection: (sectionId, content) => set((state) => ({
                draftSections: state.draftSections.map((s) =>
                    s.section_id === sectionId
                        ? { ...s, content, word_count: content.split(/\s+/).length }
                        : s
                )
            })),
            setCurrentSectionIndex: (index) => set({ currentSectionIndex: index }),
            setWritingSection: (isWriting) => set({ isWritingSection: isWriting }),

            // Step 4: Result
            setFinalScript: (script) => set({ finalScript: script }),
            setResult: (result) => set({ result }),
            setRunningPipeline: (isRunning) => set({ isRunningPipeline: isRunning }),

            // Templates
            setTemplates: (templates) => set({ templates }),

            // Error
            setError: (error) => set({ error }),

            // Reset
            reset: () => set(initialState),
        }),
        {
            name: 'script-workflow-storage',
            partialize: (state) => ({
                // Only persist templates, not active workflow state
                templates: state.templates,
            }),
        }
    )
);
