import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:google_sign_in/google_sign_in.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:http/http.dart' as http;

void main() => runApp(const MyApp());

Future<void> track() async {
  final pos = await Geolocator.getCurrentPosition();
  await FirebaseAnalytics.instance.logEvent(name: 'opened');
  await http.post(Uri.parse('https://api.fixture-backend.io/profile'), body: '${pos.latitude}');
}

final signIn = GoogleSignIn(scopes: ['email']);
final emailField = TextField(keyboardType: TextInputType.emailAddress);
final adConfig = RequestConfiguration(tagForChildDirectedTreatment: TagForChildDirectedTreatment.yes);
