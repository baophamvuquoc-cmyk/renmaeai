import { useState, useEffect } from 'react';
import { useLicenseStore } from '../../stores/useLicenseStore';
import { LEMONSQUEEZY_STORE_URL } from '../../lib/lemonsqueezy';

/**
 * LicenseGate — Full-screen license activation page.
 * Wraps the entire app; only renders children if license is valid.
 */
export function LicenseGate({ children }: { children: React.ReactNode }) {
    const {
        isActivated,
        isLoading,
        error,
        customerEmail,
        variantName,
        activate,
        checkLicense,
        clearError,
    } = useLicenseStore();

    const [keyInput, setKeyInput] = useState('');
    const [isActivating, setIsActivating] = useState(false);
    const [showSuccess, setShowSuccess] = useState(false);

    // Check license on mount
    useEffect(() => {
        checkLicense();
    }, [checkLicense]);

    async function handleActivate() {
        if (!keyInput.trim()) return;
        setIsActivating(true);
        clearError();

        const success = await activate(keyInput.trim());

        if (success) {
            setShowSuccess(true);
            setTimeout(() => setShowSuccess(false), 2000);
        }

        setIsActivating(false);
    }

    function handleKeyDown(e: React.KeyboardEvent) {
        if (e.key === 'Enter') handleActivate();
    }

    // Loading state
    if (isLoading) {
        return (
            <div className="lic-gate">
                <div className="lic-aurora">
                    <div className="lic-orb lic-orb-1" />
                    <div className="lic-orb lic-orb-2" />
                </div>
                <div className="lic-loader">
                    <div className="lic-spinner" />
                    <p className="lic-loader-text">Verifying license...</p>
                </div>
                <LicenseGateStyles />
            </div>
        );
    }

    // Activated — render the app
    if (isActivated && !showSuccess) {
        return <>{children}</>;
    }

    // Success flash
    if (showSuccess) {
        return (
            <div className="lic-gate">
                <div className="lic-aurora">
                    <div className="lic-orb lic-orb-1" />
                    <div className="lic-orb lic-orb-2" />
                </div>
                <div className="lic-success-card">
                    <div className="lic-success-icon">✓</div>
                    <h2 className="lic-success-title">License Activated!</h2>
                    <p className="lic-success-sub">Welcome to RenmaeAI Studio</p>
                </div>
                <LicenseGateStyles />
            </div>
        );
    }

    // Gate — license activation form
    return (
        <div className="lic-gate">
            {/* Aurora Background */}
            <div className="lic-aurora">
                <div className="lic-orb lic-orb-1" />
                <div className="lic-orb lic-orb-2" />
                <div className="lic-orb lic-orb-3" />
            </div>

            {/* Particles */}
            <div className="lic-particles">
                {Array.from({ length: 20 }).map((_, i) => (
                    <div
                        key={i}
                        className="lic-particle"
                        style={{
                            left: `${Math.random() * 100}%`,
                            top: `${Math.random() * 100}%`,
                            animationDelay: `${Math.random() * 6}s`,
                            animationDuration: `${5 + Math.random() * 7}s`,
                        }}
                    />
                ))}
            </div>

            {/* Main Card */}
            <div className="lic-card">
                {/* Logo */}
                <div className="lic-logo-ring">
                    <span className="lic-logo-letter">R</span>
                </div>

                <h1 className="lic-title">RenmaeAI Studio</h1>
                <p className="lic-subtitle">Enter your license key to get started</p>

                {/* License Input */}
                <div className="lic-input-group">
                    <input
                        type="text"
                        className="lic-input"
                        placeholder="XXXX-XXXX-XXXX-XXXX"
                        value={keyInput}
                        onChange={(e) => setKeyInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        autoFocus
                        spellCheck={false}
                    />
                    <button
                        className="lic-activate-btn"
                        onClick={handleActivate}
                        disabled={isActivating || !keyInput.trim()}
                    >
                        {isActivating ? (
                            <span className="lic-btn-spinner" />
                        ) : (
                            'Activate'
                        )}
                    </button>
                </div>

                {/* Error */}
                {error && (
                    <div className="lic-error">
                        <span className="lic-error-icon">!</span>
                        {error}
                    </div>
                )}

                {/* Divider */}
                <div className="lic-divider">
                    <span>Don't have a license?</span>
                </div>

                {/* Buy Button */}
                <a
                    href={LEMONSQUEEZY_STORE_URL}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="lic-buy-btn"
                >
                    Get License Key
                    <span className="lic-buy-arrow">→</span>
                </a>

                {/* Info */}
                <p className="lic-info">
                    Purchase a license to unlock all features.
                    <br />
                    Your key will be emailed to you instantly after payment.
                </p>

                {/* Already activated info (shown if deactivated) */}
                {customerEmail && (
                    <div className="lic-activated-info">
                        <span>Previously activated for: {customerEmail}</span>
                        <span>Plan: {variantName}</span>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="lic-footer">
                <span>RenmaeAI Studio v1.0</span>
                <span className="lic-dot">·</span>
                <a href="https://renmaeai.com" target="_blank" rel="noopener noreferrer">
                    renmaeai.com
                </a>
            </div>

            <LicenseGateStyles />
        </div>
    );
}

// ── Deactivate Button (for use in settings) ──
export function DeactivateLicenseButton() {
    const { deactivate, customerEmail, variantName } = useLicenseStore();
    const [isDeactivating, setIsDeactivating] = useState(false);

    async function handleDeactivate() {
        if (!confirm('Are you sure you want to deactivate this license? You can re-activate it later.')) return;
        setIsDeactivating(true);
        await deactivate();
        setIsDeactivating(false);
    }

    return (
        <div className="lic-deactivate-section">
            <div className="lic-deactivate-info">
                <span className="lic-deactivate-label">License</span>
                <span className="lic-deactivate-email">{customerEmail}</span>
                <span className="lic-deactivate-plan">{variantName}</span>
            </div>
            <button
                className="lic-deactivate-btn"
                onClick={handleDeactivate}
                disabled={isDeactivating}
            >
                {isDeactivating ? 'Deactivating...' : 'Deactivate License'}
            </button>
        </div>
    );
}

// ── Styles ──
function LicenseGateStyles() {
    return (
        <style>{`
      .lic-gate {
        position: fixed;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        background: #060608;
        z-index: 99999;
        overflow: hidden;
        font-family: 'Inter', -apple-system, sans-serif;
      }

      /* ── Aurora ── */
      .lic-aurora {
        position: fixed;
        inset: 0;
        z-index: 0;
        overflow: hidden;
      }

      .lic-orb {
        position: absolute;
        border-radius: 50%;
        filter: blur(120px);
        will-change: transform;
      }

      .lic-orb-1 {
        width: 500px;
        height: 500px;
        top: -20%;
        left: -10%;
        background: radial-gradient(circle, rgba(255, 170, 0, 0.15) 0%, transparent 70%);
        animation: licFloat1 20s ease-in-out infinite alternate;
      }

      .lic-orb-2 {
        width: 400px;
        height: 400px;
        bottom: -15%;
        right: -10%;
        background: radial-gradient(circle, rgba(167, 139, 250, 0.12) 0%, transparent 70%);
        animation: licFloat2 18s ease-in-out infinite alternate;
      }

      .lic-orb-3 {
        width: 350px;
        height: 350px;
        top: 50%;
        left: 60%;
        background: radial-gradient(circle, rgba(52, 211, 153, 0.06) 0%, transparent 70%);
        animation: licFloat3 16s ease-in-out infinite alternate;
      }

      @keyframes licFloat1 {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(60px, 40px) scale(1.1); }
      }
      @keyframes licFloat2 {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(-50px, -40px) scale(1.15); }
      }
      @keyframes licFloat3 {
        0% { transform: translate(0, 0) scale(1); }
        100% { transform: translate(30px, -30px) scale(1.05); }
      }

      /* ── Particles ── */
      .lic-particles {
        position: fixed;
        inset: 0;
        z-index: 1;
        pointer-events: none;
      }

      .lic-particle {
        position: absolute;
        width: 2px;
        height: 2px;
        border-radius: 50%;
        background: #FFD700;
        opacity: 0.3;
        animation: licDrift linear infinite;
      }

      @keyframes licDrift {
        0% { transform: translateY(0); opacity: 0; }
        10% { opacity: 0.4; }
        90% { opacity: 0.4; }
        100% { transform: translateY(-100px); opacity: 0; }
      }

      /* ── Card ── */
      .lic-card {
        position: relative;
        z-index: 2;
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(24px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 24px;
        padding: 40px 44px 36px;
        width: 440px;
        max-width: 92vw;
        text-align: center;
        animation: licReveal 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
      }

      @keyframes licReveal {
        0% { opacity: 0; transform: translateY(24px) scale(0.96); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
      }

      /* ── Logo ── */
      .lic-logo-ring {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        border: 2px solid rgba(255, 215, 0, 0.3);
        margin: 0 auto 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: radial-gradient(circle, rgba(255, 215, 0, 0.06) 0%, transparent 70%);
        animation: licRingPulse 4s ease-in-out infinite;
      }

      .lic-logo-letter {
        font-family: 'Fredoka', sans-serif;
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #FFD700, #F59E0B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      @keyframes licRingPulse {
        0%, 100% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.08); }
        50% { box-shadow: 0 0 40px rgba(255, 215, 0, 0.18); }
      }

      /* ── Typography ── */
      .lic-title {
        font-family: 'Fredoka', sans-serif;
        font-size: 1.6rem;
        font-weight: 700;
        margin: 0 0 6px;
        background: linear-gradient(135deg, #FFD700, #FBBF24, #F59E0B);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
      }

      .lic-subtitle {
        font-size: 0.88rem;
        color: #888;
        margin: 0 0 28px;
      }

      /* ── Input Group ── */
      .lic-input-group {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }

      .lic-input {
        flex: 1;
        padding: 12px 16px;
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        color: #E5E5E5;
        font-size: 0.9rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        letter-spacing: 0.5px;
        outline: none;
        transition: all 0.25s ease;
      }

      .lic-input::placeholder {
        color: #555;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
      }

      .lic-input:focus {
        border-color: rgba(255, 215, 0, 0.4);
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.08);
        background: rgba(255, 255, 255, 0.07);
      }

      .lic-activate-btn {
        padding: 12px 24px;
        background: linear-gradient(135deg, #FFD700, #F59E0B);
        border: none;
        border-radius: 12px;
        color: #111;
        font-weight: 700;
        font-size: 0.88rem;
        cursor: pointer;
        transition: all 0.25s ease;
        white-space: nowrap;
        min-width: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .lic-activate-btn:hover:not(:disabled) {
        transform: translateY(-1px);
        box-shadow: 0 6px 24px rgba(255, 215, 0, 0.3);
      }

      .lic-activate-btn:disabled {
        opacity: 0.5;
        cursor: not-allowed;
      }

      .lic-btn-spinner {
        width: 18px;
        height: 18px;
        border: 2.5px solid rgba(0, 0, 0, 0.2);
        border-top-color: #111;
        border-radius: 50%;
        animation: licSpin 0.6s linear infinite;
      }

      /* ── Error ── */
      .lic-error {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 10px;
        color: #f87171;
        font-size: 0.82rem;
        margin-bottom: 16px;
        text-align: left;
      }

      .lic-error-icon {
        width: 20px;
        height: 20px;
        border-radius: 50%;
        background: rgba(239, 68, 68, 0.2);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: 800;
        flex-shrink: 0;
      }

      /* ── Divider ── */
      .lic-divider {
        display: flex;
        align-items: center;
        gap: 12px;
        margin: 20px 0;
      }

      .lic-divider::before,
      .lic-divider::after {
        content: '';
        flex: 1;
        height: 1px;
        background: rgba(255, 255, 255, 0.06);
      }

      .lic-divider span {
        font-size: 0.75rem;
        color: #666;
        white-space: nowrap;
      }

      /* ── Buy Button ── */
      .lic-buy-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        width: 100%;
        padding: 13px 20px;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        color: #E5E5E5;
        font-size: 0.9rem;
        font-weight: 600;
        text-decoration: none;
        transition: all 0.25s ease;
        cursor: pointer;
      }

      .lic-buy-btn:hover {
        background: rgba(255, 215, 0, 0.08);
        border-color: rgba(255, 215, 0, 0.25);
        color: #FFD700;
      }

      .lic-buy-arrow {
        transition: transform 0.25s ease;
      }

      .lic-buy-btn:hover .lic-buy-arrow {
        transform: translateX(3px);
      }

      /* ── Info ── */
      .lic-info {
        font-size: 0.72rem;
        color: #555;
        margin: 14px 0 0;
        line-height: 1.6;
      }

      .lic-activated-info {
        margin-top: 12px;
        padding: 10px;
        background: rgba(255, 255, 255, 0.03);
        border-radius: 8px;
        display: flex;
        flex-direction: column;
        gap: 2px;
        font-size: 0.72rem;
        color: #666;
      }

      /* ── Loader ── */
      .lic-loader {
        position: relative;
        z-index: 2;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;
      }

      .lic-spinner {
        width: 36px;
        height: 36px;
        border: 3px solid rgba(255, 215, 0, 0.15);
        border-top-color: #FFD700;
        border-radius: 50%;
        animation: licSpin 0.8s linear infinite;
      }

      @keyframes licSpin {
        to { transform: rotate(360deg); }
      }

      .lic-loader-text {
        color: #888;
        font-size: 0.85rem;
      }

      /* ── Success ── */
      .lic-success-card {
        position: relative;
        z-index: 2;
        text-align: center;
        animation: licReveal 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
      }

      .lic-success-icon {
        width: 72px;
        height: 72px;
        border-radius: 50%;
        background: linear-gradient(135deg, #34d399, #10b981);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2rem;
        color: white;
        margin: 0 auto 16px;
        box-shadow: 0 0 40px rgba(52, 211, 153, 0.3);
      }

      .lic-success-title {
        font-family: 'Fredoka', sans-serif;
        font-size: 1.5rem;
        color: #34d399;
        margin: 0 0 6px;
      }

      .lic-success-sub {
        color: #888;
        font-size: 0.9rem;
        margin: 0;
      }

      /* ── Footer ── */
      .lic-footer {
        position: absolute;
        bottom: 20px;
        z-index: 2;
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 0.72rem;
        color: #444;
      }

      .lic-dot { color: #333; }

      .lic-footer a {
        color: #666;
        text-decoration: none;
        transition: color 0.2s;
      }

      .lic-footer a:hover {
        color: #FFD700;
      }

      /* ── Deactivate (Settings) ── */
      .lic-deactivate-section {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 16px 20px;
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 12px;
        margin-top: 12px;
      }

      .lic-deactivate-info {
        display: flex;
        flex-direction: column;
        gap: 2px;
      }

      .lic-deactivate-label {
        font-size: 0.75rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
      }

      .lic-deactivate-email {
        font-size: 0.85rem;
        color: #E5E5E5;
      }

      .lic-deactivate-plan {
        font-size: 0.78rem;
        color: #FFD700;
      }

      .lic-deactivate-btn {
        padding: 8px 16px;
        background: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.25);
        border-radius: 8px;
        color: #f87171;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s ease;
      }

      .lic-deactivate-btn:hover {
        background: rgba(239, 68, 68, 0.2);
        border-color: rgba(239, 68, 68, 0.4);
      }
    `}</style>
    );
}
