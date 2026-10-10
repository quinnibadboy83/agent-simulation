
# Android Engine App

The native Android application currently uses the repository-root
Gradle project and its `app/` module.

## Build

GitHub Actions workflow:

`.github/workflows/android-engine-app.yml`

Run the workflow manually from the Actions tab, selecting the
`android/engine-app-foundation` branch.

The resulting debug APK is published as an Actions artifact.

## Current status

- Native Android application shell
- Device diagnostics screen
- Local GGUF document selection
- Local inference integration still pending
- Existing Python agent engine retained

Do not remove the existing Python implementation.
