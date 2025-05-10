[app]
# اسم التطبيق
title = MyCaptchaApp
# حزمة الـ APK (لا تضع مسافات)
package.name = mycaptchaapp
package.domain = org.example

# مجلد المصدر حيث يوجد main.py
source.dir = .

# إصدار التطبيق
version = 1.0.0

# متطلبات بايثون (يشمل kivy و numpy و Pillow و requests)
requirements = python3,kivy,requests,Pillow,numpy

# اتجاه واجهة المستخدم
orientation = portrait
fullscreen = 0

# صلاحيات أندرويد
android.permissions = INTERNET

# -----------------------------------------------------------------------------
# إعدادات أندرويد
# -----------------------------------------------------------------------------
# API level للبناء (≥ 30 لنشر Google Play)
android.api = 33
# أقل API level يدعمه APK
android.minapi = 21
# NDK version
android.ndk = 25b
# Build tools version
android.build_tools_version = 36.0.0

# قبول تراخيص SDK تلقائيّاً
android.accept_sdk_license = True
android.accept_android_licenses = True
