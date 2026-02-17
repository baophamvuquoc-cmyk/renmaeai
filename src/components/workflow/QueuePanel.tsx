import { useState, useEffect } from 'react';
import { useQueueStore, QueueItem, PipelineStep } from '../../stores/useQueueStore';
import {
    Loader2,
    CheckCircle,
    XCircle,
    Trash2,
    RefreshCw,
    FileText,
    ChevronDown,
    ChevronUp,
    AlertTriangle,
} from 'lucide-react';

interface QueuePanelProps {
    onRetryItem: (item: QueueItem) => void;
    onRetryFromStep?: (item: QueueItem, step: PipelineStep) => void;
    onPresetClick?: () => void;
}

const STEP_CONFIG: { key: PipelineStep; label: string }[] = [
    { key: 'script', label: 'Kịch bản' },
    { key: 'scenes', label: 'Chia scenes' },
    { key: 'metadata', label: 'Metadata' },
    { key: 'voice', label: 'Tạo voice' },
    { key: 'keywords', label: 'Keywords' },
    { key: 'video_direction', label: 'Phân tích đạo diễn' },
    { key: 'video_prompts', label: 'Tạo prompts' },
    { key: 'entity_extraction', label: 'Trích xuất entities' },
    { key: 'reference_prompts', label: 'Ảnh tham chiếu' },
    { key: 'scene_builder', label: 'Scene Builder' },
    { key: 'assembly', label: 'Ghép video' },
    { key: 'seo', label: 'SEO' },
    { key: 'export', label: 'Xuất' },
];

