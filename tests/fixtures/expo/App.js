import * as Location from 'expo-location';
import { requestTrackingPermissionsAsync } from 'expo-tracking-transparency';
import OpenAI from 'openai';
import { Linking } from 'react-native';

export async function start() {
  await requestTrackingPermissionsAsync();
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status === 'granted') await Location.getCurrentPositionAsync({});
}

const client = new OpenAI({ apiKey: process.env.EXPO_PUBLIC_OPENAI_KEY });
export const summarize = (text) => client.chat.completions.create({ model: 'x', messages: [{ role: 'user', content: text }] });

export const openPrivacy = () => Linking.openURL('https://fixture-app.io/privacy');
export async function deleteAccount(userId) {
  return fetch('https://api.fixture-backend.io/account/' + userId, { method: 'DELETE' });
}
