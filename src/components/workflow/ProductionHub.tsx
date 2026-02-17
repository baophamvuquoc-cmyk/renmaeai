/**
 * ProductionHub — Data Table view for all completed productions.
 *
 * Displays productions in a spreadsheet-like table with:
 * - Dynamic columns based on PipelineSelection preset
 * - Click-to-copy on every cell
 * - Auto-refresh polling (5s) for realtime sync
 * - Inline actions: open folder, delete
 */

import { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { productionApi, type Production } from '../../lib/api';

// ═══════════════════════════════════════════════════════════════════════════════
// Types & Interfaces
// ═══════════════════════════════════════════════════════════════════════════════

interface PipelineSelection {
    styleAnalysis: boolean | { enabled: boolean; title?: boolean; description?: boolean; thumbnail?: boolean; voice?: boolean };
    scriptGeneration: boolean;
    voiceGeneration: boolean;
    videoProduction: {
        video_prompts: boolean;
        image_prompts: boolean;
        keywords: boolean;
        footage: boolean;
        Footage?: boolean;
    };
    seoOptimize: boolean | { enabled: boolean; mode?: string };
}

interface ColumnDef {
    key: string;
    label: string;
    icon: string;
    width: string;
    format: 'text' | 'number' | 'url' | 'filepath' | 'image' | 'status';
    alwaysShow?: boolean;
    showWhen?: (pipeline: PipelineSelection) => boolean;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Constants
// ═══════════════════════════════════════════════════════════════════════════════

const PIPELINE_STORAGE_KEY = 'renmae_pipeline_selection';
const POLL_INTERVAL_MS = 5000;

const ALL_COLUMNS: ColumnDef[] = [
    { key: 'project_name', label: 'Project', icon: '📁', width: '120px', format: 'text', alwaysShow: true },
    { key: 'sequence_number', label: 'STT', icon: '#', width: '55px', format: 'number', alwaysShow: true },
    {
        key: 'original_link', label: 'Link gốc', icon: '🔗', width: '140px', format: 'url',
        showWhen: (p) => {
            if (typeof p.styleAnalysis === 'object') return p.styleAnalysis.enabled;
            return !!p.styleAnalysis;
        }
    },
    { key: 'title', label: 'Title', icon: '📝', width: '200px', format: 'text', alwaysShow: true },
    { key: 'description', label: 'Description', icon: '📄', width: '200px', format: 'text', alwaysShow: true },
    { key: 'thumbnail', label: 'Thumbnail', icon: '🖼️', width: '200px', format: 'text', alwaysShow: true },
    {
        key: 'keywords', label: 'Keywords', icon: '🔑', width: '180px', format: 'text',
        showWhen: (p) => !!(p.videoProduction?.keywords)
    },
    {
        key: 'script_full', label: 'Script', icon: '📜', width: '200px', format: 'text',
        showWhen: (p) => !!p.scriptGeneration
    },
    {
        key: 'script_split', label: 'Split CSV', icon: '📊', width: '140px', format: 'filepath',
        showWhen: (p) => !!p.scriptGeneration
    },
    {
        key: 'voiceover', label: 'Voice', icon: '🎙️', width: '140px', format: 'filepath',
        showWhen: (p) => !!p.voiceGeneration
    },
    {
        key: 'video_footage', label: 'Footage', icon: '🎬', width: '140px', format: 'filepath',
        showWhen: (p) => !!(p.videoProduction?.footage || p.videoProduction?.Footage)
    },
    {
        key: 'video_final', label: 'Video', icon: '🎥', width: '140px', format: 'filepath',
        showWhen: (p) => !!(p.videoProduction?.footage || p.videoProduction?.Footage)
    },
    {
        key: 'prompts_reference', label: 'Prompts Ref', icon: '🖼️', width: '200px', format: 'text',
        showWhen: (p) => !!(p.videoProduction?.image_prompts)
    },
    {
        key: 'prompts_scene_builder', label: 'Prompts Scene', icon: '🏗️', width: '200px', format: 'text',
        showWhen: (p) => !!(p.videoProduction?.image_prompts)
    },
    {
        key: 'prompts_concept', label: 'Prompts Concept', icon: '🎨', width: '200px', format: 'text',
        showWhen: (p) => !!(p.videoProduction?.image_prompts)
    },
    {
        key: 'prompts_video', label: 'Prompts Video', icon: '🎬', width: '200px', format: 'text',
        showWhen: (p) => !!(p.videoProduction?.video_prompts)
    },
    { key: 'video_status', label: 'Status', icon: '🚦', width: '90px', format: 'status', alwaysShow: true },
];

function loadPipelineSelection(): PipelineSelection | null {
    try {
        const raw = localStorage.getItem(PIPELINE_STORAGE_KEY);
        if (raw) return JSON.parse(raw);
    } catch { /* ignore */ }
    return null;
}

// ═══════════════════════════════════════════════════════════════════════════════
// Utility Functions
// ═══════════════════════════════════════════════════════════════════════════════

function basename(filepath: string): string {
    if (!filepath) return '';
    const parts = filepath.replace(/\\/g, '/').split('/');
    return parts[parts.length - 1] || filepath;
}

function truncate(text: string, max: number): string {
    if (!text) return '—';
    if (text.length <= max) return text;
    return text.slice(0, max) + '…';
}

function getStatusColor(status: string): string {
    switch (status?.toLowerCase()) {
        case 'published': return '#22c55e';
        case 'uploaded': return '#3b82f6';
        case 'draft': return '#94a3b8';
        default: return '#94a3b8';
    }
}

function getStatusBg(status: string): string {
    switch (status?.toLowerCase()) {
        case 'published': return 'rgba(34, 197, 94, 0.12)';
        case 'uploaded': return 'rgba(59, 130, 246, 0.12)';
        case 'draft': return 'rgba(148, 163, 184, 0.10)';
        default: return 'rgba(148, 163, 184, 0.10)';
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// CopyCell Component
// ═══════════════════════════════════════════════════════════════════════════════

function CopyCell({ value, display, title }: { value: string; display: React.ReactNode; title?: string }) {
    const [isCopied, setIsCopied] = useState(false);

    const handleCopy = useCallback(async () => {
        if (!value) return;
        try {
            await navigator.clipboard.writeText(value);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 1500);
        } catch { /* ignore */ }
    }, [value]);

    return (
        <div
            className="cell-copy-wrap"
            onClick={handleCopy}
            title={title || value || ''}
            style={{ cursor: value ? 'pointer' : 'default', display: 'flex', alignItems: 'center', gap: '4px', minWidth: 0 }}
        >
            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                {display}
            </span>
            {value && (
                <span className="copy-icon" style={{ opacity: isCopied ? 1 : 0, transition: 'opacity 0.15s', flexShrink: 0, fontSize: '11px' }}>
                    {isCopied ? '✓' : '📋'}
                </span>
            )}
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Cell Renderers
// ═══════════════════════════════════════════════════════════════════════════════

function renderCellContent(col: ColumnDef, production: Production): React.ReactNode {
    const value = (production as any)[col.key] as string;

    switch (col.format) {
        case 'number':
            return (
                <CopyCell
                    value={String(value ?? '')}
                    display={
                        <span style={{
                            background: 'rgba(99, 102, 241, 0.15)',
                            color: '#a5b4fc',
                            padding: '2px 8px',
                            borderRadius: '10px',
                            fontSize: '11px',
                            fontWeight: 600,
                        }}>
                            {value ?? '—'}
                        </span>
                    }
                />
            );

        case 'url':
            return (
                <CopyCell
                    value={value || ''}
                    display={
                        value ? (
                            <a
                                href={value}
                                target="_blank"
                                rel="noopener noreferrer"
                                onClick={(e) => e.stopPropagation()}
                                style={{ color: '#60a5fa', textDecoration: 'none', fontSize: '12px' }}
                            >
                                {truncate(value, 30)}
                            </a>
                        ) : (
                            <span style={{ color: '#475569' }}>—</span>
                        )
                    }
                    title={value}
                />
            );

        case 'filepath': {
            const isRealPath = value && (value.includes('\\') || value.includes('/')) && /\.\w{1,5}$/.test(value.trim());
            return (
                <CopyCell
                    value={value || ''}
                    display={
                        value ? (
                            isRealPath ? (
                                <span
                                    style={{ color: '#93c5fd', fontSize: '12px', cursor: 'pointer', textDecoration: 'underline', textDecorationColor: 'rgba(147,197,253,0.3)' }}
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        productionApi.openFile(value).catch(err => {
                                            console.error('[ProductionHub] Open file failed:', err);
                                            alert(`Không thể mở file: ${value}`);
                                        });
                                    }}
                                    title={`Click để mở: ${value}`}
                                >
                                    {basename(value)}
                                </span>
                            ) : (
                                <span style={{ color: '#cbd5e1', fontSize: '12px' }} title={value}>
                                    {truncate(value, 25)}
                                </span>
                            )
                        ) : (
                            <span style={{ color: '#475569' }}>—</span>
                        )
                    }
                    title={value}
                />
            );
        }

        case 'image':
            return (
                <CopyCell
                    value={value || ''}
                    display={
                        value ? (
                            <img
                                src={value}
                                alt="thumb"
                                style={{
                                    width: '48px',
                                    height: '28px',
                                    objectFit: 'cover',
                                    borderRadius: '4px',
                                    border: '1px solid rgba(255,255,255,0.08)',
                                }}
                                onError={(e) => {
                                    (e.target as HTMLImageElement).style.display = 'none';
                                }}
                            />
                        ) : (
                            <span style={{ color: '#475569' }}>—</span>
                        )
                    }
                    title={value}
                />
            );

        case 'status':
            return (
                <CopyCell
                    value={value || 'draft'}
                    display={
                        <span style={{
                            color: getStatusColor(value),
                            background: getStatusBg(value),
                            padding: '2px 8px',
                            borderRadius: '10px',
                            fontSize: '11px',
                            fontWeight: 500,
                            textTransform: 'capitalize',
                        }}>
                            {value || 'draft'}
                        </span>
                    }
                />
            );

        case 'text':
        default: {
            const isLongContent = ['script_full', 'description', 'thumbnail', 'keywords', 'prompts_reference', 'prompts_scene_builder', 'prompts_concept', 'prompts_video'].includes(col.key);
            const maxLen = isLongContent ? 80 : 35;
            return (
                <CopyCell
                    value={value || ''}
                    display={
                        <span style={{ color: value ? '#e2e8f0' : '#475569', fontSize: '12px' }}>
                            {truncate(value || '', maxLen)}
                        </span>
                    }
                    title={value}
                />
            );
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════════════
// Schema Table (Empty State)
// ═══════════════════════════════════════════════════════════════════════════════

const SCHEMA_ROWS = [
    { name: 'project_name', type: 'TEXT', desc: 'Tên project (nhóm productions)', icon: '📁' },
    { name: 'sequence_number', type: 'INTEGER', desc: 'Số thứ tự (tự tăng theo project)', icon: '#' },
    { name: 'original_link', type: 'TEXT', desc: 'Link YouTube gốc', icon: '🔗' },
    { name: 'title', type: 'TEXT', desc: 'Tên production', icon: '📝' },
    { name: 'description', type: 'TEXT', desc: 'Mô tả video', icon: '📄' },
    { name: 'thumbnail', type: 'TEXT', desc: 'Thumbnail prompt (mô tả ảnh bìa)', icon: '🖼️' },
    { name: 'keywords', type: 'TEXT', desc: 'Search keywords cho footage', icon: '🔑' },
    { name: 'script_full', type: 'TEXT', desc: 'Kịch bản remake (chưa split)', icon: '📜' },
    { name: 'script_split', type: 'TEXT', desc: 'Kịch bản đã split (CSV)', icon: '📊' },
    { name: 'voiceover', type: 'TEXT', desc: 'File voiceover', icon: '🎙️' },
    { name: 'video_footage', type: 'TEXT', desc: 'Video footage', icon: '🎬' },
    { name: 'video_final', type: 'TEXT', desc: 'Video hoàn chỉnh', icon: '🎥' },
    { name: 'prompts_reference', type: 'TEXT', desc: 'Prompts ảnh tham chiếu (1 dòng/scene)', icon: '🖼️' },
    { name: 'prompts_scene_builder', type: 'TEXT', desc: 'Prompts scene builder (1 dòng/scene)', icon: '🏗️' },
    { name: 'prompts_concept', type: 'TEXT', desc: 'Prompts ảnh theo concept (1 dòng/scene)', icon: '🎨' },
    { name: 'prompts_video', type: 'TEXT', desc: 'Prompts video (1 dòng/scene)', icon: '🎬' },
    { name: 'upload_platform', type: 'TEXT', desc: 'Nền tảng upload (YouTube, TikTok...)', icon: '🌐' },
    { name: 'channel_name', type: 'TEXT', desc: 'Tên kênh', icon: '📺' },
    { name: 'video_status', type: 'TEXT', desc: 'Trạng thái (draft / uploaded / published)', icon: '🚦' },
];

function SchemaTable() {
    return (
        <div style={{ padding: '2rem' }}>
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                <h3 style={{ color: '#e2e8f0', margin: '0 0 0.5rem', fontSize: '1.1rem' }}>
                    Chưa có production nào
                </h3>
                <p style={{ color: '#64748b', margin: 0, fontSize: '0.85rem' }}>
                    Hoàn thành pipeline để tạo production đầu tiên
                </p>
            </div>

            <div style={{
                background: 'rgba(15, 23, 42, 0.6)',
                borderRadius: '10px',
                border: '1px solid rgba(255,255,255,0.06)',
                overflow: 'hidden',
            }}>
                <div style={{
                    padding: '0.75rem 1rem',
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    display: 'flex',
                    gap: '0.5rem',
                    color: '#94a3b8',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                }}>
                    <span style={{ flex: 1 }}>Column</span>
                    <span style={{ width: '80px' }}>Type</span>
                    <span style={{ flex: 2 }}>Description</span>
                </div>
                {SCHEMA_ROWS.map((row, i) => (
                    <div key={row.name} style={{
                        padding: '0.5rem 1rem',
                        display: 'flex',
                        gap: '0.5rem',
                        alignItems: 'center',
                        borderBottom: i < SCHEMA_ROWS.length - 1 ? '1px solid rgba(255,255,255,0.03)' : 'none',
                        fontSize: '0.8rem',
                    }}>
                        <span style={{ flex: 1, color: '#a5b4fc', fontFamily: 'monospace', fontSize: '0.78rem' }}>{row.name}</span>
                        <span style={{ width: '80px', color: '#64748b', fontFamily: 'monospace', fontSize: '0.72rem' }}>{row.type}</span>
                        <span style={{ flex: 2, color: '#94a3b8' }}>{row.desc}</span>
                    </div>
                ))}
            </div>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main Component
// ═══════════════════════════════════════════════════════════════════════════════

export function ProductionHub() {
    const [productions, setProductions] = useState<Production[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [search, setSearch] = useState('');
    const [stats, setStats] = useState<{ total: number; with_video: number } | null>(null);
    const [deletingId, setDeletingId] = useState<number | null>(null);
    const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const mountedRef = useRef(true);

    // ── Get pipeline selection for dynamic columns ──
    const pipeline = useMemo(() => loadPipelineSelection(), []);

    const visibleColumns = useMemo(() => {
        if (!pipeline) return ALL_COLUMNS.filter(c => c.alwaysShow);
        return ALL_COLUMNS.filter(col => {
            if (col.alwaysShow) return true;
            if (col.showWhen) return col.showWhen(pipeline);
            return false;
        });
    }, [pipeline]);

    // ── Fetch data ──
    const fetchProductions = useCallback(async (searchTerm = '') => {
        try {
            const data = await productionApi.list(searchTerm, 500);
            if (!mountedRef.current) return;
            setProductions(data.productions || []);
        } catch (err) {
            console.error('[ProductionHub] Failed to fetch:', err);
        }
    }, []);

    const fetchStats = useCallback(async () => {
        try {
            const data = await productionApi.getStats();
            if (!mountedRef.current) return;
            setStats(data);
        } catch { /* ignore */ }
    }, []);

    // ── Initial load ──
    useEffect(() => {
        mountedRef.current = true;
        setIsLoading(true);
        Promise.all([fetchProductions(search), fetchStats()]).finally(() => {
            if (mountedRef.current) setIsLoading(false);
        });
        return () => { mountedRef.current = false; };
    }, []);

    // ── Auto-refresh polling ──
    useEffect(() => {
        function startPolling() {
            if (pollRef.current) clearInterval(pollRef.current);
            pollRef.current = setInterval(() => {
                if (document.visibilityState === 'visible' && mountedRef.current) {
                    fetchProductions(search);
                    fetchStats();
                }
            }, POLL_INTERVAL_MS);
        }

        startPolling();

        function handleVisibility() {
            if (document.visibilityState === 'visible') {
                fetchProductions(search);
                fetchStats();
            }
        }
        document.addEventListener('visibilitychange', handleVisibility);

        return () => {
            if (pollRef.current) clearInterval(pollRef.current);
            document.removeEventListener('visibilitychange', handleVisibility);
        };
    }, [search, fetchProductions, fetchStats]);

    // ── Search handler ──
    const handleSearch = useCallback((value: string) => {
        setSearch(value);
        fetchProductions(value);
    }, [fetchProductions]);

    // ── Delete handler ──
    const handleDelete = useCallback(async (id: number) => {
        if (deletingId) return;
        setDeletingId(id);
        try {
            await productionApi.delete(id, true);
            setProductions(prev => prev.filter(p => p.id !== id));
            fetchStats();
        } catch (err) {
            console.error('[ProductionHub] Delete failed:', err);
        } finally {
            setDeletingId(null);
        }
    }, [deletingId, fetchStats]);

    // ── Open folder ──
    const handleOpenFolder = useCallback(async (id: number) => {
        try {
            await productionApi.openFolder(id);
        } catch (err) {
            console.error('[ProductionHub] Open folder failed:', err);
        }
    }, []);

    // ── Scan & Import ──
    const [isImporting, setIsImporting] = useState(false);
    const handleScanImport = useCallback(async () => {
        if (isImporting) return;
        setIsImporting(true);
        try {
            const result = await productionApi.scanImport();
            console.log('[ProductionHub] Scan import result:', result);
            if (result.imported_count > 0) {
                fetchProductions(search);
                fetchStats();
            }
            alert(result.message);
        } catch (err) {
            console.error('[ProductionHub] Scan import failed:', err);
            alert('Import thất bại');
        } finally {
            setIsImporting(false);
        }
    }, [isImporting, search, fetchProductions, fetchStats]);

    // ── Styles ──
    const styles = getStyles();

    return (
        <div style={styles.container}>
            {/* Header */}
            <div style={styles.header}>
                <div style={styles.headerLeft}>
                    <h2 style={styles.headerTitle}>
                        Production Hub
                    </h2>
                    {stats && (
                        <div style={styles.statsRow}>
                            <span style={styles.statBadge}>
                                {stats.total} productions
                            </span>
                            <span style={{ ...styles.statBadge, background: 'rgba(34, 197, 94, 0.12)', color: '#4ade80' }}>
                                {stats.with_video} có video
                            </span>
                        </div>
                    )}
                </div>
                <div style={styles.headerRight}>
                    <button
                        onClick={handleScanImport}
                        disabled={isImporting}
                        style={{
                            padding: '6px 12px',
                            background: isImporting ? 'rgba(99,102,241,0.3)' : 'rgba(99,102,241,0.15)',
                            color: '#a5b4fc',
                            border: '1px solid rgba(99,102,241,0.3)',
                            borderRadius: '6px',
                            cursor: isImporting ? 'wait' : 'pointer',
                            fontSize: '0.8rem',
                            fontWeight: 500,
                            marginRight: '8px',
                        }}
                    >
                        {isImporting ? '⏳ Đang scan...' : '📥 Import từ ổ đĩa'}
                    </button>
                    <div style={styles.searchWrap}>
                        <span style={{ color: '#64748b' }}>🔍</span>
                        <input
                            type="text"
                            placeholder="Tìm theo title hoặc project..."
                            value={search}
                            onChange={(e) => handleSearch(e.target.value)}
                            style={styles.searchInput}
                        />
                        {search && (
                            <button onClick={() => handleSearch('')} style={styles.clearBtn}>✕</button>
                        )}
                    </div>
                </div>
            </div>

            {/* Loading */}
            {isLoading && (
                <div style={styles.loadingRow}>
                    <div className="spinner" style={styles.spinner} />
                    <span style={{ color: '#94a3b8' }}>Đang tải...</span>
                </div>
            )}

            {/* Empty state */}
            {!isLoading && productions.length === 0 && <SchemaTable />}

            {/* Data Table */}
            {!isLoading && productions.length > 0 && (
                <div style={styles.tableWrap}>
                    <table style={styles.table}>
                        <thead>
                            <tr>
                                {visibleColumns.map(col => (
                                    <th key={col.key} style={{ ...styles.th, width: col.width, minWidth: col.width }}>
                                        {col.label}
                                    </th>
                                ))}
                                <th style={{ ...styles.th, width: '80px', minWidth: '80px', textAlign: 'center' }}>
                                    ⚙️
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {productions.map((prod) => (
                                <tr
                                    key={prod.id}
                                    style={styles.tr}
                                    onMouseEnter={(e) => {
                                        (e.currentTarget as HTMLTableRowElement).style.background = 'rgba(99, 102, 241, 0.06)';
                                    }}
                                    onMouseLeave={(e) => {
                                        (e.currentTarget as HTMLTableRowElement).style.background = 'transparent';
                                    }}
                                >
                                    {visibleColumns.map(col => (
                                        <td key={col.key} style={{ ...styles.td, width: col.width, maxWidth: col.width }}>
                                            {renderCellContent(col, prod)}
                                        </td>
                                    ))}
                                    <td style={{ ...styles.td, width: '80px', textAlign: 'center' }}>
                                        <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                                            <button
                                                onClick={() => handleOpenFolder(prod.id)}
                                                style={styles.actionBtn}
                                                title="Mở thư mục"
                                            >
                                                📂
                                            </button>
                                            <button
                                                onClick={() => handleDelete(prod.id)}
                                                disabled={deletingId === prod.id}
                                                style={{
                                                    ...styles.actionBtn,
                                                    opacity: deletingId === prod.id ? 0.4 : 1,
                                                }}
                                                title="Xóa"
                                            >
                                                {deletingId === prod.id ? '⏳' : '🗑️'}
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}

            {/* Inline styles for hover effects */}
            <style>{`
                .cell-copy-wrap:hover .copy-icon {
                    opacity: 1 !important;
                }
                .cell-copy-wrap:active {
                    transform: scale(0.98);
                }
                @keyframes spin {
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════════════════
// Styles
// ═══════════════════════════════════════════════════════════════════════════════

function getStyles(): Record<string, React.CSSProperties> {
    return {
        container: {
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            gap: '0',
            background: 'rgba(15, 23, 42, 0.4)',
            borderRadius: '12px',
            border: '1px solid rgba(255,255,255,0.06)',
            overflow: 'hidden',
        },
        header: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '1rem',
            padding: '0.875rem 1rem',
            borderBottom: '1px solid rgba(255,255,255,0.06)',
            flexWrap: 'wrap' as const,
        },
        headerLeft: {
            display: 'flex',
            alignItems: 'center',
            gap: '1rem',
            flexWrap: 'wrap' as const,
        },
        headerTitle: {
            margin: 0,
            fontSize: '1rem',
            fontWeight: 600,
            color: '#e2e8f0',
            display: 'flex',
            alignItems: 'center',
        },
        statsRow: {
            display: 'flex',
            gap: '0.5rem',
        },
        statBadge: {
            fontSize: '0.72rem',
            padding: '3px 10px',
            borderRadius: '12px',
            background: 'rgba(99, 102, 241, 0.12)',
            color: '#a5b4fc',
            fontWeight: 500,
        },
        headerRight: {
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
        },
        searchWrap: {
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(30, 41, 59, 0.8)',
            borderRadius: '8px',
            border: '1px solid rgba(255,255,255,0.08)',
            padding: '0 10px',
        },
        searchInput: {
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#e2e8f0',
            fontSize: '0.8rem',
            padding: '6px 0',
            width: '200px',
        },
        clearBtn: {
            background: 'none',
            border: 'none',
            color: '#64748b',
            cursor: 'pointer',
            padding: '0 2px',
            fontSize: '12px',
        },
        loadingRow: {
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem',
            padding: '3rem',
        },
        spinner: {
            width: '20px',
            height: '20px',
            border: '2px solid rgba(255,255,255,0.1)',
            borderTopColor: '#6366f1',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
        },
        tableWrap: {
            overflowX: 'auto' as const,
            overflowY: 'auto' as const,
            maxHeight: 'calc(100vh - 200px)',
        },
        table: {
            width: '100%',
            borderCollapse: 'collapse' as const,
            fontSize: '0.8rem',
            tableLayout: 'fixed' as const,
        },
        th: {
            position: 'sticky' as const,
            top: 0,
            zIndex: 10,
            padding: '8px 10px',
            textAlign: 'left' as const,
            color: '#94a3b8',
            fontSize: '0.7rem',
            fontWeight: 600,
            textTransform: 'uppercase' as const,
            letterSpacing: '0.04em',
            background: 'rgba(15, 23, 42, 0.95)',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            whiteSpace: 'nowrap' as const,
        },
        tr: {
            transition: 'background 0.15s',
            borderBottom: '1px solid rgba(255,255,255,0.03)',
        },
        td: {
            padding: '6px 10px',
            verticalAlign: 'middle' as const,
            overflow: 'hidden' as const,
        },
        actionBtn: {
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            fontSize: '14px',
            padding: '4px',
            borderRadius: '4px',
            transition: 'background 0.15s',
            lineHeight: 1,
        },
    };
}

export default ProductionHub;
