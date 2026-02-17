/**
 * Bee-themed SVG icons for RenmaeAI landing page.
 * Each variant is a cute bee character with contextual accessories.
 */

interface BeeIconProps {
    size?: number;
    className?: string;
}

/** Base bee body used by all variants */
function BeeBody({ size = 40, children, className }: BeeIconProps & { children?: React.ReactNode }) {
    return (
        <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
            {/* Wings */}
            <ellipse cx="20" cy="22" rx="10" ry="7" fill="rgba(255,255,255,0.15)" stroke="rgba(255,215,0,0.3)" strokeWidth="0.8" transform="rotate(-20 20 22)" />
            <ellipse cx="44" cy="22" rx="10" ry="7" fill="rgba(255,255,255,0.15)" stroke="rgba(255,215,0,0.3)" strokeWidth="0.8" transform="rotate(20 44 22)" />
            {/* Body */}
            <ellipse cx="32" cy="36" rx="14" ry="16" fill="#FFD700" />
            {/* Stripes */}
            <rect x="18" y="30" width="28" height="3.5" rx="1.5" fill="#1a1a1a" opacity="0.7" />
            <rect x="18" y="37" width="28" height="3.5" rx="1.5" fill="#1a1a1a" opacity="0.7" />
            <rect x="20" y="44" width="24" height="3" rx="1.5" fill="#1a1a1a" opacity="0.7" />
            {/* Face */}
            <circle cx="27" cy="26" r="2.2" fill="#1a1a1a" />
            <circle cx="37" cy="26" r="2.2" fill="#1a1a1a" />
            <circle cx="27.8" cy="25.3" r="0.7" fill="white" />
            <circle cx="37.8" cy="25.3" r="0.7" fill="white" />
            {/* Smile */}
            <path d="M28 30 Q32 33 36 30" stroke="#1a1a1a" strokeWidth="1.2" fill="none" strokeLinecap="round" />
            {/* Antennae */}
            <line x1="28" y1="20" x2="24" y2="13" stroke="#1a1a1a" strokeWidth="1.2" strokeLinecap="round" />
            <line x1="36" y1="20" x2="40" y2="13" stroke="#1a1a1a" strokeWidth="1.2" strokeLinecap="round" />
            <circle cx="24" cy="12" r="2" fill="#FFD700" />
            <circle cx="40" cy="12" r="2" fill="#FFD700" />
            {/* Stinger */}
            <polygon points="32,52 29,55 35,55" fill="#e6a800" />
            {/* Extra elements for each variant */}
            {children}
        </svg>
    );
}

/** Bee with a file/document — for "Đổi Tên File" */
export function BeeFile({ size = 40, className }: BeeIconProps) {
    return (
        <BeeBody size={size} className={className}>
            <g transform="translate(42, 38) rotate(15)">
                <rect x="0" y="0" width="12" height="15" rx="1.5" fill="rgba(96,165,250,0.8)" stroke="rgba(96,165,250,1)" strokeWidth="0.8" />
                <rect x="2.5" y="3" width="7" height="1.2" rx="0.5" fill="rgba(255,255,255,0.5)" />
                <rect x="2.5" y="5.5" width="5" height="1.2" rx="0.5" fill="rgba(255,255,255,0.4)" />
                <rect x="2.5" y="8" width="6" height="1.2" rx="0.5" fill="rgba(255,255,255,0.3)" />
                <polygon points="8,0 12,0 12,4" fill="rgba(96,165,250,0.5)" />
            </g>
        </BeeBody>
    );
}

/** Bee with sparkles/wand — for "Tạo Kịch Bản AI" */
export function BeeSparkle({ size = 40, className }: BeeIconProps) {
    return (
        <BeeBody size={size} className={className}>
            {/* Sparkle stars */}
            <g fill="#A78BFA">
                <polygon points="50,10 51.5,14 56,14 52.5,17 53.5,21 50,18.5 46.5,21 47.5,17 44,14 48.5,14" transform="scale(0.6) translate(30,-2)" />
                <polygon points="50,10 51.5,14 56,14 52.5,17 53.5,21 50,18.5 46.5,21 47.5,17 44,14 48.5,14" transform="scale(0.4) translate(120,10)" />
                <polygon points="50,10 51.5,14 56,14 52.5,17 53.5,21 50,18.5 46.5,21 47.5,17 44,14 48.5,14" transform="scale(0.35) translate(90,55)" />
            </g>
            {/* Wand */}
            <line x1="48" y1="42" x2="56" y2="28" stroke="#A78BFA" strokeWidth="1.8" strokeLinecap="round" />
            <circle cx="56" cy="27" r="2.5" fill="#A78BFA" opacity="0.8" />
        </BeeBody>
    );
}

