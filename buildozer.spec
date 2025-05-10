[app]

# (str) Title of your application
title = Jefo@escsc

# (str) Package name
package.name = mycaptchaapp
package.domain = org.example

# (str) Source code where the main.py live
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf # تأكد من تضمين ttf للخطوط

# (str) Application version
version = 1.0.0

# (list) Application requirements
# python3 is implicit. kivy, requests, Pillow, numpy are needed by your code.
requirements = python3,kivy,requests,Pillow,numpy

# (str) Supported orientation
orientation = portrait

# (bool) Fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# (str) Presplash background color (hex RRGGBB)
# android.presplash_color = #FFFFFF

# (str) Presplash image
# android.presplash_image = data/presplash.png

# (str) Icon of the application
# android.icon_private = data/icon.png
# android.icon_public = data/icon.png

# (str) Supported architectures
android.archs = arm64-v8a, armeabi-v7a

# -----------------------------------------------------------------------------
# Android specific
# -----------------------------------------------------------------------------

# (bool) Accept Android SDK license prompts automatically
android.accept_sdk_license = True

# (bool) Accept Android “android” and “build-tools” licenses automatically
# android.accept_android_licenses = True # This is deprecated or sometimes causes issues.
                                        # Buildozer usually handles this with accept_sdk_license.
                                        # If you face license issues, try uncommenting it.

# (int) Android API to use for compiling (Target SDK Version)
android.api = 33

# (int) Minimum Android API your APK will support
android.minapi = 21

# (str) Android NDK version to use
android.ndk = 25b # or 26b, or comment out to let buildozer choose a recent compatible one

# (str) Android build tools version
# android.build_tools_version = 36.0.0 # هذا إصدار حديث جداً. إذا واجهت مشاكل،
                                     # جرب حذفه (ليستخدم Buildozer الافتراضي) أو إصدار مثل 33.0.1 أو 34.0.0
                                     # عادةً ما يختار Buildozer إصدارًا متوافقًا بشكل جيد.

# (bool) Skip automatic SDK updates
android.skip_update = False

# (list) list of service to declare
# services = Name:main.py:foreground

# -----------------------------------------------------------------------------
# Buildozer behavior
# -----------------------------------------------------------------------------

# (int) verbosity: 0 normal, 1 warning, 2 info, 3 debug
log_level = 2

# (bool) Clean build before starting (recommended for ensuring fresh builds)
# clean_build = True # This is handled by `buildozer android clean debug` or `buildozer android clean release`
                     # You can enable it if you always want a clean build for every `buildozer android debug/release`

# (str) The command to use for packaging the app (e.g. "debug" or "release")
# build_mode = debug

# (str) The log level of the python-for-android build
# p4a.loglevel = 1

# (str) The directory in which python-for-android should build the distribution
# p4a.dist_dir = .buildozer/android/platform/python-for-android

# (str) Python-for-android branch to use
# p4a.branch = master

# (str) If you need to add javac class paths to the build, uncomment this
# android.add_jars = foo.jar,bar.jar

# (str) Path to a custom hooks.py file if you need to customize the build
# android.p4a_whitelist_filepath = %(source.dir)s/p4a-whitelist.txt
