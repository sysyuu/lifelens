import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  Image,
  RefreshControl,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation, useIsFocused } from '@react-navigation/native';
import { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RootStackParamList } from '../../App';
import { appApi } from '../hooks/useApi';
import { DiaryListItem } from '../types';

type Nav = NativeStackNavigationProp<RootStackParamList>;

interface ActiveBatch {
  batch_id: string;
  video_count: number;
  image_count?: number;
  pure_video_count?: number;
  status: string;
  current_node: { node_id: string; node_name: string } | null;
  completed_nodes: number;
  total_nodes: number;
  created_at: string | null;
}

type ListItem =
  | { type: 'processing'; data: ActiveBatch }
  | { type: 'diary'; data: DiaryListItem };

export default function HomeScreen() {
  const navigation = useNavigation<Nav>();
  const isFocused = useIsFocused();
  const [diaries, setDiaries] = useState<DiaryListItem[]>([]);
  const [activeBatches, setActiveBatches] = useState<ActiveBatch[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [diaryList, batches] = await Promise.all([
        appApi.listDiaries(),
        appApi.getActiveBatches(),
      ]);
      setDiaries(diaryList);
      setActiveBatches(batches);
    } catch (err) {
      console.error(err);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, []);

  // Refresh when tab becomes focused
  useEffect(() => {
    if (isFocused) loadData();
  }, [isFocused]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  }, [loadData]);

  const formatDate = (d: string | null) => {
    if (!d) return '未知日期';
    const date = new Date(d + 'T00:00:00');
    const year = date.getFullYear();
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'];
    return `${year}.${month}.${day} (${weekdays[date.getDay()]})`;
  };

  // Build merged list: processing cards first, then diary cards
  const listItems: ListItem[] = [
    ...activeBatches.map((b) => ({ type: 'processing' as const, data: b })),
    ...diaries.map((d) => ({ type: 'diary' as const, data: d })),
  ];

  const renderProcessingCard = (batch: ActiveBatch) => {
    const progress = Math.round((batch.completed_nodes / batch.total_nodes) * 100);
    const nodeName = batch.current_node?.node_name || '排队中';
    return (
      <View style={styles.card}>
        <View style={styles.processingBody}>
          <Text style={styles.dateLabel}>{formatDate(batch.created_at?.slice(0, 10) || null)}</Text>
          <View style={styles.processingBadge}>
            <ActivityIndicator size="small" color="#3b82f6" />
            <Text style={styles.processingText}>日记生成中...</Text>
          </View>
          <View style={styles.progressBarBg}>
            <View style={[styles.progressBarFill, { width: `${progress}%` }]} />
          </View>
          <Text style={styles.progressDetail}>
            {batch.completed_nodes}/{batch.total_nodes} 节点完成 · 当前：{nodeName}
          </Text>
          <Text style={styles.videoCountText}>
            {batch.image_count && batch.image_count > 0
              ? `${batch.image_count} 张图片 + ${batch.pure_video_count || 0} 个视频正在处理`
              : `${batch.video_count} 个视频正在处理`}
          </Text>
        </View>
      </View>
    );
  };

  const renderDiaryCard = (item: DiaryListItem) => (
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
        <Text style={styles.dateLabel}>{formatDate(item.diary_date)}</Text>
        <View style={styles.cardMeta}>
          <Text style={styles.insightBadge}>📝 今日总结</Text>
          <Text style={styles.eventCount}>{item.event_count} 个事件</Text>
        </View>
        <Text style={styles.insightText} numberOfLines={3}>
          {item.insight_text}
        </Text>
        {emotionBar(item)}
      </View>
    </TouchableOpacity>
  );

  const emotionBar = (item: DiaryListItem) => {
    const total = item.happy_minutes + item.angry_minutes + item.calm_minutes;
    if (total === 0) return null;
    return (
      <View style={styles.emotionBar}>
        {item.happy_minutes > 0 && (
          <View style={[styles.emotionSegment, { flex: item.happy_minutes, backgroundColor: '#fbbf24' }]} />
        )}
        {item.calm_minutes > 0 && (
          <View style={[styles.emotionSegment, { flex: item.calm_minutes, backgroundColor: '#86efac' }]} />
        )}
        {item.angry_minutes > 0 && (
          <View style={[styles.emotionSegment, { flex: item.angry_minutes, backgroundColor: '#fca5a5' }]} />
        )}
      </View>
    );
  };

  const renderItem = ({ item }: { item: ListItem }) => {
    if (item.type === 'processing') return renderProcessingCard(item.data);
    return renderDiaryCard(item.data);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <Text style={styles.header}>我的日记</Text>
      <FlatList
        data={listItems}
        keyExtractor={(item, index) =>
          item.type === 'processing' ? `batch-${item.data.batch_id}` : `diary-${item.data.id}`
        }
        renderItem={renderItem}
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
  header: { fontSize: 24, fontWeight: '700', paddingHorizontal: 20, paddingTop: 12, paddingBottom: 12 },
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
  dateLabel: { fontSize: 13, fontWeight: '600', color: '#6b7280', marginBottom: 8 },
  cardMeta: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 },
  insightBadge: { fontSize: 14, fontWeight: '600', color: '#3b82f6' },
  eventCount: { fontSize: 12, color: '#9ca3af' },
  insightText: { fontSize: 15, lineHeight: 22, color: '#1f2937' },
  emotionBar: { flexDirection: 'row', height: 4, borderRadius: 2, marginTop: 12, overflow: 'hidden' },
  emotionSegment: { height: '100%' },
  // Processing card
  processingBody: { padding: 20 },
  processingBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 12 },
  processingText: { fontSize: 15, fontWeight: '600', color: '#3b82f6' },
  progressBarBg: { height: 6, backgroundColor: '#e5e7eb', borderRadius: 3, overflow: 'hidden', marginBottom: 8 },
  progressBarFill: { height: '100%', backgroundColor: '#3b82f6', borderRadius: 3 },
  progressDetail: { fontSize: 12, color: '#6b7280', marginBottom: 4 },
  videoCountText: { fontSize: 12, color: '#9ca3af' },
  // Empty
  empty: { alignItems: 'center', paddingTop: 80 },
  emptyText: { fontSize: 16, color: '#9ca3af' },
  emptySubtext: { fontSize: 13, color: '#d1d5db', marginTop: 4 },
});
