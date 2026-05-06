import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  ScrollView,
  Image,
  StyleSheet,
  ActivityIndicator,
  TouchableOpacity,
  Modal,
  Dimensions,
} from 'react-native';
import { Video, ResizeMode } from 'expo-av';
import { RouteProp, useRoute, useNavigation } from '@react-navigation/native';
import { RootStackParamList } from '../../App';
import { appApi } from '../hooks/useApi';
import { DiaryEntry, DiaryKeyEvent, EventMedia } from '../types';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

type DetailRoute = RouteProp<RootStackParamList, 'DiaryDetail'>;

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];

function formatDiaryDate(dateStr: string | null): string {
  if (!dateStr) return '日期未知';
  const d = new Date(dateStr + 'T00:00:00');
  const y = d.getFullYear();
  const m = d.getMonth() + 1;
  const day = d.getDate();
  return `${y}年${m}月${day}日 ${WEEKDAYS[d.getDay()]}`;
}

// Gradient-like header colors based on insight type
const INSIGHT_COLORS: Record<string, { bg: string; accent: string }> = {
  highlight: { bg: '#fef3c7', accent: '#f59e0b' },
  observation: { bg: '#dbeafe', accent: '#3b82f6' },
  summary: { bg: '#fce7f3', accent: '#ec4899' },
};

export default function DiaryDetailScreen() {
  const route = useRoute<DetailRoute>();
  const navigation = useNavigation();
  const { diaryId } = route.params;
  const [diary, setDiary] = useState<DiaryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [mediaModal, setMediaModal] = useState<EventMedia | null>(null);

  useEffect(() => {
    appApi
      .getDiary(diaryId)
      .then(setDiary)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [diaryId]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }

  if (!diary) {
    return (
      <View style={styles.center}>
        <Text style={{ color: '#9ca3af' }}>日记不存在</Text>
      </View>
    );
  }

  const emotionTotal = diary.happy_minutes + diary.angry_minutes + diary.calm_minutes;
  const colors = INSIGHT_COLORS[diary.insight_type] || INSIGHT_COLORS.summary;

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Hero header with insight */}
      <View style={[styles.heroSection, { backgroundColor: colors.bg }]}>
        {/* Back button */}
        <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
          <Text style={styles.backText}>←</Text>
        </TouchableOpacity>

        {/* Date & meta */}
        <Text style={styles.dateText}>{formatDiaryDate(diary.diary_date)}</Text>

        {/* Insight badge */}
        <View style={[styles.insightBadgeContainer, { backgroundColor: colors.accent + '20' }]}>
          <Text style={[styles.insightBadge, { color: colors.accent }]}>
            📝 今日总结
          </Text>
        </View>

        {/* Insight text */}
        <Text style={styles.insightText}>{diary.insight_text}</Text>

        {/* Source meta */}
        {diary.source_video_count > 0 && (
          <Text style={styles.sourceMeta}>基于 {diary.source_video_count} 段视频生成</Text>
        )}
      </View>

      {/* Emotion section */}
      {emotionTotal > 0 && (
        <View style={styles.emotionSection}>
          <Text style={styles.sectionTitle}>今日情绪</Text>
          <View style={styles.emotionBar}>
            {diary.happy_minutes > 0 && (
              <View
                style={[styles.emotionSeg, { flex: diary.happy_minutes, backgroundColor: '#fbbf24' }]}
              />
            )}
            {diary.calm_minutes > 0 && (
              <View
                style={[styles.emotionSeg, { flex: diary.calm_minutes, backgroundColor: '#86efac' }]}
              />
            )}
            {diary.angry_minutes > 0 && (
              <View
                style={[styles.emotionSeg, { flex: diary.angry_minutes, backgroundColor: '#fca5a5' }]}
              />
            )}
          </View>
          <View style={styles.emotionLegend}>
            {diary.happy_minutes > 0 && (
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#fbbf24' }]} />
                <Text style={styles.legendText}>开心 {diary.happy_minutes}分钟</Text>
              </View>
            )}
            {diary.calm_minutes > 0 && (
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#86efac' }]} />
                <Text style={styles.legendText}>平静 {diary.calm_minutes}分钟</Text>
              </View>
            )}
            {diary.angry_minutes > 0 && (
              <View style={styles.legendItem}>
                <View style={[styles.legendDot, { backgroundColor: '#fca5a5' }]} />
                <Text style={styles.legendText}>烦躁 {diary.angry_minutes}分钟</Text>
              </View>
            )}
          </View>
        </View>
      )}

      {/* Timeline events */}
      {diary.key_events.length > 0 && (
        <View style={styles.eventsSection}>
          <Text style={styles.sectionTitle}>
            今日事件（{diary.key_events.length}）
          </Text>
          {diary.key_events.map((event, idx) => (
            <EventCard
              key={event.id}
              event={event}
              isLast={idx === diary.key_events.length - 1}
              onMediaPress={setMediaModal}
            />
          ))}
        </View>
      )}

      {/* Media fullscreen modal */}
      <Modal visible={!!mediaModal} animationType="fade" transparent>
        <View style={styles.modalBg}>
          <TouchableOpacity style={styles.modalClose} onPress={() => setMediaModal(null)}>
            <Text style={styles.modalCloseText}>✕</Text>
          </TouchableOpacity>
          {mediaModal ? (
            mediaModal.media_type === 'video_clip' ? (
              <Video
                source={{ uri: appApi.getMediaUrl(mediaModal.url) }}
                style={styles.modalMedia}
                resizeMode={ResizeMode.CONTAIN}
                useNativeControls
                shouldPlay
              />
            ) : (
              <Image
                source={{ uri: appApi.getMediaUrl(mediaModal.url) }}
                style={styles.modalMedia}
                resizeMode="contain"
              />
            )
          ) : null}
        </View>
      </Modal>
    </ScrollView>
  );
}

