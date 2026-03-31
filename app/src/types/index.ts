export interface DiaryListItem {
  id: string;
  diary_date: string | null;
  diary_date_unknown: boolean;
  insight_type: 'highlight' | 'observation' | 'summary';
  insight_text: string;
  insight_media_thumbnail_url: string | null;
  happy_minutes: number;
  angry_minutes: number;
  calm_minutes: number;
  event_count: number;
  generated_at: string;
}

export interface EventMedia {
  id: string;
  media_type: 'keyframe' | 'video_clip';
  url: string;
  thumbnail_url: string | null;
}

export interface DiaryKeyEvent {
  id: string;
  start_time: string | null;
  end_time: string | null;
  title: string;
  narrative: string;
  emotion_tag: 'happy' | 'angry' | null;
  emotion_note: string | null;
  tags: string[];
  media: EventMedia[];
}

export interface DiaryEntry {
  id: string;
  diary_date: string | null;
  diary_date_unknown: boolean;
  insight_type: string;
  insight_text: string;
  insight_media_type: string | null;
  insight_media_url: string | null;
  insight_media_thumbnail_url: string | null;
  happy_minutes: number;
  angry_minutes: number;
  calm_minutes: number;
  source_video_count: number;
  generated_at: string;
  key_events: DiaryKeyEvent[];
}

export interface SocialContact {
  id: string;
  label: string | null;
  relationship_type: string | null;
  scene_tags: string[];
  recent_frequency: number;
  last_seen_date: string | null;
}

export interface Interest {
  id: string;
  name: string;
  confidence: number;
  evidence_count: number;
  first_detected: string;
  last_detected: string;
}

export interface UserProfile {
  id: string;
  nickname: string | null;
  gender: string | null;
  age_range: string | null;
  occupation: string | null;
  city: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  social_contacts: SocialContact[];
  interests: Interest[];
  habits: {
    weekday: Record<string, any> | null;
    weekend: Record<string, any> | null;
    general: Record<string, any> | null;
  } | null;
  recent_focuses: { id: string; topic: string; detected_dates: string[]; summary: string | null }[];
}
