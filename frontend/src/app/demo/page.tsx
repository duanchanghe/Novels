'use client';

import Link from 'next/link';
import { ArrowLeft, Headphones, BookOpen, Zap, Play } from 'lucide-react';

export default function DemoPage() {
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
              <h1 className="font-semibold text-gray-900 dark:text-white">在线体验</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          <div className="bg-gradient-to-br from-primary/10 to-accent/10 rounded-2xl p-8 text-center">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">
              有声书 Demo 示例
            </h2>
            <p className="text-gray-600 dark:text-gray-300 max-w-md mx-auto">
              上传一本 EPUB 电子书，即可体验完整的 AI 有声书生成流程。
            </p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              功能演示流程
            </h3>
            <div className="space-y-4">
              {[
                {
                  step: '01',
                  icon: BookOpen,
                  title: '上传 EPUB',
                  desc: '选择一本 EPUB 电子书文件上传',
                  color: 'bg-blue-500',
                },
                {
                  step: '02',
                  icon: Zap,
                  title: '选择模式',
                  desc: '选择自动模式（连续处理）或手动模式（逐章确认）',
                  color: 'bg-yellow-500',
                },
                {
                  step: '03',
                  icon: Headphones,
                  title: '在线收听',
                  desc: '生成完成后直接在页面播放，收听效果',
                  color: 'bg-green-500',
                },
              ].map((item, i) => (
                <div key={i} className="flex gap-4 items-start">
                  <div className={`w-10 h-10 ${item.color} rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0`}>
                    {item.step}
                  </div>
                  <div>
                    <h4 className="font-medium text-gray-900 dark:text-white">{item.title}</h4>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              快速开始
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              前往书架页面，上传您的第一本 EPUB 电子书开始体验：
            </p>
            <Link
              href="/books"
              className="btn-primary flex items-center gap-2 w-fit"
            >
              <BookOpen className="w-4 h-4" />
              前往书架
            </Link>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              已有书籍
            </h3>
            <p className="text-gray-600 dark:text-gray-300 mb-4">
              您已上传了「小狗钱钱」，可以直接查看生成进度：
            </p>
            <Link
              href="/books/5"
              className="btn-outline flex items-center gap-2 w-fit"
            >
              <Play className="w-4 h-4" />
              查看书籍详情
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
