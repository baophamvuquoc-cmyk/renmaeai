import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import FileManager from './components/file-manager/FileManager';
import ScriptWorkflow from './components/workflow/ScriptWorkflow';
import ProductionHub from './components/workflow/ProductionHub';
import AISettings from './components/ai-settings/AISettings';

import { useAISettingsStore } from './stores/useAISettingsStore';
import { useLanguageStore } from './stores/useLanguageStore';
import { ArrowLeft, Package } from 'lucide-react';
import { BeeFile, BeeSparkle, BeeGear, BeeSleep, BeeSmall } from './components/ui/BeeIcons';
import { RealtimeSyncProvider } from './contexts/RealtimeSyncContext';
import { LicenseGate } from './components/license/LicenseGate';

const queryClient = new QueryClient();
const isElectron = typeof window !== 'undefined' && !!window.electron;

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
  const { t } = useTranslation();
  const { language, setLanguage } = useLanguageStore();
  const [activeTab, setActiveTab] = useState<Tab>('landing');
  const [showAIWarning, setShowAIWarning] = useState(false);

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
      label: t('app.fileRename'),
      description: t('app.fileRenameDesc'),
      icon: <BeeFile size={44} />,
      color: '#60A5FA',
    },
    {
      id: 'workflow',
      label: t('app.podcastRemake'),
      description: t('app.podcastRemakeDesc'),
      icon: <BeeSparkle size={44} />,
      color: '#A78BFA',
      requiresAI: true,
    },
    {
      id: 'ai-settings',
      label: t('app.aiSettings'),
      description: t('app.aiSettingsDesc'),
      icon: <BeeGear size={44} />,
      color: '#FFD700',
    },
    {
      id: 'productions' as Tab,
      label: t('app.productionHub'),
      description: t('app.productionHubDesc'),
      icon: <Package size={36} color="#22c55e" />,
      color: '#22c55e',
    },
    {
      id: 'coming-soon',
      label: t('app.comingSoon'),
      icon: <BeeSleep size={44} />,
      color: '#737373',
      isPlaceholder: true,
    },
    {
      id: 'coming-soon',
      label: t('app.comingSoon'),
      icon: <BeeSleep size={44} />,
      color: '#737373',
      isPlaceholder: true,
    },
  ];



  // Tagline typing animation
  const taglines = [
    t('app.tagline1'),
    t('app.tagline2'),
    t('app.tagline3'),
    t('app.tagline4'),
  ];
  const [taglineIndex, setTaglineIndex] = useState(0);
  const [displayText, setDisplayText] = useState('');
  const [isTyping, setIsTyping] = useState(true);

  useEffect(() => {
    if (activeTab !== 'landing') return;
    const target = taglines[taglineIndex];
    let timeout: ReturnType<typeof setTimeout>;

    if (isTyping) {
      if (displayText.length < target.length) {
        timeout = setTimeout(() => setDisplayText(target.slice(0, displayText.length + 1)), 55);
      } else {
        timeout = setTimeout(() => setIsTyping(false), 2200);
      }
    } else {
      if (displayText.length > 0) {
        timeout = setTimeout(() => setDisplayText(displayText.slice(0, -1)), 30);
      } else {
        setTaglineIndex((prev) => (prev + 1) % taglines.length);
        setIsTyping(true);
      }
    }
    return () => clearTimeout(timeout);
  }, [displayText, isTyping, taglineIndex, activeTab]);

  // Landing page
  if (activeTab === 'landing') {
    return (
      <QueryClientProvider client={queryClient}>
        <LicenseGate>
          <RealtimeSyncProvider>
            <div className="cosmo-landing">
              {/* AI Warning Toast */}
              {showAIWarning && (
                <div className="cosmo-toast">
                  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#FFD700" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></svg>
                  <div className="cosmo-toast-text">
                    <strong>{t('app.aiWarningTitle')}</strong>
                    <span>{t('app.aiWarningDesc')}</span>
                  </div>
                </div>
              )}

              {/* Aurora Background Layers */}
              <div className="aurora-bg">
                <div className="aurora-orb aurora-orb-1" />
                <div className="aurora-orb aurora-orb-2" />
                <div className="aurora-orb aurora-orb-3" />
                <div className="aurora-noise" />
              </div>

              {/* Floating Particles */}
              <div className="particles-field">
                {Array.from({ length: 30 }).map((_, i) => (
                  <div
                    key={i}
                    className="particle"
                    style={{
                      left: `${Math.random() * 100}%`,
                      top: `${Math.random() * 100}%`,
                      width: `${2 + Math.random() * 3}px`,
                      height: `${2 + Math.random() * 3}px`,
                      animationDelay: `${Math.random() * 8}s`,
                      animationDuration: `${6 + Math.random() * 8}s`,
                      opacity: 0.15 + Math.random() * 0.35,
                    }}
                  />
                ))}
              </div>

              {/* Main Frame */}
              <div className="cosmo-frame">
                {/* Top Bar */}
                <div className="cosmo-topbar" data-electron-drag={isElectron ? 'true' : undefined}>
                  <span className="cosmo-brand">RenmaeAI</span>
                  <span className="cosmo-status">
                    {isAIConfigured()
                      ? <><span style={{ color: '#34d399' }}>●</span> AI Ready</>
                      : <><span style={{ color: '#ef4444' }}>●</span> {t('app.aiNotConfigured')}</>
                    }
                  </span>
                  <button
                    onClick={() => setLanguage(language === 'vi' ? 'en' : 'vi')}
                    style={{
                      padding: '4px 10px', borderRadius: '16px', fontSize: '0.7rem',
                      fontWeight: 700, cursor: 'pointer', border: '1px solid rgba(255,215,0,0.3)',
                      background: 'rgba(255,215,0,0.08)', color: '#FFD700',
                      transition: 'all 0.2s', letterSpacing: '0.5px',
                      WebkitAppRegion: 'no-drag' as any,
                    }}
                  >
                    {language === 'vi' ? 'EN' : 'VI'}
                  </button>
                </div>

                {/* Hero */}
                <div className="cosmo-hero">
                  <div className="hero-glow-ring" />
                  <h1 className="cosmo-title">RenmaeAI Studio</h1>
                  <p className="cosmo-tagline">
                    {displayText}
                    <span className="cosmo-cursor">|</span>
                  </p>
                  <div className="cosmo-version">v1.0 · Creative AI Engine</div>
                </div>

                {/* Feature Cards */}
                <div className="cosmo-grid">
                  {appButtons.map((btn, index) => (
                    <button
                      key={`${btn.id}-${index}`}
                      className={`cosmo-card ${btn.isPlaceholder ? 'cosmo-card--disabled' : ''}`}
                      disabled={btn.isPlaceholder}
                      onClick={() => {
                        if (!btn.isPlaceholder) handleNavigation(btn.id as Tab, btn.requiresAI);
                      }}
                      style={{
                        '--card-accent': btn.color,
                        animationDelay: `${0.1 + index * 0.08}s`,
                      } as React.CSSProperties}
                    >
                      <div className="cosmo-card-glow" />
                      <div className="cosmo-card-header">
                        <span className="cosmo-card-title">{btn.label}</span>
                        {btn.requiresAI && !isAIConfigured() && (
                          <svg className="cosmo-card-lock" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFD700" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0110 0v4" /></svg>
                        )}
                      </div>
                      {btn.description && (
                        <p className="cosmo-card-desc">
                          {btn.description.split('\n')[0].replace(/^[🎙️📦\s]+/, '')}
                        </p>
                      )}
                      {!btn.isPlaceholder && (
                        <span className="cosmo-card-arrow">→</span>
                      )}
                    </button>
                  ))}
                </div>

                {/* Bottom Dock */}
                <div className="cosmo-dock">
                  <div className="cosmo-dock-bar" />
                </div>
              </div>
            </div>

            <style>{`
          /* ===== COSMIC HIVE LANDING ===== */
          .cosmo-landing {
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
            overflow: hidden;
            background: #060608;
          }

          /* ===== AURORA BACKGROUND ===== */
          .aurora-bg {
            position: fixed;
            inset: 0;
            z-index: 0;
            overflow: hidden;
          }

          .aurora-orb {
            position: absolute;
            border-radius: 50%;
            filter: blur(120px);
            will-change: transform;
          }

          .aurora-orb-1 {
            width: 600px;
            height: 600px;
            top: -15%;
            left: -10%;
            background: radial-gradient(circle, rgba(255, 170, 0, 0.18) 0%, transparent 70%);
            animation: auroraFloat1 18s ease-in-out infinite alternate;
          }

          .aurora-orb-2 {
            width: 500px;
            height: 500px;
            bottom: -10%;
            right: -5%;
            background: radial-gradient(circle, rgba(167, 139, 250, 0.12) 0%, transparent 70%);
            animation: auroraFloat2 22s ease-in-out infinite alternate;
          }

          .aurora-orb-3 {
            width: 400px;
            height: 400px;
            top: 40%;
            left: 50%;
            transform: translateX(-50%);
            background: radial-gradient(circle, rgba(52, 211, 153, 0.08) 0%, transparent 70%);
            animation: auroraFloat3 15s ease-in-out infinite alternate;
          }

          .aurora-noise {
            position: absolute;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");
            opacity: 0.5;
          }

          @keyframes auroraFloat1 {
            0% { transform: translate(0, 0) scale(1); }
            33% { transform: translate(80px, 40px) scale(1.15); }
            66% { transform: translate(-30px, 80px) scale(0.95); }
            100% { transform: translate(50px, -20px) scale(1.08); }
          }

          @keyframes auroraFloat2 {
            0% { transform: translate(0, 0) scale(1); }
            50% { transform: translate(-60px, -50px) scale(1.2); }
            100% { transform: translate(40px, 30px) scale(0.9); }
          }

          @keyframes auroraFloat3 {
            0% { transform: translateX(-50%) translate(0, 0) scale(1); }
            50% { transform: translateX(-50%) translate(30px, -40px) scale(1.1); }
            100% { transform: translateX(-50%) translate(-20px, 20px) scale(0.95); }
          }

          /* ===== PARTICLES ===== */
          .particles-field {
            position: fixed;
            inset: 0;
            z-index: 1;
            pointer-events: none;
          }

          .particle {
            position: absolute;
            border-radius: 50%;
            background: #FFD700;
            animation: particleDrift linear infinite;
          }

          @keyframes particleDrift {
            0% { transform: translateY(0) translateX(0); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateY(-120px) translateX(30px); opacity: 0; }
          }

          /* ===== MAIN FRAME ===== */
          .cosmo-frame {
            width: 100%;
            height: 100vh;
            position: relative;
            z-index: 2;
            display: flex;
            flex-direction: column;
            overflow: hidden;
          }

          /* ===== TOP BAR ===== */
          .cosmo-topbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 18px 36px 10px;
            flex-shrink: 0;
          }

          .cosmo-topbar[data-electron-drag="true"] {
            -webkit-app-region: drag;
            padding-right: 150px;
          }

          .cosmo-grid {
            -webkit-app-region: no-drag;
          }

          .cosmo-brand {
            font-family: 'Fredoka', sans-serif;
            font-weight: 700;
            font-size: 1.05rem;
            background: linear-gradient(135deg, #FFD700 0%, #F59E0B 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: 0.02em;
          }

          .cosmo-status {
            font-size: 0.72rem;
            color: #888;
            padding: 4px 14px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 20px;
            display: flex;
            align-items: center;
            gap: 6px;
          }

          /* ===== HERO ===== */
          .cosmo-hero {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 40px 20px 32px;
            position: relative;
            flex-shrink: 0;
          }

          .hero-glow-ring {
            width: 120px;
            height: 120px;
            border-radius: 50%;
            border: 2px solid rgba(255, 215, 0, 0.2);
            position: relative;
            margin-bottom: 24px;
            animation: ringPulse 4s ease-in-out infinite;
            background: radial-gradient(circle, rgba(255, 215, 0, 0.06) 0%, transparent 70%);
          }

          .hero-glow-ring::before {
            content: 'R';
            position: absolute;
            inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            font-family: 'Fredoka', sans-serif;
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, #FFD700 0%, #F59E0B 50%, #D97706 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
          }

          .hero-glow-ring::after {
            content: '';
            position: absolute;
            inset: -8px;
            border-radius: 50%;
            border: 1px solid rgba(255, 215, 0, 0.08);
            animation: ringPulse 4s ease-in-out infinite 1s;
          }

          @keyframes ringPulse {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.08), inset 0 0 20px rgba(255, 215, 0, 0.04); transform: scale(1); }
            50% { box-shadow: 0 0 40px rgba(255, 215, 0, 0.15), inset 0 0 30px rgba(255, 215, 0, 0.08); transform: scale(1.03); }
          }

          .cosmo-title {
            font-family: 'Fredoka', sans-serif;
            font-size: 2.6rem;
            font-weight: 700;
            margin: 0 0 8px;
            background: linear-gradient(135deg, #FFD700 0%, #FBBF24 40%, #F59E0B 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            letter-spacing: -0.02em;
            text-shadow: 0 0 60px rgba(255, 215, 0, 0.15);
          }

          .cosmo-tagline {
            font-size: 1.05rem;
            color: #888;
            margin: 0 0 12px;
            min-height: 1.6em;
            font-weight: 400;
          }

          .cosmo-cursor {
            color: #FFD700;
            animation: blink 0.8s step-end infinite;
            font-weight: 300;
            margin-left: 1px;
          }

          @keyframes blink {
            0%, 100% { opacity: 1; }
            50% { opacity: 0; }
          }

          .cosmo-version {
            font-size: 0.7rem;
            color: #555;
            padding: 4px 16px;
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 20px;
            background: rgba(255, 255, 255, 0.02);
            letter-spacing: 0.5px;
            text-transform: uppercase;
          }

          /* ===== FEATURE CARDS ===== */
          .cosmo-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            padding: 20px 64px 0;
            flex: 1;
            align-content: start;
            max-width: 960px;
            margin: 0 auto;
            width: 100%;
          }

          .cosmo-card {
            position: relative;
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 22px 20px 18px;
            cursor: pointer;
            text-align: left;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            animation: cardReveal 0.5s cubic-bezier(0.34, 1.56, 0.64, 1) both;
          }

          .cosmo-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, transparent 0%, var(--card-accent) 50%, transparent 100%);
            opacity: 0;
            transition: opacity 0.3s ease;
          }

          .cosmo-card:not(.cosmo-card--disabled):hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: color-mix(in srgb, var(--card-accent) 30%, transparent);
            transform: translateY(-4px);
            box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4), 0 0 30px color-mix(in srgb, var(--card-accent) 8%, transparent);
          }

          .cosmo-card:not(.cosmo-card--disabled):hover::before {
            opacity: 1;
          }

          .cosmo-card:not(.cosmo-card--disabled):active {
            transform: translateY(-1px) scale(0.99);
          }

          .cosmo-card--disabled {
            opacity: 0.3;
            cursor: default;
          }

          .cosmo-card-glow {
            position: absolute;
            top: -40px;
            right: -40px;
            width: 100px;
            height: 100px;
            border-radius: 50%;
            background: radial-gradient(circle, var(--card-accent) 0%, transparent 70%);
            opacity: 0;
            filter: blur(30px);
            transition: opacity 0.4s ease;
            pointer-events: none;
          }

          .cosmo-card:not(.cosmo-card--disabled):hover .cosmo-card-glow {
            opacity: 0.12;
          }

          @keyframes cardReveal {
            0% { opacity: 0; transform: translateY(20px) scale(0.95); }
            100% { opacity: 1; transform: translateY(0) scale(1); }
          }

          .cosmo-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 6px;
          }

          .cosmo-card-title {
            font-family: 'Fredoka', sans-serif;
            font-size: 0.95rem;
            font-weight: 600;
            color: #E5E5E5;
            transition: color 0.3s ease;
          }

          .cosmo-card:not(.cosmo-card--disabled):hover .cosmo-card-title {
            color: var(--card-accent);
          }

          .cosmo-card-lock {
            flex-shrink: 0;
          }

          .cosmo-card-desc {
            font-size: 0.78rem;
            color: #666;
            margin: 0;
            line-height: 1.5;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
          }

          .cosmo-card-arrow {
            position: absolute;
            bottom: 14px;
            right: 16px;
            font-size: 1rem;
            color: #444;
            transition: all 0.3s ease;
          }

          .cosmo-card:not(.cosmo-card--disabled):hover .cosmo-card-arrow {
            color: var(--card-accent);
            transform: translateX(3px);
          }

          /* ===== DOCK ===== */
          .cosmo-dock {
            padding: 12px 0 18px;
            display: flex;
            justify-content: center;
            flex-shrink: 0;
          }

          .cosmo-dock-bar {
            width: 120px;
            height: 4px;
            background: linear-gradient(90deg, transparent, rgba(255, 215, 0, 0.25), transparent);
            border-radius: 4px;
          }

          /* ===== TOAST ===== */
          .cosmo-toast {
            position: fixed;
            top: 28px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(20, 20, 20, 0.95);
            border: 1px solid rgba(255, 215, 0, 0.4);
            border-radius: 14px;
            padding: 14px 24px;
            display: flex;
            align-items: center;
            gap: 12px;
            z-index: 9999;
            animation: toastDown 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
            box-shadow: 0 8px 40px rgba(255, 215, 0, 0.15);
            backdrop-filter: blur(20px);
          }

          .cosmo-toast-text {
            display: flex;
            flex-direction: column;
            gap: 2px;
          }

          .cosmo-toast-text strong {
            color: #FFD700;
            font-size: 0.88rem;
            font-family: 'Fredoka', sans-serif;
          }

          .cosmo-toast-text span {
            color: #888;
            font-size: 0.75rem;
          }

          @keyframes toastDown {
            from { transform: translateX(-50%) translateY(-80px); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
          }

          /* ===== RESPONSIVE ===== */
          @media (max-width: 768px) {
            .cosmo-grid {
              grid-template-columns: repeat(2, 1fr);
              padding: 16px 24px 0;
            }
            .cosmo-title { font-size: 2rem; }
            .cosmo-hero { padding: 24px 16px 20px; }
          }

          @media (max-width: 480px) {
            .cosmo-grid {
              grid-template-columns: 1fr;
              padding: 12px 16px 0;
            }
            .cosmo-title { font-size: 1.6rem; }
          }
        `}</style>
          </RealtimeSyncProvider>
        </LicenseGate>
      </QueryClientProvider>
    );
  }

  // Workspace view (when a tab is active)
  const tabLabels: Record<Exclude<Tab, 'landing'>, string> = {
    files: t('app.fileRename'),
    workflow: t('app.podcastRemake'),
    'ai-settings': t('app.aiSettings'),
    productions: t('app.productionHub'),
  };

  return (
    <QueryClientProvider client={queryClient}>
      <LicenseGate>
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
          ${isElectron ? '-webkit-app-region: drag;' : ''}
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
      </LicenseGate>
    </QueryClientProvider>
  );
}

export default App;
