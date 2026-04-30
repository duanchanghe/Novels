'use client';

import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { 
  X, 
  Upload, 
  FileText, 
  CheckCircle, 
  AlertCircle,
  Loader2
} from 'lucide-react';
import { api } from '@/lib/api';
import { useUIStore } from '@/lib/stores';

export default function UploadModal() {
  const router = useRouter();
  const { uploadModalOpen, setUploadModalOpen } = useUIStore();
  const [file, setFile] = useState<File | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async (file: File) => {
      return api.uploadEpub(file, (progress) => {
        setUploadProgress(progress);
      });
    },
    onSuccess: (data) => {
      setUploadProgress(100);
      setTimeout(() => {
        setUploadModalOpen(false);
        setFile(null);
        setUploadProgress(0);
        router.push(`/books/${data.book_id}`);
      }, 1000);
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      if (!selectedFile.name.toLowerCase().endsWith('.epub')) {
        setError('请选择 EPUB 格式的文件');
        return;
      }
      if (selectedFile.size > 500 * 1024 * 1024) {
        setError('文件大小不能超过 500MB');
        return;
      }
      setFile(selectedFile);
      setError(null);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0];
    if (droppedFile) {
      if (!droppedFile.name.toLowerCase().endsWith('.epub')) {
        setError('请拖放 EPUB 格式的文件');
        return;
      }
      setFile(droppedFile);
      setError(null);
    }
  }, []);

  const handleUpload = useCallback(() => {
    if (file) {
      uploadMutation.mutate(file);
    }
  }, [file, uploadMutation]);

  const handleClose = useCallback(() => {
    if (!uploadMutation.isPending) {
      setUploadModalOpen(false);
      setFile(null);
      setUploadProgress(0);
      setError(null);
    }
  }, [uploadMutation.isPending, setUploadModalOpen]);

  if (!uploadModalOpen) return null;

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* 背景遮罩 */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm transition-opacity"
        onClick={handleClose}
      />

      {/* 模态框 */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-xl w-full max-w-lg transform transition-all">
          {/* 头部 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              上传 EPUB
            </h2>
            <button
              onClick={handleClose}
              disabled={uploadMutation.isPending}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 内容 */}
          <div className="p-6">
            {uploadMutation.isPending && uploadProgress === 100 ? (
              <div className="text-center py-8">
                <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  上传成功！
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  正在跳转到书籍详情...
                </p>
              </div>
            ) : uploadMutation.isPending ? (
              <div className="text-center py-8">
                <Loader2 className="w-16 h-16 text-primary mx-auto mb-4 animate-spin" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                  上传中...
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-4">
                  {uploadProgress}%
                </p>
                <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-gradient-to-r from-primary to-accent transition-all duration-300"
                    style={{ width: `${uploadProgress}%` }}
                  />
                </div>
              </div>
            ) : (
              <>
                {/* 拖放区域 */}
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={handleDrop}
                  className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
                    error
                      ? 'border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
                      : file
                        ? 'border-green-300 bg-green-50 dark:border-green-800 dark:bg-green-900/20'
                        : 'border-gray-300 dark:border-gray-600 hover:border-primary'
                  }`}
                >
                  <input
                    type="file"
                    accept=".epub"
                    onChange={handleFileSelect}
                    className="hidden"
                    id="epub-upload"
                  />

                  {file ? (
                    <div className="flex flex-col items-center">
                      <FileText className="w-12 h-12 text-green-500 mb-3" />
                      <p className="font-medium text-gray-900 dark:text-white mb-1">
                        {file.name}
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-3">
                        {formatFileSize(file.size)}
                      </p>
                      <button
                        onClick={() => setFile(null)}
                        className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                      >
                        重新选择
                      </button>
                    </div>
                  ) : (
                    <>
                      <Upload className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                      <p className="font-medium text-gray-900 dark:text-white mb-1">
                        拖放 EPUB 文件到此处
                      </p>
                      <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
                        或点击选择文件
                      </p>
                      <label
                        htmlFor="epub-upload"
                        className="btn-primary cursor-pointer"
                      >
                        选择文件
                      </label>
                    </>
                  )}
                </div>

                {/* 错误提示 */}
                {error && (
                  <div className="mt-4 flex items-center gap-2 text-red-600 dark:text-red-400">
                    <AlertCircle className="w-5 h-5" />
                    <span className="text-sm">{error}</span>
                  </div>
                )}

                {/* 文件大小限制提示 */}
                <p className="mt-4 text-xs text-gray-500 dark:text-gray-400 text-center">
                  支持 EPUB 格式，单个文件最大 500MB
                </p>
              </>
            )}
          </div>

          {/* 底部操作 */}
          {!uploadMutation.isPending && uploadProgress !== 100 && (
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={handleClose}
                className="btn-outline"
              >
                取消
              </button>
              <button
                onClick={handleUpload}
                disabled={!file}
                className="btn-primary disabled:opacity-50"
              >
                {uploadMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                    上传中...
                  </>
                ) : (
                  '开始上传'
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