/** Bee with a gear — for "Cấu Hình AI" */
export function BeeGear({ size = 40, className }: BeeIconProps) {
    return (
        <BeeBody size={size} className={className}>
            <g transform="translate(46, 36)">
                {/* Gear */}
                <circle cx="6" cy="6" r="4" fill="none" stroke="#FFD700" strokeWidth="1.5" />
                <circle cx="6" cy="6" r="1.5" fill="#FFD700" opacity="0.6" />
                {/* Gear teeth */}
                {[0, 45, 90, 135, 180, 225, 270, 315].map(angle => (
                    <rect
                        key={angle}
                        x="5" y="-1" width="2" height="3.5" rx="0.5"
                        fill="#FFD700"
                        transform={`rotate(${angle}, 6, 6)`}
                    />
                ))}
            </g>
        </BeeBody>
    );
}

/** Sleeping bee with ZZZ — for "Sắp Ra Mắt" */
export function BeeSleep({ size = 40, className }: BeeIconProps) {
    return (
        <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
            {/* Wings (folded) */}
            <ellipse cx="22" cy="24" rx="8" ry="5.5" fill="rgba(255,255,255,0.08)" stroke="rgba(120,120,120,0.2)" strokeWidth="0.8" transform="rotate(-15 22 24)" />
            <ellipse cx="42" cy="24" rx="8" ry="5.5" fill="rgba(255,255,255,0.08)" stroke="rgba(120,120,120,0.2)" strokeWidth="0.8" transform="rotate(15 42 24)" />
            {/* Body (dimmer) */}
            <ellipse cx="32" cy="36" rx="14" ry="16" fill="rgba(180,160,80,0.4)" />
            {/* Stripes */}
            <rect x="18" y="30" width="28" height="3.5" rx="1.5" fill="rgba(80,80,80,0.4)" />
            <rect x="18" y="37" width="28" height="3.5" rx="1.5" fill="rgba(80,80,80,0.4)" />
            <rect x="20" y="44" width="24" height="3" rx="1.5" fill="rgba(80,80,80,0.4)" />
            {/* Closed eyes */}
            <path d="M25 26 Q27 28 29 26" stroke="rgba(120,120,120,0.5)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            <path d="M35 26 Q37 28 39 26" stroke="rgba(120,120,120,0.5)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            {/* Antennae */}
            <line x1="28" y1="20" x2="24" y2="14" stroke="rgba(100,100,100,0.4)" strokeWidth="1" strokeLinecap="round" />
            <line x1="36" y1="20" x2="40" y2="14" stroke="rgba(100,100,100,0.4)" strokeWidth="1" strokeLinecap="round" />
            <circle cx="24" cy="13" r="1.5" fill="rgba(180,160,80,0.3)" />
            <circle cx="40" cy="13" r="1.5" fill="rgba(180,160,80,0.3)" />
            {/* ZZZ */}
            <text x="44" y="18" fill="rgba(120,120,120,0.5)" fontSize="8" fontWeight="bold" fontFamily="sans-serif">Z</text>
            <text x="50" y="12" fill="rgba(120,120,120,0.4)" fontSize="6" fontWeight="bold" fontFamily="sans-serif">z</text>
            <text x="54" y="8" fill="rgba(120,120,120,0.3)" fontSize="5" fontWeight="bold" fontFamily="sans-serif">z</text>
        </svg>
    );
}

