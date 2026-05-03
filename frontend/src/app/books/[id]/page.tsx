'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  Clock,
  Zap,
  Hand,
} from 'lucide-react';
import { api } from '@/lib/api';
import { usePlayerStore } from '@/lib/stores';
import type { Book, Chapter, GenerationMode } from '@/types';

const POLL_INTERVAL = 5000; // 5秒轮询章节状态

export default function BookDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const bookId = parseInt(params.id as string);

  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [showSettings, setShowSettings] = useState(false);
  const [isAutoPlayNext, setIsAutoPlayNext] = useState(true);

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
  } = usePlayerStore();

  // ── 获取书籍详情 ──
  const { data: book } = useQuery({
    queryKey: ['book', bookId],
    queryFn: () => api.getBook(bookId),
    enabled: !!bookId,
  });

  // ── 获取章节列表（带轮询） ──
  const {
    data: chaptersData,
    refetch: refetchChapters,
  } = useQuery({
    queryKey: ['book-chapters', bookId],
    queryFn: () => api.getBookChapters(bookId),
    enabled: !!bookId,
    refetchInterval: book?.status !== 'done' ? POLL_INTERVAL : false,
  });

  const chapters = chaptersData || [];

  // ── 获取选中章节的音频 URL ──
  const { data: audioData } = useQuery({
    queryKey: ['chapter-audio', bookId, selectedChapter?.id],
    queryFn: () => api.getChapterAudio(bookId, selectedChapter!.id),
    enabled: !!selectedChapter && selectedChapter.status === 'done' && !!bookId,
    retry: false,
  });

  // ── 触发生成 ──
  const generateMutation = useMutation({
    mutationFn: (mode: GenerationMode) => api.triggerGeneration(bookId, mode),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['book', bookId] });
    },
  });

  // ── 确认章节（手动模式） ──
  const confirmMutation = useMutation({
    mutationFn: (chapterId: number) => api.confirmChapter(bookId, chapterId),
    onSuccess: () => {
      refetchChapters();
    },
  });

  // ── 设置音频 URL ──
  useEffect(() => {
    if (audioData?.audio_url) {
      setAudioUrl(audioData.audio_url);
      setIsPlaying(true);
    }
  }, [audioData, setAudioUrl]);

  // ── 选中章节变化时重置播放器状态 ──
  useEffect(() => {
    setAudioUrl('');
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
  }, [selectedChapter?.id, setAudioUrl, setIsPlaying, setCurrentTime, setDuration]);

  // ── 播放控制 ──
  useEffect(() => {
    if (!audioRef.current || !audioUrl) return;
    if (isPlaying) {
      audioRef.current.play().catch((e) => {
        console.warn('播放失败:', e);
        setIsPlaying(false);
      });
    } else {
      audioRef.current.pause();
    }
  }, [isPlaying, audioUrl]);

  // ── 音量控制 ──
  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = isMuted ? 0 : volume;
  }, [volume, isMuted]);

  // ── 播放速率控制 ──
  useEffect(() => {
    if (audioRef.current) audioRef.current.playbackRate = playbackRate;
  }, [playbackRate]);

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
  }, [setCurrentTime]);

  const handleLoadedMetadata = useCallback(() => {
    if (audioRef.current) setDuration(audioRef.current.duration);
  }, [setDuration]);

  const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
    if (!progressRef.current || !audioRef.current || !duration) return;
    const rect = progressRef.current.getBoundingClientRect();
    const percent = (e.clientX - rect.left) / rect.width;
    audioRef.current.currentTime = percent * duration;
  };

  const formatTime = (seconds: number) => {
    if (!seconds || isNaN(seconds)) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // ── 下载单章音频 ──
  const handleDownloadChapter = async (chapter: Chapter) => {
    try {
      const data = await api.getChapterAudio(bookId, chapter.id);
      if (data.audio_url) {
        const link = document.createElement('a');
        link.href = data.audio_url;
        link.download = `${chapter.title || `第${chapter.chapter_index}章`}.mp3`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch {
      alert('下载失败，请稍后重试');
    }
  };

  // ── 下载整本书 ──
  const handleDownloadBook = async () => {
    if (!book?.title) {
      alert('书籍信息加载中，请稍后重试');
      return;
    }
    try {
      const data = await api.getDownloadUrl(bookId, 'mp3');
      if (data.download_url) {
        const link = document.createElement('a');
        link.href = data.download_url;
        link.download = `${book.title}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return;
      }
    } catch {
      // ZIP 不存在则尝试 M4B
    }
    try {
      const data = await api.getDownloadUrl(bookId, 'm4b');
      if (data.download_url) {
        const link = document.createElement('a');
        link.href = data.download_url;
        link.download = `${book.title}.m4b`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
    } catch {
      alert('暂无下载文件，请等待生成完成');
    }
  };

  const skipTime = (seconds: number) => {
    if (!audioRef.current || !duration) return;
    audioRef.current.currentTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds));
  };

  // ── 播放下一章（仅播放已完成章节） ──
  const playNextChapter = () => {
    if (!selectedChapter || chapters.length === 0) return;
    const idx = chapters.findIndex((ch: Chapter) => ch.id === selectedChapter.id);
    if (idx < 0 || idx >= chapters.length - 1) return;
    const next = chapters[idx + 1] as Chapter;
    if (next.status === 'done') {
      setSelectedChapter(next);
    }
  };

  const playPreviousChapter = () => {
    if (!selectedChapter || chapters.length === 0) return;
    const idx = chapters.findIndex((ch: Chapter) => ch.id === selectedChapter.id);
    if (idx <= 0) return;
    const prev = chapters[idx - 1] as Chapter;
    if (prev.status === 'done') {
      setSelectedChapter(prev);
    }
  };

  // ── 音频播放结束 ──
  const handleAudioEnded = () => {
    setIsPlaying(false);
    if (isAutoPlayNext) playNextChapter();
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      pending:         { color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',  icon: <Clock className="w-3 h-3" />, label: '等待' },
      analyzing:       { color: 'bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400', icon: <Loader2 className="w-3 h-3 animate-spin" />, label: '分析中' },
      analyzed:        { color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400', icon: <CheckCircle className="w-3 h-3" />, label: '已分析' },
      synthesizing:    { color: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400', icon: <Loader2 className="w-3 h-3 animate-spin" />, label: '合成中' },
      awaiting_confirm:{ color: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400', icon: <Hand className="w-3 h-3" />, label: '待确认' },
      done:           { color: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400', icon: <CheckCircle className="w-3 h-3" />, label: '已完成' },
      failed:         { color: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400', icon: <AlertCircle className="w-3 h-3" />, label: '失败' },
    };
    const cfg = map[status] || map.pending;
    return (
      <span className={`badge flex items-center gap-1 ${cfg.color}`}>
        {cfg.icon}
        <span>{cfg.label}</span>
      </span>
    );
  };

  const handleGenerate = (mode: GenerationMode) => {
    generateMutation.mutate(mode);
  };

  const handleConfirm = (chapter: Chapter) => {
    confirmMutation.mutate(chapter.id);
  };

  // 找到等待确认的章节
  const awaitingChapter = chapters.find((ch: Chapter) => ch.status === 'awaiting_confirm') as Chapter | undefined;

  if (!book) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <Loader2 className="w-8 h-8 text-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 pb-32">
      <audio
        ref={audioRef}
        src={audioUrl || undefined}
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onEnded={handleAudioEnded}
      />

      {/* ── 顶部导航 ── */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center h-16 gap-4">
            <button onClick={() => router.push('/books')} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div className="flex-1 min-w-0">
              <h1 className="font-semibold text-gray-900 dark:text-white truncate">{book.title}</h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">{book.author || '未知作者'}</p>
            </div>
            {book.status === 'done' && (
              <button onClick={handleDownloadBook} className="btn-outline flex items-center gap-2">
                <Download className="w-4 h-4" />下载全部
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid lg:grid-cols-3 gap-8">
          {/* ── 左侧：书籍信息 ── */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white dark:bg-gray-800 rounded-2xl p-6 shadow-sm">
              <div className="aspect-[3/4] bg-gradient-to-br from-primary/20 to-accent/20 rounded-xl overflow-hidden mb-6">
                {book.cover_image_url ? (
                  <img src={book.cover_image_url} alt={book.title} className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Play className="w-16 h-16 text-gray-300 dark:text-gray-600" />
                  </div>
                )}
              </div>

              <div className="space-y-4">
                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">状态</p>
                  <div className="mt-1">{getStatusBadge(book.status)}</div>
                </div>

                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">进度</p>
                  <p className="text-lg font-medium text-gray-900 dark:text-white">
                    {book.processed_chapters || 0} / {book.total_chapters || 0} 章节
                  </p>
                  <div className="mt-2 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-accent transition-all"
                      style={{ width: `${book.progress_percentage || 0}%` }}
                    />
                  </div>
                </div>

                <div>
                  <p className="text-sm text-gray-500 dark:text-gray-400">总时长</p>
                  <p className="text-lg font-medium text-gray-900 dark:text-white">
                    {book.total_duration
                      ? `${Math.floor(book.total_duration / 3600)}小时${Math.floor((book.total_duration % 3600) / 60)}分钟`
                      : '计算中...'}
                  </p>
                </div>

                {/* 生成模式 */}
                {book.status !== 'done' && (
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">生成模式</p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleGenerate('auto')}
                        disabled={['analyzing', 'synthesizing', 'post_processing', 'publishing'].includes(book.status)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium border transition-colors ${
                          book.generation_mode === 'auto'
                            ? 'bg-blue-50 border-blue-300 text-blue-700 dark:bg-blue-900/30 dark:border-blue-700 dark:text-blue-300'
                            : 'border-gray-300 text-gray-600 hover:border-gray-400 dark:border-gray-600 dark:text-gray-400'
                        } disabled:opacity-50`}
                      >
                        <Zap className="w-4 h-4" />自动模式
                      </button>
                      <button
                        onClick={() => handleGenerate('manual')}
                        disabled={['analyzing', 'synthesizing', 'post_processing', 'publishing'].includes(book.status)}
                        className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium border transition-colors ${
                          book.generation_mode === 'manual'
                            ? 'bg-orange-50 border-orange-300 text-orange-700 dark:bg-orange-900/30 dark:border-orange-700 dark:text-orange-300'
                            : 'border-gray-300 text-gray-600 hover:border-gray-400 dark:border-gray-600 dark:text-gray-400'
                        } disabled:opacity-50`}
                      >
                        <Hand className="w-4 h-4" />手动模式
                      </button>
                    </div>
                    {generateMutation.isPending && (
                      <p className="text-xs text-primary mt-1 flex items-center gap-1">
                        <Loader2 className="w-3 h-3 animate-spin" />
                        {generateMutation.variables === 'auto' ? '自动生成中...' : '手动模式已设置'}
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* 手动模式：确认按钮（置顶提示） */}
            {awaitingChapter && (
              <div className="bg-orange-50 dark:bg-orange-900/20 border border-orange-300 dark:border-orange-700 rounded-2xl p-5 shadow-sm">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-orange-100 dark:bg-orange-900/50 rounded-lg">
                    <Hand className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-orange-900 dark:text-orange-300">
                      等待您的确认
                    </h3>
                    <p className="text-sm text-orange-700 dark:text-orange-400 mt-1">
                      {awaitingChapter.title || `第 ${awaitingChapter.chapter_index} 章`}
                      已准备就绪，请确认开始生成。
                    </p>
                    <button
                      onClick={() => handleConfirm(awaitingChapter)}
                      disabled={confirmMutation.isPending}
                      className="mt-3 btn-primary flex items-center gap-2"
                    >
                      {confirmMutation.isPending ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <Zap className="w-4 h-4" />
                      )}
                      确认开始
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* ── 右侧：章节列表 ── */}
          <div className="lg:col-span-2">
            <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-sm overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white">章节列表</h2>
                {!chaptersData ? (
                  <Loader2 className="w-5 h-5 text-gray-400 animate-spin" />
                ) : null}
              </div>

              <div className="divide-y divide-gray-200 dark:divide-gray-700 max-h-[60vh] overflow-y-auto">
                {chapters.length === 0 ? (
                  <div className="text-center py-12 text-gray-500 dark:text-gray-400">暂无章节数据</div>
                ) : (
                  chapters.map((chapter: Chapter) => {
                    const isSelected = selectedChapter?.id === chapter.id;
                    const isAwaiting = chapter.status === 'awaiting_confirm';
                    const isDone = chapter.status === 'done';

                    return (
                      <div
                        key={chapter.id}
                        onClick={() => {
                          if (chapter.status === 'done') {
                            setSelectedChapter(chapter);
                          } else if (chapter.status === 'awaiting_confirm') {
                            handleConfirm(chapter);
                          }
                        }}
                        className={`px-6 py-4 cursor-pointer transition-colors ${
                          isSelected
                            ? 'bg-primary/5'
                            : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                        } ${isAwaiting ? 'cursor-pointer' : ''}`}
                      >
                        <div className="flex items-center gap-4">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <p className="font-medium text-gray-900 dark:text-white truncate">
                                {chapter.title || `第 ${chapter.chapter_index} 章`}
                              </p>
                              {isSelected && (
                                <span className="w-2 h-2 rounded-full bg-primary flex-shrink-0" />
                              )}
                            </div>
                            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                              {chapter.audio_duration
                                ? `${Math.floor(chapter.audio_duration / 60)}:${String(Math.floor(chapter.audio_duration % 60)).padStart(2, '0')}`
                                : '等待生成'}
                            </p>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            {getStatusBadge(chapter.status)}

                            {isDone && (
                              <>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    handleDownloadChapter(chapter);
                                  }}
                                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                                  title="下载"
                                >
                                  <Download className="w-4 h-4" />
                                </button>
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedChapter(chapter);
                                    setIsPlaying(true);
                                  }}
                                  className="p-2 hover:bg-gray-100 dark:hover:bg-gray-600 rounded-lg"
                                  title="播放"
                                >
                                  <Play className="w-4 h-4" />
                                </button>
                              </>
                            )}

                            {isAwaiting && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleConfirm(chapter);
                                }}
                                disabled={confirmMutation.isPending}
                                className="flex items-center gap-1 px-3 py-1.5 bg-orange-500 hover:bg-orange-600 text-white rounded-lg text-sm font-medium disabled:opacity-50"
                              >
                                <Zap className="w-3 h-3" />
                                开始
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* ── 底部播放器 ── */}
      <div className="fixed bottom-0 left-0 right-0 bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 shadow-lg">
        {/* 进度条 */}
        <div
          ref={progressRef}
          onClick={handleProgressClick}
          className="h-1 bg-gray-200 dark:bg-gray-700 cursor-pointer group"
        >
          <div
            className="h-full bg-gradient-to-r from-primary to-accent transition-all relative"
            style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
          >
            <div className="absolute right-0 top-1/2 -translate-y-1/2 w-3 h-3 bg-primary rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex items-center gap-4">
            {/* 章节信息 */}
            <div className="flex-1 min-w-0 hidden sm:block">
              <p className="font-medium text-gray-900 dark:text-white truncate">
                {selectedChapter?.title || '选择章节播放'}
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 truncate">{book.title}</p>
            </div>

            {/* 播放控制 */}
            <div className="flex items-center gap-1">
              <button
                onClick={playPreviousChapter}
                disabled={!selectedChapter || (chapters.findIndex((ch: Chapter) => ch.id === selectedChapter?.id) <= 0)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-30"
                title="上一章"
              >
                <SkipBack className="w-4 h-4" />
              </button>

              <button
                onClick={() => skipTime(-10)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-xs font-bold"
                title="后退10秒"
              >
                -10
              </button>

              <button
                onClick={() => {
                  if (!audioUrl && selectedChapter?.status === 'done') {
                    // 触发音频加载
                    api.getChapterAudio(bookId, selectedChapter.id).then((d) => {
                      if (d.audio_url) setAudioUrl(d.audio_url);
                    });
                  } else {
                    setIsPlaying(!isPlaying);
                  }
                }}
                disabled={!selectedChapter || (selectedChapter.status !== 'done')}
                className="w-11 h-11 bg-primary text-white rounded-full flex items-center justify-center hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>

              <button
                onClick={() => skipTime(10)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg text-xs font-bold"
                title="前进10秒"
              >
                +10
              </button>

              <button
                onClick={playNextChapter}
                disabled={!selectedChapter || (chapters.findIndex((ch: Chapter) => ch.id === selectedChapter?.id) >= chapters.length - 1)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg disabled:opacity-30"
                title="下一章"
              >
                <SkipForward className="w-4 h-4" />
              </button>
            </div>

            {/* 时间 */}
            <div className="text-sm text-gray-500 dark:text-gray-400 w-28 text-center hidden sm:block">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>

            {/* 音量 */}
            <div className="hidden md:flex items-center gap-2">
              <button onClick={() => setIsMuted(!isMuted)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
              </button>
              <input
                type="range" min="0" max="1" step="0.05"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="w-20 accent-primary"
              />
            </div>

            {/* 设置 */}
            <div className="relative">
              <button onClick={() => setShowSettings(!showSettings)} className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg">
                <Settings2 className="w-4 h-4" />
              </button>
              {showSettings && (
                <div className="absolute bottom-full right-0 mb-2 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 p-3 min-w-[160px]">
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">播放速率</p>
                  {[0.5, 0.75, 1, 1.25, 1.5, 2].map((rate) => (
                    <button
                      key={rate}
                      onClick={() => { setPlaybackRate(rate); setShowSettings(false); }}
                      className={`w-full text-left px-2 py-1.5 rounded text-sm ${
                        playbackRate === rate
                          ? 'bg-primary/10 text-primary font-medium'
                          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
                      }`}
                    >
                      {rate}x
                    </button>
                  ))}
                  <div className="border-t border-gray-200 dark:border-gray-700 my-2" />
                  <button
                    onClick={() => { setIsAutoPlayNext(!isAutoPlayNext); setShowSettings(false); }}
                    className="w-full text-left px-2 py-1.5 rounded text-sm hover:bg-gray-100 dark:hover:bg-gray-700"
                  >
                    自动播放下一章 {isAutoPlayNext ? '✓' : ''}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
