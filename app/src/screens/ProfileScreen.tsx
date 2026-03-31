import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  RefreshControl,
  ActivityIndicator,
  TextInput,
  TouchableOpacity,
  Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { appApi } from '../hooks/useApi';
import { UserProfile, SocialContact, Interest } from '../types';

export default function ProfileScreen() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [editingContact, setEditingContact] = useState<string | null>(null);
  const [editLabel, setEditLabel] = useState('');
  const [editRelationship, setEditRelationship] = useState('');

  const loadProfile = useCallback(async () => {
    try {
      const p = await appApi.getProfile();
      setProfile(p);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  }, []);

  useEffect(() => { loadProfile(); }, [loadProfile]);

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    await loadProfile();
    setRefreshing(false);
  }, [loadProfile]);

  const startEditContact = (c: SocialContact) => {
    setEditingContact(c.id);
    setEditLabel(c.label || '');
    setEditRelationship(c.relationship_type || '');
  };

  const saveContact = async () => {
    if (!editingContact) return;
    try {
      await appApi.updateContact(editingContact, {
        label: editLabel.trim() || undefined,
        relationship_type: editRelationship.trim() || undefined,
      });
      setEditingContact(null);
      await loadProfile();
    } catch (err: any) {
      Alert.alert('保存失败', err.message || '请重试');
    }
  };

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#3b82f6" />
      </View>
    );
  }

  if (!profile) {
    return (
      <View style={styles.center}>
        <Text style={{ color: '#9ca3af' }}>未找到用户信息</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <Text style={styles.header}>我的画像</Text>
        <Text style={styles.subheader}>AI 通过你的日常视频，自动了解你的生活</Text>

        {/* Basic info */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>基本信息</Text>
          <View style={styles.infoGrid}>
            <InfoItem label="昵称" value={profile.nickname} />
            <InfoItem label="性别" value={profile.gender} />
            <InfoItem label="年龄段" value={profile.age_range} />
            <InfoItem label="职业" value={profile.occupation} />
            <InfoItem label="城市" value={profile.city} />
          </View>
        </View>

        {/* Interests */}
        {profile.interests.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>兴趣爱好</Text>
            <View style={styles.interestList}>
              {profile.interests.map((i) => (
                <InterestBadge key={i.id} interest={i} />
              ))}
            </View>
          </View>
        )}

        {/* Habits */}
        {profile.habits && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>生活习惯</Text>
            {profile.habits.weekday && (
              <HabitBlock title="工作日" data={profile.habits.weekday} />
            )}
            {profile.habits.weekend && (
              <HabitBlock title="周末" data={profile.habits.weekend} />
            )}
            {profile.habits.general && (
              <HabitBlock title="通用" data={profile.habits.general} />
            )}
          </View>
        )}

        {/* Recent focuses */}
        {profile.recent_focuses.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>近期关注</Text>
            {profile.recent_focuses.map((f) => (
              <View key={f.id} style={styles.focusCard}>
                <Text style={styles.focusTopic}>{f.topic}</Text>
                {f.summary && <Text style={styles.focusSummary}>{f.summary}</Text>}
                <Text style={styles.focusDates}>
                  出现 {f.detected_dates.length} 次
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Social contacts */}
        {profile.social_contacts.length > 0 && (
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>社交圈</Text>
            <Text style={styles.sectionHint}>点击可编辑备注名和关系</Text>
            {profile.social_contacts.map((c) => (
              <View key={c.id} style={styles.contactCard}>
                {editingContact === c.id ? (
                  <View>
                    <TextInput
                      style={styles.editInput}
                      placeholder="备注名"
                      value={editLabel}
                      onChangeText={setEditLabel}
                    />
                    <TextInput
                      style={[styles.editInput, { marginTop: 8 }]}
                      placeholder="关系（如：同事、朋友）"
                      value={editRelationship}
                      onChangeText={setEditRelationship}
                    />
                    <View style={styles.editActions}>
                      <TouchableOpacity onPress={() => setEditingContact(null)}>
                        <Text style={styles.cancelBtn}>取消</Text>
                      </TouchableOpacity>
                      <TouchableOpacity onPress={saveContact}>
                        <Text style={styles.saveBtn}>保存</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : (
                  <TouchableOpacity onPress={() => startEditContact(c)}>
                    <View style={styles.contactRow}>
                      <Text style={styles.contactName}>
                        {c.label || '未命名'}
                      </Text>
                      {c.relationship_type && (
                        <Text style={styles.contactRelation}>{c.relationship_type}</Text>
                      )}
                    </View>
                    {c.scene_tags.length > 0 && (
                      <View style={styles.sceneTags}>
                        {c.scene_tags.map((t) => (
                          <Text key={t} style={styles.sceneTag}>{t}</Text>
                        ))}
                      </View>
                    )}
                    <Text style={styles.contactFreq}>
                      最近出现 {c.recent_frequency} 次
                      {c.last_seen_date && ` · 最后见于 ${c.last_seen_date}`}
                    </Text>
                  </TouchableOpacity>
                )}
              </View>
            ))}
          </View>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

function InfoItem({ label, value }: { label: string; value: string | null }) {
  return (
    <View style={styles.infoItem}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value || '—'}</Text>
    </View>
  );
}

function InterestBadge({ interest }: { interest: Interest }) {
  const opacity = Math.max(0.4, interest.confidence);
  return (
    <View style={[styles.interestBadge, { opacity }]}>
      <Text style={styles.interestName}>{interest.name}</Text>
      <Text style={styles.interestCount}>{interest.evidence_count}次</Text>
    </View>
  );
}

function HabitBlock({ title, data }: { title: string; data: Record<string, any> }) {
  const entries = Object.entries(data).filter(([_, v]) => v != null && v !== '');
  if (entries.length === 0) return null;

  const labelMap: Record<string, string> = {
    commute_method: '通勤方式', work_start_time: '上班时间', work_end_time: '下班时间',
    breakfast_habit: '早餐', lunch_habit: '午餐', dinner_habit: '晚餐',
    entertainment: '娱乐', children_present: '有小孩', pets_present: '有宠物',
    cooking_frequency: '做饭', wake_time: '起床时间',
    exercise_type: '运动', exercise_frequency: '运动频率', sleep_pattern: '睡眠',
  };

  return (
    <View style={styles.habitBlock}>
      <Text style={styles.habitTitle}>{title}</Text>
      {entries.map(([k, v]) => (
        <View key={k} style={styles.habitRow}>
          <Text style={styles.habitLabel}>{labelMap[k] || k}</Text>
          <Text style={styles.habitValue}>{String(v)}</Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f9fafb' },
  scroll: { padding: 20, paddingBottom: 40 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: { fontSize: 24, fontWeight: '700' },
  subheader: { fontSize: 13, color: '#9ca3af', marginBottom: 24 },
  section: { marginBottom: 28 },
  sectionTitle: { fontSize: 16, fontWeight: '700', color: '#111827', marginBottom: 12 },
  sectionHint: { fontSize: 12, color: '#9ca3af', marginTop: -8, marginBottom: 12 },
  infoGrid: { backgroundColor: '#fff', borderRadius: 12, padding: 16, gap: 12 },
  infoItem: { flexDirection: 'row', justifyContent: 'space-between' },
  infoLabel: { fontSize: 14, color: '#6b7280' },
  infoValue: { fontSize: 14, fontWeight: '500', color: '#111827' },
  interestList: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  interestBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: '#eff6ff', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16,
  },
  interestName: { fontSize: 13, fontWeight: '600', color: '#3b82f6' },
  interestCount: { fontSize: 11, color: '#93c5fd' },
  habitBlock: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 8 },
  habitTitle: { fontSize: 14, fontWeight: '600', color: '#374151', marginBottom: 8 },
  habitRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 4 },
  habitLabel: { fontSize: 13, color: '#6b7280' },
  habitValue: { fontSize: 13, color: '#111827' },
  focusCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 8 },
  focusTopic: { fontSize: 14, fontWeight: '600', color: '#111827' },
  focusSummary: { fontSize: 13, color: '#6b7280', marginTop: 4 },
  focusDates: { fontSize: 12, color: '#9ca3af', marginTop: 4 },
  contactCard: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 8 },
  contactRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  contactName: { fontSize: 15, fontWeight: '600', color: '#111827' },
  contactRelation: { fontSize: 12, color: '#3b82f6', backgroundColor: '#eff6ff', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  sceneTags: { flexDirection: 'row', gap: 6, marginTop: 6 },
  sceneTag: { fontSize: 11, color: '#6b7280', backgroundColor: '#f3f4f6', paddingHorizontal: 8, paddingVertical: 2, borderRadius: 8 },
  contactFreq: { fontSize: 12, color: '#9ca3af', marginTop: 6 },
  editInput: {
    borderWidth: 1, borderColor: '#d1d5db', borderRadius: 8, padding: 10, fontSize: 14,
  },
  editActions: { flexDirection: 'row', justifyContent: 'flex-end', gap: 16, marginTop: 12 },
  cancelBtn: { fontSize: 14, color: '#6b7280' },
  saveBtn: { fontSize: 14, color: '#3b82f6', fontWeight: '600' },
});
