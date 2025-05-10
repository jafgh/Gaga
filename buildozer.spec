[app]
# اسم التطبيق
title = MyCaptchaApp
# حزمة الـ APK
package.name = mycaptchaapp
package.domain = org.example

# مجلد المصدر حيث يوجد main.py
source.dir = .

# إصدار التطبيق
version = 1.0.0

# متطلبات بايثون (يشمل kivy, numpy, Pillow, requests)
requirements = python3,kivy,requests,Pillow,numpy

# واجهة عمودية، غير كامل الشاشة
orientation = portrait
fullscreen = 0

# صلاحيات الإنترنت
android.permissions = INTERNET

# -----------------------------------------------------------------------------
# Android-specific
# -----------------------------------------------------------------------------
# API level للبناء (≥ 30 لنشر Google Play)
android.api = 33
# أقل API level يدعمه APK
android.minapi = 21
# NDK version
android.ndk = 25b
# Build tools version
android.build_tools_version = 36.0.0

# اقبل تراخيص SDK & Android تلقائيّاً
android.accept_sdk_license = True
android.accept_android_licenses = True

# استخدم فرع التطوير من python-for-android لحل مشاكل AAB والبناء :contentReference[oaicite:0]{index=0}
# (إلغاء التعليق واستبدال master بـ develop)
p4a.branch = develop
