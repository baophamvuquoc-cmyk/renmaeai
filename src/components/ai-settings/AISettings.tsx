import { useState, useEffect, useCallback } from 'react';
import { useAISettingsStore, AIProvider } from '../../stores/useAISettingsStore';
import { aiApi, footageKeysApi } from '../../lib/api';
import type { FootageKeyInfo } from '../../lib/api';
import { Key, CheckCircle, XCircle, Loader, RefreshCw, Film, Sparkles, Bot, Cpu, Plus, Trash2, ToggleLeft, ToggleRight } from 'lucide-react';


export default function AISettings() {
    const {
        openaiApiKey,
        openaiBaseUrl,
        openaiModel,
        geminiApiKey,
        customApiKey,
        customBaseUrl,
        customModel,
        activeContentProvider,
        connectionStatus,
        availableModels,
        setOpenaiApiKey,
        setOpenaiBaseUrl,
        setOpenaiModel,
        setGeminiApiKey,
        setCustomApiKey,
        setCustomBaseUrl,
        setCustomModel,
        setActiveContentProvider,
        setConnectionStatus,
        setAvailableModels,
        isProviderConfigured,
        loadSettingsFromBackend,
        isLoaded,
    } = useAISettingsStore();

    const [showTokens, setShowTokens] = useState(false);
    const [loadingModels, setLoadingModels] = useState(false);

    //  Key Pool State 
    const [pexelsKeys, setPexelsKeys] = useState<FootageKeyInfo[]>([]);
    const [pixabayKeys, setPixabayKeys] = useState<FootageKeyInfo[]>([]);
    const [newPexelsKey, setNewPexelsKey] = useState('');
    const [newPexelsLabel, setNewPexelsLabel] = useState('');
    const [newPixabayKey, setNewPixabayKey] = useState('');
    const [newPixabayLabel, setNewPixabayLabel] = useState('');
    const [isAddingKey, setIsAddingKey] = useState<{ pexels: boolean; pixabay: boolean }>({ pexels: false, pixabay: false });
    const [testingKeyId, setTestingKeyId] = useState<number | null>(null);

    const loadKeys = useCallback(async (source: 'pexels' | 'pixabay') => {
        try {
            const result = await footageKeysApi.getKeys(source);
            if (result.success) {
                if (source === 'pexels') setPexelsKeys(result.keys);
                else setPixabayKeys(result.keys);
            }
        } catch (e) {
            console.error(`Failed to load ${source} keys:`, e);
        }
    }, []);

    useEffect(() => {
        if (!isLoaded) {
            loadSettingsFromBackend();
        }
    }, [isLoaded, loadSettingsFromBackend]);

    useEffect(() => {
        loadKeys('pexels');
        loadKeys('pixabay');
    }, [loadKeys]);

    const handleToggleProvider = (provider: AIProvider) => {
        if (activeContentProvider === provider) {
            setActiveContentProvider(null);
        } else {
            setActiveContentProvider(provider);
            setAvailableModels([]);
        }
    };

    const handleFetchModels = async (baseUrl: string, apiKey: string) => {
        if (!apiKey) {
            alert('Vui lòng nhập API Key trước');
            return;
        }
        const url = baseUrl || 'https://api.openai.com/v1';
        setLoadingModels(true);
        try {
            const models = await aiApi.fetchModels(url, apiKey);
            setAvailableModels(models);
            if (models.length > 0) {
                alert(` Tìm thấy ${models.length} models từ provider`);
            } else {
                alert(' Không tìm thấy model nào. API có thể không hỗ trợ endpoint /models.');
            }
        } catch (error: any) {
            alert(` Lỗi: ${error.message}`);
        } finally {
            setLoadingModels(false);
        }
    };

    const handleTestConnection = async (provider: string) => {
        setConnectionStatus(provider, 'testing');
        try {
            const settings = {
                geminiApiKey,
                openaiApiKey: provider === 'custom' ? customApiKey : openaiApiKey,
                openaiBaseUrl: provider === 'custom' ? customBaseUrl : openaiBaseUrl,
                openaiModel: provider === 'custom' ? customModel : openaiModel,
            };
            const testProvider = provider === 'custom' ? 'openai' : provider;
            const result = await aiApi.testConnection(testProvider, settings);

            if (result.success === false) {
                setConnectionStatus(provider, 'failed');
                const errorMsg = result.message || result.error || result.detail || 'Không thể kết nối';
                setTimeout(() => {
                    alert(` Kết nối thất bại: ${errorMsg}`);
                }, 100);
                return;
            }

            setConnectionStatus(provider, 'connected');
            setTimeout(() => {
                alert(` Kết nối thành công!`);
            }, 100);
        } catch (error: any) {
            setConnectionStatus(provider, 'failed');
            const msg = error.response?.data?.error || error.response?.data?.detail || error.message;
            setTimeout(() => {
                alert(` Kết nối thất bại: ${msg}`);
            }, 100);
        }
    };

    //  Key Pool CRUD handlers 
    const handleAddKey = async (source: 'pexels' | 'pixabay') => {
        const apiKey = source === 'pexels' ? newPexelsKey : newPixabayKey;
        const label = source === 'pexels' ? newPexelsLabel : newPixabayLabel;
        if (!apiKey.trim()) { alert('Vui lòng nhập API Key'); return; }

        try {
            const result = await footageKeysApi.addKey(source, apiKey.trim(), label.trim());
            if (result.success) {
                if (source === 'pexels') { setNewPexelsKey(''); setNewPexelsLabel(''); }
                else { setNewPixabayKey(''); setNewPixabayLabel(''); }
                setIsAddingKey(prev => ({ ...prev, [source]: false }));
                await loadKeys(source);
            } else {
                alert(`Lỗi: ${result.error || 'Key đã tồn tại'}`);
            }
        } catch (error: any) {
            const msg = error.response?.data?.error || error.message;
            alert(`Lỗi thêm key: ${msg}`);
        }
    };

    const handleRemoveKey = async (keyId: number, source: string) => {
        if (!confirm('Bạn chắc chắn muốn xoá key này?')) return;
        try {
            await footageKeysApi.removeKey(keyId);
            await loadKeys(source as 'pexels' | 'pixabay');
        } catch (e) { console.error('Remove key failed:', e); }
    };

    const handleToggleKey = async (keyId: number, currentActive: number, source: string) => {
        try {
            await footageKeysApi.toggleKey(keyId, currentActive === 0);
            await loadKeys(source as 'pexels' | 'pixabay');
        } catch (e) { console.error('Toggle key failed:', e); }
    };

    const handleTestPoolKey = async (keyId: number, source: 'pexels' | 'pixabay', apiKey: string) => {
        setTestingKeyId(keyId);
        try {
            const result = await footageKeysApi.testKey(source, apiKey);
            if (result.success) {
                alert(` ${source === 'pexels' ? 'Pexels' : 'Pixabay'} key hoạt động!`);
            }
            await loadKeys(source);
        } catch (error: any) {
            const msg = error.response?.data?.error || error.message;
            alert(` Key thất bại: ${msg}`);
            await loadKeys(source);
        } finally {
            setTestingKeyId(null);
        }
    };

    const getStatusIcon = (provider: string) => {
        const status = connectionStatus[provider] || 'unknown';
        switch (status) {
            case 'testing':
                return <Loader size={16} className="animate-spin" style={{ color: '#60a5fa' }} />;
            case 'connected':
                return <CheckCircle size={16} style={{ color: '#34d399' }} />;
            case 'failed':
                return <XCircle size={16} style={{ color: '#f87171' }} />;
            default:
                return null;
        }
    };

    const renderModelSelector = (
        currentModel: string,
        setModel: (m: string) => void,
        baseUrl: string,
        apiKey: string
    ) => (
        <div className="form-group">
            <label>Model</label>
            <div className="input-with-button">
                {availableModels.length > 0 ? (
                    <select
                        className="input"
                        value={currentModel}
                        onChange={(e) => setModel(e.target.value)}
                    >
                        {availableModels.map((model) => (
                            <option key={model.id} value={model.id}>
                                {model.name} - {model.description}
                            </option>
                        ))}
                    </select>
                ) : (
                    <input
                        type="text"
                        className="input"
                        placeholder="gpt-4o"
                        value={currentModel}
                        onChange={(e) => setModel(e.target.value)}
                    />
                )}
                <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => handleFetchModels(baseUrl, apiKey)}
                    disabled={loadingModels || !apiKey}
                    title="Fetch models từ API"
                >
                    {loadingModels ? (
                        <Loader size={16} className="animate-spin" />
                    ) : (
                        <RefreshCw size={16} />
                    )}
                </button>
            </div>
            <small className="text-tertiary">
                Click refresh để lấy danh sách models. Nhập tay nếu biết tên model.
            </small>
        </div>
    );

    //  Key Pool Section Renderer 
    const renderKeyPoolSection = (source: 'pexels' | 'pixabay', keys: FootageKeyInfo[], docsUrl: string) => {
        const sourceName = source === 'pexels' ? 'Pexels' : 'Pixabay';
        const activeCount = keys.filter(k => k.is_active).length;
        const isAdding = isAddingKey[source];
        const newKey = source === 'pexels' ? newPexelsKey : newPixabayKey;
        const newLabel = source === 'pexels' ? newPexelsLabel : newPixabayLabel;
        const setNewKey = source === 'pexels' ? setNewPexelsKey : setNewPixabayKey;
        const setNewLabel = source === 'pexels' ? setNewPexelsLabel : setNewPixabayLabel;

        return (
            <div className="key-pool-section">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <strong style={{ fontSize: 14 }}>{sourceName}</strong>
                        <span className="badge badge-sm" style={{
                            background: activeCount > 0 ? 'rgba(52,211,153,0.15)' : 'rgba(248,113,113,0.15)',
                            color: activeCount > 0 ? '#34d399' : '#f87171',
                            padding: '2px 8px', borderRadius: 10, fontSize: 11
                        }}>
                            {activeCount} active / {keys.length} total
                        </span>
                    </div>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                        <a href={docsUrl} target="_blank" rel="noopener noreferrer" style={{ fontSize: 11, color: '#60a5fa' }}>Lấy key</a>
                        <button
                            className="btn btn-accent btn-sm"
                            style={{ padding: '3px 10px', fontSize: 11 }}
                            onClick={() => setIsAddingKey(prev => ({ ...prev, [source]: !prev[source] }))}
                        >
                            <Plus size={13} style={{ marginRight: 3 }} />
                            Thêm Key
                        </button>
                    </div>
                </div>

                {/* Add key form */}
                {isAdding && (
                    <div style={{ display: 'flex', gap: 6, marginBottom: 8, alignItems: 'center' }}>
                        <input
                            type="text"
                            className="input"
                            placeholder="API Key..."
                            value={newKey}
                            onChange={(e) => setNewKey(e.target.value)}
                            style={{ flex: 2, fontSize: 12, padding: '5px 8px' }}
                        />
                        <input
                            type="text"
                            className="input"
                            placeholder="Label (tuỳ chọn)..."
                            value={newLabel}
                            onChange={(e) => setNewLabel(e.target.value)}
                            style={{ flex: 1, fontSize: 12, padding: '5px 8px' }}
                        />
                        <button
                            className="btn btn-accent btn-sm"
                            style={{ padding: '5px 12px', fontSize: 11 }}
                            onClick={() => handleAddKey(source)}
                            disabled={!newKey.trim()}
                        >
                            Lưu
                        </button>
                        <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '5px 8px', fontSize: 11 }}
                            onClick={() => {
                                setIsAddingKey(prev => ({ ...prev, [source]: false }));
                                setNewKey(''); setNewLabel('');
                            }}
                        >
                            Huỷ
                        </button>
                    </div>
                )}

                {/* Key list table */}
                {keys.length > 0 ? (
                    <div style={{ border: '1px solid rgba(255,255,255,0.06)', borderRadius: 8, overflow: 'hidden' }}>
                        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                            <thead>
                                <tr style={{ background: 'rgba(255,255,255,0.03)', textAlign: 'left' }}>
                                    <th style={{ padding: '6px 10px', fontWeight: 500 }}>Label</th>
                                    <th style={{ padding: '6px 10px', fontWeight: 500 }}>API Key</th>
                                    <th style={{ padding: '6px 10px', fontWeight: 500, textAlign: 'center' }}>Sử dụng</th>
                                    <th style={{ padding: '6px 10px', fontWeight: 500, textAlign: 'center' }}>Trạng thái</th>
                                    <th style={{ padding: '6px 10px', fontWeight: 500, textAlign: 'right' }}>Hành động</th>
                                </tr>
                            </thead>
                            <tbody>
                                {keys.map((k) => (
                                    <tr key={k.id} style={{
                                        borderTop: '1px solid rgba(255,255,255,0.04)',
                                        opacity: k.is_active ? 1 : 0.45,
                                        background: k.is_active ? 'transparent' : 'rgba(0,0,0,0.15)',
                                    }}>
                                        <td style={{ padding: '6px 10px' }}>
                                            {k.label || <span style={{ color: '#6b7280', fontStyle: 'italic' }}>Không tên</span>}
                                        </td>
                                        <td style={{ padding: '6px 10px', fontFamily: 'monospace', fontSize: 11, color: '#94a3b8' }}>
                                            {showTokens ? k.api_key : k.api_key_masked}
                                        </td>
                                        <td style={{ padding: '6px 10px', textAlign: 'center', color: '#94a3b8' }}>
                                            {k.request_count}
                                        </td>
                                        <td style={{ padding: '6px 10px', textAlign: 'center' }}>
                                            {k.test_status === 'success' && <CheckCircle size={14} style={{ color: '#34d399' }} />}
                                            {k.test_status === 'failed' && <XCircle size={14} style={{ color: '#f87171' }} />}
                                            {k.test_status === 'untested' && <span style={{ color: '#6b7280', fontSize: 11 }}>--</span>}
                                        </td>
                                        <td style={{ padding: '5px 10px', textAlign: 'right' }}>
                                            <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                                                <button
                                                    className="btn btn-secondary btn-sm"
                                                    style={{ padding: '2px 6px', fontSize: 10 }}
                                                    title="Test key"
                                                    disabled={testingKeyId === k.id}
                                                    onClick={() => handleTestPoolKey(k.id, source, k.api_key)}
                                                >
                                                    {testingKeyId === k.id ? <Loader size={11} className="animate-spin" /> : 'Test'}
                                                </button>
                                                <button
                                                    className="btn btn-secondary btn-sm"
                                                    style={{ padding: '2px 6px' }}
                                                    title={k.is_active ? 'Tắt key' : 'Bật key'}
                                                    onClick={() => handleToggleKey(k.id, k.is_active, source)}
                                                >
                                                    {k.is_active
                                                        ? <ToggleRight size={14} style={{ color: '#34d399' }} />
                                                        : <ToggleLeft size={14} style={{ color: '#6b7280' }} />}
                                                </button>
                                                <button
                                                    className="btn btn-secondary btn-sm"
                                                    style={{ padding: '2px 6px', color: '#f87171' }}
                                                    title="Xoá key"
                                                    onClick={() => handleRemoveKey(k.id, source)}
                                                >
                                                    <Trash2 size={12} />
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <div style={{ padding: '12px 10px', textAlign: 'center', color: '#6b7280', fontSize: 12, background: 'rgba(255,255,255,0.02)', borderRadius: 8 }}>
                        Chưa có key nào. Nhấn "Thêm Key" để bắt đầu.
                    </div>
                )}
            </div>
        );
    };

    return (
        <div className="ai-settings">
            <div className="settings-header">
                <div>
                    <h2>Cấu Hình AI</h2>
                    <p className="text-secondary">
                        Thiết lập API keys cho Content AI và Footage
                    </p>
                </div>
                <div className="flex gap-2">
                    <button
                        className="btn btn-secondary"
                        onClick={() => setShowTokens(!showTokens)}
                    >
                        <Key size={18} />
                        {showTokens ? 'Ẩn API Keys' : 'Hiện API Keys'}
                    </button>
                </div>
            </div>

            <div className="settings-sections">
                {/*  */}
                {/* SECTION 1: Content AI */}
                {/*  */}
                <div className="glass-card settings-section">
                    <div className="section-header">
                        <div className="flex items-center gap-2">
                            <Sparkles size={22} style={{ color: '#a78bfa' }} />
                            <h3>Content AI</h3>
                        </div>
                        <small className="text-tertiary">Chọn AI provider để tạo nội dung</small>
                    </div>

                    {/* Provider Checkboxes */}
                    <div className="provider-checkboxes">
                        <label className={`provider-checkbox ${activeContentProvider === 'openai' ? 'active' : ''}`}>
                            <input
                                type="checkbox"
                                checked={activeContentProvider === 'openai'}
                                onChange={() => handleToggleProvider('openai')}
                            />
                            <img
                                src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2310a37f'%3E%3Cpath d='M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z'/%3E%3C/svg%3E"
                                alt="ChatGPT"
                                style={{ width: '18px', height: '18px' }}
                            />
                            <span>ChatGPT</span>
                            {isProviderConfigured('openai') && (
                                <span className="badge badge-success badge-sm"></span>
                            )}
                        </label>

                        <label className={`provider-checkbox ${activeContentProvider === 'gemini_api' ? 'active' : ''}`}>
                            <input
                                type="checkbox"
                                checked={activeContentProvider === 'gemini_api'}
                                onChange={() => handleToggleProvider('gemini_api')}
                            />
                            <Bot size={18} style={{ color: '#818cf8' }} />
                            <span>Gemini</span>
                            {isProviderConfigured('gemini_api') && (
                                <span className="badge badge-success badge-sm"></span>
                            )}
                        </label>

                        <label className={`provider-checkbox ${activeContentProvider === 'custom' ? 'active' : ''}`}>
                            <input
                                type="checkbox"
                                checked={activeContentProvider === 'custom'}
                                onChange={() => handleToggleProvider('custom')}
                            />
                            <Cpu size={18} style={{ color: '#f59e0b' }} />
                            <span>Custom API</span>
                            {isProviderConfigured('custom') && (
                                <span className="badge badge-success badge-sm"></span>
                            )}
                        </label>
                    </div>

                    {/*  ChatGPT / OpenAI Fields  */}
                    {activeContentProvider === 'openai' && (
                        <div className="provider-fields">
                            <div className="provider-fields-header">
                                <h4>
                                    <img
                                        src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%2310a37f'%3E%3Cpath d='M22.282 9.821a5.985 5.985 0 0 0-.516-4.91 6.046 6.046 0 0 0-6.51-2.9A6.065 6.065 0 0 0 4.981 4.18a5.985 5.985 0 0 0-3.998 2.9 6.046 6.046 0 0 0 .743 7.097 5.98 5.98 0 0 0 .51 4.911 6.051 6.051 0 0 0 6.515 2.9A5.985 5.985 0 0 0 13.26 24a6.056 6.056 0 0 0 5.772-4.206 5.99 5.99 0 0 0 3.997-2.9 6.056 6.056 0 0 0-.747-7.073zM13.26 22.43a4.476 4.476 0 0 1-2.876-1.04l.141-.081 4.779-2.758a.795.795 0 0 0 .392-.681v-6.737l2.02 1.168a.071.071 0 0 1 .038.052v5.583a4.504 4.504 0 0 1-4.494 4.494zM3.6 18.304a4.47 4.47 0 0 1-.535-3.014l.142.085 4.783 2.759a.771.771 0 0 0 .78 0l5.843-3.369v2.332a.08.08 0 0 1-.033.062L9.74 19.95a4.5 4.5 0 0 1-6.14-1.646zM2.34 7.896a4.485 4.485 0 0 1 2.366-1.973V11.6a.766.766 0 0 0 .388.676l5.815 3.355-2.02 1.168a.076.076 0 0 1-.071 0l-4.83-2.786A4.504 4.504 0 0 1 2.34 7.872zm16.597 3.855l-5.833-3.387L15.119 7.2a.076.076 0 0 1 .071 0l4.83 2.791a4.494 4.494 0 0 1-.676 8.105v-5.678a.79.79 0 0 0-.407-.667zm2.01-3.023l-.141-.085-4.774-2.782a.776.776 0 0 0-.785 0L9.409 9.23V6.897a.066.066 0 0 1 .028-.061l4.83-2.787a4.5 4.5 0 0 1 6.68 4.66zm-12.64 4.135l-2.02-1.164a.08.08 0 0 1-.038-.057V6.075a4.5 4.5 0 0 1 7.375-3.453l-.142.08L8.704 5.46a.795.795 0 0 0-.393.681zm1.097-2.365l2.602-1.5 2.607 1.5v2.999l-2.597 1.5-2.607-1.5z'/%3E%3C/svg%3E"
                                        alt="OpenAI"
                                        style={{ width: '18px', height: '18px' }}
                                    />
                                    OpenAI / ChatGPT
                                </h4>
                                <div className="flex items-center gap-2">
                                    {getStatusIcon('openai')}
                                </div>
                            </div>

                            <div className="form-group">
                                <label>OpenAI API Key</label>
                                <div className="input-with-button">
                                    <input
                                        type={showTokens ? 'text' : 'password'}
                                        className="input"
                                        placeholder="sk-proj-..."
                                        value={openaiApiKey}
                                        onChange={(e) => setOpenaiApiKey(e.target.value)}
                                    />
                                    <button
                                        className="btn btn-accent btn-sm"
                                        onClick={() => handleTestConnection('openai')}
                                        disabled={!openaiApiKey}
                                    >
                                        Test
                                    </button>
                                </div>
                                <small className="text-tertiary">
                                    Lấy API key tại{' '}
                                    <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-accent-blue">
                                        OpenAI Platform
                                    </a>
                                </small>
                            </div>

                            <div className="form-group">
                                <label>Base URL <span className="text-tertiary">(Optional)</span></label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="https://api.openai.com/v1"
                                    value={openaiBaseUrl}
                                    onChange={(e) => setOpenaiBaseUrl(e.target.value)}
                                />
                                <small className="text-tertiary">
                                    Để trống để sử dụng mặc định. Dùng khi dùng Azure OpenAI, local models (Ollama), hoặc proxy.
                                </small>
                            </div>

                            {renderModelSelector(openaiModel, setOpenaiModel, openaiBaseUrl, openaiApiKey)}
                        </div>
                    )}

                    {/*  Gemini Fields  */}
                    {activeContentProvider === 'gemini_api' && (
                        <div className="provider-fields">
                            <div className="provider-fields-header">
                                <h4>
                                    <Bot size={18} style={{ color: '#818cf8' }} />
                                    Gemini API (Free)
                                </h4>
                                <div className="flex items-center gap-2">
                                    {getStatusIcon('gemini_api')}
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Gemini API Key</label>
                                <div className="input-with-button">
                                    <input
                                        type={showTokens ? 'text' : 'password'}
                                        className="input"
                                        placeholder="AIzaSy..."
                                        value={geminiApiKey}
                                        onChange={(e) => setGeminiApiKey(e.target.value)}
                                    />
                                    <button
                                        className="btn btn-accent btn-sm"
                                        onClick={() => handleTestConnection('gemini_api')}
                                        disabled={!geminiApiKey}
                                    >
                                        Test
                                    </button>
                                </div>
                                <small className="text-tertiary">
                                    Lấy key miễn phí tại{' '}
                                    <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noopener noreferrer" className="text-accent-blue">
                                        Google AI Studio
                                    </a>
                                </small>
                            </div>
                        </div>
                    )}

                    {/*  Custom API Fields  */}
                    {activeContentProvider === 'custom' && (
                        <div className="provider-fields">
                            <div className="provider-fields-header">
                                <h4>
                                    <Cpu size={18} style={{ color: '#f59e0b' }} />
                                    Custom API Provider
                                </h4>
                                <div className="flex items-center gap-2">
                                    {getStatusIcon('custom')}
                                </div>
                            </div>

                            <div className="form-group">
                                <label>Base URL <span className="text-accent" style={{ color: '#f87171' }}>*</span></label>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="https://api.example.com/v1"
                                    value={customBaseUrl}
                                    onChange={(e) => setCustomBaseUrl(e.target.value)}
                                />
                                <small className="text-tertiary">
                                    URL endpoint của provider (ví dụ: OpenRouter, Together, Groq, Ollama local...)
                                </small>
                            </div>

                            <div className="form-group">
                                <label>API Key</label>
                                <div className="input-with-button">
                                    <input
                                        type={showTokens ? 'text' : 'password'}
                                        className="input"
                                        placeholder="Nhập API key..."
                                        value={customApiKey}
                                        onChange={(e) => setCustomApiKey(e.target.value)}
                                    />
                                    <button
                                        className="btn btn-accent btn-sm"
                                        onClick={() => handleTestConnection('custom')}
                                        disabled={!customApiKey || !customBaseUrl}
                                    >
                                        Test
                                    </button>
                                </div>
                            </div>

                            {renderModelSelector(customModel, setCustomModel, customBaseUrl, customApiKey)}
                        </div>
                    )}

                    {/* No provider selected message */}
                    {!activeContentProvider && (
                        <div className="no-provider-message">
                            <Sparkles size={24} style={{ color: '#6b7280', opacity: 0.5 }} />
                            <p>Chọn một AI provider ở trên để bắt đầu cấu hình</p>
                        </div>
                    )}
                </div>

                {/*  */}
                {/* SECTION 2: Footage API Key Pool */}
                {/*  */}
                <div className="glass-card settings-section">
                    <div className="section-header">
                        <div className="flex items-center gap-2">
                            <Film size={22} style={{ color: '#f59e0b' }} />
                            <h3>Footage API Key Pool</h3>
                        </div>
                        <small className="text-tertiary">Quản lý nhiều API keys - tự động xoay vòng (round-robin)</small>
                    </div>

                    {/*  Pexels Keys  */}
                    {renderKeyPoolSection('pexels', pexelsKeys, 'https://www.pexels.com/api/')}

                    <div style={{ height: 16 }} />

                    {/*  Pixabay Keys  */}
                    {renderKeyPoolSection('pixabay', pixabayKeys, 'https://pixabay.com/api/docs/')}
                </div>
            </div>

            <style>{`
                .ai-settings {
                    max-width: 1200px;
                    margin: 0 auto;
                }

                .settings-header {
                    display: flex;
                    align-items: flex-start;
                    justify-content: space-between;
                    margin-bottom: 2rem;
                }

                .settings-header h2 {
                    font-size: 1.75rem;
                    margin-bottom: 0.5rem;
                }

                .settings-sections {
                    display: flex;
                    flex-direction: column;
                    gap: 1.5rem;
                }

                .settings-section {
                    padding: 1.5rem;
                }

                .section-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 1.5rem;
                    padding-bottom: 1rem;
                    border-bottom: 1px solid var(--border-color);
                }

                .section-header h3 {
                    margin: 0;
                    font-size: 1.2rem;
                }

                /*  Provider Checkboxes  */
                .provider-checkboxes {
                    display: flex;
                    gap: 0.75rem;
                    margin-bottom: 1.5rem;
                    flex-wrap: wrap;
                }

                .provider-checkbox {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.625rem 1rem;
                    background: var(--bg-secondary, #1e293b);
                    border: 2px solid var(--border-color, #334155);
                    border-radius: 10px;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    font-size: 0.9rem;
                    font-weight: 500;
                    user-select: none;
                }

                .provider-checkbox:hover {
                    border-color: #667eea;
                    background: rgba(102, 126, 234, 0.05);
                }

                .provider-checkbox.active {
                    border-color: #667eea;
                    background: rgba(102, 126, 234, 0.1);
                    box-shadow: 0 0 0 1px rgba(102, 126, 234, 0.3);
                }

                .provider-checkbox input[type="checkbox"] {
                    width: 16px;
                    height: 16px;
                    accent-color: #667eea;
                    cursor: pointer;
                }

                .badge-sm {
                    font-size: 0.7rem;
                    padding: 1px 6px;
                    border-radius: 4px;
                }

                /*  Provider Fields  */
                .provider-fields {
                    animation: slideDown 0.25s ease-out;
                    padding: 1.25rem;
                    background: rgba(255, 255, 255, 0.02);
                    border: 1px solid var(--border-color, #334155);
                    border-radius: 10px;
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }

                .provider-fields-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    margin-bottom: 0.25rem;
                }

                .provider-fields-header h4 {
                    margin: 0;
                    font-size: 1rem;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                }

                @keyframes slideDown {
                    from {
                        opacity: 0;
                        transform: translateY(-8px);
                    }
                    to {
                        opacity: 1;
                        transform: translateY(0);
                    }
                }

                /*  Footage Fields  */
                .footage-fields {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }

                /*  No Provider Message  */
                .no-provider-message {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 0.75rem;
                    padding: 2rem;
                    color: var(--text-tertiary, #6b7280);
                    text-align: center;
                }

                .no-provider-message p {
                    margin: 0;
                    font-size: 0.9rem;
                }

                /*  Form Groups  */
                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 0.5rem;
                }

                .form-group label {
                    font-size: 0.875rem;
                    font-weight: 600;
                    color: var(--text-primary);
                    display: flex;
                    align-items: center;
                }

                .form-group small {
                    font-size: 0.75rem;
                }

                .input-with-button {
                    display: flex;
                    gap: 0.5rem;
                }

                .input-with-button .input {
                    flex: 1;
                }

                .animate-spin {
                    animation: spin 1s linear infinite;
                }

                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }

                @media (max-width: 768px) {
                    .provider-checkboxes {
                        flex-direction: column;
                    }
                }
            `}</style>
        </div>
    );
}
