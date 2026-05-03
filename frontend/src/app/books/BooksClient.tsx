'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  Plus, 
  Search, 
  Filter, 
  MoreVertical, 
  Trash2, 
  RefreshCw,
  Play,
  Zap,
  Download,
  Eye,
  ChevronLeft,
  ChevronRight,
  Loader2,
  BookOpen,
  Clock,
  CheckCircle,
  AlertCircle
} from 'lucide-react';
import { api } from '@/lib/api';
import { useBookStore, useUIStore } from '@/lib/stores';
import type { Book } from '@/types';

interface BooksClientProps {
  initialBooks: Book[];
  initialTotal: number;
}

export default function BooksClient({ initialBooks, initialTotal }: BooksClientProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 20;

  const queryClient = useQueryClient();
  const { setBooks, setCurrentBook } = useBookStore();
  const { setUploadModalOpen } = useUIStore();

  // 获取书籍列表（使用初始数据作为 fallback）
  const { data, isLoading, error } = useQuery({
    queryKey: ['books', currentPage, pageSize, statusFilter, searchQuery],
    queryFn: () => api.getBooks({
      page: currentPage,
      page_size: pageSize,
      status: statusFilter || undefined,
      search: searchQuery || undefined,
    }),
    initialData: initialTotal > 0 ? { 
      total: initialTotal, 
      page: 1, 
      page_size: pageSize, 
      items: initialBooks 
    } : undefined,
  });

  // 删除书籍
  const deleteMutation = useMutation({
    mutationFn: (bookId: number) => api.deleteBook(bookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] });
    },
  });

  // 触发生成
  const generateMutation = useMutation({
    mutationFn: (bookId: number) => api.triggerGeneration(bookId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['books'] });
    },
  });

  const booksList = data?.items || [];
  const totalPages = Math.ceil((data?.total || 0) / pageSize);

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
      pending: { color: 'badge-info', icon: <Clock className="w-3 h-3" /> },
      analyzing: { color: 'badge-warning', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
      synthesizing: { color: 'badge-warning', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
      post_processing: { color: 'badge-warning', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
      publishing: { color: 'badge-warning', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
      done: { color: 'badge-success', icon: <CheckCircle className="w-3 h-3" /> },
      failed: { color: 'badge-error', icon: <AlertCircle className="w-3 h-3" /> },
    };

    const config = statusConfig[status] || statusConfig.pending;

    return (
      <span className={`badge ${config.color} flex items-center gap-1`}>
        {config.icon}
        {status === 'done' ? '已完成' : 
         status === 'failed' ? '失败' :
         status === 'pending' ? '等待中' :
         status === 'analyzing' ? '分析中' :
         status === 'synthesizing' ? '合成中' :
         status === 'post_processing' ? '后处理' : '发布中'}
      </span>
    );
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 顶部导航 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2">
                <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-white" />
                </div>
                <span className="font-semibold text-gray-900 dark:text-white">AI 有声书工坊</span>
              </Link>
            </div>
            <button
              onClick={() => setUploadModalOpen(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              上传 EPUB
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 页面标题 */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">我的书架</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">管理您的有声书收藏</p>
          </div>
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <BookOpen className="w-4 h-4" />
            <span>共 {data?.total || 0} 本</span>
          </div>
        </div>

        {/* 搜索和筛选 */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="搜索书名或作者..."
              className="input pl-10"
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1);
              }}
            />
          </div>
          <div className="flex gap-2">
            <select
              className="input w-auto"
              value={statusFilter || ''}
              onChange={(e) => {
                setStatusFilter(e.target.value || null);
                setCurrentPage(1);
              }}
            >
              <option value="">全部状态</option>
              <option value="pending">等待中</option>
              <option value="analyzing">分析中</option>
              <option value="synthesizing">合成中</option>
              <option value="done">已完成</option>
              <option value="failed">失败</option>
            </select>
            <button
              onClick={() => queryClient.invalidateQueries({ queryKey: ['books'] })}
              className="btn-outline p-2"
              title="刷新"
            >
              <RefreshCw className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 书籍列表 */}
        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : error ? (
          <div className="text-center py-20">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <p className="text-gray-500 dark:text-gray-400">加载失败，请稍后重试</p>
          </div>
        ) : booksList.length === 0 ? (
          <div className="text-center py-20 bg-white dark:bg-gray-800 rounded-2xl">
            <BookOpen className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              还没有书籍
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              上传您的第一本 EPUB 电子书开始转换
            </p>
            <button
              onClick={() => setUploadModalOpen(true)}
              className="btn-primary"
            >
              <Plus className="w-4 h-4 mr-2" />
              上传 EPUB
            </button>
          </div>
        ) : (
          <>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {booksList.map((book: Book) => (
                <div
                  key={book.id}
                  className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-shadow"
                >
                  {/* 封面 */}
                  <div className="relative h-48 bg-gradient-to-br from-primary/20 to-accent/20 flex items-center justify-center">
                    {book.cover_image_url ? (
                      <img
                        src={book.cover_image_url}
                        alt={book.title}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <BookOpen className="w-16 h-16 text-gray-300 dark:text-gray-600" />
                    )}

                    {/* 状态徽章 */}
                    <div className="absolute top-3 right-3">
                      {getStatusBadge(book.status)}
                    </div>

                    {/* 进度条 */}
                    {book.status !== 'pending' && book.status !== 'done' && (
                      <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200">
                        <div
                          className="h-full bg-primary transition-all"
                          style={{ width: `${book.progress_percentage}%` }}
                        />
                      </div>
                    )}
                  </div>

                  {/* 内容 */}
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 dark:text-white truncate mb-1">
                      {book.title}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400 truncate mb-3">
                      {book.author || '未知作者'}
                    </p>

                    <div className="flex items-center justify-between text-xs text-gray-400 dark:text-gray-500 mb-4">
                      <span>{book.total_chapters} 章</span>
                      <span>{formatFileSize(book.file_size)}</span>
                      <span>{formatDate(book.created_at)}</span>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex gap-2">
                      <Link
                        href={`/books/${book.id}`}
                        className="btn-outline flex-1 flex items-center justify-center gap-1 text-sm py-2"
                      >
                        <Eye className="w-4 h-4" />
                        查看
                      </Link>
                      {book.status === 'done' ? (
                        <Link
                          href={`/books/${book.id}`}
                          className="btn-primary flex-1 flex items-center justify-center gap-1 text-sm py-2"
                        >
                          <Play className="w-4 h-4" />
                          播放
                        </Link>
                      ) : book.status === 'pending' || book.status === 'failed' ? (
                        <button
                          onClick={() => generateMutation.mutate(book.id)}
                          disabled={generateMutation.isPending}
                          className="btn-primary flex-1 flex items-center justify-center gap-1 text-sm py-2"
                        >
                          <Zap className="w-4 h-4" />
                          生成
                        </button>
                      ) : (
                        <button
                          disabled
                          className="btn-outline flex-1 flex items-center justify-center gap-1 text-sm py-2 opacity-50"
                        >
                          <Loader2 className="w-4 h-4 animate-spin" />
                          生成中
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* 分页 */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-2 mt-8">
                <button
                  onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                  disabled={currentPage === 1}
                  className="btn-outline p-2"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  第 {currentPage} / {totalPages} 页
                </span>
                <button
                  onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                  disabled={currentPage === totalPages}
                  className="btn-outline p-2"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
