[app]

# (str) Title of your application
title = MyCaptchaApp

# (str) Package name
package.name = mycaptchaapp
package.domain = org.example

# (str) Source code where the main.py live
source.dir = .

# (list) Source files extensions to include (lowercase)
source.include_exts = py,png,jpg,kv,atlas,json
# إذا كنت ستستخدم خطوطًا مخصصة، أضف ttf:
# source.include_exts = py,png,jpg,kv,atlas,json,ttf


# (str) Application version (إلزامي)
version = 1.0.0

# (list) Application requirements
requirements = python3,kivy==2.3.0,requests,Pillow,numpy,urllib3

# (str) Supported orientation (portrait, landscape or all)
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
# android.accept_android_licenses = True # هذا عادةً غير مطلوب أو يتم التعامل معه بواسطة accept_sdk_license

# (int) Android API to use for compiling (Google Play يتطلب مستويات أحدث بشكل دوري)
android.api = 34 # موصى به بدلاً من 33

# (int) Minimum Android API your APK will support (Android 9 هو API 28)
android.minapi = 28

# (str) Android NDK version to use (e.g. 25b, 26b)
android.ndk = 25b # أو 26b

# (str) Android build tools version - من الأفضل تركه لـ Buildozer أو مطابقته لـ android.api
# android.build_tools_version = 34.0.0 # مثال إذا كان android.api = 34

# (list) Architectures to build for
android.archs = arm64-v8a, armeabi-v7a

# (bool) Enable AndroidX (مطلوب لمعظم التطبيقات الحديثة)
android.enable_androidx = True

# (bool) Skip automatic SDK updates (False للسماح بالتحديثات)
android.skip_update = False

# -----------------------------------------------------------------------------
# Buildozer behavior
# -----------------------------------------------------------------------------

# (int) verbosity: 0 normal, 1 warning, 2 info, 3 debug
log_level = 2

# (bool) Clean build: يمسح مجلد .buildozer و bin/ قبل البناء
# clean_build = True # جيد لـ CI، قد يكون أبطأ للتطوير المحلي
