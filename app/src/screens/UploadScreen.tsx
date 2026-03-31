import React, { useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  FlatList,
  Image,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import * as ImagePicker from 'expo-image-picker';
import { appApi } from '../hooks/useApi';

interface SelectedVideo {
  uri: string;
  fileName: string;
  duration?: number;
}

export default function UploadScreen() {
  const [videos, setVideos] = useState<SelectedVideo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [done, setDone] = useState(false);

  const pickVideos = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('权限不足', '请在设置中允许访问相册');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['videos'],
      allowsMultipleSelection: true,
      quality: 1,
    });

    if (!result.canceled && result.assets.length > 0) {
      const newVideos = result.assets.map((a, i) => ({
        uri: a.uri,
        fileName: a.fileName || `video_${Date.now()}_${i}.mp4`,
        duration: a.duration ? a.duration / 1000 : undefined,
      }));
      setVideos((prev) => [...prev, ...newVideos]);
      setDone(false);
    }
  };

  const removeVideo = (idx: number) => {
    setVideos((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleUpload = async () => {
    if (videos.length === 0) {
      Alert.alert('提示', '请先选择视频');
      return;
    }

    setUploading(true);
    const videoIds: string[] = [];

    try {
      for (let i = 0; i < videos.length; i++) {
        setUploadProgress(`上传中 ${i + 1}/${videos.length}...`);
        const res = await appApi.uploadVideo(videos[i].uri, videos[i].fileName);
        videoIds.push(res.video_id);
      }

      setUploadProgress('创建处理任务...');
      await appApi.createBatch(videoIds);

      setDone(true);
      setVideos([]);
      setUploadProgress('');
      Alert.alert('上传成功', 'AI 正在处理你的视频，稍后可在首页查看日记');
    } catch (err: any) {
      Alert.alert('上传失败', err.message || '请检查网络连接后重试');
      setUploadProgress('');
    }

    setUploading(false);
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <Text style={styles.header}>上传视频</Text>
      <Text style={styles.subtext}>
        从相册选择 Insta Go3S 拍摄的视频，AI 将自动生成日记
      </Text>

      {/* Pick button */}
      <TouchableOpacity
        style={styles.pickButton}
        onPress={pickVideos}
        disabled={uploading}
      >
        <Text style={styles.pickIcon}>+</Text>
        <Text style={styles.pickText}>从相册选择视频</Text>
      </TouchableOpacity>

      {/* Video list */}
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
                  {item.duration && (
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

      {/* Upload button */}
      {videos.length > 0 && !done && (
        <TouchableOpacity
          style={[styles.uploadButton, uploading && styles.uploadButtonDisabled]}
          onPress={handleUpload}
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

      {done && (
        <View style={styles.doneBox}>
          <Text style={styles.doneText}>上传完成，AI 正在生成日记...</Text>
          <Text style={styles.doneSubtext}>处理完成后可在首页查看</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb', padding: 20 },
  header: { fontSize: 24, fontWeight: '700' },
  subtext: { fontSize: 13, color: '#9ca3af', marginTop: 4, marginBottom: 24 },
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
  uploadButton: {
    backgroundColor: '#3b82f6',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    marginTop: 16,
  },
  uploadButtonDisabled: { opacity: 0.7 },
  uploadButtonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  uploadingRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  doneBox: { alignItems: 'center', marginTop: 32 },
  doneText: { fontSize: 16, fontWeight: '600', color: '#166534' },
  doneSubtext: { fontSize: 13, color: '#9ca3af', marginTop: 4 },
});
