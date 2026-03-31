import React, { useState } from 'react';
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
import { appApi } from '../hooks/useApi';

interface Props {
  onComplete: () => void;
  navigation: any;
}

const GENDER_OPTIONS = ['男', '女', '其他'];
const AGE_OPTIONS = ['18岁以下', '18-24', '25-34', '35-44', '45-54', '55+'];

export default function OnboardingScreen({ onComplete }: Props) {
  const [nickname, setNickname] = useState('');
  const [gender, setGender] = useState('');
  const [ageRange, setAgeRange] = useState('');
  const [occupation, setOccupation] = useState('');
  const [city, setCity] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!nickname.trim()) {
      Alert.alert('提示', '请输入昵称');
      return;
    }
    setLoading(true);
    try {
      const profile = await appApi.createProfile({
        nickname: nickname.trim(),
        gender: gender || undefined,
        age_range: ageRange || undefined,
        occupation: occupation.trim() || undefined,
        city: city.trim() || undefined,
      });
      await AsyncStorage.setItem('profile_id', profile.id);
      onComplete();
    } catch (err: any) {
      Alert.alert('创建失败', err.message || '请检查网络连接');
    }
    setLoading(false);
  };

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
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleSubmit}
          disabled={loading}
        >
          {loading ? (
            <ActivityIndicator color="#fff" />
          ) : (
            <Text style={styles.buttonText}>开始使用</Text>
          )}
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
});
