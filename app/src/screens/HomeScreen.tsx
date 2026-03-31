import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Image,
  RefreshControl,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { appApi } from '../hooks/useApi';
import { DiaryListItem } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const [dates, setDates] = useState<string[]>([]);
  const [selectedDate, setSelectedDate] = useState<string | undefined>();
  const [diaries, setDiaries] = useState<DiaryListItem[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    appApi.listDiaryDates().then((d) => {
      setDates(d);
      if (d.length > 0) setSelectedDate(d[0]);
    }).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedDate !== undefined) loadDiaries();
  }, [selectedDate]);

  const loadDiaries = useCallback(async () => {
    try {
      const list = await appApi.listDiaries(selectedDate);
      setDiaries(list);
    } catch (err) {
      console.error(err);
    }
  }, [selectedDate]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadDiaries();
    setRefreshing(false);
  }, [loadDiaries]);

  const formatDate = (d: string) => {
    const date = new Date(d);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `${month}月${day}日 ${weekdays[date.getDay()]}`;
  };

  const emotionBar = (item: DiaryListItem) => {
    const total = item.happy_minutes + item.angry_minutes + item.calm_minutes;
    if (total === 0) return null;
    return (
      <View style={styles.emotionBar}>
        {item.happy_minutes > 0 && (
          <View
            style={[styles.emotionSegment, { flex: item.happy_minutes, backgroundColor: '#fbbf24' }]}
          />
        )}
        {item.calm_minutes > 0 && (
          <View
            style={[styles.emotionSegment, { flex: item.calm_minutes, backgroundColor: '#86efac' }]}
          />
        )}
        {item.angry_minutes > 0 && (
          <View
            style={[styles.emotionSegment, { flex: item.angry_minutes, backgroundColor: '#fca5a5' }]}
          />
        )}
      </View>
    );
  };

  const renderDiary = ({ item }: { item: DiaryListItem }) => (
    <TouchableOpacity
      style={styles.card}
      activeOpacity={0.7}
      onPress={() => navigation.navigate('DiaryDetail', { diaryId: item.id })}
    >
      {item.insight_media_thumbnail_url && (
        <Image
          source={{ uri: appApi.getMediaUrl(item.insight_media_thumbnail_url) }}
          style={styles.cardImage}
          resizeMode="cover"
        />
      )}
      <View style={styles.cardBody}>
        <View style={styles.cardMeta}>
          <Text style={styles.insightBadge}>
            {item.insight_type === 'highlight' ? '✨ 高光时刻' :
             item.insight_type === 'observation' ? '👀 生活观察' : '💝 温暖小结'}
          </Text>
          <Text style={styles.eventCount}>{item.event_count} 个事件</Text>
        </View>
        <Text style={styles.insightText} numberOfLines={3}>
          {item.insight_text}
        </Text>
        {emotionBar(item)}
      </View>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <Text style={styles.header}>我的日记</Text>

      {/* Date filter */}
      {dates.length > 0 && (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.dateRow}
        >
          {dates.map((d) => (
            <TouchableOpacity
              key={d}
              style={[styles.dateChip, selectedDate === d && styles.dateChipActive]}
              onPress={() => setSelectedDate(d)}
            >
              <Text style={[styles.dateChipText, selectedDate === d && styles.dateChipTextActive]}>
                {formatDate(d)}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      <FlatList
        data={diaries}
        keyExtractor={(item) => item.id}
        renderItem={renderDiary}
        contentContainerStyle={styles.list}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={
          <View style={styles.empty}>
            <Text style={styles.emptyText}>暂无日记</Text>
            <Text style={styles.emptySubtext}>上传视频后，AI 将为你生成日记</Text>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  header: { fontSize: 24, fontWeight: '700', paddingHorizontal: 20, paddingTop: 12, paddingBottom: 8 },
  dateRow: { paddingHorizontal: 16, paddingBottom: 12, gap: 8 },
  dateChip: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 16,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  dateChipActive: { backgroundColor: '#3b82f6', borderColor: '#3b82f6' },
  dateChipText: { fontSize: 13, color: '#374151' },
  dateChipTextActive: { color: '#fff', fontWeight: '600' },
  list: { padding: 16, paddingTop: 4 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 16,
    marginBottom: 16,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  cardImage: { width: '100%', height: 180 },
  cardBody: { padding: 16 },
  cardMeta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  insightBadge: { fontSize: 13, fontWeight: '600', color: '#3b82f6' },
  eventCount: { fontSize: 12, color: '#9ca3af' },
  insightText: { fontSize: 15, lineHeight: 22, color: '#1f2937' },
  emotionBar: { flexDirection: 'row', height: 4, borderRadius: 2, marginTop: 12, overflow: 'hidden' },
  emotionSegment: { height: '100%' },
  empty: { alignItems: 'center', paddingTop: 80 },
  emptyText: { fontSize: 16, color: '#9ca3af' },
  emptySubtext: { fontSize: 13, color: '#d1d5db', marginTop: 4 },
});