function QueueItemBar({ item, onRetry, onRetryFromStep, onRemove, onPresetClick }: {
    item: QueueItem;
    onRetry: () => void;
    onRetryFromStep?: (step: PipelineStep) => void;
    onRemove: () => void;
    onPresetClick?: () => void;
}) {
    const [expanded, setExpanded] = useState(item.status === 'error');
    const canExpand = item.status === 'done' || item.status === 'error';

    // Auto-expand when status transitions to 'error'
    useEffect(() => {
        if (item.status === 'error') setExpanded(true);
    }, [item.status]);

    const completedSteps = item.completedSteps || [];
    const hasNoVideo = item.status === 'done' && !item.finalVideoPath;

    const statusColors: Record<string, { bg: string; border: string; text: string; barBg: string }> = {
        queued: {
            bg: 'rgba(148, 163, 184, 0.06)',
            border: 'rgba(148, 163, 184, 0.2)',
            text: 'var(--text-secondary)',
            barBg: 'rgba(148, 163, 184, 0.3)',
        },
        running: {
            bg: 'rgba(255, 215, 0, 0.06)',
            border: 'rgba(255, 215, 0, 0.3)',
            text: '#FFD700',
            barBg: 'linear-gradient(135deg, #FFD700, #F59E0B)',
        },
        done: {
            bg: hasNoVideo ? 'rgba(245, 158, 11, 0.06)' : 'rgba(34, 197, 94, 0.06)',
            border: hasNoVideo ? 'rgba(245, 158, 11, 0.25)' : 'rgba(34, 197, 94, 0.25)',
            text: hasNoVideo ? '#f59e0b' : '#22c55e',
            barBg: hasNoVideo
                ? 'linear-gradient(135deg, #f59e0b, #d97706)'
                : 'linear-gradient(135deg, #22c55e, #16a34a)',
        },
        error: {
            bg: 'rgba(239, 68, 68, 0.06)',
            border: 'rgba(239, 68, 68, 0.25)',
            text: '#ef4444',
            barBg: 'linear-gradient(135deg, #ef4444, #dc2626)',
        },
    };

    const colors = statusColors[item.status];
    const scriptPreview = item.scriptText.slice(0, 80).replace(/\n/g, ' ') + (item.scriptText.length > 80 ? '...' : '');

    return (
        <div style={{
            padding: '0.75rem 1rem',
            borderRadius: '12px',
            border: `1px solid ${colors.border}`,
            background: colors.bg,
            transition: 'all 0.3s',
        }}>
            {/* Header row */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '0.5rem',
            }}>
                <div
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.5rem',
                        flex: 1,
                        minWidth: 0,
                        cursor: canExpand ? 'pointer' : 'default',
                    }}
                    onClick={() => canExpand && setExpanded(!expanded)}
                >
                    {/* Status icon */}
                    {item.status === 'running' && <Loader2 size={14} className="spin" style={{ color: colors.text, flexShrink: 0 }} />}
                    {item.status === 'done' && !hasNoVideo && <CheckCircle size={14} style={{ color: colors.text, flexShrink: 0 }} />}
                    {item.status === 'done' && hasNoVideo && <AlertTriangle size={14} style={{ color: colors.text, flexShrink: 0 }} />}
                    {item.status === 'error' && <XCircle size={14} style={{ color: colors.text, flexShrink: 0 }} />}
                    {item.status === 'queued' && <FileText size={14} style={{ color: colors.text, flexShrink: 0 }} />}

                    {/* Script preview */}
                    <span style={{
                        fontSize: '0.85rem',
                        color: 'var(--text-primary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                    }}>
                        {scriptPreview}
                    </span>

                    {/* Expand chevron */}
                    {canExpand && (
                        expanded
                            ? <ChevronUp size={14} style={{ color: 'var(--text-secondary)', flexShrink: 0 }} />
                            : <ChevronDown size={14} style={{ color: 'var(--text-secondary)', flexShrink: 0 }} />
                    )}
                </div>

                {/* Actions */}
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', flexShrink: 0, marginLeft: '0.5rem' }}>
                    {(item.status === 'queued' || item.status === 'done' || item.status === 'error') && (
                        <button
                            onClick={onRemove}
                            title="Xóa"
                            style={{
                                display: 'flex',
                                alignItems: 'center',
                                padding: '0.25rem',
                                borderRadius: '6px',
                                border: '1px solid rgba(239, 68, 68, 0.2)',
                                background: 'transparent',
                                color: 'var(--text-secondary)',
                                cursor: 'pointer',
                            }}
                        >
                            <Trash2 size={12} />
                        </button>
                    )}
                </div>
            </div>

            {/* Progress bar */}
            <div style={{
                height: '6px',
                borderRadius: '3px',
                background: 'rgba(255,255,255,0.06)',
                overflow: 'hidden',
                marginBottom: (item.status === 'running' || item.status === 'error' || (item.status === 'done' && hasNoVideo)) ? '0.35rem' : 0,
            }}>
                <div style={{
                    height: '100%',
                    width: `${item.status === 'done' ? 100 : item.progress}%`,
                    background: typeof colors.barBg === 'string' && colors.barBg.startsWith('linear') ? colors.barBg : colors.barBg,
                    borderRadius: '3px',
                    transition: 'width 0.5s ease',
                }} />
            </div>

            {/* Original Metadata Preview — compact */}
            {(item.originalTitle || item.originalDescription || item.thumbnailUrl) && (
                <div style={{
                    marginTop: '0.35rem',
                    marginBottom: '0.35rem',
                    padding: '0.45rem',
                    borderRadius: '8px',
                    background: 'rgba(139, 92, 246, 0.06)',
                    border: '1px solid rgba(139, 92, 246, 0.15)',
                    display: 'flex',
                    gap: '0.5rem',
                    alignItems: 'flex-start',
                }}>
                    {item.thumbnailUrl && (
                        <img
                            src={item.thumbnailUrl}
                            alt="thumb"
                            style={{
                                width: '56px',
                                height: '32px',
                                borderRadius: '4px',
                                objectFit: 'cover',
                                flexShrink: 0,
                                border: '1px solid var(--border-color)',
                            }}
                            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                        />
                    )}
                    <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.15rem' }}>
                        {item.originalTitle && (
                            <div style={{
                                fontSize: '0.72rem',
                                fontWeight: 600,
                                color: 'var(--text-primary)',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap' as const,
                            }}>
                                {item.originalTitle}
                            </div>
                        )}
                        {item.originalDescription && (
                            <div style={{
                                fontSize: '0.65rem',
                                color: 'var(--text-secondary)',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap' as const,
                            }}>
                                {item.originalDescription.slice(0, 100)}{item.originalDescription.length > 100 ? '...' : ''}
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Status text */}
            {(item.status === 'running' || item.status === 'error' || (item.status === 'done' && hasNoVideo)) && (
                <div style={{
                    fontSize: '0.75rem',
                    color: colors.text,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                }}>
                    <span>{item.status === 'error' ? item.error : item.currentStep}</span>
                    {item.status === 'running' && (
                        <span style={{ fontWeight: 700 }}>{item.progress}%</span>
                    )}
                </div>
            )}

            {/* Expanded: Context-aware retry */}
            {expanded && canExpand && (
                <div style={{
                    marginTop: '0.5rem',
                    padding: '0.6rem',
                    borderRadius: '8px',
                    background: 'rgba(0,0,0,0.15)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '0.4rem',
                }}>
                    {item.status === 'error' && item.failedStep ? (
                        <>
                            {/* Context-aware: show which step failed */}
                            <div style={{
                                fontSize: '0.72rem',
                                color: 'var(--text-secondary)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.35rem',
                            }}>
                                <XCircle size={12} style={{ color: '#ef4444' }} />
                                Lỗi tại bước: <strong style={{ color: '#ef4444' }}>
                                    {STEP_CONFIG.find(s => s.key === item.failedStep)?.label || item.failedStep}
                                </strong>
                            </div>

                            {/* Completed steps summary */}
                            {completedSteps.length > 0 && (
                                <div style={{
                                    fontSize: '0.68rem',
                                    color: 'var(--text-secondary)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.25rem',
                                    flexWrap: 'wrap',
                                }}>
                                    <span>Đã hoàn thành:</span>
                                    {completedSteps.map(s => (
                                        <span key={s} style={{
                                            padding: '0.1rem 0.35rem',
                                            borderRadius: '4px',
                                            background: 'rgba(34, 197, 94, 0.1)',
                                            border: '1px solid rgba(34, 197, 94, 0.2)',
                                            color: '#22c55e',
                                            fontSize: '0.65rem',
                                        }}>
                                            ✓ {STEP_CONFIG.find(c => c.key === s)?.label || s}
                                        </span>
                                    ))}
                                </div>
                            )}

                            {/* Primary: Retry from failed step */}
                            <button
                                onClick={() => onRetryFromStep?.(item.failedStep!)}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.4rem',
                                    padding: '0.5rem 0.75rem',
                                    borderRadius: '8px',
                                    border: '1px solid rgba(255, 215, 0, 0.4)',
                                    background: 'rgba(255, 215, 0, 0.12)',
                                    color: '#FFD700',
                                    cursor: 'pointer',
                                    fontSize: '0.8rem',
                                    fontWeight: 600,
                                    transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => {
                                    e.currentTarget.style.background = 'rgba(255, 215, 0, 0.25)';
                                    e.currentTarget.style.borderColor = 'rgba(255, 215, 0, 0.6)';
                                }}
                                onMouseLeave={e => {
                                    e.currentTarget.style.background = 'rgba(255, 215, 0, 0.12)';
                                    e.currentTarget.style.borderColor = 'rgba(255, 215, 0, 0.4)';
                                }}
                            >
                                <RefreshCw size={14} />
                                Retry từ: {STEP_CONFIG.find(s => s.key === item.failedStep)?.label || item.failedStep}
                            </button>

                            {/* Secondary: Retry all (smaller) */}
                            <button
                                onClick={onRetry}
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.3rem',
                                    padding: '0.3rem 0.6rem',
                                    borderRadius: '6px',
                                    border: '1px solid rgba(148, 163, 184, 0.2)',
                                    background: 'transparent',
                                    color: 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    fontSize: '0.7rem',
                                    fontWeight: 500,
                                    transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => {
                                    e.currentTarget.style.background = 'rgba(255, 215, 0, 0.1)';
                                    e.currentTarget.style.color = '#FFD700';
                                }}
                                onMouseLeave={e => {
                                    e.currentTarget.style.background = 'transparent';
                                    e.currentTarget.style.color = 'var(--text-secondary)';
                                }}
                            >
                                <RefreshCw size={10} />
                                Retry toàn bộ từ đầu
                            </button>
                        </>
                    ) : (
                        <>
                            {/* Done items: full step overview */}
                            <div style={{
                                fontSize: '0.7rem',
                                color: 'var(--text-secondary)',
                                marginBottom: '0.25rem',
                                fontWeight: 600,
                            }}>
                                Retry từ bước:
                            </div>
                            <div style={{
                                display: 'flex',
                                flexWrap: 'wrap',
                                gap: '0.35rem',
                            }}>
                                {STEP_CONFIG.map(step => {
                                    const isDone = completedSteps.includes(step.key);
                                    return (
                                        <button
                                            key={step.key}
                                            onClick={() => onRetryFromStep?.(step.key)}
                                            title={`Retry từ: ${step.label}`}
                                            style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.3rem',
                                                padding: '0.3rem 0.55rem',
                                                borderRadius: '6px',
                                                border: `1px solid ${isDone ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`,
                                                background: isDone ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)',
                                                color: isDone ? '#22c55e' : '#ef4444',
                                                cursor: 'pointer',
                                                fontSize: '0.72rem',
                                                fontWeight: 500,
                                                transition: 'all 0.2s',
                                            }}
                                            onMouseEnter={e => {
                                                e.currentTarget.style.background = 'rgba(255, 215, 0, 0.15)';
                                                e.currentTarget.style.borderColor = 'rgba(255, 215, 0, 0.4)';
                                                e.currentTarget.style.color = '#FFD700';
                                            }}
                                            onMouseLeave={e => {
                                                e.currentTarget.style.background = isDone ? 'rgba(34, 197, 94, 0.08)' : 'rgba(239, 68, 68, 0.08)';
                                                e.currentTarget.style.borderColor = isDone ? 'rgba(34, 197, 94, 0.3)' : 'rgba(239, 68, 68, 0.3)';
                                                e.currentTarget.style.color = isDone ? '#22c55e' : '#ef4444';
                                            }}
                                        >
                                            {step.label}
                                            <RefreshCw size={10} style={{ marginLeft: '0.15rem', opacity: 0.6 }} />
                                        </button>
                                    );
                                })}
                            </div>

                            {/* Full retry button */}
                            <button
                                onClick={onRetry}
                                style={{
                                    marginTop: '0.25rem',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    gap: '0.4rem',
                                    padding: '0.4rem 0.75rem',
                                    borderRadius: '6px',
                                    border: '1px solid rgba(255, 215, 0, 0.3)',
                                    background: 'rgba(255, 215, 0, 0.1)',
                                    color: '#FFD700',
                                    cursor: 'pointer',
                                    fontSize: '0.72rem',
                                    fontWeight: 600,
                                    transition: 'all 0.2s',
                                }}
                                onMouseEnter={e => {
                                    e.currentTarget.style.background = 'rgba(255, 215, 0, 0.2)';
                                }}
                                onMouseLeave={e => {
                                    e.currentTarget.style.background = 'rgba(255, 215, 0, 0.1)';
                                }}
                            >
                                <RefreshCw size={12} />
                                Retry toàn bộ
                            </button>
                        </>
                    )}
                </div>
            )}

            {/* Preset badge */}
            {item.presetName && (
                <button
                    onClick={onPresetClick}
                    style={{
                        marginTop: '0.35rem',
                        fontSize: '0.7rem',
                        color: 'var(--text-secondary)',
                        opacity: 0.7,
                        background: 'none',
                        border: 'none',
                        padding: 0,
                        cursor: 'pointer',
                        textAlign: 'left',
                        transition: 'color 0.2s',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.color = '#FFD700'; e.currentTarget.style.opacity = '1'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-secondary)'; e.currentTarget.style.opacity = '0.7'; }}
                >
                    Preset: {item.presetName}
                </button>
            )}
        </div>
    );
}

