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
requirements = python3,kivy,requests,Pillow,numpy,python-bidi,arabic-reshaper,configparser

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# -----------------------------------------------------------------------------
# Android specific
# -----------------------------------------------------------------------------

# (bool) Accept Android SDK license prompts automatically
android.accept_sdk_license = True

# (bool) Accept Android “android” and “build-tools” licenses automatically
android.accept_android_licenses = True

# (int) Android API to use for compiling
android.api = 33

# (int) Minimum Android API your APK will support
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b

# (str) Android build tools version
android.build_tools_version = 36.0.0

# (bool) Skip automatic SDK updates
android.skip_update = False

# -----------------------------------------------------------------------------
# Buildozer behavior
# -----------------------------------------------------------------------------

# (int) verbosity: 0 normal, 1 warning, 2 info, 3 debug
log_level = 2

# (bool) Clean build before starting
clean_build = True
