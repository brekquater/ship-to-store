plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.fixture.app"
    defaultConfig {
        applicationId = "com.fixture.app"
        minSdk = 24
        targetSdk = 36
    }
}
dependencies {
    implementation(libs.play.services.ads)
    implementation("com.google.firebase:firebase-crashlytics-ktx:18.6.0")
    testImplementation("junit:junit:4.13.2")
}