/** Small bee for status bar, back button, etc. */
export function BeeSmall({ size = 20, className }: BeeIconProps) {
    return (
        <svg width={size} height={size} viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
            {/* Wings */}
            <ellipse cx="10" cy="10" rx="5" ry="3.5" fill="rgba(255,255,255,0.15)" stroke="rgba(255,215,0,0.3)" strokeWidth="0.5" transform="rotate(-20 10 10)" />
            <ellipse cx="22" cy="10" rx="5" ry="3.5" fill="rgba(255,255,255,0.15)" stroke="rgba(255,215,0,0.3)" strokeWidth="0.5" transform="rotate(20 22 10)" />
            {/* Body */}
            <ellipse cx="16" cy="18" rx="7" ry="8" fill="#FFD700" />
            {/* Stripes */}
            <rect x="9" y="15" width="14" height="2" rx="1" fill="#1a1a1a" opacity="0.7" />
            <rect x="9" y="19" width="14" height="2" rx="1" fill="#1a1a1a" opacity="0.7" />
            {/* Eyes */}
            <circle cx="13.5" cy="13" r="1.2" fill="#1a1a1a" />
            <circle cx="18.5" cy="13" r="1.2" fill="#1a1a1a" />
            <circle cx="14" cy="12.5" r="0.4" fill="white" />
            <circle cx="19" cy="12.5" r="0.4" fill="white" />
            {/* Smile */}
            <path d="M14 15.5 Q16 17 18 15.5" stroke="#1a1a1a" strokeWidth="0.8" fill="none" strokeLinecap="round" />
            {/* Antennae */}
            <line x1="14" y1="10" x2="12" y2="6" stroke="#1a1a1a" strokeWidth="0.8" strokeLinecap="round" />
            <line x1="18" y1="10" x2="20" y2="6" stroke="#1a1a1a" strokeWidth="0.8" strokeLinecap="round" />
            <circle cx="12" cy="5.5" r="1" fill="#FFD700" />
            <circle cx="20" cy="5.5" r="1" fill="#FFD700" />
        </svg>
    );
}

/** Large hero bee for the landing page */
export function BeeHero({ size = 48, className }: BeeIconProps) {
    return (
        <svg width={size} height={size} viewBox="0 0 80 80" fill="none" xmlns="http://www.w3.org/2000/svg" className={className}>
            {/* Glow */}
            <circle cx="40" cy="40" r="35" fill="url(#beeHeroGlow)" opacity="0.3" />
            {/* Wings */}
            <ellipse cx="22" cy="26" rx="13" ry="9" fill="rgba(255,255,255,0.15)" stroke="rgba(255,215,0,0.35)" strokeWidth="1" transform="rotate(-22 22 26)" />
            <ellipse cx="58" cy="26" rx="13" ry="9" fill="rgba(255,255,255,0.15)" stroke="rgba(255,215,0,0.35)" strokeWidth="1" transform="rotate(22 58 26)" />
            {/* Body */}
            <ellipse cx="40" cy="44" rx="17" ry="20" fill="#FFD700" />
            {/* Stripes */}
            <rect x="23" y="37" width="34" height="4" rx="2" fill="#1a1a1a" opacity="0.7" />
            <rect x="23" y="45" width="34" height="4" rx="2" fill="#1a1a1a" opacity="0.7" />
            <rect x="25" y="53" width="30" height="3.5" rx="1.5" fill="#1a1a1a" opacity="0.7" />
            {/* Face */}
            <circle cx="34" cy="32" r="2.8" fill="#1a1a1a" />
            <circle cx="46" cy="32" r="2.8" fill="#1a1a1a" />
            <circle cx="34.8" cy="31" r="1" fill="white" />
            <circle cx="46.8" cy="31" r="1" fill="white" />
            {/* Big smile */}
            <path d="M34 37 Q40 41 46 37" stroke="#1a1a1a" strokeWidth="1.5" fill="none" strokeLinecap="round" />
            {/* Blush */}
            <circle cx="29" cy="36" r="3" fill="rgba(255,150,100,0.2)" />
            <circle cx="51" cy="36" r="3" fill="rgba(255,150,100,0.2)" />
            {/* Antennae */}
            <line x1="35" y1="24" x2="30" y2="14" stroke="#1a1a1a" strokeWidth="1.5" strokeLinecap="round" />
            <line x1="45" y1="24" x2="50" y2="14" stroke="#1a1a1a" strokeWidth="1.5" strokeLinecap="round" />
            <circle cx="30" cy="13" r="2.5" fill="#FFD700" />
            <circle cx="50" cy="13" r="2.5" fill="#FFD700" />
            {/* Crown / sparkle on top */}
            <polygon points="40,6 42,10 46,10 43,13 44,17 40,14 36,17 37,13 34,10 38,10" fill="rgba(255,215,0,0.6)" />
            {/* Stinger */}
            <polygon points="40,64 37,68 43,68" fill="#e6a800" />
            <defs>
                <radialGradient id="beeHeroGlow" cx="40" cy="40" r="35" gradientUnits="userSpaceOnUse">
                    <stop offset="0%" stopColor="#FFD700" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#FFD700" stopOpacity="0" />
                </radialGradient>
            </defs>
        </svg>
    );
}
