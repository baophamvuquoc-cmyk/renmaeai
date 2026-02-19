import { useState, useRef } from 'react';
import { useQueueStore } from '../../stores/useQueueStore';
import { youtubeApi } from '../../lib/api';
import {
    Plus,
    Play,
    Square,
    Trash2,
    Settings,
    FolderOpen,
    Clock,
    ChevronDown,
    ChevronUp,
    Link2,
    Loader2,
    X,
} from 'lucide-react';

// Labels for readable display
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
const MODE_LABELS: Record<string, string> = { footage: 'Footage', concept: 'Concept', storytelling: 'Storytelling', custom: 'Custom', voiceover: 'Voiceover' };
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

interface CurrentConfig {
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
    splitMode: string;
    sceneMode: string;
    selectedVoice: string;
    voiceLanguage: string;
    voiceSpeed: number;
    selectedModel: string;
    footageOrientation?: string;
    videoQuality?: string;
    enableSubtitles?: boolean;
    channelName?: string;
    promptStyle?: string;
    mainCharacter?: string;
    contextDescription?: string;
    pipelineSelection: {
        styleAnalysis: boolean | { voiceStyle: boolean; title: boolean; thumbnail: boolean; description: boolean };
        scriptGeneration: boolean;
        voiceGeneration: boolean;
        videoProduction: {
            video_prompts: boolean;
            image_prompts: boolean;
            keywords: boolean;
            footage: boolean;
            image_prompt_mode?: string;
            video_prompt_mode?: string;
        };
        seoOptimize?: boolean | { enabled: boolean; mode: string };
    };
}

interface QueueSidebarProps {
    activePresetName: string;
    onSelectOutputPath: () => void;
    currentConfig?: CurrentConfig;
    isPresetOpen: boolean;
    onPresetToggle: () => void;
    activeVoiceId?: string;
}

