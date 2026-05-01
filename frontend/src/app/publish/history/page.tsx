'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft,
  RefreshCw,
  Globe,
  CheckCircle,
  AlertCircle,
  Clock,
  Loader2,
  ExternalLink,
  Eye
} from 'lucide-react';
import { api } from '@/lib/api';

interface PublishRecord {
  id: number;
  book_id: number;
  channel_id: number;
  channel_name?: string;
  external_album_id: string | null;
  external_album_url: string | null;
  status: string;
  published_chapters: number;
  total_chapters: number;
  chapters_published: Record<string, string>;
  published_at: string | null;
  error_message: string | null;
  retry_count: number;
  created_at: string;
}

export default function PublishHistoryPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 获取发布记录列表
  const { data: recordsData, isLoading, error, refetch } = useQuery({
    queryKey: ['publish-records'],
    queryFn: () => api.getPublishRecords(),
    refetchInterval: autoRefresh ? 60000 : false,
  });

  const records = recordsData?.items || [];

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      pending: { 
        color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300', 
        icon: <Clock className="w-3 h-3" />,
        label: '等待中'
      },
      preparing: { 
        color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400', 
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
        label: '准备中'
      },
      publishing: { 
        color: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400', 
        icon: <Loader2 className="w-3 h-3 animate-spin" />,
        label: '发布中'
      },
      partial_done: { 
        color: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400', 
        icon: <AlertCircle className="w-3 h-3" />,
        label: '部分成功'
      },
      done: { 
        color: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400', 
        icon: <CheckCircle className="w-3 h-3" />,
        label: '已完成'
      },
      failed: { 
        color: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400', 
        icon: <AlertCircle className="w-3 h-3" />,
        label: '失败'
      },
      cancelled: { 
        color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300', 
        icon: <Clock className="w-3 h-3" />,
        label: '已取消'
      },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <span className={`badge flex items-center gap-1 ${config.color}`}>
        {config.icon}
        {config.label}
      </span>
    );
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 顶部导航 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="font-semibold text-gray-900 dark:text-white">
                  发布历史
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  查看有声书发布记录
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
                <input
                  type="checkbox"
                  checked={autoRefresh}
                  onChange={(e) => setAutoRefresh(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                自动刷新
              </label>

              <button
                onClick={() => refetch()}
                className="btn-outline flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                刷新
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {isLoading && records.length === 0 ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6 text-center">
            <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-red-900 dark:text-red-200 mb-2">
              加载失败
            </h3>
            <p className="text-red-700 dark:text-red-300">
              {(error as Error).message}
            </p>
          </div>
        ) : records.length === 0 ? (
          <div className="bg-white dark:bg-gray-800 rounded-2xl p-12 text-center">
            <Globe className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
              暂无发布记录
            </h3>
            <p className="text-gray-500 dark:text-gray-400 mb-6">
              当您发布有声书后，记录将显示在这里
            </p>
            <Link
              href="/books"
              className="btn-primary"
            >
              查看我的书架
            </Link>
          </div>
        ) : (
          <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      书籍
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      渠道
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      进度
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      发布时间
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <Link 
                          href={`/books/${record.book_id}`}
                          className="text-primary hover:underline"
                        >
                          #{record.book_id}
                        </Link>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Globe className="w-4 h-4 text-gray-400" />
                          <span className="text-gray-900 dark:text-white">
                            {record.channel_name || `渠道 #${record.channel_id}`}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <div className="w-24 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                            <div
                              className="h-full bg-primary"
                              style={{ 
                                width: `${record.total_chapters > 0 
                                  ? (record.published_chapters / record.total_chapters) * 100 
                                  : 0}%` 
                              }}
                            />
                          </div>
                          <span className="text-sm text-gray-500 dark:text-gray-400">
                            {record.published_chapters}/{record.total_chapters}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        {getStatusBadge(record.status)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                        {record.published_at 
                          ? formatDate(record.published_at)
                          : record.created_at
                            ? formatDate(record.created_at)
                            : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <div className="flex items-center gap-2">
                          <Link
                            href={`/books/${record.book_id}`}
                            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400"
                            title="查看书籍"
                          >
                            <Eye className="w-4 h-4" />
                          </Link>
                          {record.external_album_url && (
                            <a
                              href={record.external_album_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400"
                              title="打开链接"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </a>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
