'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  ArrowLeft,
  Plus,
  Loader2,
  AlertCircle,
  CheckCircle,
  Globe,
  Bell,
  Zap,
  Shield
} from 'lucide-react';
import { api } from '@/lib/api';

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [showAddChannel, setShowAddChannel] = useState(false);

  // 获取发布渠道
  const { data: channelsData, isLoading: channelsLoading } = useQuery({
    queryKey: ['channels'],
    queryFn: () => api.getChannels(),
  });

  // 创建渠道
  const createChannelMutation = useMutation({
    mutationFn: (data: any) => api.createChannel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setShowAddChannel(false);
    },
  });

  // 删除渠道
  const deleteChannelMutation = useMutation({
    mutationFn: (channelId: number) => api.deleteChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
    },
  });

  const channels = channelsData || [];

  const getPlatformIcon = (platformType: string) => {
    switch (platformType) {
      case 'self_hosted':
        return <Globe className="w-5 h-5" />;
      case 'ximalaya':
        return <Zap className="w-5 h-5" />;
      default:
        return <Globe className="w-5 h-5" />;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 顶部导航 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-4 h-16">
            <Link
              href="/"
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div>
              <h1 className="font-semibold text-gray-900 dark:text-white">
                设置
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                管理发布渠道和系统配置
              </p>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 发布渠道 */}
        <section className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Globe className="w-5 h-5" />
                发布渠道
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                配置有声书自动发布的目标平台
              </p>
            </div>
            <button
              onClick={() => setShowAddChannel(true)}
              className="btn-primary flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              添加渠道
            </button>
          </div>

          {channelsLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="w-8 h-8 text-primary animate-spin" />
            </div>
          ) : channels.length === 0 ? (
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-8 text-center">
              <Globe className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
                暂无发布渠道
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-6">
                添加发布渠道以实现有声书自动分发
              </p>
              <button
                onClick={() => setShowAddChannel(true)}
                className="btn-primary"
              >
                <Plus className="w-4 h-4 mr-2" />
                添加渠道
              </button>
            </div>
          ) : (
            <div className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-sm">
              <div className="divide-y divide-gray-200 dark:divide-gray-700">
                {channels.map((channel: any) => (
                  <div key={channel.id} className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
                          {getPlatformIcon(channel.platform_type)}
                        </div>
                        <div>
                          <h3 className="font-medium text-gray-900 dark:text-white">
                            {channel.name}
                          </h3>
                          <p className="text-sm text-gray-500 dark:text-gray-400">
                            {channel.platform_type === 'self_hosted' ? '自建平台' : channel.platform_type}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        {channel.auto_publish ? (
                          <span className="badge badge-success flex items-center gap-1">
                            <CheckCircle className="w-3 h-3" />
                            自动发布
                          </span>
                        ) : (
                          <span className="badge badge-info flex items-center gap-1">
                            手动发布
                          </span>
                        )}

                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          成功 {channel.success_count || 0} / {channel.total_published || 0}
                        </div>

                        <button
                          onClick={() => deleteChannelMutation.mutate(channel.id)}
                          className="text-red-500 hover:text-red-600 text-sm"
                        >
                          删除
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* 系统设置 */}
        <section>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center gap-2 mb-6">
            <Shield className="w-5 h-5" />
            系统设置
          </h2>

          <div className="bg-white dark:bg-gray-800 rounded-2xl overflow-hidden shadow-sm">
            {/* 通知设置 */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-blue-100 dark:bg-blue-900/30 rounded-lg flex items-center justify-center text-blue-600 dark:text-blue-400">
                    <Bell className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      任务完成通知
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      有声书生成完成后发送通知
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 dark:peer-focus:ring-primary/40 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>

            {/* 失败通知 */}
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center text-red-600 dark:text-red-400">
                    <AlertCircle className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      失败告警通知
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      生成失败时发送告警通知
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" defaultChecked />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 dark:peer-focus:ring-primary/40 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>

            {/* 自动发布 */}
            <div className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 bg-green-100 dark:bg-green-900/30 rounded-lg flex items-center justify-center text-green-600 dark:text-green-400">
                    <Zap className="w-5 h-5" />
                  </div>
                  <div>
                    <h3 className="font-medium text-gray-900 dark:text-white">
                      生成完成后自动发布
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      自动将生成完成的有声书发布到已配置的渠道
                    </p>
                  </div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary/20 dark:peer-focus:ring-primary/40 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full rtl:peer-checked:after:-translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:start-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary"></div>
                </label>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
