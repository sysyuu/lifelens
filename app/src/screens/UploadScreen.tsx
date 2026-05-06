import React, { useState, useCallback } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Alert,
  ActivityIndicator,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import * as ImagePicker from 'expo-image-picker';
import * as MediaLibrary from 'expo-media-library';
import { appApi } from '../hooks/useApi';

interface MediaAsset {
  uri: string;
  fileName: string;
  duration?: number; // seconds
  mediaType: 'photo' | 'video';
  skipped?: boolean; // video >1min
}

function showAlert(title: string, msg: string) {
  if (Platform.OS === 'web') {
    window.alert(`${title}\n${msg}`);
  } else {
    Alert.alert(title, msg);
  }
}

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六'];

function formatDateLabel(d: Date): string {
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 周${WEEKDAYS[d.getDay()]}`;
}

function toDateStr(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

// Simple calendar grid component
function CalendarPicker({
  selectedDate,
  onSelect,
}: {
  selectedDate: Date | null;
  onSelect: (d: Date) => void;
}) {
  const [viewMonth, setViewMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });

  const year = viewMonth.getFullYear();
  const month = viewMonth.getMonth();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Days in month
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  // First day of week (0=Sun)
  const firstDow = new Date(year, month, 1).getDay();

  const cells: (number | null)[] = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) cells.push(d);

  const prevMonth = () => setViewMonth(new Date(year, month - 1, 1));
  const nextMonth = () => {
    const next = new Date(year, month + 1, 1);
    if (next <= new Date()) setViewMonth(next);
  };

  const selStr = selectedDate ? toDateStr(selectedDate) : '';

  return (
    <View style={calStyles.container}>
      {/* Month nav */}
      <View style={calStyles.header}>
        <TouchableOpacity onPress={prevMonth} style={calStyles.navBtn}>
          <Text style={calStyles.navText}>{'<'}</Text>
        </TouchableOpacity>
        <Text style={calStyles.monthLabel}>
          {year}年{month + 1}月
        </Text>
        <TouchableOpacity onPress={nextMonth} style={calStyles.navBtn}>
          <Text style={calStyles.navText}>{'>'}</Text>
        </TouchableOpacity>
      </View>

      {/* Weekday headers */}
      <View style={calStyles.weekRow}>
        {['日', '一', '二', '三', '四', '五', '六'].map((w) => (
          <Text key={w} style={calStyles.weekLabel}>{w}</Text>
        ))}
      </View>

      {/* Day grid */}
      <View style={calStyles.grid}>
        {cells.map((day, i) => {
          if (day === null) {
            return <View key={`e${i}`} style={calStyles.cell} />;
          }
          const cellDate = new Date(year, month, day);
          const isFuture = cellDate > today;
          const isSelected = toDateStr(cellDate) === selStr;
          const isToday = toDateStr(cellDate) === toDateStr(today);

          return (
            <TouchableOpacity
              key={day}
              style={[
                calStyles.cell,
                isSelected && calStyles.cellSelected,
                isToday && !isSelected && calStyles.cellToday,
              ]}
              disabled={isFuture}
              onPress={() => onSelect(cellDate)}
            >
              <Text
                style={[
                  calStyles.dayText,
                  isFuture && calStyles.dayFuture,
                  isSelected && calStyles.daySelected,
                ]}
              >
                {day}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const calStyles = StyleSheet.create({
  container: { backgroundColor: '#fff', borderRadius: 16, padding: 16, marginBottom: 16 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  navBtn: { padding: 8 },
  navText: { fontSize: 18, color: '#3b82f6', fontWeight: '600' },
  monthLabel: { fontSize: 16, fontWeight: '700', color: '#111827' },
  weekRow: { flexDirection: 'row', marginBottom: 4 },
  weekLabel: { flex: 1, textAlign: 'center', fontSize: 12, color: '#9ca3af', fontWeight: '500' },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: '14.28%', aspectRatio: 1, justifyContent: 'center', alignItems: 'center', borderRadius: 20 },
  cellSelected: { backgroundColor: '#3b82f6' },
  cellToday: { backgroundColor: '#eff6ff' },
  dayText: { fontSize: 14, color: '#374151' },
  dayFuture: { color: '#d1d5db' },
  daySelected: { color: '#fff', fontWeight: '700' },
});

export default function UploadScreen() {
  const navigation = useNavigation<any>();
  // Mode: 'pick' = manual video selection, 'date' = calendar date import
  const [mode, setMode] = useState<'pick' | 'date'>('date');

  // Manual pick state
  const [videos, setVideos] = useState<MediaAsset[]>([]);

  // Date import state
  const [selectedDate, setSelectedDate] = useState<Date | null>(null);
  const [dateAssets, setDateAssets] = useState<MediaAsset[]>([]);
  const [scanning, setScanning] = useState(false);
  const [photoCount, setPhotoCount] = useState(0);
  const [videoCount, setVideoCount] = useState(0);
  const [skippedCount, setSkippedCount] = useState(0);

  // Upload state
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');

  // --- Manual video pick ---
  const pickVideos = async () => {
    try {
      const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!perm.granted) {
        showAlert('权限不足', '请在设置中允许访问相册');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ['videos'],
        allowsMultipleSelection: true,
      });

      if (!result.canceled && result.assets.length > 0) {
        const newVideos: MediaAsset[] = [];
        for (const a of result.assets) {
          newVideos.push({
            uri: a.uri,
            fileName: a.fileName || `video_${Date.now()}_${newVideos.length}.mp4`,
            duration: a.duration ? a.duration / 1000 : undefined,
            mediaType: 'video',
          });
        }
        setVideos((prev) => [...prev, ...newVideos]);
      }
    } catch (err: any) {
      showAlert('选择失败', `请尝试选择更少的视频：${err.message || err}`);
    }
  };

  const removeVideo = (idx: number) => {
    setVideos((prev) => prev.filter((_, i) => i !== idx));
  };

  // --- Date-based gallery import ---
  const handleDateSelect = useCallback(async (d: Date) => {
    setSelectedDate(d);
    setScanning(true);
    setDateAssets([]);
    setPhotoCount(0);
    setVideoCount(0);
    setSkippedCount(0);

    try {
      const perm = await MediaLibrary.requestPermissionsAsync();
      if (!perm.granted) {
        showAlert('权限不足', '请在设置中允许访问相册');
        setScanning(false);
        return;
      }

      // Query all assets for the selected date
      const startOfDay = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 0, 0, 0);
      const endOfDay = new Date(d.getFullYear(), d.getMonth(), d.getDate(), 23, 59, 59);

      const assets: MediaAsset[] = [];
      let hasMore = true;
      let after: string | undefined;
      let photos = 0;
      let vids = 0;
      let skipped = 0;

      while (hasMore) {
        const page = await MediaLibrary.getAssetsAsync({
          mediaType: [MediaLibrary.MediaType.photo, MediaLibrary.MediaType.video],
          createdAfter: startOfDay.getTime(),
          createdBefore: endOfDay.getTime(),
          first: 100,
          after,
          sortBy: [MediaLibrary.SortBy.creationTime],
        });

        for (const a of page.assets) {
          if (a.mediaType === 'photo') {
            photos++;
            assets.push({
              uri: a.uri,
              fileName: a.filename || `photo_${photos}.jpg`,
              mediaType: 'photo',
            });
          } else if (a.mediaType === 'video') {
            const durSec = a.duration || 0;
            if (durSec > 60) {
              skipped++;
            } else {
              vids++;
              assets.push({
                uri: a.uri,
                fileName: a.filename || `video_${vids}.mp4`,
                duration: durSec,
                mediaType: 'video',
              });
            }
          }
        }

        hasMore = page.hasNextPage;
        after = page.endCursor;
      }

      setDateAssets(assets);
      setPhotoCount(photos);
      setVideoCount(vids);
      setSkippedCount(skipped);
    } catch (err: any) {
      showAlert('扫描失败', err.message || '无法读取相册');
    } finally {
      setScanning(false);
    }
  }, []);

  // --- Upload handlers ---
  const handleManualUpload = async () => {
    if (videos.length === 0) {
      showAlert('提示', '请先选择视频');
      return;
    }

    setUploading(true);
    const videoIds: string[] = [];
    let completed = 0;

    try {
      const CONCURRENCY = 3;
      for (let i = 0; i < videos.length; i += CONCURRENCY) {
        const batch = videos.slice(i, i + CONCURRENCY);
        const results = await Promise.all(
          batch.map((v) => appApi.uploadVideo(v.uri, v.fileName))
        );
        for (const res of results) videoIds.push(res.video_id);
        completed += batch.length;
        setUploadProgress(`上传中 ${completed}/${videos.length}...`);
      }

      setUploadProgress('创建处理任务...');
      await appApi.createBatch(videoIds);

      setVideos([]);
      setUploadProgress('');
      setUploading(false);
      navigation.navigate('Home');
    } catch (err: any) {
      const detail = err.response
        ? `服务器错误 ${err.response.status}: ${JSON.stringify(err.response.data)}`
        : err.message || '请检查网络连接后重试';
      showAlert('上传失败', detail);
      setUploadProgress('');
      setUploading(false);
    }
  };

  const handleDateUpload = async () => {
    if (dateAssets.length === 0) {
      showAlert('提示', '当天没有可上传的素材');
      return;
    }

    setUploading(true);
    const videoIds: string[] = [];
    const imageIds: string[] = [];
    let completed = 0;
    const total = dateAssets.length;
    const dateStr = selectedDate ? toDateStr(selectedDate) : undefined;

    try {
      const CONCURRENCY = 5;
      for (let i = 0; i < dateAssets.length; i += CONCURRENCY) {
        const batch = dateAssets.slice(i, i + CONCURRENCY);
        const results = await Promise.all(
          batch.map(async (asset) => {
            if (asset.mediaType === 'video') {
              const res = await appApi.uploadVideo(asset.uri, asset.fileName);
              return { type: 'video' as const, id: res.video_id };
            } else {
              const res = await appApi.uploadImage(asset.uri, asset.fileName, dateStr);
              return { type: 'image' as const, id: res.media_id };
            }
          })
        );
        for (const res of results) {
          if (res.type === 'video') videoIds.push(res.id);
          else imageIds.push(res.id);
        }
        completed += batch.length;
        setUploadProgress(`上传中 ${completed}/${total}...`);
      }

      setUploadProgress('创建处理任务...');
      await appApi.createBatch(videoIds, dateStr, imageIds);

      setDateAssets([]);
      setSelectedDate(null);
      setUploadProgress('');
      setUploading(false);
      navigation.navigate('Home');
    } catch (err: any) {
      const detail = err.response
        ? `服务器错误 ${err.response.status}: ${JSON.stringify(err.response.data)}`
        : err.message || '请检查网络连接后重试';
      showAlert('上传失败', detail);
      setUploadProgress('');
      setUploading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <Text style={styles.header}>上传素材</Text>

      {/* Mode tabs */}
      <View style={styles.modeTabs}>
        <TouchableOpacity
          style={[styles.modeTab, mode === 'date' && styles.modeTabActive]}
          onPress={() => setMode('date')}
          disabled={uploading}
        >
          <Text style={[styles.modeTabText, mode === 'date' && styles.modeTabTextActive]}>
            按日期导入
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.modeTab, mode === 'pick' && styles.modeTabActive]}
          onPress={() => setMode('pick')}
          disabled={uploading}
        >
          <Text style={[styles.modeTabText, mode === 'pick' && styles.modeTabTextActive]}>
            手动选择视频
          </Text>
        </TouchableOpacity>
      </View>

      {mode === 'date' ? (
        <ScrollView style={styles.scrollBody} showsVerticalScrollIndicator={false}>
          {/* Calendar */}
          <CalendarPicker selectedDate={selectedDate} onSelect={handleDateSelect} />

          {/* Scan results */}
          {scanning && (
            <View style={styles.scanningBox}>
              <ActivityIndicator size="small" color="#3b82f6" />
              <Text style={styles.scanningText}>扫描相册中...</Text>
            </View>
          )}

          {selectedDate && !scanning && (
            <View style={styles.statsBox}>
              <Text style={styles.statsTitle}>{formatDateLabel(selectedDate)}</Text>
              {dateAssets.length > 0 ? (
                <>
                  <View style={styles.statsRow}>
                    <View style={styles.statItem}>
                      <Text style={styles.statNum}>{photoCount}</Text>
                      <Text style={styles.statLabel}>张图片</Text>
                    </View>
                    <View style={styles.statItem}>
                      <Text style={styles.statNum}>{videoCount}</Text>
                      <Text style={styles.statLabel}>个视频</Text>
                    </View>
                    {skippedCount > 0 && (
                      <View style={styles.statItem}>
                        <Text style={[styles.statNum, { color: '#f59e0b' }]}>{skippedCount}</Text>
                        <Text style={styles.statLabel}>已过滤</Text>
                      </View>
                    )}
                  </View>
                  {skippedCount > 0 && (
                    <Text style={styles.skippedNote}>
                      已过滤 {skippedCount} 个超过1分钟的视频
                    </Text>
                  )}
                </>
              ) : (
                <Text style={styles.noAssets}>当天没有照片或视频</Text>
              )}
            </View>
          )}

          {/* Upload button for date mode */}
          {dateAssets.length > 0 && (
            <TouchableOpacity
              style={[styles.uploadButton, uploading && styles.uploadButtonDisabled]}
              onPress={handleDateUpload}
              disabled={uploading}
            >
              {uploading ? (
                <View style={styles.uploadingRow}>
                  <ActivityIndicator color="#fff" size="small" />
                  <Text style={styles.uploadButtonText}>{uploadProgress}</Text>
                </View>
              ) : (
                <Text style={styles.uploadButtonText}>
                  上传并生成日记（{photoCount}张图片 + {videoCount}个视频{skippedCount > 0 ? `，过滤${skippedCount}个` : ''}）
                </Text>
              )}
            </TouchableOpacity>
          )}

          <View style={{ height: 40 }} />
        </ScrollView>
      ) : (
        /* Manual pick mode */
        <View style={styles.pickBody}>
          <Text style={styles.subtext}>
            从相册选择 Insta Go3S 拍摄的视频，AI 将自动生成日记
          </Text>

          <TouchableOpacity
            style={styles.pickButton}
            onPress={pickVideos}
            disabled={uploading}
          >
            <Text style={styles.pickIcon}>+</Text>
            <Text style={styles.pickText}>从相册选择视频</Text>
          </TouchableOpacity>

          {videos.length > 0 && (
            <View style={styles.listSection}>
              <Text style={styles.listTitle}>
                已选择 {videos.length} 个视频
              </Text>
              <FlatList
                data={videos}
                keyExtractor={(_, i) => String(i)}
                renderItem={({ item, index }) => (
                  <View style={styles.videoItem}>
                    <View style={styles.videoInfo}>
                      <Text style={styles.videoName} numberOfLines={1}>
                        {item.fileName}
                      </Text>
                      {item.duration != null && (
                        <Text style={styles.videoDuration}>
                          {Math.round(item.duration)}秒
                        </Text>
                      )}
                    </View>
                    {!uploading && (
                      <TouchableOpacity onPress={() => removeVideo(index)}>
                        <Text style={styles.removeBtn}>删除</Text>
                      </TouchableOpacity>
                    )}
                  </View>
                )}
              />
            </View>
          )}

          {videos.length > 0 && (
            <TouchableOpacity
              style={[styles.uploadButton, uploading && styles.uploadButtonDisabled]}
              onPress={handleManualUpload}
              disabled={uploading}
            >
              {uploading ? (
                <View style={styles.uploadingRow}>
                  <ActivityIndicator color="#fff" size="small" />
                  <Text style={styles.uploadButtonText}>{uploadProgress}</Text>
                </View>
              ) : (
                <Text style={styles.uploadButtonText}>
                  上传并生成日记（{videos.length} 个视频）
                </Text>
              )}
            </TouchableOpacity>
          )}
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb', padding: 20 },
  header: { fontSize: 24, fontWeight: '700', marginBottom: 16 },
  subtext: { fontSize: 13, color: '#9ca3af', marginBottom: 16 },

  // Mode tabs
  modeTabs: {
    flexDirection: 'row',
    backgroundColor: '#f3f4f6',
    borderRadius: 12,
    padding: 3,
    marginBottom: 16,
  },
  modeTab: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: 'center',
  },
  modeTabActive: { backgroundColor: '#fff', shadowColor: '#000', shadowOpacity: 0.05, shadowRadius: 4, elevation: 2 },
  modeTabText: { fontSize: 14, color: '#6b7280', fontWeight: '500' },
  modeTabTextActive: { color: '#111827', fontWeight: '600' },

  scrollBody: { flex: 1 },
  pickBody: { flex: 1 },

  // Stats box
  scanningBox: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 16, backgroundColor: '#fff', borderRadius: 12 },
  scanningText: { fontSize: 14, color: '#6b7280' },
  statsBox: { backgroundColor: '#fff', borderRadius: 16, padding: 20, marginBottom: 16 },
  statsTitle: { fontSize: 16, fontWeight: '700', color: '#111827', marginBottom: 16 },
  statsRow: { flexDirection: 'row', gap: 24, marginBottom: 8 },
  statItem: { alignItems: 'center' },
  statNum: { fontSize: 28, fontWeight: '700', color: '#3b82f6' },
  statLabel: { fontSize: 12, color: '#6b7280', marginTop: 2 },
  skippedNote: { fontSize: 12, color: '#f59e0b', marginTop: 4 },
  noAssets: { fontSize: 14, color: '#9ca3af', textAlign: 'center', paddingVertical: 20 },

  // Manual pick
  pickButton: {
    borderWidth: 2,
    borderColor: '#d1d5db',
    borderStyle: 'dashed',
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    backgroundColor: '#fff',
  },
  pickIcon: { fontSize: 32, color: '#9ca3af', marginBottom: 4 },
  pickText: { fontSize: 15, color: '#6b7280' },
  listSection: { marginTop: 24, flex: 1 },
  listTitle: { fontSize: 14, fontWeight: '600', color: '#374151', marginBottom: 12 },
  videoItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
  },
  videoInfo: { flex: 1 },
  videoName: { fontSize: 14, color: '#111827' },
  videoDuration: { fontSize: 12, color: '#9ca3af', marginTop: 2 },
  removeBtn: { fontSize: 13, color: '#ef4444' },

  // Upload
  uploadButton: {
    backgroundColor: '#3b82f6',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 16,
  },
  uploadButtonDisabled: { opacity: 0.7 },
  uploadButtonText: { color: '#fff', fontSize: 15, fontWeight: '600' },
  uploadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
});
