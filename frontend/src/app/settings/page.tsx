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
  Shield,
  X,
  Save,
  ExternalLink,
  Trash2,
  Edit2
} from 'lucide-react';
import { api } from '@/lib/api';

interface Channel {
  id: number;
  name: string;
  platform_type: string;
  description?: string;
  is_enabled: boolean;
  auto_publish: boolean;
  priority: number;
  publish_as_draft: boolean;
  category?: string;
  tags?: string[];
  total_published: number;
  success_count: number;
  failure_count: number;
  last_published_at?: string;
  created_at?: string;
}

const PLATFORM_OPTIONS = [
  { value: 'self_hosted', label: '自建平台', description: '使用 MinIO 预签名 URL 分发，无需外部配置' },
  { value: 'ximalaya', label: '喜马拉雅', description: '喜马拉雅开放平台（需申请开发者权限）' },
  { value: 'qingting', label: '蜻蜓 FM', description: '蜻蜓 FM 开放平台（需申请开发者权限）' },
  { value: 'lizhi', label: '荔枝 FM', description: '荔枝 FM 开放平台（需申请开发者权限）' },
  { value: 'custom', label: '自定义平台', description: '支持自定义 API 配置的发布平台' },
];

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [showAddChannel, setShowAddChannel] = useState(false);
  const [editingChannel, setEditingChannel] = useState<Channel | null>(null);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState<number | null>(null);

  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    platform_type: 'self_hosted',
    description: '',
    api_config: {} as Record<string, string>,
    auto_publish: false,
    publish_as_draft: true,
    category: '',
  });
  const [apiConfigInputs, setApiConfigInputs] = useState<{ key: string; value: string }[]>([
    { key: '', value: '' }
  ]);

  // 获取发布渠道
  const { data: channelsData, isLoading: channelsLoading, error } = useQuery<Channel[]>({
    queryKey: ['channels'],
    queryFn: () => api.getChannels() as Promise<Channel[]>,
  });

  const channels = channelsData || [];

  // 创建渠道
  const createChannelMutation = useMutation({
    mutationFn: (data: any) => api.createChannel(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      closeModal();
    },
    onError: (err: Error) => {
      alert(`创建失败: ${err.message}`);
    },
  });

  // 更新渠道
  const updateChannelMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.updateChannel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      closeModal();
    },
    onError: (err: Error) => {
      alert(`更新失败: ${err.message}`);
    },
  });

  // 删除渠道
  const deleteChannelMutation = useMutation({
    mutationFn: (channelId: number) => api.deleteChannel(channelId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['channels'] });
      setShowDeleteConfirm(null);
    },
    onError: (err: Error) => {
      alert(`删除失败: ${err.message}`);
    },
  });

  const resetForm = () => {
    setFormData({
      name: '',
      platform_type: 'self_hosted',
      description: '',
      api_config: {},
      auto_publish: false,
      publish_as_draft: true,
      category: '',
    });
    setApiConfigInputs([{ key: '', value: '' }]);
    setEditingChannel(null);
  };

  const closeModal = () => {
    setShowAddChannel(false);
    setEditingChannel(null);
    resetForm();
  };

  const openEditModal = (channel: Channel) => {
    setEditingChannel(channel);
    setFormData({
      name: channel.name,
      platform_type: channel.platform_type,
      description: channel.description || '',
      api_config: {},
      auto_publish: channel.auto_publish,
      publish_as_draft: channel.publish_as_draft,
      category: channel.category || '',
    });
    setApiConfigInputs([{ key: '', value: '' }]);
    setShowAddChannel(true);
  };

  const handleSubmit = () => {
    // 构建 API 配置
    const apiConfig: Record<string, string> = {};
    apiConfigInputs.forEach(item => {
      if (item.key && item.value) {
        apiConfig[item.key] = item.value;
      }
    });

    const payload = {
      name: formData.name,
      platform_type: formData.platform_type,
      api_config: apiConfig,
      auto_publish: formData.auto_publish,
    };

    if (editingChannel) {
      updateChannelMutation.mutate({ id: editingChannel.id, data: payload });
    } else {
      createChannelMutation.mutate(payload);
    }
  };

  const addApiConfigInput = () => {
    setApiConfigInputs([...apiConfigInputs, { key: '', value: '' }]);
  };

  const removeApiConfigInput = (index: number) => {
    setApiConfigInputs(apiConfigInputs.filter((_, i) => i !== index));
  };

  const updateApiConfigInput = (index: number, field: 'key' | 'value', value: string) => {
    const updated = [...apiConfigInputs];
    updated[index][field] = value;
    setApiConfigInputs(updated);
  };

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

  const getPlatformName = (platformType: string) => {
    const platform = PLATFORM_OPTIONS.find(p => p.value === platformType);
    return platform?.label || platformType;
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
              onClick={() => {
                resetForm();
                setShowAddChannel(true);
              }}
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
                {channels.map((channel) => (
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
                            {getPlatformName(channel.platform_type)}
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
                          onClick={() => openEditModal(channel)}
                          className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-gray-500 hover:text-gray-700 dark:text-gray-400"
                          title="编辑"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>

                        <button
                          onClick={() => setShowDeleteConfirm(channel.id)}
                          className="p-1.5 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg text-red-500 hover:text-red-600"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4" />
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

      {/* 添加/编辑渠道模态框 */}
      {showAddChannel && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                {editingChannel ? '编辑发布渠道' : '添加发布渠道'}
              </h2>
              <button
                onClick={closeModal}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* 渠道名称 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  渠道名称 <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="例如：我的自建平台"
                  className="w-full px-4 py-2.5 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent bg-white dark:bg-gray-900 text-gray-900 dark:text-white"
                  required
                />
              </div>

              {/* 平台类型 */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  平台类型 <span className="text-red-500">*</span>
                </label>
                <div className="space-y-2">
                  {PLATFORM_OPTIONS.map((platform) => (
                    <label
                      key={platform.value}
                      className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors ${
                        formData.platform_type === platform.value
                          ? 'border-primary bg-primary/5'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <input
                        type="radio"
                        name="platform_type"
                        value={platform.value}
                        checked={formData.platform_type === platform.value}
                        onChange={(e) => setFormData({ ...formData, platform_type: e.target.value })}
                        className="mt-1"
                      />
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">
                          {platform.label}
                        </div>
                        <div className="text-sm text-gray-500 dark:text-gray-400">
                          {platform.description}
                        </div>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* API 配置（仅非自建平台显示） */}
              {formData.platform_type !== 'self_hosted' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    API 配置
                  </label>
                  <div className="space-y-2">
                    {apiConfigInputs.map((input, index) => (
                      <div key={index} className="flex gap-2">
                        <input
                          type="text"
                          value={input.key}
                          onChange={(e) => updateApiConfigInput(index, 'key', e.target.value)}
                          placeholder="配置项名称"
                          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
                        />
                        <input
                          type="text"
                          value={input.value}
                          onChange={(e) => updateApiConfigInput(index, 'value', e.target.value)}
                          placeholder="配置值"
                          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white text-sm"
                        />
                        {apiConfigInputs.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeApiConfigInput(index)}
                            className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    ))}
                    <button
                      type="button"
                      onClick={addApiConfigInput}
                      className="text-sm text-primary hover:text-primary/80 flex items-center gap-1"
                    >
                      <Plus className="w-4 h-4" />
                      添加配置项
                    </button>
                  </div>
                </div>
              )}

              {/* 自动发布 */}
              <div className="flex items-center gap-3">
                <input
                  type="checkbox"
                  id="auto_publish"
                  checked={formData.auto_publish}
                  onChange={(e) => setFormData({ ...formData, auto_publish: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
                />
                <label htmlFor="auto_publish" className="text-sm text-gray-700 dark:text-gray-300">
                  启用自动发布（生成完成后自动发布到此渠道）
                </label>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
              <button
                onClick={closeModal}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!formData.name || createChannelMutation.isPending || updateChannelMutation.isPending}
                className="btn-primary flex items-center gap-2 disabled:opacity-50"
              >
                {(createChannelMutation.isPending || updateChannelMutation.isPending) ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                {editingChannel ? '保存' : '创建'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 删除确认模态框 */}
      {showDeleteConfirm !== null && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-2xl w-full max-w-md p-6">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-red-100 dark:bg-red-900/30 rounded-full flex items-center justify-center">
                <Trash2 className="w-6 h-6 text-red-600 dark:text-red-400" />
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  确认删除
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  此操作不可撤销
                </p>
              </div>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              确定要删除此发布渠道吗？删除后，该渠道的发布配置将被永久移除。
            </p>
            <div className="flex items-center justify-end gap-3">
              <button
                onClick={() => setShowDeleteConfirm(null)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={() => deleteChannelMutation.mutate(showDeleteConfirm)}
                disabled={deleteChannelMutation.isPending}
                className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 disabled:opacity-50 flex items-center gap-2"
              >
                {deleteChannelMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                确认删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
