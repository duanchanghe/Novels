'use client';

import Link from 'next/link';
import { ArrowLeft, Headphones, Zap, BookOpen, Volume2, Users } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <Link href="/" className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex items-center gap-2">
              <Headphones className="w-6 h-6 text-primary" />
              <h1 className="font-semibold text-gray-900 dark:text-white">关于</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* 项目介绍 */}
          <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
              <Headphones className="w-6 h-6 text-primary" />
              AI 有声书工坊
            </h2>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              AI Audiobook Workshop 是一个开源项目，旨在将 EPUB 电子书自动转换为高质量的 AI 有声书。
              让每一本电子书都能被"听见"。
            </p>
            <div className="flex gap-3">
              <a
                href="https://github.com"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-outline text-sm"
              >
                GitHub
              </a>
              <Link href="/" className="btn-primary text-sm">
                立即使用
              </Link>
            </div>
          </section>

          {/* 核心特性 */}
          <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">核心特性</h3>
            <div className="grid gap-4">
              {[
                {
                  icon: BookOpen,
                  title: '智能 EPUB 解析',
                  desc: '支持多种编码和格式，自动识别章节结构，提取高质量文本内容',
                },
                {
                  icon: Users,
                  title: 'AI 角色区分',
                  desc: 'DeepSeek 智能识别角色，自动匹配不同音色，让对话更生动',
                },
                {
                  icon: Volume2,
                  title: '超高品质音质',
                  desc: 'MiniMax 专业级 TTS，媲美真人录制，44.1kHz/192kbps CD 级音质',
                },
                {
                  icon: Zap,
                  title: '全自动化流水线',
                  desc: '放入 EPUB 自动开始，零操作完成转换，支持手动/自动双模式',
                },
              ].map((item, i) => (
                <div key={i} className="flex gap-4">
                  <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center flex-shrink-0">
                    <item.icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">{item.title}</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          {/* 技术栈 */}
          <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">技术栈</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              {[
                ['后端', 'FastAPI + Celery'],
                ['前端', 'Next.js + TypeScript'],
                ['数据库', 'PostgreSQL'],
                ['存储', 'MinIO (S3 兼容)'],
                ['LLM', 'DeepSeek'],
                ['TTS', 'MiniMax'],
                ['容器化', 'Docker'],
                ['队列', 'Redis'],
              ].map(([label, value]) => (
                <div key={label} className="flex justify-between">
                  <span className="text-gray-500 dark:text-gray-400">{label}</span>
                  <span className="text-gray-900 dark:text-white font-medium">{value}</span>
                </div>
              ))}
            </div>
          </section>

          {/* 版本信息 */}
          <section className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">版本信息</h3>
            <p className="text-gray-500 dark:text-gray-400 text-sm">
              当前版本：V1.7.x（2026-05-03）
            </p>
          </section>
        </div>
      </main>
    </div>
  );
}
