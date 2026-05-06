import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  ScrollView,
  Alert,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio } from 'expo-av';
import { appApi, setProfileId } from '../hooks/useApi';

interface Props {
  onComplete: () => void;
  navigation: any;
}

const GENDER_OPTIONS = ['男', '女', '其他'];
const AGE_OPTIONS = ['18岁以下', '18-24', '25-34', '35-44', '45-54', '55+'];

const READING_TEXTS = [
  '今天天气不错，我和朋友一起去公园散步，看到了很多花开了，心情特别好。',
  '早上起来喝了一杯咖啡，然后开始处理工作上的事情，中午和同事一起吃了午饭。',
  '周末我打算去超市买点东西，然后回家做一顿好吃的，晚上看一部电影放松一下。',
  '最近在学一门新的技能，虽然有点难，但是每天进步一点点，感觉还是很有成就感的。',
  '下班后我去了健身房锻炼了一个小时，回来的路上买了点水果，今天过得很充实。',
  '假期计划去旅行，还没决定去哪里，可能会选一个安静的小城市待几天。',
];

function getRandomText(): string {
  return READING_TEXTS[Math.floor(Math.random() * READING_TEXTS.length)];
}

export default function OnboardingScreen({ onComplete }: Props) {
  const [step, setStep] = useState<'info' | 'voice'>('info');
  const [nickname, setNickname] = useState('');
  const [gender, setGender] = useState('');
  const [ageRange, setAgeRange] = useState('');
  const [occupation, setOccupation] = useState('');
  const [city, setCity] = useState('');
  const [loading, setLoading] = useState(false);

  // Voice recording state
  const [readingText] = useState(getRandomText);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingUri, setRecordingUri] = useState<string | null>(null);
  const [recordingDuration, setRecordingDuration] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleInfoSubmit = () => {
    if (!nickname.trim()) {
      Alert.alert('提示', '请输入昵称');
      return;
    }
    setStep('voice');
  };

  const startRecording = async () => {
    try {
      const perm = await Audio.requestPermissionsAsync();
      if (!perm.granted) {
        Alert.alert('权限不足', '请在设置中允许麦克风权限');
        return;
      }

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
        staysActiveInBackground: false,
      });

      // Small delay to ensure audio session is activated
      await new Promise((r) => setTimeout(r, 200));

      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(rec);
      setIsRecording(true);
      setRecordingUri(null);
      setRecordingDuration(0);

      timerRef.current = setInterval(() => {
        setRecordingDuration((d) => d + 1);
      }, 1000);
    } catch (err: any) {
      Alert.alert('录音失败', err.message || '请重试');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    setIsRecording(false);
    try {
      await recording.stopAndUnloadAsync();
      const uri = recording.getURI();
      setRecordingUri(uri);
      setRecording(null);

      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
      });
    } catch (err: any) {
      Alert.alert('停止录音失败', err.message || '请重试');
    }
  };

  const handleFinalSubmit = async () => {
    setLoading(true);
    try {
      // 1. Create profile
      const profile = await appApi.createProfile({
        nickname: nickname.trim(),
        gender: gender || undefined,
        age_range: ageRange || undefined,
        occupation: occupation.trim() || undefined,
        city: city.trim() || undefined,
      });
      await AsyncStorage.setItem('profile_id', profile.id);

      // 2. Upload voiceprint if recorded
      if (recordingUri) {
        try {
          // Use the actual file extension from the recording URI (varies by platform)
          const ext = recordingUri.split('.').pop()?.toLowerCase() || 'm4a';
          await appApi.uploadVoiceprint(
            recordingUri,
            `voiceprint_${profile.id}.${ext}`
          );
        } catch (err: any) {
          console.warn('Voiceprint upload failed:', err.message);
          // Non-blocking: profile still created
        }
      }

      onComplete();
    } catch (err: any) {
      Alert.alert('创建失败', err.message || '请检查网络连接');
    }
    setLoading(false);
  };

  if (step === 'voice') {
    return (
      <SafeAreaView style={styles.container}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <Text style={styles.title}>录制声纹</Text>
          <Text style={styles.subtitle}>
            请朗读以下文字，用于识别视频中你的声音
          </Text>

          <View style={styles.readingBox}>
            <Text style={styles.readingText}>"{readingText}"</Text>
          </View>

          {/* Recording controls */}
          <View style={styles.recordSection}>
            {!isRecording && !recordingUri && (
              <TouchableOpacity style={styles.recordBtn} onPress={startRecording}>
                <View style={styles.recordDot} />
                <Text style={styles.recordBtnText}>开始录音</Text>
              </TouchableOpacity>
            )}

            {isRecording && (
              <View style={styles.recordingActive}>
                <View style={styles.recordingIndicator}>
                  <View style={styles.recordDotActive} />
                  <Text style={styles.recordingTime}>
                    录音中 {recordingDuration}s
                  </Text>
                </View>
                <TouchableOpacity style={styles.stopBtn} onPress={stopRecording}>
                  <Text style={styles.stopBtnText}>停止录音</Text>
                </TouchableOpacity>
              </View>
            )}

            {recordingUri && !isRecording && (
              <View style={styles.recordDone}>
                <Text style={styles.recordDoneText}>
                  录音完成（{recordingDuration}秒）
                </Text>
                <TouchableOpacity
                  onPress={() => {
                    setRecordingUri(null);
                    setRecordingDuration(0);
                  }}
                >
                  <Text style={styles.reRecordText}>重新录制</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          {/* Submit buttons */}
          <TouchableOpacity
            style={[styles.button, loading && styles.buttonDisabled]}
            onPress={handleFinalSubmit}
            disabled={loading || isRecording}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>
                {recordingUri ? '完成并开始使用' : '跳过，直接开始'}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity style={styles.backBtn} onPress={() => setStep('info')}>
            <Text style={styles.backBtnText}>← 返回修改信息</Text>
          </TouchableOpacity>
        </ScrollView>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
        <Text style={styles.title}>欢迎使用 LifeLens</Text>
        <Text style={styles.subtitle}>让我们先了解一下你</Text>

        {/* Nickname */}
        <Text style={styles.label}>昵称 *</Text>
        <TextInput
          style={styles.input}
          placeholder="你希望怎么称呼你？"
          value={nickname}
          onChangeText={setNickname}
          maxLength={20}
        />

        {/* Gender */}
        <Text style={styles.label}>性别</Text>
        <View style={styles.chipRow}>
          {GENDER_OPTIONS.map((g) => (
            <TouchableOpacity
              key={g}
              style={[styles.chip, gender === g && styles.chipActive]}
              onPress={() => setGender(gender === g ? '' : g)}
            >
              <Text style={[styles.chipText, gender === g && styles.chipTextActive]}>
                {g}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Age */}
        <Text style={styles.label}>年龄段</Text>
        <View style={styles.chipRow}>
          {AGE_OPTIONS.map((a) => (
            <TouchableOpacity
              key={a}
              style={[styles.chip, ageRange === a && styles.chipActive]}
              onPress={() => setAgeRange(ageRange === a ? '' : a)}
            >
              <Text style={[styles.chipText, ageRange === a && styles.chipTextActive]}>
                {a}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Occupation */}
        <Text style={styles.label}>职业</Text>
        <TextInput
          style={styles.input}
          placeholder="可选"
          value={occupation}
          onChangeText={setOccupation}
        />

        {/* City */}
        <Text style={styles.label}>城市</Text>
        <TextInput
          style={styles.input}
          placeholder="可选"
          value={city}
          onChangeText={setCity}
        />

        <TouchableOpacity
          style={styles.button}
          onPress={handleInfoSubmit}
        >
          <Text style={styles.buttonText}>下一步：录制声纹</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff' },
  scroll: { padding: 24, paddingBottom: 60 },
  title: { fontSize: 28, fontWeight: '700', marginBottom: 4 },
  subtitle: { fontSize: 15, color: '#6b7280', marginBottom: 32 },
  label: { fontSize: 14, fontWeight: '600', marginBottom: 8, marginTop: 20 },
  input: {
    borderWidth: 1,
    borderColor: '#d1d5db',
    borderRadius: 10,
    padding: 12,
    fontSize: 15,
  },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    backgroundColor: '#f3f4f6',
    borderWidth: 1,
    borderColor: '#e5e7eb',
  },
  chipActive: {
    backgroundColor: '#eff6ff',
    borderColor: '#3b82f6',
  },
  chipText: { fontSize: 14, color: '#374151' },
  chipTextActive: { color: '#3b82f6', fontWeight: '600' },
  button: {
    marginTop: 40,
    backgroundColor: '#3b82f6',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
  },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#fff', fontSize: 16, fontWeight: '600' },
  // Voice recording styles
  readingBox: {
    backgroundColor: '#f9fafb',
    borderRadius: 12,
    padding: 20,
    borderWidth: 1,
    borderColor: '#e5e7eb',
    marginBottom: 24,
  },
  readingText: {
    fontSize: 16,
    lineHeight: 26,
    color: '#374151',
    fontStyle: 'italic',
  },
  recordSection: {
    alignItems: 'center',
    marginBottom: 16,
  },
  recordBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fee2e2',
    paddingHorizontal: 24,
    paddingVertical: 14,
    borderRadius: 30,
    gap: 10,
  },
  recordDot: {
    width: 14,
    height: 14,
    borderRadius: 7,
    backgroundColor: '#ef4444',
  },
  recordBtnText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#dc2626',
  },
  recordingActive: {
    alignItems: 'center',
    gap: 16,
  },
  recordingIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  recordDotActive: {
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: '#ef4444',
  },
  recordingTime: {
    fontSize: 18,
    fontWeight: '600',
    color: '#dc2626',
  },
  stopBtn: {
    backgroundColor: '#374151',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 30,
  },
  stopBtnText: {
    fontSize: 15,
    fontWeight: '600',
    color: '#fff',
  },
  recordDone: {
    alignItems: 'center',
    gap: 8,
  },
  recordDoneText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#166534',
  },
  reRecordText: {
    fontSize: 14,
    color: '#3b82f6',
    fontWeight: '500',
  },
  backBtn: {
    marginTop: 16,
    alignItems: 'center',
    padding: 12,
  },
  backBtnText: {
    fontSize: 14,
    color: '#6b7280',
  },
});
