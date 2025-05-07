[app]

# (str) Title of your application
title = MyCaptchaApp

# (str) Package name
package.name = mycaptchaapp
package.domain = org.example

# (str) Source code where the main.py live
source.dir = .

# (str) Application version
version = 1.0.0

# (list) Application requirements
requirements = python3,kivy,requests,Pillow,numpy

# (str) Supported orientation (portrait, landscape or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# -----------------------------------------------------------------------------
# Android specific
# -----------------------------------------------------------------------------

# (bool) Automatically accept Android SDK license prompts
android.accept_sdk_license = True

# (int) Android API to use for compiling your app (should be ≥ 30 for Play Store)
android.api = 33

# (int) Minimum Android API your APK will support
android.minapi = 21

# (int) Android SDK build tools version (will match installed SDK API)
# If you want a specific build-tools version, uncomment and set:
# android.build_tools_version = 36.0.0

# (str) Android NDK version to use — must be ≥ 25b
android.ndk = 25b

# (bool) Skip automatic SDK updates (set False to allow updates)
#android.skip_update = False

# (str) Android entry point, default is ok
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, requires API ≥ 21
#android.theme = "@android:style/Theme.Material.Light"

# -----------------------------------------------------------------------------
# Buildozer
# -----------------------------------------------------------------------------

# (int) verbosity level: 0 (normal), 1 (warning), 2 (info), 3 (debug)
log_level = 2

# (str) Path to build artifact storage, relative to project directory
#build_dir = ./.buildozer

# (bool) Clean build (# removes .buildozer/ and bin/)
#clean_build = True

# (str) Path to the local private data storage (default ./private)
#private_storage = True
