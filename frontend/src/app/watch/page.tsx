'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  ArrowLeft,
  RefreshCw,
  Play,
  Pause,
  AlertTriangle,
  CheckCircle,
  Clock,
  HardDrive,
  Activity,
  Loader2,
  Eye
} from 'lucide-react';
import { api } from '@/lib/api';

export default function WatchStatusPage() {
  const queryClient = useQueryClient();
  const [autoRefresh, setAutoRefresh] = useState(true);

  // 获取监听状态
  const { data: watchStatus, isLoading: statusLoading, error: statusError } = useQuery({
    queryKey: ['watch-status'],
    queryFn: () => api.getWatchStatus(),
    refetchInterval: autoRefresh ? 30000 : false,
  });

  // 重启监听服务
  const restartMutation = useMutation({
    mutationFn: () => api.restartWatcher(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watch-status'] });
    },
  });

  const getStatusColor = (running: boolean) => {
    return running 
      ? 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
      : 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400';
  };

  const getStatusIcon = (running: boolean) => {
    return running 
      ? <CheckCircle className="w-5 h-5" />
      : <AlertTriangle className="w-5 h-5" />;
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
                  监听状态
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  监控文件夹自动监听服务
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
                onClick={() => queryClient.invalidateQueries({ queryKey: ['watch-status'] })}
                className="btn-outline flex items-center gap-2"
              >
                <RefreshCw className={`w-4 h-4 ${statusLoading ? 'animate-spin' : ''}`} />
                刷新
              </button>

              <button
                onClick={() => restartMutation.mutate()}
                disabled={restartMutation.isPending}
                className="btn-primary flex items-center gap-2"
              >
                {restartMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <RefreshCw className="w-4 h-4" />
                )}
                重启服务
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {statusLoading && !watchStatus ? (
          <div className="flex justify-center items-center py-20">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
          </div>
        ) : statusError ? (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-2xl p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-red-900 dark:text-red-200 mb-2">
              无法获取监听状态
            </h3>
            <p className="text-red-700 dark:text-red-300">
              请检查服务是否正常运行
            </p>
          </div>
        ) : (
          <>
            {/* 状态概览 */}
            <div className="grid md:grid-cols-4 gap-6 mb-8">
              {/* 运行状态 */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl ${getStatusColor(watchStatus?.running)}`}>
                    {getStatusIcon(watchStatus?.running)}
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">服务状态</p>
                    <p className="text-xl font-semibold text-gray-900 dark:text-white">
                      {watchStatus?.running ? '运行中' : '已停止'}
                    </p>
                  </div>
                </div>
              </div>

              {/* 处理统计 */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400">
                    <Activity className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">总处理</p>
                    <p className="text-xl font-semibold text-gray-900 dark:text-white">
                      {watchStatus?.total_processed || 0}
                    </p>
                  </div>
                </div>
              </div>

              {/* 队列状态 */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-xl bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
                    <Clock className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">空闲队列</p>
                    <p className="text-xl font-semibold text-gray-900 dark:text-white">
                      {watchStatus?.queue_available || 0} / 3
                    </p>
                  </div>
                </div>
              </div>

              {/* 失败统计 */}
              <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
                <div className="flex items-center gap-4">
                  <div className={`p-3 rounded-xl ${
                    (watchStatus?.total_failed || 0) > 0
                      ? 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
                      : 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400'
                  }`}>
                    <AlertTriangle className="w-5 h-5" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400">失败任务</p>
                    <p className="text-xl font-semibold text-gray-900 dark:text-white">
                      {watchStatus?.total_failed || 0}
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* 监听目录 */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <HardDrive className="w-5 h-5" />
                  监听目录
                </h2>
              </div>
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {watchStatus?.watch_dirs?.map((dir: string, index: number) => (
                  <div key={index} className="px-6 py-4">
                    <code className="text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-900 px-3 py-1 rounded">
                      {dir}
                    </code>
                  </div>
                )) || (
                  <div className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                    暂无监听目录
                  </div>
                )}
              </div>
            </div>

            {/* 详细统计 */}
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  统计信息
                </h2>
              </div>
              <div className="p-6">
                <div className="grid md:grid-cols-3 gap-6">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">检测文件数</p>
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {watchStatus?.total_detected || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">处理成功</p>
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {watchStatus?.total_processed || 0}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">处理失败</p>
                    <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                      {watchStatus?.total_failed || 0}
                    </p>
                  </div>
                </div>

                {watchStatus?.last_processed && (
                  <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      最后处理时间：{new Date(watchStatus.last_processed).toLocaleString('zh-CN')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
