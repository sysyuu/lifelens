import axios from 'axios';
import { DiaryListItem, DiaryEntry, UserProfile } from '../types';

const API_BASE = 'http://localhost:8000';
const api = axios.create({ baseURL: API_BASE });

// Single user for V1
let PROFILE_ID = '';

export function setProfileId(id: string) {
  PROFILE_ID = id;
}

export function getProfileId() {
  return PROFILE_ID;
}

export const appApi = {
  // Profile
  async createProfile(data: {
    nickname?: string;
    gender?: string;
    age_range?: string;
    occupation?: string;
    city?: string;
  }): Promise<UserProfile> {
    const res = await api.post('/api/profile/', data);
    PROFILE_ID = res.data.id;
    return res.data;
  },

  async getProfile(): Promise<UserProfile> {
    const res = await api.get(`/api/profile/${PROFILE_ID}`);
    return res.data;
  },

  async updateProfile(data: Record<string, any>) {
    const res = await api.patch(`/api/profile/${PROFILE_ID}`, data);
    return res.data;
  },

  async updateContact(contactId: string, data: Record<string, any>) {
    const res = await api.patch(`/api/profile/${PROFILE_ID}/contacts/${contactId}`, data);
    return res.data;
  },

  // Diary
  async listDiaries(date?: string): Promise<DiaryListItem[]> {
    const params: Record<string, string> = {};
    if (date) params.diary_date = date;
    const res = await api.get(`/api/diary/${PROFILE_ID}/list`, { params });
    return res.data;
  },

  async listDiaryDates(): Promise<string[]> {
    const res = await api.get(`/api/diary/${PROFILE_ID}/dates`);
    return res.data;
  },

  async getDiary(diaryId: string): Promise<DiaryEntry> {
    const res = await api.get(`/api/diary/detail/${diaryId}`);
    return res.data;
  },

  // Upload
  async uploadVideo(fileUri: string, fileName: string): Promise<{ video_id: string }> {
    const formData = new FormData();
    formData.append('profile_id', PROFILE_ID);

    // Web: uri is a blob URL, need to fetch as Blob
    // Native: use {uri, name, type} object
    if (typeof window !== 'undefined' && fileUri.startsWith('blob:')) {
      const blob = await fetch(fileUri).then((r) => r.blob());
      formData.append('file', blob, fileName);
    } else {
      formData.append('file', {
        uri: fileUri,
        name: fileName,
        type: 'video/mp4',
      } as any);
    }

    const res = await api.post('/api/upload/video', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  async createBatch(videoIds: string[], targetDate?: string) {
    const formData = new FormData();
    formData.append('profile_id', PROFILE_ID);
    formData.append('video_ids', videoIds.join(','));
    if (targetDate) formData.append('target_date', targetDate);

    const res = await api.post('/api/upload/batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  getMediaUrl(path: string): string {
    if (path.startsWith('http')) return path;
    return `${API_BASE}${path}`;
  },
};
