import { create } from 'zustand';

export interface FileItem {
    path: string;
    name: string;
    size: number;
    type: 'file' | 'directory';
    extension?: string;
    modified?: string; // ISO date string
    selected?: boolean;
}

interface RenamePattern {
    prefix: string;
    suffix: string;
    useIndex: boolean;
    indexStart: number;
    indexPadding: number;
    regex: string;
    replacement: string;
    // Simple keyword replacement
    findKeyword: string;
    replaceKeyword: string;
    // Component selection flags
    includeOriginalName: boolean;
    includeExtension: boolean;
    includePrefix: boolean;
    includeSuffix: boolean;
    // Sequential naming mode
    nameList: string;
    useSequentialMode: boolean;
}

export type SortBy = 'name' | 'date' | 'size' | 'type';
export type SortOrder = 'asc' | 'desc';

interface FileStore {
    currentDirectory: string | null;
    files: FileItem[];
    selectedFiles: string[];
    renamePattern: RenamePattern;
    previewMap: Map<string, string>;
    previewOrder: string[]; // Thứ tự files trong preview (có thể kéo thả)
    searchKeywords: string;
    sortBy: SortBy;
    sortOrder: SortOrder;

    setCurrentDirectory: (path: string) => void;
    setFiles: (files: FileItem[]) => void;
    toggleFileSelection: (path: string) => void;
    selectAll: () => void;
    clearSelection: () => void;
    setRenamePattern: (pattern: Partial<RenamePattern>) => void;
    setPreviewMap: (map: Map<string, string>) => void;
    setPreviewOrder: (order: string[]) => void;
    reorderPreviewFiles: (fromIndex: number, toIndex: number) => void;
    setSearchKeywords: (keywords: string) => void;
    setSortBy: (sortBy: SortBy, sortOrder?: SortOrder) => void;
    getFilteredSortedFiles: () => FileItem[];
}

export const useFileStore = create<FileStore>((set, get) => ({
    currentDirectory: null,
    files: [],
    selectedFiles: [],
    renamePattern: {
        prefix: '',
        suffix: '',
        useIndex: true,
        indexStart: 1,
        indexPadding: 3,
        regex: '',
        replacement: '',
        findKeyword: '',
        replaceKeyword: '',
        includeOriginalName: false,
        includeExtension: true,
        includePrefix: true,
        includeSuffix: true,
        nameList: '',
        useSequentialMode: false,
    },
    previewMap: new Map(),
    previewOrder: [],
    searchKeywords: '',
    sortBy: 'name',
    sortOrder: 'asc',

    setCurrentDirectory: (path) => set({ currentDirectory: path }),
    setFiles: (files) => set({ files }),
    toggleFileSelection: (path) =>
        set((state) => ({
            selectedFiles: state.selectedFiles.includes(path)
                ? state.selectedFiles.filter((p) => p !== path)
                : [...state.selectedFiles, path],
        })),
    selectAll: () =>
        set((state) => ({
            selectedFiles: state.files.map((f) => f.path),
        })),
    clearSelection: () => set({ selectedFiles: [] }),
    setRenamePattern: (pattern) =>
        set((state) => ({
            renamePattern: { ...state.renamePattern, ...pattern },
        })),
    setPreviewMap: (map) => set({ previewMap: map }),
    setPreviewOrder: (order) => set({ previewOrder: order }),
    reorderPreviewFiles: (fromIndex, toIndex) =>
        set((state) => {
            const newOrder = [...state.previewOrder];
            const [movedItem] = newOrder.splice(fromIndex, 1);
            newOrder.splice(toIndex, 0, movedItem);
            return { previewOrder: newOrder };
        }),
    setSearchKeywords: (keywords) => set({ searchKeywords: keywords }),
    setSortBy: (sortBy, sortOrder) =>
        set((state) => {
            console.log('Setting sort:', { sortBy, sortOrder, currentSortBy: state.sortBy, currentSortOrder: state.sortOrder });
            return {
                sortBy,
                sortOrder: sortOrder !== undefined ? sortOrder : state.sortOrder,
            };
        }),
    getFilteredSortedFiles: () => {
        const state = get();
        let result = [...state.files];

        // Apply keyword filtering
        if (state.searchKeywords.trim()) {
            const keywords = state.searchKeywords
                .split(',')
                .map((k) => k.trim().toLowerCase())
                .filter((k) => k.length > 0);

            if (keywords.length > 0) {
                result = result.filter((file) =>
                    keywords.some((keyword) =>
                        file.name.toLowerCase().includes(keyword)
                    )
                );
            }
        }

        // Apply sorting
        result.sort((a, b) => {
            // Always put directories first
            if (a.type !== b.type) {
                return a.type === 'directory' ? -1 : 1;
            }

            let comparison = 0;

            switch (state.sortBy) {
                case 'name':
                    comparison = a.name.localeCompare(b.name, undefined, {
                        numeric: true,
                        sensitivity: 'base',
                    });
                    break;
                case 'date':
                    // Handle missing dates by treating them as very old (epoch 0)
                    const dateA = a.modified ? new Date(a.modified).getTime() : 0;
                    const dateB = b.modified ? new Date(b.modified).getTime() : 0;
                    comparison = dateA - dateB;
                    break;
                case 'size':
                    comparison = a.size - b.size;
                    break;
                case 'type':
                    const extA = a.extension || '';
                    const extB = b.extension || '';
                    comparison = extA.localeCompare(extB);
                    break;
            }

            return state.sortOrder === 'desc' ? -comparison : comparison;
        });

        return result;
    },
}));

