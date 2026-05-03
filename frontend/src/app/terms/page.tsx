'use client';

import Link from 'next/link';
import { ArrowLeft, Headphones } from 'lucide-react';

export default function TermsPage() {
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
              <h1 className="font-semibold text-gray-900 dark:text-white">服务条款</h1>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="prose dark:prose-invert max-w-none">
          <p className="text-gray-500 dark:text-gray-400 text-sm mb-6">最后更新：2026年5月3日</p>

          <h2>1. 服务说明</h2>
          <p>
            AI 有声书工坊（以下简称"本服务"）是一个将 EPUB 电子书转换为 AI 语音有声书的在线平台。
            本服务仅作为技术转换工具，不拥有任何电子书内容的版权。
          </p>

          <h2>2. 使用规范</h2>
          <p>您承诺不会利用本服务：</p>
          <ul>
            <li>上传或转换受版权保护的作品（除非您拥有合法授权或该作品已进入公有领域）</li>
            <li>生成任何违法、有害、欺诈或侵犯他人权益的内容</li>
            <li>对服务进行反向工程、破解或绕过任何安全措施</li>
            <li>进行任何可能损害服务稳定性或性能的行为</li>
          </ul>

          <h2>3. 版权声明</h2>
          <p>
            本服务生成的 AI 有声书仅供个人学习、娱乐或无障碍阅读（视障人士）使用。
            将 AI 有声书用于商业用途或公开传播前，请确保您拥有相应内容的合法授权。
            因版权问题产生的一切法律责任由使用者自行承担。
          </p>

          <h2>4. 服务可用性</h2>
          <p>
            本服务会尽合理努力保持正常运行，但不对以下情况承担责任：
          </p>
          <ul>
            <li>因网络故障、服务器维护或不可抗力导致的服务中断</li>
            <li>因第三方 API（如 AI 语音合成服务）故障导致的处理失败</li>
            <li>因用户操作不当或上传文件格式错误导致的处理异常</li>
          </ul>

          <h2>5. API 使用成本</h2>
          <p>
            本服务的语音合成功能依赖第三方 AI API，将消耗您的 API 调用配额。
            请注意监控您的 API 使用情况，因 API 配额耗尽导致的服务中断由用户自行负责。
          </p>

          <h2>6. 隐私保护</h2>
          <p>
            我们会妥善保管您上传的 EPUB 文件和生成的音频数据。
            文件仅用于处理您的转换请求，不会用于任何其他目的。
            详细隐私政策请参阅 <Link href="/privacy" className="text-primary hover:underline">隐私政策</Link>。
          </p>

          <h2>7. 免责声明</h2>
          <p>
            本服务按"原样"提供，不对生成音频的质量、准确性或适用性作出任何明示或暗示的保证。
            用户需自行承担使用本服务的风险。
          </p>

          <h2>8. 条款修改</h2>
          <p>
            我们保留随时修改本服务条款的权利。修改后的条款将在本页面上公布。
            继续使用本服务即表示您接受修改后的条款。
          </p>

          <h2>9. 联系我们</h2>
          <p>
            如对本服务条款有任何疑问，请通过 GitHub Issues 与我们联系。
          </p>
        </div>
      </main>
    </div>
  );
}
