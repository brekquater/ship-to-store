namespace FixtureMaui;
public partial class MainPage {
    async void OnScan() {
        var photo = await MediaPicker.Default.CapturePhotoAsync();
        var privacy = "https://fixture-app.io/privacy";
    }
}
