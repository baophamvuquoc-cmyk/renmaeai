import { create } from 'zustand';
import {
    activateLicense,
    validateLicense,
    deactivateLicense,
    saveLicenseCache,
    loadLicenseCache,
    clearLicenseCache,
    isCacheValid,
} from '../lib/lemonsqueezy';

interface LicenseState {
    // State
    isActivated: boolean;
    isLoading: boolean;
    licenseKey: string;
    instanceId: string;
    productName: string;
    variantName: string;
    customerEmail: string;
    expiresAt: string | null;
    error: string | null;

    // Actions
    activate: (key: string) => Promise<boolean>;
    checkLicense: () => Promise<void>;
    deactivate: () => Promise<void>;
    clearError: () => void;
}

export const useLicenseStore = create<LicenseState>((set, get) => ({
    isActivated: false,
    isLoading: true,
    licenseKey: '',
    instanceId: '',
    productName: '',
    variantName: '',
    customerEmail: '',
    expiresAt: null,
    error: null,

    activate: async (key: string) => {
        set({ isLoading: true, error: null });

        const result = await activateLicense(key);

        if (result.activated && result.license_key && result.instance && result.meta) {
            const cacheData = {
                key,
                instanceId: result.instance.id,
                activatedAt: Date.now(),
                lastValidated: Date.now(),
                productName: result.meta.product_name || 'RenmaeAI Studio',
                variantName: result.meta.variant_name || 'License',
                customerEmail: result.meta.customer_email || '',
                expiresAt: result.license_key.expires_at,
            };

            saveLicenseCache(cacheData);

            set({
                isActivated: true,
                isLoading: false,
                licenseKey: key,
                instanceId: result.instance.id,
                productName: cacheData.productName,
                variantName: cacheData.variantName,
                customerEmail: cacheData.customerEmail,
                expiresAt: result.license_key.expires_at,
                error: null,
            });

            return true;
        }

        set({
            isLoading: false,
            error: result.error || 'Activation failed. Please check your license key.',
        });

        return false;
    },

    checkLicense: async () => {
        set({ isLoading: true });

        // 1. Check local cache first
        const cache = loadLicenseCache();

        if (!cache) {
            set({ isActivated: false, isLoading: false });
            return;
        }

        // 2. Try to validate online
        const result = await validateLicense(cache.key, cache.instanceId);

        if (result.valid) {
            // Update last validated timestamp
            saveLicenseCache({ ...cache, lastValidated: Date.now() });

            set({
                isActivated: true,
                isLoading: false,
                licenseKey: cache.key,
                instanceId: cache.instanceId,
                productName: cache.productName,
                variantName: cache.variantName,
                customerEmail: cache.customerEmail,
                expiresAt: cache.expiresAt,
                error: null,
            });
            return;
        }

        // 3. Online validation failed — check offline grace period
        if (isCacheValid(cache)) {
            set({
                isActivated: true,
                isLoading: false,
                licenseKey: cache.key,
                instanceId: cache.instanceId,
                productName: cache.productName,
                variantName: cache.variantName,
                customerEmail: cache.customerEmail,
                expiresAt: cache.expiresAt,
                error: null,
            });
            return;
        }

        // 4. Cache expired — require re-activation
        clearLicenseCache();
        set({
            isActivated: false,
            isLoading: false,
            error: 'License expired or revoked. Please re-activate.',
        });
    },

    deactivate: async () => {
        const { licenseKey, instanceId } = get();

        if (licenseKey && instanceId) {
            await deactivateLicense(licenseKey, instanceId);
        }

        clearLicenseCache();

        set({
            isActivated: false,
            isLoading: false,
            licenseKey: '',
            instanceId: '',
            productName: '',
            variantName: '',
            customerEmail: '',
            expiresAt: null,
            error: null,
        });
    },

    clearError: () => set({ error: null }),
}));
