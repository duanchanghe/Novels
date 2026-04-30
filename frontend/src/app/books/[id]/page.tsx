'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { 
  ArrowLeft,
  Play, 
  Pause, 
  SkipBack, 
  SkipForward,
  Volume2,
  VolumeX,
  Settings2,
  Download,
  Loader2,
  CheckCircle,
  AlertCircle,
  Clock
} from 'lucide-react';
import { api } from '@/lib/api';
import { usePlayerStore } from '@/lib/stores';
import type { Book, Chapter } from '@/types';

export default function BookDetailPage() {
  const params = useParams();
  const bookId = parseInt(params.id as string);

  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showSettings, setShowSettings] = useState(false);

  const audioRef = useRef<HTMLAudioElement>(null);
  const progressRef = useRef<HTMLDivElement>(null);

  const { 
    isPlaying, 
    setIsPlaying, 
    currentTime, 
    setCurrentTime, 
    duration, 
    setDuration,
    audioUrl,
    setAudioUrl,
    reset 
  } = usePlayerStore();

  // 获取书籍详情
  const { data: book, isLoading: bookLoading } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => api.getBook(bookId),
    enabled: !!bookId,
  });

  // 获取章节列表
  const { data: chaptersData, isLoading: chaptersLoading } = useQuery({
    queryKey: ['book-chapters', bookId],
    queryFn: () => api.getBookChapters(bookId),
    enabled: !!bookId,
  });

  const chapters = chaptersData || [];

  // 获取章节音频
  const { data: audioData } = useQuery({
    queryKey: ['chapter-audio', bookId, selectedChapter?.id],
    queryFn: () => api.getChapterAudio(bookId, selectedChapter!.id),
    enabled: !!selectedChapter && !!bookId,
  });

  // 设置音频 URL
  useEffect(() => {
    if (audioData?.audio_url) {
      setAudioUrl(audioData.audio_url);
    }
  }, [audioData, setAudioUrl]);

  // 播放控制
  useEffect(() => {
    if (audioRef.current && audioUrl) {
      if (isPlaying) {
        audioRef.current.play().catch(console.error);
      } else {
        audioRef.current.pause();
      }
    }
  }, [isPlaying, audioUrl]);

  // 音量控制
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.volume = isMuted ? 0 : volume;
    }
  }, [volume, isMuted]);

  // 播放速率控制
  useEffect(() => {
    if (audioRef.current) {
      audioRef.current.playbackRate = playbackRate;
    }
  }, [playbackRate]);

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      setCurrentTime(audioRef.current.currentTime);
    }
  }, [setCurrentTime]);

  const handleLoadedMetadata = useCallback(() => {
    if (audioRef.current) {
      setDuration(audioRef.current.duration);
    }
  }, [setDuration]);

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (progressRef.current && audioRef.current) {
      const rect = progressRef.current.getBoundingClientRect();
      const percent = (e.clientX - rect.left) / rect.width;
      audioRef.current.currentTime = percent * duration;
    }
  };

  const formatTime = (seconds: number) => {
    if (!seconds || isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const skipTime = (seconds: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = Math.max(
        0,
        Math.min(duration, audioRef.current.currentTime + seconds)
      );
    }
  };

  const getStatusBadge = (status: string) => {
    const statusConfig: Record<string, { color: string; icon: React.ReactNode }> = {
      pending: { color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300', icon: <Clock className="w-3 h-3" /> },
      analyzing: { color: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
      analyzed: { color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400', icon: <CheckCircle className="w-3 h-3" /> },
      synthesizing: { color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
      done: { color: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400', icon: <CheckCircle className="w-3 h-3" /> },
      failed: { color: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400', icon: <AlertCircle className="w-3 h-3" /> },
    };

    const config = statusConfig[status] || statusConfig.pending;
    return (
      <span className={`badge flex items-center gap-1 ${config.color}`}>
        {config.icon}
      </span>
    );
  };

  if (bookLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-32">
      {/* 顶部导航 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <Link
              href="/books"
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
            >
              <ArrowLeft className="w-5 h-5" />
            </Link>
            <div className="flex-1 min-w-0">
              <h1 className="font-semibold text-gray-900 dark:text-white truncate">
                {book?.title || '加载中...'}
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {book?.author || '未知作者'}
              </p>
            </div>
            <button className="btn-outline flex items-center gap-2">
              <Download className="w-4 h-4" />
              下载全部
            </button>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* 左侧：书籍信息 */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
              {/* 封面 */}
              <div className="relative aspect-[3/4] bg-gradient-to-br from-primary/20 to-accent/20 rounded-xl overflow-hidden mb-6">
                {book?.cover_image_url ? (
                  <img
                    src={book.cover_image_url}
                    alt={book.title}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Play className="w-16 h-16 text-gray-300 dark:text-gray-600" />
                  </div>
                )}
              </div>

              {/* 书籍信息 */}
              <div className="space-y-4">
                <div>
                  <h3 className="text-sm text-gray-500 dark:text-gray-400">状态</h3>
                  <div className="mt-1">
                    {book?.status && getStatusBadge(book.status)}
                  </div>
                </div>

                <div>
                  <h3 className="text-sm text-gray-500 dark:text-gray-400">进度</h3>
                  <p className="text-lg font-medium text-gray-900 dark:text-white">
                    {book?.processed_chapters || 0} / {book?.total_chapters || 0} 章节
                  </p>
                  <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-accent transition-all"
                      style={{ width: `${book?.progress_percentage || 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <h3 className="text-sm text-gray-500 dark:text-gray-400">总时长</h3>
                  <p className="text-lg font-medium text-gray-900 dark:text-white">
                    {book?.total_duration 
                      ? `${Math.floor(book.total_duration / 3600)}小时${Math.floor((book.total_duration % 3600) / 60)}分钟`
                      : '计算中...'}
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 右侧：章节列表 */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                  章节列表
                </h2>
              </div>

              <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[60vh] overflow-y-auto">
                {chaptersLoading ? (
                  <div className="flex justify-center py-12">
                    <Loader2 className="w-6 h-6 text-primary animate-spin" />
                  </div>
                ) : chapters.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                    暂无章节数据
                  </div>
                ) : (
                  chapters.map((chapter: Chapter) => (
                    <div
                      key={chapter.id}
                      onClick={() => {
                        setSelectedChapter(chapter);
                        if (chapter.status === 'done') {
                          setIsPlaying(true);
                        }
                      }}
                      className={`px-6 py-4 cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
                        selectedChapter?.id === chapter.id ? 'bg-primary/5' : ''
                      }`}
                    >
                      <div className="flex items-center gap-4">
                        <div className="flex-1 min-w-0">
                          <p className="font-medium text-gray-900 dark:text-white truncate">
                            {chapter.title || `第 ${chapter.chapter_index} 章`}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                            {chapter.audio_duration 
                              ? `${Math.floor(chapter.audio_duration / 60)}:${String(Math.floor(chapter.audio_duration % 60)).padStart(2, '0')}`
                              : '等待生成'}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          {getStatusBadge(chapter.status)}
                          {chapter.status === 'done' && (
                            <button className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg">
                              <Play className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 底部播放器 */}
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg">
        <audio
          ref={audioRef}
          src={audioUrl || undefined}
          onTimeUpdate={handleTimeUpdate}
          onLoadedMetadata={handleLoadedMetadata}
          onEnded={() => setIsPlaying(false)}
        />

        {/* 进度条 */}
        <div
          ref={progressRef}
          onClick={handleProgressClick}
          className="h-1 bg-gray-200 dark:bg-gray-700 cursor-pointer"
        >
          <div
            className="h-full bg-gradient-to-r from-primary to-accent"
            style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
          />
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center gap-4">
            {/* 章节信息 */}
            <div className="flex-1 min-w-0 hidden sm:block">
              <p className="font-medium text-gray-900 dark:text-white truncate">
                {selectedChapter?.title || '选择章节播放'}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {book?.title}
              </p>
            </div>

            {/* 播放控制 */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => skipTime(-10)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <SkipBack className="w-5 h-5" />
              </button>

              <button
                onClick={() => setIsPlaying(!isPlaying)}
                disabled={!selectedChapter || selectedChapter.status !== 'done'}
                className="w-12 h-12 bg-primary text-white rounded-full flex items-center justify-center hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isPlaying ? (
                  <Pause className="w-6 h-6" />
                ) : (
                  <Play className="w-6 h-6 ml-1" />
                )}
              </button>

              <button
                onClick={() => skipTime(10)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <SkipForward className="w-5 h-5" />
              </button>
            </div>

            {/* 时间 */}
            <div className="text-sm text-gray-500 dark:text-gray-400 w-20 text-center hidden sm:block">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            {/* 音量 */}
            <div className="hidden md:flex items-center gap-2">
              <button
                onClick={() => setIsMuted(!isMuted)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                {isMuted ? (
                  <VolumeX className="w-5 h-5" />
                ) : (
                  <Volume2 className="w-5 h-5" />
                )}
              </button>
              <input
                type="range"
                min="0"
                max="1"
                step="0.1"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="w-20 accent-primary"
              />
            </div>

            {/* 播放速率 */}
            <div className="relative">
              <button
                onClick={() => setShowSettings(!showSettings)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <Settings2 className="w-5 h-5" />
              </button>

              {showSettings && (
                <div className="absolute bottom-full right-0 mb-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-2 min-w-[120px]">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2 px-2">播放速率</p>
                  {[0.5, 0.75, 1, 1.25, 1.5, 2].map((rate) => (
                    <button
                      key={rate}
                      onClick={() => {
                        setPlaybackRate(rate);
                        setShowSettings(false);
                      }}
                      className={`w-full text-left px-2 py-1 rounded text-sm ${
                        playbackRate === rate
                          ? 'bg-primary/10 text-primary'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
