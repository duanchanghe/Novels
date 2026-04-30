// 书籍相关类型
export interface Book {
  id: number;
  title: string;
  author: string | null;
  description: string | null;
  cover_image_url: string | null;
  file_size: number;
  file_hash: string;
  status: BookStatus;
  source_type: SourceType;
  total_chapters: number;
  processed_chapters: number;
  progress_percentage: number;
  total_duration: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export type BookStatus = 
  | 'pending'
  | 'analyzing'
  | 'synthesizing'
  | 'post_processing'
  | 'publishing'
  | 'done'
  | 'failed';

export type SourceType = 'manual' | 'watch';

// 章节相关类型
export interface Chapter {
  id: number;
  book_id: number;
  chapter_index: number;
  title: string | null;
  raw_text: string | null;
  cleaned_text: string | null;
  analysis_result: any | null;
  characters: Character[] | null;
  status: ChapterStatus;
  audio_file_path: string | null;
  audio_duration: number | null;
  audio_file_size: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export type ChapterStatus = 
  | 'pending'
  | 'analyzing'
  | 'analyzed'
  | 'synthesizing'
  | 'done'
  | 'failed';

// 角色相关类型
export interface Character {
  name: string;
  aliases: string[];
  dialogue_count: number;
  emotions: string[];
}

// 音频片段相关类型
export interface AudioSegment {
  id: number;
  chapter_id: number;
  segment_index: number;
  text_content: string;
  role: string;
  emotion: string;
  voice_id: string;
  speed: number;
  audio_file_path: string | null;
  audio_duration_ms: number | null;
  status: SegmentStatus;
  retry_count: number;
  error_message: string | null;
}

export type SegmentStatus = 
  | 'pending'
  | 'synthesizing'
  | 'success'
  | 'failed';

// 发布相关类型
export interface PublishChannel {
  id: number;
  name: string;
  platform_type: string;
  api_config: any;
  is_enabled: boolean;
  auto_publish: boolean;
  priority: number;
  total_published: number;
  success_count: number;
  failure_count: number;
  last_published_at: string | null;
  created_at: string;
}

export interface PublishRecord {
  id: number;
  book_id: number;
  channel_id: number;
  external_album_id: string | null;
  external_album_url: string | null;
  status: PublishStatus;
  published_chapters: number;
  total_chapters: number;
  chapters_published: Record<string, string>;
  published_at: string | null;
  error_message: string | null;
  retry_count: number;
}

export type PublishStatus = 
  | 'pending'
  | 'preparing'
  | 'publishing'
  | 'partial_done'
  | 'done'
  | 'failed'
  | 'cancelled';

// 音色相关类型
export interface Voice {
  id: string;
  name: string;
  gender: 'male' | 'female';
  description: string;
}

export interface Emotion {
  id: string;
  name: string;
  intensity_levels: string[] | null;
}

// 监听相关类型
export interface WatchStatus {
  enabled: boolean;
  running: boolean;
  watch_dirs: string[];
  observer_count: number;
  total_detected: number;
  total_processed: number;
  total_failed: number;
  last_processed: string | null;
  queue_available: number;
  queue_current: number;
}

// API 响应类型
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

// 任务状态类型
export interface TaskStatus {
  book_id: number;
  status: BookStatus;
  progress_percentage: number;
  total_chapters: number;
  processed_chapters: number;
  error_message: string | null;
}

// 上传相关类型
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadResult {
  book_id: number;
  title: string;
  author: string | null;
  total_chapters: number;
  file_size: number;
}

// 音频统计类型
export interface AudioStats {
  duration_ms: number;
  duration_seconds: number;
  channels: number;
  sample_rate: number;
  max_dBFS: number;
  rms_dBFS: number;
}

// 成本追踪类型
export interface CostTracking {
  book_id: number;
  deepseek_total_tokens: number;
  minimax_total_characters: number;
  estimated_cost: number;
}
