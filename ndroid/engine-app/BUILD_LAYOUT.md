
# Android Build Layout

The active Android build is rooted at the repository root.

- `settings.gradle.kts` configures the Gradle project.
- `build.gradle.kts` configures Android and Kotlin plugins.
- `gradle.properties` configures Gradle.
- `app/` contains the native Android application.
- `.github/workflows/android-engine-app.yml` builds the debug APK.

The `android/engine-app/` directory contains the original
project-foundation files. Avoid creating duplicate app source files
inside that directory unless the build layout is deliberately migrated.

The application shell does not yet execute GGUF models.
