import { useState, useEffect } from 'react';
import { useFileStore } from '../../stores/useFileStore';
import { fileApi } from '../../lib/api';
import {
    Folder,
    File,
    FolderOpen,
    HardDrive,
    RefreshCw,
    Edit3,
    CheckCircle2,
    XCircle,
    Search,
    X,
    ArrowUpDown,
    ChevronDown,
    GripVertical,
} from 'lucide-react';

export default function FileManager() {
    const {
        currentDirectory,
        files,
        selectedFiles,
        renamePattern,
        previewMap,
        previewOrder,
        searchKeywords,
        sortBy,
        sortOrder,
        setCurrentDirectory,
        setFiles,
        toggleFileSelection,
        selectAll,
        clearSelection,
        setRenamePattern,
        setPreviewMap,
        setPreviewOrder,
        reorderPreviewFiles,
        setSearchKeywords,
        setSortBy,
        getFilteredSortedFiles,
    } = useFileStore();

    const [isLoading, setIsLoading] = useState(false);
    const [showPreview, setShowPreview] = useState(false);
    const [isRenaming, setIsRenaming] = useState(false);
    const [showSortMenu, setShowSortMenu] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
    const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

    // Debug: log when sort changes
    useEffect(() => {
        console.log('Sort state changed:', { sortBy, sortOrder });
    }, [sortBy, sortOrder]);

    // Close sort menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (showSortMenu) {
                const target = event.target as HTMLElement;
                if (!target.closest('.sort-dropdown') && !target.closest('.sort-button')) {
                    setShowSortMenu(false);
                }
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [showSortMenu]);

    const handleSelectDirectory = async () => {
        try {
            console.log('Attempting to open directory dialog...');
            setError(null);

            // Check if electron API is available
            if (!window.electron || !window.electron.selectDirectory) {
                console.error('Electron API not available');
                const errorMsg = 'Electron API không khả dụng. Vui lòng khởi động lại ứng dụng.';
                setError(errorMsg);
                alert(errorMsg);
                return;
            }

            const path = await window.electron.selectDirectory();
            console.log('Selected path:', path);

            if (path) {
                setCurrentDirectory(path);
                await loadDirectory(path);
            }
        } catch (error) {
            console.error('Error selecting directory:', error);
            const errorMsg = 'Lỗi khi chọn thư mục: ' + (error as Error).message;
            setError(errorMsg);
            alert(errorMsg);
        }
    };

    const loadDirectory = async (path: string) => {
        setIsLoading(true);
        setError(null);
        try {
            console.log('Loading directory:', path);
            const data = await fileApi.listDirectory(path);
            console.log('Received files:', data.files?.length || 0);
            setFiles(data.files || []);

            if (!data.files || data.files.length === 0) {
                setError('Thư mục này không chứa file nào hoặc không có quyền truy cập.');
            }
        } catch (error: any) {
            console.error('Failed to load directory:', error);
            const errorMsg = error.response?.data?.detail || error.message || 'Không thể tải danh sách file';
            setError(errorMsg);
        } finally {
            setIsLoading(false);
        }
    };

    const handleGeneratePreview = async () => {
        if (selectedFiles.length === 0) {
            alert('Vui lòng chọn ít nhất một file');
            return;
        }

        setIsLoading(true);
        try {
            // Get sorted files in the same order as displayed in file browser
            const sortedSelectedFiles = getFilteredSortedFiles()
                .filter((file) => selectedFiles.includes(file.path))
                .map((file) => file.path);

            const data = await fileApi.renamePreview(
                currentDirectory!,
                sortedSelectedFiles,
                renamePattern
            );
            setPreviewMap(new Map(Object.entries(data.preview)));
            setPreviewOrder(sortedSelectedFiles); // Khởi tạo thứ tự preview
            setShowPreview(true);
        } catch (error) {
            console.error('Failed to generate preview:', error);
        } finally {
            setIsLoading(false);
        }
    };

    // Drag-drop handlers cho preview reorder
    const handleDragStart = (index: number) => {
        setDraggedIndex(index);
    };

    const handleDragOver = (e: React.DragEvent, index: number) => {
        e.preventDefault();
        if (draggedIndex !== null && draggedIndex !== index) {
            setDragOverIndex(index);
        }
    };

    const handleDragLeave = () => {
        setDragOverIndex(null);
    };

    const handleDrop = async (e: React.DragEvent, toIndex: number) => {
        e.preventDefault();
        if (draggedIndex !== null && draggedIndex !== toIndex) {
            // Reorder trong store
            reorderPreviewFiles(draggedIndex, toIndex);

            // Regenerate preview với thứ tự mới
            const newOrder = [...previewOrder];
            const [movedItem] = newOrder.splice(draggedIndex, 1);
            newOrder.splice(toIndex, 0, movedItem);

            try {
                const data = await fileApi.renamePreview(
                    currentDirectory!,
                    newOrder,
                    renamePattern
                );
                setPreviewMap(new Map(Object.entries(data.preview)));
            } catch (error) {
                console.error('Failed to regenerate preview:', error);
            }
        }
        setDraggedIndex(null);
        setDragOverIndex(null);
    };

    const handleDragEnd = () => {
        setDraggedIndex(null);
        setDragOverIndex(null);
    };

    const handleExecuteRename = async () => {
        setIsRenaming(true);
        try {
            const renameMapObj = Object.fromEntries(previewMap);
            await fileApi.renameExecute(currentDirectory!, renameMapObj);

            // Reload directory
            await loadDirectory(currentDirectory!);
            setShowPreview(false);
            clearSelection();
            alert('Đổi tên thành công!');
        } catch (error) {
            console.error('Failed to rename files:', error);
            alert('Lỗi khi đổi tên file!');
        } finally {
            setIsRenaming(false);
        }
    };

    const getSortLabel = (sortBy: string, sortOrder: string): string => {
        const labels: Record<string, Record<string, string>> = {
            name: { asc: 'Tên (A → Z)', desc: 'Tên (Z → A)' },
            date: { asc: 'Ngày sửa (Cũ nhất)', desc: 'Ngày sửa (Mới nhất)' },
            size: { asc: 'Kích thước (Nhỏ nhất)', desc: 'Kích thước (Lớn nhất)' },
            type: { asc: 'Loại (A → Z)', desc: 'Loại (Z → A)' },
        };
        return labels[sortBy]?.[sortOrder] || 'Tên (A → Z)';
    };

    return (
        <div className="file-manager">
            <div className="manager-header">
                <h2>Quản Lý File</h2>
                <p className="text-secondary">
                    Đổi tên hàng loạt với preview an toàn và regex pattern
                </p>
            </div>

            {/* Directory Selection */}
            <div className="glass-card mb-6">
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                        <HardDrive className="text-accent-purple" size={24} />
                        <div>
                            <div className="font-semibold">Thư mục hiện tại</div>
                            <div className="text-sm text-secondary">
                                {currentDirectory || 'Chưa chọn thư mục'}
                            </div>
                        </div>
                    </div>
                    <div className="flex gap-2">
                        {currentDirectory && (
                            <button
                                className="btn btn-secondary"
                                onClick={() => loadDirectory(currentDirectory)}
                                disabled={isLoading}
                            >
                                <RefreshCw size={18} />
                                Làm mới
                            </button>
                        )}
                        <button className="btn btn-primary" onClick={handleSelectDirectory}>
                            <FolderOpen size={18} />
                            Chọn Thư Mục
                        </button>
                    </div>
                </div>
            </div>

            {/* Rename Pattern Configuration */}
            {currentDirectory && (
                <div className="glass-card mb-6">
                    <h3 className="mb-4 flex items-center gap-2">
                        <Edit3 size={20} />
                        Cấu Hình Đổi Tên
                    </h3>

                    {/* Mode Toggle */}
                    <div className="mode-toggle-container mb-4">
                        <button
                            className={`mode-toggle-btn ${!renamePattern.useSequentialMode ? 'active' : ''
                                }`}
                            onClick={() =>
                                setRenamePattern({ useSequentialMode: false })
                            }
                        >
                            Pattern Mode
                        </button>
                        <button
                            className={`mode-toggle-btn ${renamePattern.useSequentialMode ? 'active' : ''
                                }`}
                            onClick={() =>
                                setRenamePattern({ useSequentialMode: true })
                            }
                        >
                            Sequential Mode
                        </button>
                    </div>

                    {/* Sequential Mode UI */}
                    {renamePattern.useSequentialMode ? (
                        <div>
                            <label className="input-label">
                                Nhập Danh Sách Tên (cách nhau bằng dấu phẩy)
                            </label>
                            <textarea
                                className="input"
                                rows={4}
                                placeholder="Tên 1, Tên 2, Tên 3, Tên 4, ..."
                                value={renamePattern.nameList}
                                onChange={(e) =>
                                    setRenamePattern({ nameList: e.target.value })
                                }
                            />
                            <div className="mt-2 flex items-center justify-between text-sm">
                                <span className="text-secondary">
                                    {renamePattern.nameList.split(',').filter(n => n.trim()).length} tên đã nhập / {selectedFiles.length} files đã chọn
                                </span>
                                {renamePattern.nameList.split(',').filter(n => n.trim()).length !== selectedFiles.length && selectedFiles.length > 0 && (
                                    <span className="text-accent-pink">
                                        Số lượng không khớp
                                    </span>
                                )}
                            </div>
                        </div>
                    ) : (
                        /* Pattern Mode UI */
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <label className="input-label">Tiền tố (Prefix)</label>
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <input
                                            type="checkbox"
                                            checked={renamePattern.includePrefix}
                                            onChange={(e) =>
                                                setRenamePattern({ includePrefix: e.target.checked })
                                            }
                                        />
                                        <span>Sử dụng</span>
                                    </label>
                                </div>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="video_"
                                    value={renamePattern.prefix}
                                    disabled={!renamePattern.includePrefix}
                                    onChange={(e) =>
                                        setRenamePattern({ prefix: e.target.value })
                                    }
                                />
                            </div>
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <label className="input-label">Hậu tố (Suffix)</label>
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <input
                                            type="checkbox"
                                            checked={renamePattern.includeSuffix}
                                            onChange={(e) =>
                                                setRenamePattern({ includeSuffix: e.target.checked })
                                            }
                                        />
                                        <span>Sử dụng</span>
                                    </label>
                                </div>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="_final"
                                    value={renamePattern.suffix}
                                    disabled={!renamePattern.includeSuffix}
                                    onChange={(e) =>
                                        setRenamePattern({ suffix: e.target.value })
                                    }
                                />
                            </div>
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <label className="input-label">Tìm từ khóa (Find)</label>
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <input
                                            type="checkbox"
                                            checked={renamePattern.includeOriginalName}
                                            onChange={(e) =>
                                                setRenamePattern({ includeOriginalName: e.target.checked })
                                            }
                                        />
                                        <span>Sử dụng</span>
                                    </label>
                                </div>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="keyword_to_find"
                                    value={renamePattern.findKeyword}
                                    disabled={!renamePattern.includeOriginalName}
                                    onChange={(e) =>
                                        setRenamePattern({ findKeyword: e.target.value })
                                    }
                                />
                            </div>
                            <div>
                                <div className="flex items-center justify-between mb-2">
                                    <label className="input-label">Thay bằng (Replace)</label>
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <input
                                            type="checkbox"
                                            checked={renamePattern.includeOriginalName}
                                            onChange={(e) =>
                                                setRenamePattern({ includeOriginalName: e.target.checked })
                                            }
                                        />
                                        <span>Sử dụng</span>
                                    </label>
                                </div>
                                <input
                                    type="text"
                                    className="input"
                                    placeholder="replacement_text"
                                    value={renamePattern.replaceKeyword}
                                    disabled={!renamePattern.includeOriginalName}
                                    onChange={(e) =>
                                        setRenamePattern({ replaceKeyword: e.target.value })
                                    }
                                />
                            </div>

                            {/* Số thứ tự section */}
                            <div className="col-span-2">
                                <div className="flex items-center justify-between mb-2">
                                    <label className="input-label">Số thứ tự (Index)</label>
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <input
                                            type="checkbox"
                                            checked={renamePattern.useIndex}
                                            onChange={(e) =>
                                                setRenamePattern({ useIndex: e.target.checked })
                                            }
                                        />
                                        <span>Sử dụng số thứ tự</span>
                                    </label>
                                </div>
                            </div>

                            {renamePattern.useIndex && (
                                <>
                                    <div>
                                        <label className="input-label">Bắt đầu từ số</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={renamePattern.indexStart}
                                            onChange={(e) =>
                                                setRenamePattern({
                                                    indexStart: parseInt(e.target.value),
                                                })
                                            }
                                        />
                                    </div>
                                    <div>
                                        <label className="input-label">Độ dài số (padding)</label>
                                        <input
                                            type="number"
                                            className="input"
                                            value={renamePattern.indexPadding}
                                            onChange={(e) =>
                                                setRenamePattern({
                                                    indexPadding: parseInt(e.target.value),
                                                })
                                            }
                                        />
                                    </div>
                                </>
                            )}

                            {/* Extension checkbox */}
                            <div className="col-span-2">
                                <div className="flex items-center justify-between mb-2">
                                    <label className="input-label">Phần mở rộng (Extension)</label>
                                    <label className="flex items-center gap-2 cursor-pointer text-sm">
                                        <input
                                            type="checkbox"
                                            checked={renamePattern.includeExtension}
                                            onChange={(e) =>
                                                setRenamePattern({ includeExtension: e.target.checked })
                                            }
                                        />
                                        <span>Giữ phần mở rộng file</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    )}
                    <div className="flex gap-2 mt-4">
                        <button
                            className="btn btn-accent"
                            onClick={handleGeneratePreview}
                            disabled={isLoading || selectedFiles.length === 0}
                        >
                            {isLoading ? (
                                <div className="spinner" />
                            ) : (
                                <>
                                    <Edit3 size={18} />
                                    Xem Trước ({selectedFiles.length} files)
                                </>
                            )}
                        </button>
                        <button
                            className="btn btn-secondary"
                            onClick={clearSelection}
                            disabled={selectedFiles.length === 0}
                        >
                            Bỏ Chọn Tất Cả
                        </button>
                    </div>
                </div>
            )}

            {/* Search & Sort Controls */}
            {currentDirectory && (
                <div className="glass-card search-sort-container mb-6">
                    <h3 className="mb-4 flex items-center gap-2">
                        <Search size={20} />
                        Tìm Kiếm & Sắp Xếp
                    </h3>
                    <div className="flex gap-3">
                        {/* Search Input */}
                        <div className="flex-1 relative">
                            <input
                                type="text"
                                className="input pr-10"
                                placeholder="Nhập từ khóa (phân cách bằng dấu phẩy)"
                                value={searchKeywords}
                                onChange={(e) => setSearchKeywords(e.target.value)}
                            />
                            {searchKeywords && (
                                <button
                                    className="absolute right-2 top-1/2 -translate-y-1/2 text-secondary hover:text-accent-pink transition-colors"
                                    onClick={() => setSearchKeywords('')}
                                    title="Xóa bộ lọc"
                                >
                                    <X size={18} />
                                </button>
                            )}
                        </div>

                        {/* Sort Dropdown */}
                        <div className="relative">
                            <button
                                className="btn btn-secondary sort-button flex items-center gap-2 min-w-[200px] justify-between"
                                onClick={() => setShowSortMenu(!showSortMenu)}
                            >
                                <div className="flex items-center gap-2">
                                    <ArrowUpDown size={18} />
                                    <span>{getSortLabel(sortBy, sortOrder)}</span>
                                </div>
                                <ChevronDown size={16} />
                            </button>

                            {showSortMenu && (
                                <div className="sort-dropdown">
                                    <div className="sort-section">
                                        <div className="sort-section-title">Tên</div>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('name', 'asc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            A → Z
                                        </button>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('name', 'desc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            Z → A
                                        </button>
                                    </div>
                                    <div className="sort-section">
                                        <div className="sort-section-title">Ngày sửa</div>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('date', 'desc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            Mới nhất
                                        </button>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('date', 'asc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            Cũ nhất
                                        </button>
                                    </div>
                                    <div className="sort-section">
                                        <div className="sort-section-title">Kích thước</div>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('size', 'desc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            Lớn nhất
                                        </button>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('size', 'asc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            Nhỏ nhất
                                        </button>
                                    </div>
                                    <div className="sort-section">
                                        <div className="sort-section-title">Loại</div>
                                        <button
                                            className="sort-option"
                                            onClick={() => {
                                                setSortBy('type', 'asc');
                                                setShowSortMenu(false);
                                            }}
                                        >
                                            A → Z
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* File List */}
            {currentDirectory && files.length > 0 && (
                <div className="glass-card">
                    <div className="flex items-center justify-between mb-4">
                        <h3>
                            {getFilteredSortedFiles().length} / {files.length} files
                        </h3>
                        <button className="btn btn-secondary" onClick={selectAll}>
                            Chọn Tất Cả
                        </button>
                    </div>
                    <div className="file-list">
                        {getFilteredSortedFiles().map((file) => (
                            <div
                                key={file.path}
                                className={`file-item ${selectedFiles.includes(file.path) ? 'selected' : ''
                                    }`}
                                onClick={() => toggleFileSelection(file.path)}
                            >
                                <div className="flex items-center gap-3 flex-1">
                                    {file.type === 'directory' ? (
                                        <Folder className="text-accent-blue" size={20} />
                                    ) : (
                                        <File className="text-accent-purple" size={20} />
                                    )}
                                    <div>
                                        <div className="file-name">{file.name}</div>
                                        {file.type === 'file' && (
                                            <div className="file-size text-sm text-secondary">
                                                {formatSize(file.size)}
                                            </div>
                                        )}
                                    </div>
                                </div>
                                {selectedFiles.includes(file.path) && (
                                    <CheckCircle2
                                        className="text-accent-green"
                                        size={20}
                                    />
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Empty State */}
            {currentDirectory && files.length === 0 && !isLoading && (
                <div className="glass-card">
                    <div className="empty-state">
                        <Folder size={48} className="text-secondary" />
                        <h3>Không tìm thấy file nào</h3>
                        <p className="text-secondary">
                            {error || 'Thư mục này đang trống hoặc chỉ chứa thư mục con'}
                        </p>
                        <button className="btn btn-secondary" onClick={() => loadDirectory(currentDirectory!)}>
                            <RefreshCw size={18} />
                            Tải lại
                        </button>
                    </div>
                </div>
            )}

            {/* Error State */}
            {error && files.length > 0 && (
                <div className="glass-card mb-6">
                    <div className="error-banner">
                        <XCircle size={20} />
                        <span>{error}</span>
                    </div>
                </div>
            )}

            {/* Preview Modal */}
            {showPreview && (
                <div className="modal-overlay" onClick={() => setShowPreview(false)}>
                    <div className="modal-content preview-modal" onClick={(e) => e.stopPropagation()}>
                        <h2 className="mb-4">Xem Trước Kết Quả Đổi Tên</h2>
                        <p className="text-secondary text-sm mb-4">
                            <GripVertical size={14} className="inline-block mr-1" />
                            Kéo thả để sắp xếp lại thứ tự file
                        </p>
                        <div className="preview-list">
                            {previewOrder.map((filePath, index) => {
                                const newName = previewMap.get(filePath);
                                if (!newName) return null;

                                const isDragging = draggedIndex === index;
                                const isDragOver = dragOverIndex === index;

                                return (
                                    <div
                                        key={filePath}
                                        className={`preview-item draggable ${isDragging ? 'dragging' : ''} ${isDragOver ? 'drag-over' : ''}`}
                                        draggable
                                        onDragStart={() => handleDragStart(index)}
                                        onDragOver={(e) => handleDragOver(e, index)}
                                        onDragLeave={handleDragLeave}
                                        onDrop={(e) => handleDrop(e, index)}
                                        onDragEnd={handleDragEnd}
                                    >
                                        <div className="drag-handle">
                                            <GripVertical size={16} className="text-secondary" />
                                        </div>
                                        <div className="preview-item-content">
                                            <div className="preview-index">{index + 1}</div>
                                            <div className="preview-names">
                                                <div className="flex items-center gap-2">
                                                    <XCircle className="text-accent-pink" size={14} />
                                                    <span className="text-secondary line-through text-sm">
                                                        {filePath.split('\\').pop()}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <CheckCircle2 className="text-accent-green" size={14} />
                                                    <span className="font-semibold">
                                                        {newName.split('\\').pop()}
                                                    </span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                        <div className="flex gap-2 mt-6">
                            <button
                                className="btn btn-success flex-1"
                                onClick={handleExecuteRename}
                                disabled={isRenaming}
                            >
                                {isRenaming ? (
                                    <div className="spinner" />
                                ) : (
                                    <>
                                        <CheckCircle2 size={18} />
                                        Xác Nhận Đổi Tên
                                    </>
                                )}
                            </button>
                            <button
                                className="btn btn-secondary"
                                onClick={() => setShowPreview(false)}
                            >
                                Hủy
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <style>{`
        .manager-header {
          margin-bottom: 2rem;
        }

        .manager-header h2 {
          font-size: 1.75rem;
          margin-bottom: 0.5rem;
        }

        .input-label {
          display: block;
          margin-bottom: 0.5rem;
          font-size: 0.875rem;
          font-weight: 600;
          color: var(--text-secondary);
        }

        .grid {
          display: grid;
        }

        .grid-cols-2 {
          grid-template-columns: repeat(2, 1fr);
        }

        .mode-toggle-container {
          display: flex;
          gap: 0.5rem;
          background: var(--bg-tertiary);
          padding: 0.25rem;
          border-radius: var(--radius-md);
        }

        .mode-toggle-btn {
          flex: 1;
          padding: 0.75rem 1.5rem;
          background: transparent;
          border: none;
          border-radius: var(--radius-sm);
          color: var(--text-secondary);
          font-weight: 500;
          cursor: pointer;
          transition: all var(--transition-base);
        }

        .mode-toggle-btn:hover {
          background: rgba(255, 255, 255, 0.05);
          color: var(--text-primary);
        }

        .mode-toggle-btn.active {
          background: var(--accent-purple);
          color: white;
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }

        textarea.input {
          resize: vertical;
          min-height: 100px;
          font-family: inherit;
        }

        .file-list {
          max-height: 400px;
          overflow-y: auto;
          border: 1px solid var(--border-color);
          border-radius: var(--radius-md);
        }

        .file-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0.75rem 1rem;
          border-bottom: 1px solid var(--border-color);
          cursor: pointer;
          transition: all var(--transition-base);
        }

        .file-item:last-child {
          border-bottom: none;
        }

        .file-item:hover {
          background: rgba(255, 255, 255, 0.03);
        }

        .file-item.selected {
          background: rgba(102, 126, 234, 0.1);
          border-left: 3px solid var(--accent-purple);
        }

        .file-name {
          font-weight: 500;
        }

        .file-size {
          margin-top: 0.25rem;
        }

        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.8);
          backdrop-filter: blur(10px);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          animation: fadeIn var(--transition-base);
        }

        .modal-content {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-lg);
          padding: 2rem;
          max-width: 600px;
          width: 90%;
          max-height: 80vh;
          overflow-y: auto;
          animation: scaleIn var(--transition-slow);
        }

        .preview-list {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
          max-height: 400px;
          overflow-y: auto;
          padding: 1rem;
          background: var(--bg-tertiary);
          border-radius: var(--radius-md);
        }

        .preview-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.75rem;
          background: var(--bg-secondary);
          border-radius: var(--radius-sm);
          border: 1px solid transparent;
          transition: all var(--transition-base);
        }

        .preview-item.draggable {
          cursor: grab;
        }

        .preview-item.draggable:active {
          cursor: grabbing;
        }

        .preview-item.dragging {
          opacity: 0.5;
          background: var(--bg-tertiary);
          border: 1px dashed var(--accent-purple);
        }

        .preview-item.drag-over {
          border: 2px solid var(--accent-purple);
          background: rgba(102, 126, 234, 0.1);
          transform: scale(1.02);
        }

        .drag-handle {
          display: flex;
          align-items: center;
          padding: 0.25rem;
          cursor: grab;
          opacity: 0.5;
          transition: opacity var(--transition-base);
        }

        .preview-item:hover .drag-handle {
          opacity: 1;
        }

        .preview-item-content {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex: 1;
        }

        .preview-index {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          background: var(--accent-purple);
          color: white;
          font-size: 0.75rem;
          font-weight: 600;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .preview-names {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
          flex: 1;
          min-width: 0;
        }

        .preview-names span {
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .preview-modal {
          max-width: 700px;
        }

        .line-through {
          text-decoration: line-through;
        }

        .search-sort-container {
          overflow: visible !important;
          position: relative;
          z-index: 50;
        }

        .sort-dropdown {
          position: absolute;
          top: calc(100% + 0.5rem);
          right: 0;
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: var(--radius-md);
          padding: 0.5rem;
          min-width: 200px;
          z-index: 1000;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
          backdrop-filter: blur(10px);
          animation: fadeIn var(--transition-base);
        }

        .sort-section {
          padding: 0.5rem 0;
          border-bottom: 1px solid var(--border-color);
        }

        .sort-section:last-child {
          border-bottom: none;
        }

        .sort-section-title {
          font-size: 0.75rem;
          font-weight: 600;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          padding: 0.25rem 0.75rem;
          margin-bottom: 0.25rem;
        }

        .sort-option {
          width: 100%;
          text-align: left;
          padding: 0.5rem 0.75rem;
          background: transparent;
          border: none;
          color: var(--text-primary);
          cursor: pointer;
          transition: all var(--transition-base);
          border-radius: var(--radius-sm);
          font-size: 0.875rem;
        }

        .sort-option:hover {
          background: rgba(102, 126, 234, 0.1);
          color: var(--accent-purple);
          transform: translateX(4px);
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes scaleIn {
          from {
            opacity: 0;
            transform: scale(0.95);
          }
          to {
            opacity: 1;
            transform: scale(1);
          }
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          padding: 4rem 2rem;
          text-align: center;
          gap: 1rem;
        }

        .empty-state h3 {
          margin: 0.5rem 0;
          font-size: 1.25rem;
        }

        .empty-state p {
          margin: 0.5rem 0 1.5rem;
          max-width: 400px;
        }

        .error-banner {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem;
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid rgba(239, 68, 68, 0.3);
          border-radius: var(--radius-md);
          color: #ef4444;
        }
      `}</style>
        </div>
    );
}

function formatSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 * 1024 * 1024)
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}
