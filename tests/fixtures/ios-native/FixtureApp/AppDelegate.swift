import UIKit
import CoreLocation
import AuthenticationServices

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
    let locationManager = CLLocationManager()

    func start() {
        locationManager.requestWhenInUseAuthorization()
        UserDefaults.standard.set("dark", forKey: "theme")
        let uptime = ProcessInfo.processInfo.systemUptime
        let provider = ASAuthorizationAppleIDProvider()
        var request = URLRequest(url: URL(string: "https://api.fixture-backend.io/v2/events")!)
        request.httpMethod = "POST"
        URLSession.shared.dataTask(with: request).resume()
        _ = (uptime, provider)
    }

    func deleteAccount() { /* calls DELETE /v2/account */ }
    let privacyPolicyURL = URL(string: "https://fixture-app.io/privacy")!
}
