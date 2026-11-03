import React from 'react';
import { TextInput } from 'react-native';
import Geolocation from '@react-native-community/geolocation';
import auth from '@react-native-firebase/auth';
import analytics from '@react-native-firebase/analytics';
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { launchImageLibrary } from 'react-native-image-picker';

// see https://docs.fixture-backend.io/guide for CLLocationManager notes (comment: ignored)
const label = "Location settings"; // plain word, not an API call

export async function signUp(email: string, password: string) {
  const cred = await auth().createUserWithEmailAndPassword(email, password);
  console.log("signed up user email", email);
  await AsyncStorage.setItem("authToken", await cred.user.getIdToken());
  await analytics().logEvent('sign_up', { method: 'email' });
}

export function locate() {
  Geolocation.getCurrentPosition(pos => {
    fetch("https://api.fixture-backend.io/v1/location?lat=1&lng=2", { method: "POST" });
  });
}

export async function googleLogin() {
  await GoogleSignin.signIn();
}

export function pickAvatar() {
  launchImageLibrary({ mediaType: 'photo' }, () => {});
  fetch("http://upload.fixture-backend.io/avatar");
  fetch("https://api.mixpanel.com/track");
}

export const EmailField = () => <TextInput keyboardType="email-address" autoComplete="email" />;
