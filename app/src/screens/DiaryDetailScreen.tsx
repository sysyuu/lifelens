import React, { useState, useEffect } from 'react';
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
import { RouteProp, useRoute } from '@react-navigation/native';
import { RootStackParamList } from '../../App';
import { appApi } from '../hooks/useApi';
import { DiaryEntry, DiaryKeyEvent, EventMedia } from '../types';

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get('window');

type DetailRoute = RouteProp<RootStackParamList, 'DiaryDetail'>;

export default function DiaryDetailScreen() {
  const route = useRoute<DetailRoute>();
  const { diaryId } = route.params;
  const [diary, setDiary] = useState<DiaryEntry | null>(null);
  const [loading, setLoading] = useState(true);
  const [mediaModal, setMediaModal] = useState<EventMedia | null>(null);

  useEffect(() => {
    appApi.getDiary(diaryId)
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

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Insight header */}
      {diary.insight_media_url && (
        <TouchableOpacity
          onPress={() => {
            if (diary.insight_media_type === 'video_clip') {
              setMediaModal({
                id: 'insight',
                media_type: 'video_clip',
                url: diary.insight_media_url!,
                thumbnail_url: diary.insight_media_thumbnail_url,
              });
            }
          }}
        >
          {diary.insight_media_type === 'video_clip' ? (
            <View>
              <Image
                source={{ uri: appApi.getMediaUrl(diary.insight_media_thumbnail_url || diary.insight_media_url) }}
                style={styles.heroImage}
                resizeMode="cover"
              />
              <View style={styles.playOverlay}>
                <Text style={styles.playIcon}>▶</Text>
              </View>
            </View>
          ) : (
            <Image
              source={{ uri: appApi.getMediaUrl(diary.insight_media_url) }}
              style={styles.heroImage}
              resizeMode="cover"
            />
          )}
        </TouchableOpacity>
      )}

      <View style={styles.insightSection}>
        <Text style={styles.insightBadge}>
          {diary.insight_type === 'highlight' ? '✨ 今日高光' :
           diary.insight_type === 'observation' ? '👀 生活观察' : '💝 温暖小结'}
        </Text>
        <Text style={styles.insightText}>{diary.insight_text}</Text>
      </View>

      {/* Emotion bar */}
      {emotionTotal > 0 && (
        <View style={styles.emotionSection}>
          <Text style={styles.sectionTitle}>今日情绪</Text>
          <View style={styles.emotionBar}>
            {diary.happy_minutes > 0 && (
              <View style={[styles.emotionSeg, { flex: diary.happy_minutes, backgroundColor: '#fbbf24' }]} />
            )}
            {diary.calm_minutes > 0 && (
              <View style={[styles.emotionSeg, { flex: diary.calm_minutes, backgroundColor: '#86efac' }]} />
            )}
            {diary.angry_minutes > 0 && (
              <View style={[styles.emotionSeg, { flex: diary.angry_minutes, backgroundColor: '#fca5a5' }]} />
            )}
          </View>
          <View style={styles.emotionLegend}>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#fbbf24' }]} />
              <Text style={styles.legendText}>开心 {diary.happy_minutes}分钟</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#86efac' }]} />
              <Text style={styles.legendText}>平静 {diary.calm_minutes}分钟</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: '#fca5a5' }]} />
              <Text style={styles.legendText}>烦躁 {diary.angry_minutes}分钟</Text>
            </View>
          </View>
        </View>
      )}

      {/* Key events */}
      {diary.key_events.length > 0 && (
        <View style={styles.eventsSection}>
          <Text style={styles.sectionTitle}>今日事件</Text>
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
          <TouchableOpacity
            style={styles.modalClose}
            onPress={() => setMediaModal(null)}
          >
            <Text style={styles.modalCloseText}>✕</Text>
          </TouchableOpacity>
          {mediaModal?.media_type === 'video_clip' ? (
            <Video
              source={{ uri: appApi.getMediaUrl(mediaModal.url) }}
              style={styles.modalMedia}
              resizeMode={ResizeMode.CONTAIN}
              useNativeControls
              shouldPlay
            />
          ) : mediaModal ? (
            <Image
              source={{ uri: appApi.getMediaUrl(mediaModal.url) }}
              style={styles.modalMedia}
              resizeMode="contain"
            />
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
  const emotionEmoji = event.emotion_tag === 'happy' ? '😊' : event.emotion_tag === 'angry' ? '😤' : '';

  return (
    <View style={[styles.eventCard, !isLast && styles.eventCardBorder]}>
      <View style={styles.eventHeader}>
        <Text style={styles.eventTitle}>
          {emotionEmoji ? `${emotionEmoji} ` : ''}{event.title}
        </Text>
        {event.tags.length > 0 && (
          <View style={styles.tagRow}>
            {event.tags.slice(0, 3).map((tag) => (
              <Text key={tag} style={styles.tag}>#{tag}</Text>
            ))}
          </View>
        )}
      </View>
      <Text style={styles.eventNarrative}>{event.narrative}</Text>
      {event.emotion_note && (
        <Text style={styles.emotionNote}>{event.emotion_note}</Text>
      )}

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
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  content: { paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  heroImage: { width: '100%', height: 240 },
  playOverlay: {
    position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
    justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.2)',
  },
  playIcon: { fontSize: 40, color: '#fff' },
  insightSection: { padding: 20 },
  insightBadge: { fontSize: 14, fontWeight: '600', color: '#3b82f6', marginBottom: 8 },
  insightText: { fontSize: 16, lineHeight: 26, color: '#1f2937' },
  sectionTitle: { fontSize: 16, fontWeight: '700', marginBottom: 12, color: '#111827' },
  emotionSection: { paddingHorizontal: 20, marginBottom: 24 },
  emotionBar: { flexDirection: 'row', height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 8 },
  emotionSeg: { height: '100%' },
  emotionLegend: { flexDirection: 'row', gap: 16 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  legendDot: { width: 8, height: 8, borderRadius: 4 },
  legendText: { fontSize: 12, color: '#6b7280' },
  eventsSection: { paddingHorizontal: 20 },
  eventCard: { paddingVertical: 16 },
  eventCardBorder: { borderBottomWidth: 1, borderBottomColor: '#f3f4f6' },
  eventHeader: { marginBottom: 8 },
  eventTitle: { fontSize: 15, fontWeight: '600', color: '#111827' },
  tagRow: { flexDirection: 'row', gap: 6, marginTop: 4 },
  tag: { fontSize: 12, color: '#3b82f6', backgroundColor: '#eff6ff', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  eventNarrative: { fontSize: 14, lineHeight: 22, color: '#374151' },
  emotionNote: { fontSize: 13, color: '#6b7280', fontStyle: 'italic', marginTop: 4 },
  mediaRow: { gap: 8, marginTop: 12 },
  mediaThumbnail: { width: 120, height: 80, borderRadius: 8 },
  miniPlayOverlay: {
    position: 'absolute', top: 0, left: 0, width: 120, height: 80,
    justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 8,
  },
  miniPlayIcon: { fontSize: 20, color: '#fff' },
  modalBg: {
    flex: 1, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center',
  },
  modalClose: { position: 'absolute', top: 60, right: 20, zIndex: 10 },
  modalCloseText: { fontSize: 28, color: '#fff' },
  modalMedia: { width: SCREEN_W, height: SCREEN_H * 0.7 },
});