function ConfigRow({ label, value }: { label: string; value: string }) {
    return (
        <div style={{
            display: 'flex', alignItems: 'center', gap: '0.5rem',
            padding: '0.3rem 0', fontSize: '0.78rem', lineHeight: 1.3,
        }}>
            <span style={{ color: 'var(--text-secondary)', flexShrink: 0 }}>{label}:</span>
            <span style={{ color: 'var(--text-primary)', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {value}
            </span>
        </div>
    );
}

function PipelineTag({ label, enabled }: { label: string; enabled: boolean }) {
    return (
        <span style={{
            padding: '0.15rem 0.5rem',
            borderRadius: '6px',
            fontSize: '0.72rem',
            fontWeight: 600,
            background: enabled ? 'rgba(255, 215, 0, 0.12)' : 'var(--bg-tertiary)',
            color: enabled ? '#FFD700' : 'var(--text-secondary)',
            border: `1px solid ${enabled ? 'rgba(255, 215, 0, 0.25)' : 'var(--border-color)'}`,
            opacity: enabled ? 1 : 0.5,
            textDecoration: enabled ? 'none' : 'line-through',
        }}>
            {label}
        </span>
    );
}

export default function QueueSidebar({ activePresetName, onSelectOutputPath, currentConfig, isPresetOpen, onPresetToggle, activeVoiceId }: QueueSidebarProps) {
    const {
        items,
        maxConcurrent,
        delayBetweenMs,
        outputPath,
        isQueueRunning,
        exportOptions,
        addItem,
        clearCompleted,
        clearAll,
        setMaxConcurrent,
        setDelayBetween,
        setIsQueueRunning,
        setExportOptions,
    } = useQueueStore();

    const [scriptInput, setScriptInput] = useState('');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // YouTube URL extraction
    const [youtubeUrl, setYoutubeUrl] = useState('');
    const [isExtractingYt, setIsExtractingYt] = useState(false);
    const [ytExtracted, setYtExtracted] = useState<{
        title: string;
        description: string;
        thumbnail_url: string;
        channel_name: string;
    } | null>(null);

    // Metadata input fields
    const [metadataTitle, setMetadataTitle] = useState('');
    const [metadataDescription, setMetadataDescription] = useState('');
    const [metadataThumbnailUrl, setMetadataThumbnailUrl] = useState('');

    // Determine which metadata fields are active based on pipeline selection
    const pipe = currentConfig?.pipelineSelection;
    const analysisObj = typeof pipe?.styleAnalysis === 'object' ? pipe.styleAnalysis : null;
    const showTitleInput = analysisObj?.title === true;
    const showDescriptionInput = analysisObj?.description === true;
    const showThumbnailInput = analysisObj?.thumbnail === true;
    const hasAnyMetadataField = showTitleInput || showDescriptionInput || showThumbnailInput;

    const handleAddToQueue = () => {
        const text = scriptInput.trim();
        if (!text) return;
        addItem(text, activePresetName, activeVoiceId, {
            originalTitle: metadataTitle.trim() || undefined,
            originalDescription: metadataDescription.trim() || undefined,
            thumbnailUrl: metadataThumbnailUrl.trim() || undefined,
        });
        setScriptInput('');
        setMetadataTitle('');
        setMetadataDescription('');
        setMetadataThumbnailUrl('');
        setYtExtracted(null);
        textareaRef.current?.focus();
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
            e.preventDefault();
            handleAddToQueue();
        }
    };

    const handleExtractYoutube = async () => {
        const url = youtubeUrl.trim();
        if (!url) return;
        setIsExtractingYt(true);
        try {
            const result = await youtubeApi.extractFromUrl(url);
            if (!result.success) {
                alert(result.error || 'Không thể lấy dữ liệu từ YouTube URL');
                return;
            }
            // Auto-fill transcript into script textarea
            if (result.transcript) {
                setScriptInput(result.transcript);
            }
            // Auto-fill metadata fields
            if (result.title) setMetadataTitle(result.title);
            if (result.description) setMetadataDescription(result.description);
            if (result.thumbnail_url) setMetadataThumbnailUrl(result.thumbnail_url);

            setYtExtracted({
                title: result.title || '',
                description: result.description || '',
                thumbnail_url: result.thumbnail_url || '',
                channel_name: result.channel_name || '',
            });
            setYoutubeUrl('');
        } catch (err: any) {
            alert(err.message || 'Lỗi kết nối đến server');
        } finally {
            setIsExtractingYt(false);
        }
    };

    const queuedCount = items.filter(i => i.status === 'queued').length;
    const runningCount = items.filter(i => i.status === 'running').length;
    const doneCount = items.filter(i => i.status === 'done').length;

    const cfg = currentConfig;
    const adv = cfg?.advancedSettings;

    return (
        <div style={{
            width: '340px',
            minWidth: '340px',
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: '1rem',
            padding: '1.25rem',
            background: 'var(--bg-secondary)',
            borderRadius: '16px',
            border: '1px solid var(--border-color)',
            overflowY: 'auto',
        }}>
            {/* Active Preset Badge — Clickable to expand config panel */}
            <div style={{
                borderRadius: '12px',
                border: '1px solid rgba(255, 215, 0, 0.25)',
                overflow: 'hidden',
                transition: 'all 0.3s',
            }}>
                <button
                    onClick={onPresetToggle}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        width: '100%',
                        padding: '0.6rem 0.75rem',
                        background: 'rgba(255, 215, 0, 0.08)',
                        border: 'none',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                    }}
                >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Preset:</span>
                        <span style={{ fontWeight: 600, color: '#FFD700' }}>
                            {activePresetName || 'Mặc định'}
                        </span>
                    </span>
                    {isPresetOpen ? <ChevronUp size={14} style={{ color: '#FFD700' }} /> : <ChevronDown size={14} style={{ color: '#FFD700' }} />}
                </button>

                {/* Expanded Config Panel */}
                {isPresetOpen && cfg && (
                    <div style={{
                        padding: '0.75rem',
                        background: 'rgba(255, 215, 0, 0.03)',
                        borderTop: '1px solid rgba(255, 215, 0, 0.12)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.5rem',
                    }}>
                        {/* Pipeline Steps */}
                        <div>
                            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                Pipeline
                            </span>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.3rem', marginTop: '0.3rem' }}>
                                <PipelineTag label="Phân tích" enabled={typeof pipe?.styleAnalysis === 'object' ? (pipe.styleAnalysis.voiceStyle || pipe.styleAnalysis.title || pipe.styleAnalysis.thumbnail || pipe.styleAnalysis.description) : pipe?.styleAnalysis !== false} />
                                <PipelineTag label="Kịch bản" enabled={pipe?.scriptGeneration !== false} />
                                <PipelineTag label="Voice" enabled={pipe?.voiceGeneration !== false} />
                                <PipelineTag label="Video Prompts" enabled={pipe?.videoProduction?.video_prompts !== false} />
                                <PipelineTag label="Image Prompts" enabled={pipe?.videoProduction?.image_prompts !== false} />
                                <PipelineTag label="Keywords" enabled={pipe?.videoProduction?.keywords !== false} />
                                <PipelineTag label="Footage" enabled={pipe?.videoProduction?.footage !== false} />
                                <PipelineTag label="SEO" enabled={typeof pipe?.seoOptimize === 'object' ? pipe.seoOptimize.enabled : !!pipe?.seoOptimize} />
                            </div>
                        </div>

                        {/* Divider */}
                        <div style={{ height: '1px', background: 'rgba(255, 215, 0, 0.1)', margin: '0.15rem 0' }} />

                        {/* Script Settings */}
                        <div>
                            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                Cài đặt kịch bản
                            </span>
                            <div style={{ marginTop: '0.2rem' }}>
                                {cfg.channelName && (
                                    <ConfigRow label="Tên kênh" value={cfg.channelName} />
                                )}
                                <ConfigRow label="Ngôn ngữ" value={LANG_LABELS[adv?.language || 'vi'] || adv?.language || 'vi'} />
                                {adv?.sourceLanguage && (
                                    <ConfigRow label="Ngôn ngữ gốc" value={LANG_LABELS[adv.sourceLanguage] || adv.sourceLanguage} />
                                )}
                                {adv?.dialect && (
                                    <ConfigRow label="Phương ngữ" value={adv.dialect} />
                                )}
                                <ConfigRow label="Số từ" value={`~${adv?.targetWordCount || 1200} từ`} />
                                {adv?.enableStorytellingStyle && (
                                    <ConfigRow label="Phong cách" value={STYLE_LABELS[adv.storytellingStyle] || adv.storytellingStyle} />
                                )}
                                <ConfigRow label="Ngôi kể" value={VOICE_LABELS[adv?.narrativeVoice || 'third_person'] || adv?.narrativeVoice || ''} />
                                {adv?.enableAudienceAddress && (
                                    <ConfigRow label="Xưng hô" value={adv.audienceAddress || adv.customAudienceAddress || 'Bật'} />
                                )}
                                {adv?.enableValueType && (
                                    <ConfigRow label="Mục tiêu" value={VALUE_LABELS[adv.valueType] || adv.valueType} />
                                )}
                                {adv?.enableValueType && adv?.customValue && (
                                    <ConfigRow label="Chi tiết CTA" value={adv.customValue} />
                                )}
                                {adv?.addQuiz && (
                                    <ConfigRow label="Quiz" value="Bật" />
                                )}
                                <ConfigRow label="Chia scene" value={MODE_LABELS[cfg.splitMode] || cfg.splitMode} />
                            </div>
                        </div>

                        {/* Divider */}
                        <div style={{ height: '1px', background: 'rgba(255, 215, 0, 0.1)', margin: '0.15rem 0' }} />

                        {/* Voice & Video */}
                        <div>
                            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                Voice & Video
                            </span>
                            <div style={{ marginTop: '0.2rem' }}>
                                {pipe?.voiceGeneration !== false && (
                                    <>
                                        <ConfigRow label="Voice" value={cfg.selectedVoice || 'Chưa chọn'} />
                                        <ConfigRow label="Tốc độ" value={`${cfg.voiceSpeed}x`} />
                                    </>
                                )}
                                {pipe?.videoProduction?.footage === true && (
                                    <>
                                        {cfg.footageOrientation && (
                                            <ConfigRow label="Tỉ lệ" value={ORIENT_LABELS[cfg.footageOrientation] || cfg.footageOrientation} />
                                        )}
                                        {cfg.videoQuality && (
                                            <ConfigRow label="Chất lượng" value={cfg.videoQuality} />
                                        )}
                                        <ConfigRow label="Phụ đề" value={cfg.enableSubtitles ? 'Bật' : 'Tắt'} />
                                        <ConfigRow label="Scene mode" value={MODE_LABELS[cfg.sceneMode] || cfg.sceneMode} />
                                    </>
                                )}
                                {pipe?.videoProduction?.video_prompts !== false && pipe?.videoProduction?.video_prompt_mode && (
                                    <ConfigRow label="Video mode" value={VIDEO_PROMPT_MODE_LABELS[pipe.videoProduction.video_prompt_mode] || pipe.videoProduction.video_prompt_mode} />
                                )}
                                {pipe?.videoProduction?.image_prompts !== false && pipe?.videoProduction?.image_prompt_mode && (() => {
                                    const imgMode = pipe.videoProduction.image_prompt_mode;
                                    const vidMode = pipe.videoProduction?.video_prompt_mode;
                                    const baseLabel = IMAGE_PROMPT_MODE_LABELS[imgMode] || imgMode;
                                    // When full_sync, both reference + scene_builder run
                                    const displayLabel = (vidMode === 'full_sync' && imgMode === 'reference')
                                        ? `${baseLabel} + Scene builder`
                                        : baseLabel;
                                    return <ConfigRow label="Image mode" value={displayLabel} />;
                                })()}
                                {cfg.promptStyle && (
                                    <ConfigRow label="Prompt style" value={cfg.promptStyle.length > 40 ? cfg.promptStyle.slice(0, 40) + '…' : cfg.promptStyle} />
                                )}
                                {cfg.mainCharacter && (
                                    <ConfigRow label="Nhân vật chính" value={cfg.mainCharacter.length > 40 ? cfg.mainCharacter.slice(0, 40) + '…' : cfg.mainCharacter} />
                                )}
                                {cfg.contextDescription && (
                                    <ConfigRow label="Context" value={cfg.contextDescription.length > 40 ? cfg.contextDescription.slice(0, 40) + '…' : cfg.contextDescription} />
                                )}
                            </div>
                        </div>

                        {/* SEO Settings */}
                        {typeof pipe?.seoOptimize === 'object' && pipe.seoOptimize.enabled && (
                            <>
                                <div style={{ height: '1px', background: 'rgba(255, 215, 0, 0.1)', margin: '0.15rem 0' }} />
                                <div>
                                    <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                                        SEO
                                    </span>
                                    <div style={{ marginTop: '0.2rem' }}>
                                        <ConfigRow label="Chế độ" value={pipe.seoOptimize.mode === 'review' ? '👁 Duyệt trước' : '⚡ AI Tự động'} />
                                    </div>
                                </div>
                            </>
                        )}

                        {/* Model */}
                        <div style={{ height: '1px', background: 'rgba(255, 215, 0, 0.1)', margin: '0.15rem 0' }} />
                        <ConfigRow label="Model AI" value={cfg.selectedModel || 'Mặc định'} />
                    </div>
                )}
            </div>

            {/* Script Input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', flex: 1, minHeight: 0 }}>
                <label style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                    Kịch bản gốc
                </label>

                {/* YouTube URL Extraction */}
                <div style={{
                    borderRadius: '10px',
                    border: '1px solid rgba(239, 68, 68, 0.25)',
                    background: 'rgba(239, 68, 68, 0.04)',
                    padding: '0.6rem',
                }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.4rem' }}>
                        <Link2 size={13} style={{ color: '#EF4444' }} />
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#EF4444' }}>YouTube Auto-Extract</span>
                    </div>
                    <div style={{ display: 'flex', gap: '0.4rem' }}>
                        <input
                            type="text"
                            placeholder="Dán link YouTube..."
                            value={youtubeUrl}
                            onChange={e => setYoutubeUrl(e.target.value)}
                            disabled={isExtractingYt}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && youtubeUrl.trim() && !isExtractingYt) {
                                    e.preventDefault();
                                    handleExtractYoutube();
                                }
                            }}
                            style={{
                                flex: 1,
                                background: 'var(--bg-tertiary)',
                                color: 'var(--text-primary)',
                                border: '1px solid var(--border-color)',
                                borderRadius: '8px',
                                padding: '0.45rem 0.6rem',
                                fontSize: '0.8rem',
                                outline: 'none',
                                minWidth: 0,
                            }}
                        />
                        <button
                            onClick={handleExtractYoutube}
                            disabled={!youtubeUrl.trim() || isExtractingYt}
                            style={{
                                background: isExtractingYt ? 'rgba(239, 68, 68, 0.3)' : 'linear-gradient(135deg, #EF4444, #DC2626)',
                                border: 'none',
                                color: '#fff',
                                padding: '0.45rem 0.75rem',
                                borderRadius: '8px',
                                fontSize: '0.78rem',
                                fontWeight: 600,
                                cursor: !youtubeUrl.trim() || isExtractingYt ? 'not-allowed' : 'pointer',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.3rem',
                                whiteSpace: 'nowrap' as const,
                                opacity: !youtubeUrl.trim() ? 0.5 : 1,
                            }}
                        >
                            {isExtractingYt ? (
                                <><Loader2 size={13} className="spin" /> Đang lấy...</>
                            ) : (
                                <>Lấy</>
                            )}
                        </button>
                    </div>

                    {/* Extracted info */}
                    {ytExtracted && (
                        <div style={{
                            marginTop: '0.5rem',
                            padding: '0.5rem',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '8px',
                            position: 'relative',
                        }}>
                            <button
                                onClick={() => setYtExtracted(null)}
                                style={{
                                    position: 'absolute',
                                    top: '0.3rem',
                                    right: '0.3rem',
                                    background: 'rgba(239,68,68,0.15)',
                                    border: '1px solid rgba(239,68,68,0.3)',
                                    color: '#ef4444',
                                    borderRadius: '4px',
                                    padding: '0.15rem',
                                    cursor: 'pointer',
                                    display: 'flex',
                                    lineHeight: 1,
                                }}
                                title="Xóa thông tin"
                            >
                                <X size={10} />
                            </button>
                            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'flex-start' }}>
                                {ytExtracted.thumbnail_url && (
                                    <img
                                        src={ytExtracted.thumbnail_url}
                                        alt="thumb"
                                        style={{ width: '64px', height: '36px', borderRadius: '4px', objectFit: 'cover', flexShrink: 0, border: '1px solid var(--border-color)' }}
                                    />
                                )}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <div style={{ fontSize: '0.78rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const, paddingRight: '1rem' }}>
                                        {ytExtracted.title}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.15rem' }}>
                                        {ytExtracted.channel_name || 'Unknown'}
                                    </div>
                                    {ytExtracted.description && (
                                        <div style={{ fontSize: '0.68rem', color: 'var(--text-secondary)', marginTop: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const }}>
                                            {ytExtracted.description.substring(0, 100)}...
                                        </div>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
                <textarea
                    ref={textareaRef}
                    value={scriptInput}
                    onChange={e => setScriptInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={"Dán kịch bản gốc vào đây...\n\nCtrl+Enter để thêm vào hàng đợi"}
                    style={{
                        flex: 1,
                        minHeight: '180px',
                        padding: '0.75rem',
                        borderRadius: '10px',
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-tertiary)',
                        color: 'var(--text-primary)',
                        fontSize: '0.85rem',
                        lineHeight: 1.5,
                        resize: 'none',
                        fontFamily: 'inherit',
                    }}
                />

                {/* Metadata Input Fields — Conditional on pipeline selection */}
                {hasAnyMetadataField && (
                    <div style={{
                        borderRadius: '10px',
                        border: '1px solid rgba(139, 92, 246, 0.25)',
                        background: 'rgba(139, 92, 246, 0.04)',
                        padding: '0.6rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.5rem',
                    }}>
                        <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#8B5CF6' }}>
                            Metadata gốc
                        </span>

                        {showTitleInput && (
                            <div>
                                <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                    Title gốc
                                </label>
                                <input
                                    type="text"
                                    placeholder="Nhập title video gốc..."
                                    value={metadataTitle}
                                    onChange={e => setMetadataTitle(e.target.value)}
                                    style={{
                                        width: '100%',
                                        background: 'var(--bg-tertiary)',
                                        color: 'var(--text-primary)',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '8px',
                                        padding: '0.4rem 0.6rem',
                                        fontSize: '0.8rem',
                                        outline: 'none',
                                        boxSizing: 'border-box' as const,
                                    }}
                                />
                            </div>
                        )}

                        {showDescriptionInput && (
                            <div>
                                <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                    Description gốc
                                </label>
                                <textarea
                                    placeholder="Nhập description video gốc..."
                                    value={metadataDescription}
                                    onChange={e => setMetadataDescription(e.target.value)}
                                    rows={3}
                                    style={{
                                        width: '100%',
                                        background: 'var(--bg-tertiary)',
                                        color: 'var(--text-primary)',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '8px',
                                        padding: '0.4rem 0.6rem',
                                        fontSize: '0.8rem',
                                        resize: 'vertical',
                                        fontFamily: 'inherit',
                                        outline: 'none',
                                        boxSizing: 'border-box' as const,
                                    }}
                                />
                            </div>
                        )}

                        {showThumbnailInput && (
                            <div>
                                <label style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>
                                    Thumbnail URL
                                </label>
                                <input
                                    type="text"
                                    placeholder="URL hình thumbnail gốc..."
                                    value={metadataThumbnailUrl}
                                    onChange={e => setMetadataThumbnailUrl(e.target.value)}
                                    style={{
                                        width: '100%',
                                        background: 'var(--bg-tertiary)',
                                        color: 'var(--text-primary)',
                                        border: '1px solid var(--border-color)',
                                        borderRadius: '8px',
                                        padding: '0.4rem 0.6rem',
                                        fontSize: '0.8rem',
                                        outline: 'none',
                                        boxSizing: 'border-box' as const,
                                    }}
                                />
                                {metadataThumbnailUrl.trim() && (
                                    <img
                                        src={metadataThumbnailUrl}
                                        alt="Thumbnail preview"
                                        style={{
                                            marginTop: '0.35rem',
                                            width: '100%',
                                            maxHeight: '100px',
                                            objectFit: 'cover',
                                            borderRadius: '6px',
                                            border: '1px solid var(--border-color)',
                                        }}
                                        onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                        onLoad={e => { (e.target as HTMLImageElement).style.display = 'block'; }}
                                    />
                                )}
                            </div>
                        )}
                    </div>
                )}

                <button
                    onClick={handleAddToQueue}
                    disabled={!scriptInput.trim()}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        padding: '0.7rem',
                        borderRadius: '10px',
                        border: 'none',
                        background: scriptInput.trim()
                            ? 'linear-gradient(135deg, #FFD700, #F59E0B)'
                            : 'var(--bg-tertiary)',
                        color: scriptInput.trim() ? '#0a0a0a' : 'var(--text-secondary)',
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        cursor: scriptInput.trim() ? 'pointer' : 'not-allowed',
                        transition: 'all 0.3s',
                    }}
                >
                    <Plus size={16} /> Thêm vào hàng đợi
                </button>
            </div>

            {/* Execution Settings (collapsible) */}
            <div style={{
                borderRadius: '10px',
                border: '1px solid var(--border-color)',
                overflow: 'hidden',
            }}>
                <button
                    onClick={() => setIsSettingsOpen(!isSettingsOpen)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        width: '100%',
                        padding: '0.6rem 0.75rem',
                        background: 'var(--bg-tertiary)',
                        border: 'none',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        fontWeight: 600,
                    }}
                >
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Settings size={14} /> Cài đặt thực thi
                    </span>
                    {isSettingsOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </button>
                {isSettingsOpen && (
                    <div style={{
                        padding: '0.75rem',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '0.75rem',
                        background: 'var(--bg-primary)',
                    }}>
                        {/* Concurrent threads */}
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.3rem' }}>
                                Luồng đồng thời
                            </label>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input
                                    type="range"
                                    min={1}
                                    max={5}
                                    value={maxConcurrent}
                                    onChange={e => setMaxConcurrent(parseInt(e.target.value))}
                                    style={{ flex: 1, accentColor: '#FFD700' }}
                                />
                                <span style={{ fontWeight: 700, fontSize: '0.9rem', color: '#FFD700', minWidth: '2ch' }}>{maxConcurrent}</span>
                            </div>
                        </div>

                        {/* Delay */}
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.3rem' }}>
                                <Clock size={12} /> Delay giữa các luồng
                            </label>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <input
                                    type="range"
                                    min={0}
                                    max={10000}
                                    step={500}
                                    value={delayBetweenMs}
                                    onChange={e => setDelayBetween(parseInt(e.target.value))}
                                    style={{ flex: 1, accentColor: '#FFD700' }}
                                />
                                <span style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)', minWidth: '4ch' }}>{(delayBetweenMs / 1000).toFixed(1)}s</span>
                            </div>
                        </div>

                        {/* Output path */}
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: '0.3rem', marginBottom: '0.3rem' }}>
                                <FolderOpen size={12} /> Thư mục lưu kết quả
                            </label>
                            <button
                                onClick={onSelectOutputPath}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.4rem',
                                    width: '100%',
                                    padding: '0.5rem 0.75rem',
                                    borderRadius: '8px',
                                    border: '1px solid var(--border-color)',
                                    background: 'var(--bg-secondary)',
                                    color: outputPath ? 'var(--text-primary)' : 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    textAlign: 'left',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                }}
                            >
                                {outputPath || 'Chưa chọn thư mục'}
                            </button>
                            {outputPath && (
                                <span style={{ fontSize: '0.7rem', color: 'rgba(34, 197, 94, 0.8)', marginTop: '0.2rem', display: 'block' }}>
                                    ✓ Kết quả sẽ lưu vào thư mục này
                                </span>
                            )}
                        </div>

                        {/* Export options — dynamic based on pipeline selection */}
                        <div>
                            <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.4rem' }}>
                                Xuất kết quả
                            </label>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                                {[
                                    { key: 'fullScript' as const, label: 'Script đầy đủ (.txt)', available: pipe?.scriptGeneration !== false },
                                    { key: 'splitCsv' as const, label: 'Script chia scene (.csv)', available: pipe?.scriptGeneration !== false },
                                    { key: 'finalVideo' as const, label: 'Video hoàn chỉnh (.mp4)', available: pipe?.videoProduction?.footage === true },
                                    { key: 'voiceZip' as const, label: 'Voice (.zip)', available: pipe?.voiceGeneration !== false },
                                    { key: 'footageZip' as const, label: 'Video footage (.zip)', available: pipe?.videoProduction?.footage === true },
                                    { key: 'keywordsTxt' as const, label: 'Keywords (.txt)', available: pipe?.videoProduction?.keywords !== false },
                                    { key: 'promptsTxt' as const, label: 'Prompts (.txt)', available: pipe?.videoProduction?.video_prompts !== false || pipe?.videoProduction?.image_prompts !== false },
                                ].map(opt => (
                                    <label
                                        key={opt.key}
                                        style={{
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.4rem',
                                            fontSize: '0.78rem',
                                            color: !opt.available
                                                ? 'var(--text-secondary)'
                                                : exportOptions[opt.key]
                                                    ? 'var(--text-primary)'
                                                    : 'var(--text-secondary)',
                                            cursor: opt.available ? 'pointer' : 'not-allowed',
                                            padding: '0.15rem 0',
                                            opacity: opt.available ? 1 : 0.4,
                                            textDecoration: opt.available ? 'none' : 'line-through',
                                        }}
                                    >
                                        <input
                                            type="checkbox"
                                            checked={opt.available && exportOptions[opt.key]}
                                            disabled={!opt.available}
                                            onChange={e => setExportOptions({ [opt.key]: e.target.checked })}
                                            style={{ accentColor: '#FFD700', width: '14px', height: '14px' }}
                                        />
                                        {opt.label}
                                    </label>
                                ))}
                            </div>
                            {!outputPath && (
                                <span style={{ fontSize: '0.68rem', color: 'rgba(251, 191, 36, 0.7)', marginTop: '0.3rem', display: 'block' }}>
                                    ⚠ Chọn thư mục lưu kết quả ở trên để xuất
                                </span>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Queue Stats */}
            <div style={{
                display: 'flex',
                gap: '0.5rem',
                fontSize: '0.75rem',
                color: 'var(--text-secondary)',
            }}>
                <span style={{ padding: '0.25rem 0.5rem', borderRadius: '6px', background: 'var(--bg-tertiary)' }}>
                    Chờ: {queuedCount}
                </span>
                <span style={{ padding: '0.25rem 0.5rem', borderRadius: '6px', background: 'rgba(255, 215, 0, 0.1)', color: '#FFD700' }}>
                    Chạy: {runningCount}
                </span>
                <span style={{ padding: '0.25rem 0.5rem', borderRadius: '6px', background: 'rgba(34, 197, 94, 0.1)', color: '#22c55e' }}>
                    Xong: {doneCount}
                </span>
            </div>

            {/* Queue Control Buttons */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                <button
                    onClick={() => {
                        if (!isQueueRunning && !outputPath) {
                            setIsSettingsOpen(true);
                            return;
                        }
                        setIsQueueRunning(!isQueueRunning);
                    }}
                    disabled={!isQueueRunning && (queuedCount === 0 || !outputPath)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.5rem',
                        padding: '0.75rem',
                        borderRadius: '10px',
                        border: 'none',
                        background: isQueueRunning
                            ? 'linear-gradient(135deg, #ef4444, #dc2626)'
                            : (queuedCount > 0 && outputPath
                                ? 'linear-gradient(135deg, #22c55e, #16a34a)'
                                : 'var(--bg-tertiary)'),
                        color: (!isQueueRunning && (queuedCount === 0 || !outputPath)) ? 'var(--text-secondary)' : 'white',
                        fontWeight: 700,
                        fontSize: '0.9rem',
                        cursor: (!isQueueRunning && (queuedCount === 0 || !outputPath)) ? 'not-allowed' : 'pointer',
                        transition: 'all 0.3s',
                    }}
                >
                    {isQueueRunning ? (
                        <><Square size={16} /> Dừng tất cả</>
                    ) : (
                        <><Play size={16} /> Chạy hàng đợi ({queuedCount})</>
                    )}
                </button>
                {!isQueueRunning && queuedCount > 0 && !outputPath && (
                    <span style={{
                        fontSize: '0.72rem',
                        color: '#FBBF24',
                        textAlign: 'center',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: '0.3rem',
                    }}>
                        <FolderOpen size={11} /> Chọn thư mục lưu kết quả trước khi chạy
                    </span>
                )}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        onClick={clearCompleted}
                        disabled={doneCount === 0}
                        style={{
                            flex: 1,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            padding: '0.5rem',
                            borderRadius: '8px',
                            border: '1px solid var(--border-color)',
                            background: 'var(--bg-tertiary)',
                            color: doneCount > 0 ? 'var(--text-primary)' : 'var(--text-secondary)',
                            cursor: doneCount > 0 ? 'pointer' : 'not-allowed',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            opacity: doneCount > 0 ? 1 : 0.5,
                        }}
                    >
                        Xóa đã xong
                    </button>
                    <button
                        onClick={clearAll}
                        disabled={items.length === 0}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            gap: '0.35rem',
                            padding: '0.5rem 0.75rem',
                            borderRadius: '8px',
                            border: '1px solid rgba(239, 68, 68, 0.3)',
                            background: 'rgba(239, 68, 68, 0.08)',
                            color: items.length > 0 ? '#ef4444' : 'var(--text-secondary)',
                            cursor: items.length > 0 ? 'pointer' : 'not-allowed',
                            fontSize: '0.8rem',
                            fontWeight: 600,
                            opacity: items.length > 0 ? 1 : 0.5,
                        }}
                    >
                        <Trash2 size={12} /> Xóa hết
                    </button>
                </div>
            </div>
        </div >
    );
}
