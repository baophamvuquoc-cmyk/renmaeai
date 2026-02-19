/**
 * LemonSqueezy License API Client
 * Handles license activation, validation, and deactivation.
 * No server required — calls LemonSqueezy API directly.
 */

const LS_API_BASE = 'https://api.lemonsqueezy.com/v1/licenses';

// ── Configuration ──
// Replace with your actual LemonSqueezy store URL after creating your product
export const LEMONSQUEEZY_STORE_URL = 'https://renmaeai.lemonsqueezy.com/checkout/buy/67fa8a80-96f6-49ac-b9eb-8ae172d65bbd';

// ── Master Keys (loaded from env, never committed to source) ──
const MASTER_KEYS: string[] = (import.meta.env.VITE_MASTER_KEYS || '')
    .split(',')
    .map((k: string) => k.trim().toUpperCase())
    .filter(Boolean);

export function isMasterKey(key: string): boolean {
    return MASTER_KEYS.includes(key.trim().toUpperCase());
}

function masterKeyResult() {
    return {
        license_key: {
            id: 0,
            status: 'active',
            key: 'MASTER',
            activation_limit: 999,
            activation_usage: 1,
            expires_at: null,
        },
        instance: { id: 'master', name: 'master' },
        meta: {
            store_id: 0,
            product_id: 0,
            product_name: 'RenmaeAI Studio',
            variant_id: 0,
            variant_name: 'Master License',
            customer_id: 0,
            customer_name: 'Owner',
            customer_email: 'owner@renmaeai.com',
        },
    };
}

// ── Machine ID ──
function generateMachineId(): string {
    const stored = localStorage.getItem('renmae_machine_id');
    if (stored) return stored;

    const id = `renmae_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem('renmae_machine_id', id);
    return id;
}

export function getMachineId(): string {
    return generateMachineId();
}

// ── Types ──
export interface LicenseActivationResult {
    activated: boolean;
    error?: string;
    license_key?: {
        id: number;
        status: string;
        key: string;
        activation_limit: number;
        activation_usage: number;
        expires_at: string | null;
    };
    instance?: {
        id: string;
        name: string;
    };
    meta?: {
        store_id: number;
        product_id: number;
        product_name: string;
        variant_id: number;
        variant_name: string;
        customer_id: number;
        customer_name: string;
        customer_email: string;
    };
}

export interface LicenseValidationResult {
    valid: boolean;
    error?: string;
    license_key?: {
        id: number;
        status: string;
        key: string;
        activation_limit: number;
        activation_usage: number;
        expires_at: string | null;
    };
    meta?: {
        store_id: number;
        product_id: number;
        product_name: string;
        variant_id: number;
        variant_name: string;
        customer_id: number;
        customer_name: string;
        customer_email: string;
    };
}

// ── API Functions ──

/**
 * Activate a license key for this machine
 */
export async function activateLicense(licenseKey: string): Promise<LicenseActivationResult> {
    if (isMasterKey(licenseKey)) {
        const m = masterKeyResult();
        return { activated: true, ...m };
    }

    try {
        const response = await fetch(`${LS_API_BASE}/activate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                license_key: licenseKey.trim(),
                instance_name: getMachineId(),
            }),
        });

        const data = await response.json();

        if (data.activated || data.valid) {
            return {
                activated: true,
                license_key: data.license_key,
                instance: data.instance,
                meta: data.meta,
            };
        }

        return {
            activated: false,
            error: data.error || 'License activation failed',
        };
    } catch (err) {
        return {
            activated: false,
            error: err instanceof Error ? err.message : 'Network error — check your connection',
        };
    }
}

/**
 * Validate an already-activated license key
 */
export async function validateLicense(licenseKey: string, instanceId?: string): Promise<LicenseValidationResult> {
    if (isMasterKey(licenseKey)) {
        const m = masterKeyResult();
        return { valid: true, license_key: m.license_key, meta: m.meta };
    }

    try {
        const body: Record<string, string> = { license_key: licenseKey.trim() };
        if (instanceId) body.instance_id = instanceId;

        const response = await fetch(`${LS_API_BASE}/validate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams(body),
        });

        const data = await response.json();

        return {
            valid: data.valid === true,
            error: data.valid ? undefined : (data.error || 'Invalid license'),
            license_key: data.license_key,
            meta: data.meta,
        };
    } catch {
        return { valid: false, error: 'Network error — using cached license' };
    }
}

/**
 * Deactivate license on this machine
 */
export async function deactivateLicense(licenseKey: string, instanceId: string): Promise<boolean> {
    try {
        const response = await fetch(`${LS_API_BASE}/deactivate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                license_key: licenseKey.trim(),
                instance_id: instanceId,
            }),
        });

        const data = await response.json();
        return data.deactivated === true;
    } catch {
        return false;
    }
}

// ── Local Cache (Encrypted-ish) ──

const CACHE_KEY = 'renmae_lic_cache';

interface CachedLicense {
    key: string;
    instanceId: string;
    activatedAt: number;
    lastValidated: number;
    productName: string;
    variantName: string;
    customerEmail: string;
    expiresAt: string | null;
}

function encodeCache(data: CachedLicense): string {
    return btoa(encodeURIComponent(JSON.stringify(data)));
}

function decodeCache(encoded: string): CachedLicense | null {
    try {
        return JSON.parse(decodeURIComponent(atob(encoded)));
    } catch {
        return null;
    }
}

export function saveLicenseCache(data: CachedLicense): void {
    localStorage.setItem(CACHE_KEY, encodeCache(data));
}

export function loadLicenseCache(): CachedLicense | null {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    return decodeCache(raw);
}

export function clearLicenseCache(): void {
    localStorage.removeItem(CACHE_KEY);
}

/**
 * Check if cached license is still within offline grace period (3 days)
 */
export function isCacheValid(cache: CachedLicense): boolean {
    const threeDaysMs = 3 * 24 * 60 * 60 * 1000;
    const timeSinceValidation = Date.now() - cache.lastValidated;
    return timeSinceValidation < threeDaysMs;
}
