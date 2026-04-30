'use client';

import { useState } from 'react';
import Link from 'next/link';
import { 
  BookOpen, 
  Upload, 
  Headphones, 
  Settings, 
  Activity,
  Play,
  ChevronRight,
  Volume2,
  Zap,
  Shield,
  Clock
} from 'lucide-react';
import { useUIStore } from '@/lib/stores';

export default function HomePage() {
  const [isAnimating, setIsAnimating] = useState(false);
  const { setUploadModalOpen } = useUIStore();

  const features = [
    {
      icon: BookOpen,
      title: '智能解析',
      description: '自动识别章节结构，提取高质量文本内容',
      color: 'text-blue-500',
      bg: 'bg-blue-50 dark:bg-blue-900/20',
    },
    {
      icon: Headphones,
      title: '角色区分',
      description: 'AI 智能识别角色，自动匹配不同音色',
      color: 'text-purple-500',
      bg: 'bg-purple-50 dark:bg-purple-900/20',
    },
    {
      icon: Volume2,
      title: '超高品质',
      description: '专业级音频后处理，媲美真人录制',
      color: 'text-green-500',
      bg: 'bg-green-50 dark:bg-green-900/20',
    },
    {
      icon: Zap,
      title: '全自动化',
      description: '放入 EPUB 自动开始，零操作完成转换',
      color: 'text-yellow-500',
      bg: 'bg-yellow-50 dark:bg-yellow-900/20',
    },
  ];

  const stats = [
    { label: '支持格式', value: 'EPUB' },
    { label: '处理速度', value: '<30分钟' },
    { label: '音质标准', value: '44.1kHz' },
    { label: '角色识别', value: '≥90%' },
  ];

  return (
    <div className="min-h-screen">
      {/* 导航栏 */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center gap-2">
              <div className="w-10 h-10 bg-gradient-to-br from-primary to-accent rounded-xl flex items-center justify-center">
                <Headphones className="w-6 h-6 text-white" />
              </div>
              <span className="text-xl font-bold text-gray-900 dark:text-white">
                AI 有声书工坊
              </span>
            </div>

            <div className="hidden md:flex items-center gap-6">
              <Link 
                href="/books" 
                className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white transition-colors"
              >
                我的书架
              </Link>
              <Link 
                href="/watch" 
                className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white transition-colors"
              >
                监听状态
              </Link>
              <Link 
                href="/settings" 
                className="text-gray-600 hover:text-gray-900 dark:text-gray-300 dark:hover:text-white transition-colors"
              >
                设置
              </Link>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => setUploadModalOpen(true)}
                className="btn-primary flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                上传 EPUB
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero 区域 */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 px-4 py-2 bg-primary/10 rounded-full text-primary text-sm font-medium mb-8">
              <Zap className="w-4 h-4" />
              全自动化 · AI 驱动 · 专业品质
            </div>

            <h1 className="text-5xl md:text-7xl font-bold text-gray-900 dark:text-white mb-6 leading-tight">
              让每一本电子书
              <br />
              <span className="bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
                都能被"听见"
              </span>
            </h1>

            <p className="text-xl text-gray-600 dark:text-gray-400 mb-10 max-w-2xl mx-auto">
              放入 EPUB，自动解析、自动合成、自动发布。
              <br className="hidden md:block" />
              零操作完成从电子书到有声书的转换。
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <button
                onClick={() => {
                  setIsAnimating(true);
                  setUploadModalOpen(true);
                  setTimeout(() => setIsAnimating(false), 500);
                }}
                className={`btn-primary text-lg px-8 py-4 flex items-center justify-center gap-2 ${
                  isAnimating ? 'animate-pulse' : ''
                }`}
              >
                <Upload className="w-5 h-5" />
                开始转换
              </button>
              <Link
                href="/demo"
                className="btn-outline text-lg px-8 py-4 flex items-center justify-center gap-2"
              >
                <Play className="w-5 h-5" />
                查看演示
              </Link>
            </div>

            {/* 统计数据 */}
            <div className="mt-16 grid grid-cols-2 md:grid-cols-4 gap-8">
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <div className="text-3xl font-bold text-gray-900 dark:text-white mb-1">
                    {stat.value}
                  </div>
                  <div className="text-sm text-gray-500 dark:text-gray-400">
                    {stat.label}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* 功能特性 */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-white dark:bg-gray-800">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              为什么选择我们
            </h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              专业级的有声书转换服务，让您的阅读体验升级
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className="p-6 rounded-2xl bg-gray-50 dark:bg-gray-900 card-hover"
              >
                <div className={`w-14 h-14 ${feature.bg} rounded-xl flex items-center justify-center mb-4`}>
                  <feature.icon className={`w-7 h-7 ${feature.color}`} />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                  {feature.title}
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 工作流程 */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              简单三步，即刻拥有有声书
            </h2>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            {[
              {
                step: '01',
                title: '上传 EPUB',
                description: '将您的 EPUB 电子书上传到平台',
                icon: Upload,
              },
              {
                step: '02',
                title: '自动处理',
                description: 'AI 自动完成解析、合成、后期处理',
                icon: Activity,
              },
              {
                step: '03',
                title: '收听下载',
                description: '在线收听或下载高品质有声书',
                icon: Headphones,
              },
            ].map((item, index) => (
              <div key={index} className="relative">
                <div className="flex flex-col items-center text-center">
                  <div className="w-20 h-20 bg-gradient-to-br from-primary/20 to-accent/20 rounded-full flex items-center justify-center mb-6">
                    <item.icon className="w-10 h-10 text-primary" />
                  </div>
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-8 h-8 bg-primary rounded-full flex items-center justify-center text-white text-sm font-bold">
                    {item.step}
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                    {item.title}
                  </h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    {item.description}
                  </p>
                </div>

                {index < 2 && (
                  <ChevronRight className="hidden md:block absolute top-10 -right-4 w-8 h-8 text-gray-300 dark:text-gray-600" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 底部 CTA */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 bg-gradient-to-br from-primary to-accent">
        <div className="max-w-4xl mx-auto text-center text-white">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">
            准备好开始了吗？
          </h2>
          <p className="text-xl text-white/80 mb-8">
            立即体验 AI 有声书工坊，让您的阅读更加便捷
          </p>
          <button
            onClick={() => setUploadModalOpen(true)}
            className="bg-white text-primary font-semibold px-8 py-4 rounded-xl hover:bg-white/90 transition-colors"
          >
            立即开始
          </button>
        </div>
      </section>

      {/* 页脚 */}
      <footer className="py-8 px-4 sm:px-6 lg:px-8 border-t border-gray-200 dark:border-gray-800">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-4">
          <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
            <Headphones className="w-5 h-5" />
            <span>AI 有声书工坊</span>
          </div>
          <div className="flex items-center gap-6 text-sm text-gray-500 dark:text-gray-400">
            <Link href="/about" className="hover:text-primary transition-colors">
              关于
            </Link>
            <Link href="/privacy" className="hover:text-primary transition-colors">
              隐私政策
            </Link>
            <Link href="/terms" className="hover:text-primary transition-colors">
              服务条款
            </Link>
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400">
            © 2026 AI Audiobook Workshop
          </div>
        </div>
      </footer>
    </div>
  );
}
