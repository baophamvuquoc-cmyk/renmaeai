import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FileManager from './components/file-manager/FileManager';
import ScriptWorkflow from './components/workflow/ScriptWorkflow';
import ProductionHub from './components/workflow/ProductionHub';
import AISettings from './components/ai-settings/AISettings';

import { useAISettingsStore } from './stores/useAISettingsStore';
import { ArrowLeft, Package } from 'lucide-react';
import { BeeFile, BeeSparkle, BeeGear, BeeSleep, BeeSmall, BeeHero } from './components/ui/BeeIcons';
import { RealtimeSyncProvider } from './contexts/RealtimeSyncContext';

const queryClient = new QueryClient();

type Tab = 'landing' | 'files' | 'workflow' | 'ai-settings' | 'productions';

interface AppButton {
  id: Tab | 'coming-soon';
  label: string;
  description?: string;
  icon: React.ReactNode;
  color: string;
  requiresAI?: boolean;
  isPlaceholder?: boolean;
}

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('landing');
  const [showAIWarning, setShowAIWarning] = useState(false);
  const [selectedButton, setSelectedButton] = useState<number | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);

  const {
    isProviderConfigured,
    getActiveProvider,
    loadSettingsFromBackend,
    isLoaded,
  } = useAISettingsStore();

  useEffect(() => {
    if (!isLoaded) {
      loadSettingsFromBackend();
    }
  }, [isLoaded, loadSettingsFromBackend]);

  function isAIConfigured(): boolean {
    const provider = getActiveProvider();
    if (!provider) return false;
    return isProviderConfigured(provider);
  }

  function handleNavigation(target: Tab, requiresAI = false) {
    if (requiresAI && !isAIConfigured()) {
      setShowAIWarning(true);
      setTimeout(() => {
        setShowAIWarning(false);
        setActiveTab('ai-settings');
      }, 1800);
      return;
    }
    // Clear stale project ID so ScriptWorkflow starts fresh with entry section
    if (target === 'workflow') {
      setActiveProjectId(null);
    }
    setActiveTab(target);
  }

  const appButtons: AppButton[] = [
    {
      id: 'files',
      label: 'Đổi Tên File',
      description: 'Đổi tên hàng loạt file theo mẫu tùy chỉnh.\n• Hỗ trợ prefix, suffix, đánh số tự động\n• Xem trước kết quả trước khi áp dụng\n• Hoàn tác nhanh nếu cần',
      icon: <BeeFile size={44} />,
      color: '#60A5FA',
    },
    {
      id: 'workflow',
      label: 'Podcast Remake',
      description: '🎙️ Chỉ dành cho Podcast\n\nTạo lại podcast thành video hoàn chỉnh bằng AI:\n• Tạo kịch bản từ nội dung podcast\n• Chia scene tự động theo ngữ cảnh\n• Tìm footage miễn phí (Pexels/Pixabay)\n• Ghép video + phụ đề tự động\n• Hỗ trợ TTS đa ngôn ngữ',
      icon: <BeeSparkle size={44} />,
      color: '#A78BFA',
      requiresAI: true,
    },
    {
      id: 'ai-settings',
      label: 'Cấu Hình AI',
      description: 'Thiết lập và quản lý cấu hình AI.\n• Chọn model AI (GPT, Gemini, Claude...)\n• Cấu hình API key\n• Thiết lập Pexels/Pixabay cho footage\n• Test kết nối trước khi sử dụng',
      icon: <BeeGear size={44} />,
      color: '#FFD700',
    },
    {
      id: 'productions' as Tab,
      label: 'Production Hub',
      description: '📦 Quản lý tất cả output\n\nXem và quản lý mọi kết quả đã export:\n• Danh sách toàn bộ productions\n• Xem files output (script, video, voice...)\n• Mở thư mục output nhanh\n• Thống kê dung lượng\n• Upload YouTube (sắp ra mắt)',
      icon: <Package size={36} color="#22c55e" />,
      color: '#22c55e',
    },
    {
      id: 'coming-soon',
      label: 'Sắp Ra Mắt',
      icon: <BeeSleep size={44} />,
      color: '#737373',
      isPlaceholder: true,
    },
    {
      id: 'coming-soon',
      label: 'Sắp Ra Mắt',
      icon: <BeeSleep size={44} />,
      color: '#737373',
      isPlaceholder: true,
    },
  ];

  function handleButtonClick(btn: AppButton, index: number) {
    if (btn.isPlaceholder) return;
    if (selectedButton === index) {
      // Second click → navigate
      setSelectedButton(null);
      handleNavigation(btn.id as Tab, btn.requiresAI);
    } else {
      // First click → show description
      setSelectedButton(index);
    }
  }

  // Landing page
  if (activeTab === 'landing') {
    return (
      <QueryClientProvider client={queryClient}>
        <RealtimeSyncProvider>
          <div className="landing-root">
            {/* AI Warning Toast */}
            {showAIWarning && (
              <div className="ai-warning-toast">
                <div className="ai-warning-icon">
                  <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#FFD700" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
                </div>
                <div className="ai-warning-text">
                  <strong>Chưa cấu hình AI!</strong>
                  <span>Đang chuyển đến Cấu Hình AI...</span>
                </div>
              </div>
            )}

            {/* iPad Frame */}
            <div className="ipad-frame">
              {/* Status Bar */}
              <div className="ipad-statusbar">
                <div className="statusbar-left">
                  <span className="bee-icon"><BeeSmall size={20} /></span>
                  <span className="app-name">RenmaeAI</span>
                </div>
                <div className="statusbar-right">
                  <span className="statusbar-badge">
                    {isAIConfigured()
                      ? <><span style={{ color: '#22c55e', marginRight: 4 }}>●</span>AI Ready</>
                      : <><span style={{ color: '#ef4444', marginRight: 4 }}>●</span>AI Chưa Cấu Hình</>
                    }
                  </span>
                </div>
              </div>

              {/* Main Content — Logo left, Grid right */}
              <div className="ipad-body">
                {/* Left: Hero / Brand */}
                <div className="ipad-hero">
                  <div className="hero-logo">
                    <BeeHero size={128} className="hero-bee" />
                  </div>
                  <h1 className="hero-title">RenmaeAI Studio</h1>
                  <p className="hero-subtitle">Trợ lý sáng tạo nội dung AI</p>
                </div>

                {/* Right: App Grid */}
                <div className="ipad-grid">
                  {appButtons.map((btn, index) => {
                    const isExpanded = selectedButton === index && !!btn.description;
                    return (
                      <div
                        key={`${btn.id}-${index}`}
                        className={`app-icon-wrapper ${isExpanded ? 'expanded' : ''}`}
                        style={{
                          borderColor: isExpanded ? `${btn.color}55` : 'transparent',
                          boxShadow: isExpanded ? `0 8px 40px ${btn.color}15, 0 0 30px ${btn.color}08` : 'none',
                        }}
                      >
                        <button
                          className={`app-icon-btn ${btn.isPlaceholder ? 'placeholder' : ''} ${isExpanded ? 'selected' : ''}`}
                          onClick={() => handleButtonClick(btn, index)}
                          style={{
                            animationDelay: `${index * 0.08}s`,
                          }}
                          disabled={btn.isPlaceholder}
                        >
                          <div
                            className="app-icon-circle"
                            style={{
                              background: btn.isPlaceholder
                                ? 'rgba(60, 60, 60, 0.5)'
                                : `linear-gradient(145deg, ${btn.color}22, ${btn.color}11)`,
                              borderColor: btn.isPlaceholder
                                ? 'rgba(80, 80, 80, 0.3)'
                                : `${btn.color}44`,
                              boxShadow: btn.isPlaceholder
                                ? 'none'
                                : `0 8px 25px ${btn.color}22, inset 0 1px 0 ${btn.color}18`,
                            }}
                          >
                            <span className="app-icon-emoji">{btn.icon}</span>
                          </div>
                          <span className={`app-icon-label ${btn.isPlaceholder ? 'placeholder-label' : ''}`}>
                            {btn.label}
                          </span>
                          {btn.requiresAI && !isAIConfigured() && (
                            <div className="app-icon-lock">
                              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#FFD700" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0110 0v4" /></svg>
                            </div>
                          )}
                        </button>

                        {/* Expanded description area */}
                        {isExpanded && (
                          <div className="feature-expand-content">
                            <div className="feature-expand-divider" style={{ background: `${btn.color}33` }} />
                            <div className="feature-expand-body">
                              {btn.description!.split('\n').map((line, i) => (
                                <p key={i} className={line.startsWith('•') ? 'feature-bullet' : line === '' ? 'feature-spacer' : 'feature-text'}>
                                  {line}
                                </p>
                              ))}
                            </div>
                            <button
                              className="feature-open-btn"
                              style={{ background: `linear-gradient(135deg, ${btn.color}33, ${btn.color}18)`, borderColor: `${btn.color}55`, color: btn.color }}
                              onClick={(e) => { e.stopPropagation(); setSelectedButton(null); handleNavigation(btn.id as Tab, btn.requiresAI); }}
                            >
                              Mở {btn.label} →
                            </button>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Bottom Dock */}
              <div className="ipad-dock">
                <div className="dock-indicator" />
              </div>
            </div>

            {/* Honeycomb Background Decoration */}
            <div className="honeycomb-bg">
              {Array.from({ length: 18 }).map((_, i) => (
                <div
                  key={i}
                  className="honeycomb-cell"
                  style={{
                    left: `${Math.random() * 100}%`,
                    top: `${Math.random() * 100}%`,
                    animationDelay: `${Math.random() * 5}s`,
                    opacity: 0.03 + Math.random() * 0.04,
                  }}
                />
              ))}
            </div>
          </div>

          <style>{`
          .landing-root {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            background: #0a0a0a;
          }

          /* ===== AI WARNING TOAST ===== */
          .ai-warning-toast {
            position: fixed;
            top: 32px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(135deg, #1e1e1e 0%, #2a2a00 100%);
            border: 2px solid #FFD700;
            border-radius: 16px;
            padding: 16px 28px;
            display: flex;
            align-items: center;
            gap: 14px;
            z-index: 9999;
            animation: toastSlideDown 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 8px 40px rgba(255, 215, 0, 0.25), 0 0 60px rgba(255, 215, 0, 0.1);
          }

          .ai-warning-icon {
            font-size: 28px;
            animation: wobble 0.6s ease-in-out;
          }

          .ai-warning-text {
            display: flex;
            flex-direction: column;
            gap: 2px;
          }

          .ai-warning-text strong {
            color: #FFD700;
            font-size: 0.95rem;
            font-family: 'Fredoka', sans-serif;
          }

          .ai-warning-text span {
            color: #A3A3A3;
            font-size: 0.8rem;
          }

          @keyframes toastSlideDown {
            from { transform: translateX(-50%) translateY(-100px); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
          }

          @keyframes wobble {
            0% { transform: rotate(0deg); }
            25% { transform: rotate(-15deg); }
            50% { transform: rotate(15deg); }
            75% { transform: rotate(-5deg); }
            100% { transform: rotate(0deg); }
          }

          /* ===== iPAD FRAME ===== */
          .ipad-frame {
            width: 100%;
            height: 100vh;
            background: linear-gradient(180deg, #111111 0%, #0d0d0d 100%);
            border: none;
            border-radius: 0;
            padding: 0;
            position: relative;
            z-index: 2;
            overflow: hidden;
            display: flex;
            flex-direction: column;
          }

          @keyframes ipadFloat {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
          }

          /* ===== STATUS BAR ===== */
          .ipad-statusbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 28px 8px;
            -webkit-app-region: drag;
          }

          .statusbar-left {
            display: flex;
            align-items: center;
            gap: 8px;
          }

          .bee-icon {
            font-size: 20px;
            animation: float 3s ease-in-out infinite;
          }

          .app-name {
            font-family: 'Fredoka', sans-serif;
            font-weight: 600;
            font-size: 1rem;
            background: linear-gradient(135deg, #FFD700, #FBBF24);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }

          .statusbar-right {
            display: flex;
            align-items: center;
          }

          .statusbar-badge {
            font-size: 0.7rem;
            color: #A3A3A3;
            padding: 3px 10px;
            background: rgba(255, 255, 255, 0.04);
            border-radius: 20px;
            border: 1px solid rgba(255, 255, 255, 0.06);
          }

          /* ===== iPAD BODY — two-column layout ===== */
          .ipad-body {
            display: flex;
            align-items: stretch;
            padding: 32px 64px 40px;
            gap: 60px;
            -webkit-app-region: no-drag;
            flex: 1;
          }

          /* ===== HERO — Upper-left quadrant ===== */
          .ipad-hero {
            display: flex;
            flex-direction: column;
            align-items: flex-start;
            justify-content: center;
            padding: 24px 16px;
            min-width: 280px;
            flex-shrink: 0;
          }

          .hero-logo {
            width: 160px;
            height: 160px;
            margin: 0 0 20px 0;
            background: radial-gradient(circle, rgba(255, 215, 0, 0.12) 0%, transparent 70%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
          }

          .hero-logo::after {
            content: '';
            position: absolute;
            width: 100%;
            height: 100%;
            border-radius: 50%;
            border: 2px solid rgba(255, 215, 0, 0.15);
            animation: pulse-glow 3s ease-in-out infinite;
          }

          .hero-bee {
            display: block;
            animation: float 4s ease-in-out infinite;
          }

          .hero-title {
            font-family: 'Fredoka', sans-serif;
            font-size: 2.2rem;
            font-weight: 700;
            margin: 0 0 6px;
            background: linear-gradient(135deg, #FFD700 0%, #FBBF24 50%, #F59E0B 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.02em;
            text-align: left;
          }

          .hero-subtitle {
            font-size: 1rem;
            color: #737373;
            margin: 0;
            font-weight: 400;
            text-align: left;
          }

          /* ===== APP GRID — right side ===== */
          .ipad-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 12px;
            flex: 1;
            align-content: center;
          }

          .app-icon-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            padding: 14px 6px;
            background: none;
            border: none;
            cursor: pointer;
            border-radius: 20px;
            transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
            position: relative;
            animation: bounceIn 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
          }

          .app-icon-btn:not(.placeholder):hover {
            transform: scale(1.08) translateY(-4px);
          }

          .app-icon-btn:not(.placeholder):active {
            transform: scale(0.95);
          }

          .app-icon-btn.placeholder {
            cursor: default;
            opacity: 0.4;
          }

          .app-icon-circle {
            width: 80px;
            height: 80px;
            border-radius: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            border: 1.5px solid;
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
          }

          .app-icon-btn:not(.placeholder):hover .app-icon-circle {
            transform: translateY(-2px);
            box-shadow: 0 12px 35px rgba(255, 215, 0, 0.15) !important;
          }

          /* Cartoon shine effect */
          .app-icon-circle::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: linear-gradient(
              45deg,
              transparent 30%,
              rgba(255, 255, 255, 0.08) 50%,
              transparent 70%
            );
            animation: iconShine 4s ease-in-out infinite;
            pointer-events: none;
          }

          @keyframes iconShine {
            0% { transform: translateX(-100%) rotate(45deg); }
            100% { transform: translateX(100%) rotate(45deg); }
          }

          @keyframes bounceIn {
            0% { opacity: 0; transform: scale(0.3) translateY(20px); }
            50% { opacity: 1; transform: scale(1.05) translateY(-5px); }
            70% { transform: scale(0.95) translateY(2px); }
            100% { transform: scale(1) translateY(0); }
          }

          @keyframes float {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-6px); }
          }

          @keyframes pulse-glow {
            0%, 100% { box-shadow: 0 0 15px rgba(255, 215, 0, 0.1); }
            50% { box-shadow: 0 0 30px rgba(255, 215, 0, 0.25); }
          }

          .app-icon-emoji {
            font-size: 36px;
            position: relative;
            z-index: 1;
          }

          .app-icon-label {
            font-size: 0.72rem;
            font-weight: 600;
            color: #D4D4D4;
            text-align: center;
            line-height: 1.2;
            max-width: 100px;
          }

          .app-icon-label.placeholder-label {
            color: #525252;
            font-weight: 500;
          }

          .app-icon-lock {
            position: absolute;
            top: 8px;
            right: 10px;
            font-size: 12px;
            background: rgba(0, 0, 0, 0.6);
            border-radius: 50%;
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          /* ===== APP ICON WRAPPER — Expanding Frame ===== */
          .app-icon-wrapper {
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            border: 1.5px solid transparent;
            border-radius: 20px;
            padding: 4px;
            transition: all 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
            background: transparent;
          }

          .app-icon-wrapper.expanded {
            background: linear-gradient(160deg, rgba(26, 26, 26, 0.97) 0%, rgba(18, 18, 18, 0.99) 100%);
            backdrop-filter: blur(20px);
            padding: 8px 12px 14px;
            animation: expandFrame 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
            z-index: 50;
          }

          @keyframes expandFrame {
            from {
              padding: 4px;
              background: transparent;
              border-color: transparent;
              box-shadow: none;
            }
          }

          .app-icon-wrapper.expanded .app-icon-btn {
            margin-bottom: 0;
          }

          /* ===== EXPAND CONTENT ===== */
          .feature-expand-content {
            width: 100%;
            animation: contentSlideIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
            overflow: hidden;
          }

          @keyframes contentSlideIn {
            from { opacity: 0; max-height: 0; transform: translateY(-8px); }
            to { opacity: 1; max-height: 400px; transform: translateY(0); }
          }

          .feature-expand-divider {
            height: 1px;
            margin: 6px 0 10px;
            border-radius: 1px;
          }

          .feature-expand-body {
            margin-bottom: 10px;
            padding: 0 4px;
          }

          .feature-expand-body .feature-text {
            font-size: 0.78rem;
            color: #A3A3A3;
            margin: 0 0 4px;
            line-height: 1.5;
          }

          .feature-expand-body .feature-bullet {
            font-size: 0.75rem;
            color: #9CA3AF;
            margin: 0 0 3px;
            padding-left: 4px;
            line-height: 1.4;
          }

          .feature-expand-body .feature-spacer {
            margin: 0;
            height: 6px;
          }

          .feature-open-btn {
            width: 100%;
            padding: 7px 14px;
            border: 1.5px solid;
            border-radius: 10px;
            font-family: 'Fredoka', sans-serif;
            font-size: 0.78rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s ease;
            text-align: center;
          }

          .feature-open-btn:hover {
            filter: brightness(1.3);
            transform: translateY(-1px);
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.15);
          }

          /* ===== DOCK ===== */
          .ipad-dock {
            padding: 8px 0 16px;
            display: flex;
            justify-content: center;
          }

          .dock-indicator {
            width: 140px;
            height: 4px;
            background: rgba(255, 215, 0, 0.2);
            border-radius: 4px;
          }

          /* ===== HONEYCOMB BG ===== */
          .honeycomb-bg {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 0;
            overflow: hidden;
          }

          .honeycomb-cell {
            position: absolute;
            width: 60px;
            height: 60px;
            background: transparent;
            border: 1px solid rgba(255, 215, 0, 0.08);
            clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
            animation: float 8s ease-in-out infinite;
          }
        `}</style>
        </RealtimeSyncProvider>
      </QueryClientProvider>
    );
  }

  // Workspace view (when a tab is active)
  const tabLabels: Record<Exclude<Tab, 'landing'>, string> = {
    files: 'Đổi Tên File',
    workflow: 'Podcast Remake',
    'ai-settings': 'Cấu Hình AI',
    productions: 'Production Hub',
  };

  return (
    <QueryClientProvider client={queryClient}>
      <RealtimeSyncProvider>
        <div className="app-layout">
          {/* Workspace Header with Back Button */}
          <header className="workspace-header">
            <div className="workspace-header-content">
              <button
                className="back-btn"
                onClick={() => {
                  if (activeTab === 'workflow' && activeProjectId) {
                    // Go back to entry section (not home)
                    setActiveProjectId(null);
                  } else {
                    setActiveTab('landing');
                  }
                }}
              >
                <ArrowLeft size={20} />
                <span className="back-bee"><BeeSmall size={16} /></span>
              </button>
              <h2 className="workspace-title">{tabLabels[activeTab]}</h2>
              <div className="workspace-breadcrumb">
                RenmaeAI Studio / {tabLabels[activeTab]}
              </div>
            </div>
          </header>

          {/* Content */}
          <main className="workspace-content">
            {activeTab === 'files' && <FileManager />}
            {activeTab === 'workflow' && <ScriptWorkflow activeProjectId={activeProjectId} setActiveProjectId={setActiveProjectId} />}
            {activeTab === 'ai-settings' && <AISettings />}
            {activeTab === 'productions' && (
              <div style={{ padding: '1rem', width: '100%' }}>
                <ProductionHub />
              </div>
            )}

          </main>
        </div>

        <style>{`
        .app-layout {
          display: flex;
          flex-direction: column;
          min-height: 100vh;
          background: var(--bg-primary);
          position: relative;
          z-index: 1;
        }

        /* ===== WORKSPACE HEADER ===== */
        .workspace-header {
          padding: 12px 24px;
          background: rgba(14, 14, 14, 0.8);
          backdrop-filter: blur(10px);
          border-bottom: 1px solid var(--border-color);
          -webkit-app-region: drag;
          flex-shrink: 0;
        }

        .workspace-header-content {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .back-btn {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 8px 14px;
          background: rgba(255, 215, 0, 0.08);
          border: 1px solid rgba(255, 215, 0, 0.2);
          border-radius: 12px;
          color: #FFD700;
          cursor: pointer;
          transition: all 0.25s ease;
          -webkit-app-region: no-drag;
          font-size: 14px;
        }

        .back-btn:hover {
          background: rgba(255, 215, 0, 0.15);
          border-color: rgba(255, 215, 0, 0.35);
          transform: translateX(-2px);
          box-shadow: 0 0 20px rgba(255, 215, 0, 0.1);
        }

        .back-bee {
          font-size: 16px;
        }

        .workspace-title {
          font-family: 'Fredoka', sans-serif;
          font-size: 1.15rem;
          font-weight: 600;
          margin: 0;
          color: var(--text-primary);
          flex: 1;
        }

        .workspace-breadcrumb {
          font-size: 0.75rem;
          color: var(--text-tertiary);
          font-weight: 500;
        }

        .workspace-content {
          flex: 1;
          padding: 24px 28px;
          overflow-y: auto;
          animation: fadeIn var(--transition-base);
          -webkit-app-region: no-drag;
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>
      </RealtimeSyncProvider>
    </QueryClientProvider>
  );
}

export default App;
