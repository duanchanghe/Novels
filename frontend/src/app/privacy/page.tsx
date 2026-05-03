'use client';

import Link from 'next/link';
import { ArrowLeft, Headphones } from 'lucide-react';

export default function PrivacyPage() {
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
              <h1 className="font-semibold text-gray-900 dark:text-white">隐私政策</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="prose dark:prose-invert max-w-none">
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">最后更新：2026年5月3日</p>

          <h2>1. 信息收集</h2>
          <p>我们收集以下信息：</p>
          <ul>
            <li><strong>EPUB 文件</strong>：您上传的电子书文件，用于转换为有声书</li>
            <li><strong>使用日志</strong>：API 调用记录、处理状态，用于服务优化和故障排查</li>
            <li><strong>基础技术信息</strong>：浏览器类型、访问时间等标准服务器日志信息</li>
          </ul>

          <h2>2. 数据存储</h2>
          <ul>
            <li>EPUB 文件和生成的音频存储在本地对象存储服务（MinIO）中</li>
            <li>书籍元数据（书名、作者、状态）存储在 PostgreSQL 数据库中</li>
            <li>文件在转换完成后将根据您的请求进行清理</li>
          </ul>

          <h2>3. 数据安全</h2>
          <ul>
            <li>所有存储服务均配置访问控制，未授权用户无法访问他人文件</li>
            <li>音频文件通过预签名 URL 分享，具有时效性限制</li>
            <li>数据库访问受密码保护</li>
          </ul>

          <h2>4. 第三方 API</h2>
          <p>本服务使用以下第三方 AI 服务：</p>
          <ul>
            <li><strong>DeepSeek</strong>：用于文本分析和角色识别</li>
            <li><strong>MiniMax</strong>：用于语音合成</li>
            <li>您的文本内容将传输至这些服务商以完成处理，请参阅各服务商的隐私政策</li>
          </ul>

          <h2>5. Cookie 使用</h2>
          <p>本服务不使用追踪 Cookie。播放进度等偏好信息仅存储在您浏览器的本地存储中。</p>

          <h2>6. 数据保留</h2>
          <ul>
            <li>处理完成的音频文件默认保留 30 天（可配置）</li>
            <li>元数据（书名、状态）在删除书籍后一并清除</li>
            <li>API 日志保留 90 天</li>
          </ul>

          <h2>7. 您的权利</h2>
          <p>您可以：</p>
          <ul>
            <li>随时删除已上传的书籍（对应文件一并清除）</li>
            <li>请求导出您的账户数据</li>
            <li>联系我们就任何隐私问题提出疑问</li>
          </ul>

          <h2>8. 联系我们</h2>
          <p>
            如有任何隐私相关问题，请通过 GitHub Issues 与我们联系。
          </p>
        </div>
      </main>
    </div>
  );
}
