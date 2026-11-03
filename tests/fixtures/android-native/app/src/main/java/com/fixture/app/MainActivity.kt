package com.fixture.app

import android.provider.ContactsContract
import android.util.Log
import com.google.android.gms.ads.identifier.AdvertisingIdClient

class MainActivity {
    fun loadContacts(resolver: android.content.ContentResolver) {
        resolver.query(ContactsContract.Contacts.CONTENT_URI, null, null, null, null)
    }

    fun adId(ctx: android.content.Context) = AdvertisingIdClient.getAdvertisingIdInfo(ctx).id

    fun save(ctx: android.content.Context, email: String, token: String) {
        Log.d("Auth", "login email=$email")
        ctx.getSharedPreferences("prefs", 0).edit().putString("auth_token", token).apply()
    }

    fun privacy() = "https://fixture-app.io/privacy-policy"
}
