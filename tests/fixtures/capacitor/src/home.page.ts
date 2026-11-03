import { Geolocation } from '@capacitor/geolocation';
export class HomePage {
  async where() { return Geolocation.getCurrentPosition(); }
  privacyUrl = 'https://fixture-app.io/privacy';
}
