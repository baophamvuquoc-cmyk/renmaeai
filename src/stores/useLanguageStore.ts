import { create } from 'zustand';
import i18n from '../i18n';

interface LanguageState {
    language: 'vi' | 'en';
    setLanguage: (lang: 'vi' | 'en') => void;
}

export const useLanguageStore = create<LanguageState>((set) => ({
    language: (localStorage.getItem('renmae_language') || 'vi') as 'vi' | 'en',
    setLanguage: (lang) => {
        localStorage.setItem('renmae_language', lang);
        i18n.changeLanguage(lang);
        set({ language: lang });
    },
}));