function EventCard({
  event,
  isLast,
  onMediaPress,
}: {
  event: DiaryKeyEvent;
  isLast: boolean;
  onMediaPress: (m: EventMedia) => void;
}) {
  const emotionEmoji =
    event.emotion_tag === 'happy' ? '😊' : event.emotion_tag === 'angry' ? '😤' : '';
  const hasTime = event.start_time || event.end_time;

  return (
    <View style={styles.timelineRow}>
      {/* Timeline left column */}
      <View style={styles.timelineLeft}>
        {hasTime ? (
          <Text style={styles.timeText}>{event.start_time || ''}</Text>
        ) : (
          <View style={{ height: 16 }} />
        )}
        <View style={styles.timelineDot} />
        {!isLast && <View style={styles.timelineLine} />}
      </View>

      {/* Event content */}
      <View style={[styles.eventCard, !isLast && styles.eventCardSpacing]}>
        {/* Title row */}
        <Text style={styles.eventTitle}>
          {emotionEmoji ? `${emotionEmoji} ` : ''}
          {event.title}
        </Text>

        {/* Time range badge */}
        {hasTime && (
          <View style={styles.timeRangeBadge}>
            <Text style={styles.timeRangeText}>
              {event.start_time}
              {event.end_time ? ` - ${event.end_time}` : ''}
            </Text>
          </View>
        )}

        {/* Tags */}
        {event.tags.length > 0 && (
          <View style={styles.tagRow}>
            {event.tags.slice(0, 4).map((tag) => (
              <Text key={tag} style={styles.tag}>
                #{tag}
              </Text>
            ))}
          </View>
        )}

        {/* Narrative */}
        <Text style={styles.eventNarrative}>{event.narrative}</Text>

        {/* Emotion note */}
        {event.emotion_note ? (
          <View style={styles.emotionNoteBox}>
            <Text style={styles.emotionNote}>
              {event.emotion_tag === 'happy' ? '😊 ' : event.emotion_tag === 'angry' ? '😤 ' : '💭 '}
              {event.emotion_note}
            </Text>
          </View>
        ) : null}

        {/* Media gallery */}
        {event.media.length > 0 && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.mediaRow}
          >
            {event.media.map((m) => (
              <TouchableOpacity key={m.id} onPress={() => onMediaPress(m)}>
                <Image
                  source={{ uri: appApi.getMediaUrl(m.thumbnail_url || m.url) }}
                  style={styles.mediaThumbnail}
                  resizeMode="cover"
                />
                {m.media_type === 'video_clip' && (
                  <View style={styles.miniPlayOverlay}>
                    <Text style={styles.miniPlayIcon}>▶</Text>
                  </View>
                )}
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { paddingBottom: 60 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },

  // Hero
  heroSection: {
    paddingTop: 56,
    paddingBottom: 24,
    paddingHorizontal: 20,
    borderBottomLeftRadius: 24,
    borderBottomRightRadius: 24,
  },
  backButton: {
    position: 'absolute',
    top: 16,
    left: 16,
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: 'rgba(255,255,255,0.8)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 10,
  },
  backText: { fontSize: 20, color: '#374151' },
  dateText: {
    fontSize: 22,
    fontWeight: '700',
    color: '#111827',
    marginBottom: 12,
  },
  insightBadgeContainer: {
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 12,
    marginBottom: 12,
  },
  insightBadge: { fontSize: 13, fontWeight: '600' },
  insightText: {
    fontSize: 16,
    lineHeight: 26,
    color: '#1f2937',
  },
  sourceMeta: {
    fontSize: 12,
    color: '#9ca3af',
    marginTop: 12,
  },

  // Emotion
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    marginBottom: 12,
    color: '#111827',
  },
  emotionSection: { paddingHorizontal: 20, paddingTop: 24, marginBottom: 8 },
  emotionBar: {
    flexDirection: 'row',
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 10,
  },
  emotionSeg: { height: '100%' },
  emotionLegend: { flexDirection: 'row', flexWrap: 'wrap', gap: 16 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 12, color: '#6b7280' },

  // Timeline events
  eventsSection: { paddingHorizontal: 20, paddingTop: 24 },
  timelineRow: { flexDirection: 'row' },
  timelineLeft: {
    width: 52,
    alignItems: 'center',
    paddingTop: 2,
  },
  timeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#9ca3af',
    marginBottom: 6,
  },
  timelineDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#3b82f6',
    borderWidth: 2,
    borderColor: '#dbeafe',
  },
  timelineLine: {
    width: 2,
    flex: 1,
    backgroundColor: '#e5e7eb',
    marginTop: 4,
  },

  // Event card
  eventCard: {
    flex: 1,
    paddingLeft: 12,
    paddingBottom: 8,
  },
  eventCardSpacing: {
    paddingBottom: 24,
  },
  eventTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#111827',
    marginBottom: 4,
  },
  timeRangeBadge: {
    alignSelf: 'flex-start',
    backgroundColor: '#f3f4f6',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 8,
    marginBottom: 6,
  },
  timeRangeText: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '500',
  },
  tagRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginBottom: 8 },
  tag: {
    fontSize: 12,
    color: '#3b82f6',
    backgroundColor: '#eff6ff',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
  },
  eventNarrative: { fontSize: 14, lineHeight: 22, color: '#374151' },
  emotionNoteBox: {
    backgroundColor: '#fef9ef',
    borderRadius: 8,
    padding: 8,
    marginTop: 8,
  },
  emotionNote: { fontSize: 13, color: '#92400e', lineHeight: 18 },
  mediaRow: { gap: 8, marginTop: 12 },
  mediaThumbnail: { width: 120, height: 80, borderRadius: 8 },
  miniPlayOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: 120,
    height: 80,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0,0,0,0.2)',
    borderRadius: 8,
  },
  miniPlayIcon: { fontSize: 20, color: '#fff' },

  // Modal
  modalBg: {
    flex: 1,
    backgroundColor: '#000',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalClose: { position: 'absolute', top: 60, right: 20, zIndex: 10 },
  modalCloseText: { fontSize: 28, color: '#fff' },
  modalMedia: { width: SCREEN_W, height: SCREEN_H * 0.7 },
});
