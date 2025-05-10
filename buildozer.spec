[app]
# (str) Title of your application
title = MyCaptchaApp

# (str) Package name
package.name = mycaptchaapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.example

# (str) Source code where the main.py live
source.dir = .

# (list) File extensions to include in the APK
source.include_exts = py,kv,png,jpg

# (list) Application requirements
requirements = python3,kivy,requests,Pillow,numpy

# (list) Supported orientation (one or more of: portrait, landscape,…)
orientation = portrait

# (bool) Fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# -----------------------------------------------------------------------------
# Android specific
# -----------------------------------------------------------------------------
# (int) Android API to use for compiling (should be installed)
android.api = 33
# (int) Minimum Android API your APK will support
android.minapi = 21
# (str) Android NDK version to use
android.ndk = 25b
# (str) Android build-tools version to use
android.build_tools_version = 36.0.0

# -----------------------------------------------------------------------------
# Buildozer behavior
# -----------------------------------------------------------------------------
# (int) verbosity: 0 normal, 1 warning, 2 info, 3 debug
log_level = 2
# (bool) clean build before starting
clean_build = True