export default function QueuePanel({ onRetryItem, onRetryFromStep, onPresetClick }: QueuePanelProps) {
    const { items, removeItem } = useQueueStore();

    if (items.length === 0) {
        return (
            <div style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '1rem',
                padding: '2rem',
                background: 'var(--bg-secondary)',
                borderRadius: '16px',
                border: '1px dashed var(--border-color)',
                minHeight: '400px',
            }}>
                <div style={{
                    width: '64px',
                    height: '64px',
                    borderRadius: '16px',
                    background: 'rgba(255, 215, 0, 0.08)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                }}>
                    <FileText size={28} style={{ color: 'rgba(255, 215, 0, 0.4)' }} />
                </div>
                <div style={{ textAlign: 'center' }}>
                    <p style={{
                        margin: '0 0 0.35rem',
                        fontSize: '1rem',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                    }}>
                        Chưa có kịch bản nào trong hàng đợi
                    </p>
                    <p style={{
                        margin: 0,
                        fontSize: '0.85rem',
                        color: 'var(--text-secondary)',
                    }}>
                        Dán kịch bản gốc ở bên trái và click "Thêm vào hàng đợi"
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
            padding: '1.25rem',
            background: 'var(--bg-secondary)',
            borderRadius: '16px',
            border: '1px solid var(--border-color)',
            overflowY: 'auto',
            minHeight: '400px',
        }}>
            {/* Header */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '0.5rem',
            }}>
                <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    Hàng đợi ({items.length})
                </h3>
            </div>

            {/* Queue Items */}
            <div style={{
                display: 'flex',
                flexDirection: 'column',
                gap: '0.5rem',
            }}>
                {items.map(item => (
                    <QueueItemBar
                        key={item.id}
                        item={item}
                        onRetry={() => onRetryItem(item)}
                        onRetryFromStep={onRetryFromStep ? (step) => onRetryFromStep(item, step) : undefined}
                        onRemove={() => removeItem(item.id)}
                        onPresetClick={onPresetClick}
                    />
                ))}
            </div>
        </div>
    );
}
