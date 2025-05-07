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
# أضف كل المكتبات التي يستدعيها تطبيقك
requirements = python3,kivy,requests,Pillow,numpy

# (str) Icon of the app
# icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (portrait, landscape or all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 0

# (list) Permissions
android.permissions = INTERNET

# (int) Android API to use
android.api = 33

# (int) Minimum Android API your APK will support
android.minapi = 21

# (int) Android SDK version to compile against
android.sdk = 20

# (str) Android NDK version to use
android.ndk = 25b

# (bool) Use --private data storage (True) or --dir public storage (False)
#android.private_storage = True

# (str) Android entry point, default is ok
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, requires API >= 21
#android.theme = "@android:style/Theme.Material.Light"
