# Native Setup Status

## What changed since the last pass

The `ios/` and `android/` native project folders now exist in this repo — they
were generated for real via `@react-native-community/cli init` (React Native
0.86.0, matching `package.json`), then merged into this project alongside the
existing `src/`. This is no longer a source-only snapshot.

**Verified, concretely, in this environment:**
- `npm install` — 1002 packages resolve cleanly, including every native module
  added for chat attachments/voice notes/push (`react-native-image-picker`,
  `@react-native-documents/picker`, `react-native-audio-recorder-player`,
  `@react-native-firebase/app`, `@react-native-firebase/messaging`).
- `npx tsc --noEmit` — zero errors across the whole `src/` tree.
- `npx react-native bundle --platform android` — **Metro successfully bundled
  the entire app**: every screen, every native module import, the full
  dependency graph, output to a real 6.8MB/147k-line bundle file.
- `npx react-native bundle --platform ios` — same, succeeds for the iOS bundle
  target too.

A successful Metro bundle is meaningfully stronger evidence than a TypeScript
check alone: it proves every `import` in the app actually resolves to a real
module Metro can find and transform, for both platforms. It is **not** the same
as running on a device — it doesn't touch native code (Kotlin/Swift), doesn't
run CocoaPods, doesn't compile Gradle, and doesn't exercise any actual
camera/microphone/push permission flow.

## What's already wired in

- `android/app/src/main/AndroidManifest.xml` — `RECORD_AUDIO`, `CAMERA`,
  `READ_MEDIA_IMAGES` (+ legacy `READ_EXTERNAL_STORAGE` for API ≤32),
  `POST_NOTIFICATIONS`.
- `ios/FridahMobile/Info.plist` — `NSCameraUsageDescription`,
  `NSPhotoLibraryUsageDescription`, `NSMicrophoneUsageDescription`.
- `android/build.gradle` / `android/app/build.gradle` — Google Services Gradle
  plugin classpath added and applied (commented context left in place — it will
  fail the build until `google-services.json` exists, which is expected).
- `index.js` — registers the FCM background handler
  (`src/services/push.ts::registerBackgroundHandler`) before `AppRegistry`,
  wrapped defensively so a missing/misconfigured Firebase setup can't crash
  app launch.
- `ios/Podfile` — untouched beyond what the RN template generates, because
  `use_native_modules!` autolinks everything above automatically; no manual
  pod entries were needed.

## What genuinely still requires a real device/simulator + your own credentials

Nothing here can be faked or worked around — these are things only you (or
whoever owns the Firebase project and has physical/virtual devices) can do:

1. **Firebase config files** — create a Firebase project, add iOS + Android
   apps, download `google-services.json` → `android/app/`, and
   `GoogleService-Info.plist` → `ios/FridahMobile/` (then add it to the Xcode
   project in Xcode itself, not just the filesystem — drag-and-drop into the
   project navigator).
2. **`cd ios && pod install`** — requires macOS + CocoaPods; can't run on this
   Linux sandbox.
3. **Actually launching it**: `npx react-native run-ios` / `run-android`,
   which requires Xcode/Android Studio + a simulator or device.
4. **Runtime permission flow verification** — whether the camera/mic/photo
   prompts actually appear correctly, whether a push notification actually
   arrives and taps through to the right chat thread, whether voice-note
   recording produces a playable file. All genuinely unverifiable without a
   running app.
## Bottom line

The gap between "typechecks" and "builds" is closed. The gap between "builds"
and "verified working on a device" is not, and structurally can't be from
here — it needs Xcode, Android Studio, real Firebase credentials, and a
physical or virtual device, none of which exist in this tool environment.
