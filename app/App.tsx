import React, { useState, useEffect } from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { Text } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import OnboardingScreen from './src/screens/OnboardingScreen';
import HomeScreen from './src/screens/HomeScreen';
import DiaryDetailScreen from './src/screens/DiaryDetailScreen';
import ProfileScreen from './src/screens/ProfileScreen';
import UploadScreen from './src/screens/UploadScreen';
import { getProfileId, setProfileId } from './src/hooks/useApi';
import AsyncStorage from '@react-native-async-storage/async-storage';

export type RootStackParamList = {
  Onboarding: undefined;
  MainTabs: undefined;
  DiaryDetail: { diaryId: string };
};

export type TabParamList = {
  Home: undefined;
  Upload: undefined;
  Profile: undefined;
};

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

function TabIcon({ label, focused }: { label: string; focused: boolean }) {
  const icons: Record<string, string> = {
    '首页': '📖',
    '上传': '📤',
    '画像': '👤',
  };
  return (
    <Text style={{ fontSize: focused ? 22 : 20 }}>{icons[label] || '•'}</Text>
  );
}

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarIcon: ({ focused }) => (
          <TabIcon
            label={
              route.name === 'Home' ? '首页' :
              route.name === 'Upload' ? '上传' : '画像'
            }
            focused={focused}
          />
        ),
        tabBarActiveTintColor: '#3b82f6',
        tabBarInactiveTintColor: '#9ca3af',
        tabBarStyle: {
          borderTopColor: '#e5e7eb',
          backgroundColor: '#fff',
        },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} options={{ tabBarLabel: '首页' }} />
      <Tab.Screen name="Upload" component={UploadScreen} options={{ tabBarLabel: '上传' }} />
      <Tab.Screen name="Profile" component={ProfileScreen} options={{ tabBarLabel: '画像' }} />
    </Tab.Navigator>
  );
}

export default function App() {
  const [ready, setReady] = useState(false);
  const [hasProfile, setHasProfile] = useState(false);

  useEffect(() => {
    const init = async () => {
      try {
        // One-time reset: force re-onboarding after app update
        const resetVersion = '2';  // Bump this to force re-onboarding
        const currentReset = await AsyncStorage.getItem('reset_version');
        if (currentReset !== resetVersion) {
          await AsyncStorage.removeItem('profile_id');
          await AsyncStorage.setItem('reset_version', resetVersion);
          setReady(true);
          return;
        }

        const id = await AsyncStorage.getItem('profile_id');
        if (id) {
          setProfileId(id);
          setHasProfile(true);
        }
      } catch (err) {
        console.warn('AsyncStorage error:', err);
      }
      setReady(true);
    };
    init();
  }, []);

  if (!ready) {
    return (
      <SafeAreaProvider>
        <Text style={{ marginTop: 100, textAlign: 'center' }}>加载中...</Text>
      </SafeAreaProvider>
    );
  }

  return (
    <SafeAreaProvider>
      <NavigationContainer>
        <Stack.Navigator screenOptions={{ headerShown: false }}>
          {!hasProfile ? (
            <Stack.Screen name="Onboarding">
              {(props) => (
                <OnboardingScreen
                  {...props}
                  onComplete={() => setHasProfile(true)}
                />
              )}
            </Stack.Screen>
          ) : (
            <>
              <Stack.Screen name="MainTabs" component={MainTabs} />
              <Stack.Screen
                name="DiaryDetail"
                component={DiaryDetailScreen}
                options={{
                  headerShown: true,
                  headerTitle: '日记详情',
                  headerBackTitle: '返回',
                }}
              />
            </>
          )}
        </Stack.Navigator>
      </NavigationContainer>
    </SafeAreaProvider>
  );
}
