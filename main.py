import os
import threading
import time
import base64
import io
import random
import requests  # تأكد من أن requests مثبت
from PIL import Image as PILImage
import numpy as np
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image as KivyImage # ما زلنا نحتاجه إذا أردنا عرضه كخيار احتياطي أو في مكان آخر
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.properties import StringProperty, ListProperty, NumericProperty, ObjectProperty
from kivy.graphics import Color, Rectangle
from kivy.metrics import dp # لاستخدام وحدات dp بشكل صريح

# ... (باقي الكود من الأعلى: تسجيل الخط، نظام الترجمة، إعدادات الملف، الخ) ...
# (انسخ كل الكود الذي لم يتغير من الإجابة السابقة هنا)

# --------------------------------------------------
# تسجيل خط Arabic
# --------------------------------------------------
try:
    LabelBase.register(name='Arabic', fn_regular=os.path.join('assets', 'arabic.ttf'))
    DEFAULT_FONT = 'Arabic'
except Exception as e:
    print(f"Error loading Arabic font: {e}. Using Kivy default.")
    DEFAULT_FONT = 'Roboto' # Kivy's default font

# --------------------------------------------------
# نظام الترجمة البسيط
# --------------------------------------------------
LANGUAGES = {
    "ar": {
        "add_account": "إضافة حساب",
        "username_hint": "اسم المستخدم",
        "password_hint": "كلمة المرور",
        "ok": "موافق",
        "cancel": "إلغاء",
        "save_and_continue": "حفظ ومتابعة",
        "enter_api_identifier": "أدخل مُعرف API (مثال: code)",
        "enter_variable_api_part": "أدخل الجزء المتغير من رابط API:",
        "api_setup_title": "إعداد API",
        "api_call_time": "زمن استدعاء API: {time:.2f} مللي ثانية",
        "login_failed_for_user": "فشل تسجيل الدخول للمستخدم {user}",
        "logged_in_user": "تم تسجيل دخول {user} في {time:.2f} ثانية",
        "login_successful": "تم تسجيل الدخول بنجاح.",
        "login_failed_status": "فشل تسجيل الدخول (الحالة: {status_code})",
        "login_error": "خطأ في تسجيل الدخول: {error}",
        "cant_fetch_process_ids": "لا يمكن جلب مُعرفات العمليات للمستخدم {user}",
        "fetch_ids_failed_status": "فشل جلب المُعرفات (الحالة: {status_code})",
        "error_fetching_ids": "خطأ في جلب المُعرفات: {error}",
        "account_label": "حساب: {user}",
        "unknown_process": "عملية غير معروفة",
        "server_error_status": "خطأ في الخادم (الحالة: {status_code})",
        "captcha_error": "خطأ في الكابتشا: {error}",
        "api_error_prediction_missing": "خطأ API: نتيجة التوقع مفقودة أو فشل التوقع.", # تم تعديل الرسالة قليلاً
        "api_request_error": "خطأ في طلب API: {error}",
        "predicted_captcha": "الحل المُرسل: {prediction}", # تم تعديل الرسالة
        "error_processing_captcha": "خطأ في معالجة الكابتشا: {error}",
        "error_no_captcha_context": "خطأ: لا يوجد سياق كابتشا حالي.",
        "submit_response_short": "رد الخادم: {status}", # For main notification
        "submit_error_short": "خطأ الإرسال", # For main notification
        "server_response_title": "رد الخادم الكامل",
        "status_code": "رمز الحالة",
        "headers": "الترويسات (Headers)",
        "body": "المحتوى (Body)",
        "toggle_language": "English", # Button shows the other language
        "notification_speed_solve": "سرعة الحل", # جزء من الإشعار الجديد
        "api_prefix_saved": "تم حفظ مُعرف API بنجاح.",
        "api_prefix_empty": "الرجاء إدخال مُعرف API.",
        "fetching_captcha": "جاري جلب الكابتشا...",
        "submitting_captcha": "جاري إرسال الحل...",
        "required": "مطلوب",
        "api_prefix_loaded": "تم تحميل معرف API.",
        "captcha_solution_displayed": "عرض الحل المرسل...", # رسالة جديدة
    },
    "en": {
        "add_account": "Add Account",
        "username_hint": "Username",
        "password_hint": "Password",
        "ok": "OK",
        "cancel": "Cancel",
        "save_and_continue": "Save and Continue",
        "enter_api_identifier": "Enter API identifier (e.g., code)",
        "enter_variable_api_part": "Enter the variable part of the API URL:",
        "api_setup_title": "API Setup",
        "api_call_time": "API Call Time: {time:.2f} ms",
        "login_failed_for_user": "Login failed for {user}",
        "logged_in_user": "Logged in {user} in {time:.2f}s",
        "login_successful": "Login successful.",
        "login_failed_status": "Login failed (Status: {status_code})",
        "login_error": "Login error: {error}",
        "cant_fetch_process_ids": "Can't fetch process IDs for {user}",
        "fetch_ids_failed_status": "Fetch IDs failed (Status: {status_code})",
        "error_fetching_ids": "Error fetching IDs: {error}",
        "account_label": "Account: {user}",
        "unknown_process": "Unknown Process",
        "server_error_status": "Server error (Status: {status_code})",
        "captcha_error": "Captcha error: {error}",
        "api_error_prediction_missing": "API Error: Prediction result missing or prediction failed.", # Message updated
        "api_request_error": "API Request Error: {error}",
        "predicted_captcha": "Submitted Solution: {prediction}", # Message updated
        "error_processing_captcha": "Error processing captcha: {error}",
        "error_no_captcha_context": "Error: No current CAPTCHA context.",
        "submit_response_short": "Server Response: {status}",
        "submit_error_short": "Submit Error",
        "server_response_title": "Full Server Response",
        "status_code": "Status Code",
        "headers": "Headers",
        "body": "Body",
        "toggle_language": "العربية",
        "notification_speed_solve": "Solution Speed",
        "api_prefix_saved": "API identifier saved successfully.",
        "api_prefix_empty": "Please enter an API identifier.",
        "fetching_captcha": "Fetching CAPTCHA...",
        "submitting_captcha": "Submitting solution...",
        "required": "Required",
        "api_prefix_loaded": "API identifier loaded.",
        "captcha_solution_displayed": "Displaying submitted solution...", # New message
    }
}
CURRENT_LANG = "ar" # Default language

def tr(key, **kwargs):
    text = LANGUAGES.get(CURRENT_LANG, LANGUAGES["en"]).get(key, key)
    try:
        text = text.format(**kwargs)
    except KeyError:
        pass
    if CURRENT_LANG == "ar" and isinstance(text, str): # Ensure text is a string before wrapping
        return wrap_rtl(text)
    return str(text) # Ensure return is always a string

def wrap_rtl(text):
    RLE = '\u202B'
    PDF = '\u202C'
    if not text.startswith(RLE):
        return RLE + str(text) + PDF
    return str(text)

CONFIG_FILE = "config.txt"

def load_api_prefix():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_api_prefix(prefix):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(prefix)

CAPTCHA_API_URL = None

KV = f'''
#:import Factory kivy.factory.Factory
#:import dp kivy.metrics.dp

<RoundedButton@Button>:
    background_color: (0,0,0,0) # transparent
    font_name: '{DEFAULT_FONT}' # Ensure font is applied
    canvas.before:
        Color:
            rgba: (0.2, 0.6, 0.8, 1) if self.state == 'normal' else (0.1, 0.4, 0.6, 1)
        RoundedRectangle:
            size: self.size
            pos: self.pos
            radius: [dp(10),]

<TitleLabel@Label>:
    font_size: '20sp'
    font_name: '{DEFAULT_FONT}'
    halign: 'center'
    valign: 'middle'
    bold: True

<NormalLabel@Label>:
    font_name: '{DEFAULT_FONT}'
    text_size: self.width, None
    halign: 'right' if app.current_lang == 'ar' else 'left'
    valign: 'middle'

<RightAlignTextInput@TextInput>:
    font_name: '{DEFAULT_FONT}'
    multiline: False
    halign: 'right' if app.current_lang == 'ar' else 'left' # Adjust based on lang

<NotificationBanner(BoxLayout):>
    size_hint_y: None
    height: dp(5)
    opacity: 0
    banner_color: [0,1,0,1]
    canvas.before:
        Color:
            rgba: self.banner_color
        Rectangle:
            pos: self.pos
            size: self.size

<CaptchaWidget>:
    orientation: 'vertical'
    padding: dp(15)
    spacing: dp(10)
    font_name: '{DEFAULT_FONT}'

    canvas.before:
        Color:
            rgba: (0.95, 0.95, 0.95, 1)
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout:
        size_hint_y: None
        height: dp(70)
        orientation: 'vertical'
        Label:
            id: notification_label
            text: ''
            font_size: '18sp'
            font_name: '{DEFAULT_FONT}'
            text_size: self.width, None
            halign: 'center'
            valign: 'middle'
            color: (0.1, 0.1, 0.1, 1)
        NotificationBanner:
            id: speed_notification_banner

    BoxLayout:
        size_hint_y: None
        height: dp(45)
        spacing: dp(10)
        RoundedButton:
            text: app.tr('add_account')
            on_press: root.open_add_account_popup()
        RoundedButton:
            id: lang_button
            text: app.tr('toggle_language')
            on_press: app.toggle_language()

    BoxLayout:
        id: captcha_box # This is where the solution text or error will be shown
        orientation: 'vertical'
        size_hint_y: None
        height: dp(100) # Increased height for larger text, adjust as needed
        padding: [0, dp(10)]
        # To center the label within captcha_box
        canvas.before:
            Color:
                rgba: (0.85, 0.85, 0.85, 1) # A light background for the captcha area
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [dp(5),]


    ScrollView:
        bar_width: dp(10)
        scroll_type: ['bars', 'content']
        GridLayout:
            id: accounts_layout
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            row_default_height: dp(50)
            row_force_default: False
            spacing: dp(8)

    BoxLayout:
        size_hint_y: None
        height: dp(30)
        orientation: 'vertical'
        Label:
            id: speed_label
            text: app.tr('api_call_time', time=0)
            font_size: '12sp'
            font_name: '{DEFAULT_FONT}'
            text_size: self.width, None
            halign: 'center'
            valign: 'middle'
            color: (0.3, 0.3, 0.3, 1)


<PopupContent@BoxLayout>:
    orientation: 'vertical'
    spacing: dp(10)
    padding: dp(10)
    lbl_title: ''
    font_name: '{DEFAULT_FONT}' # Ensure font is inherited
    TitleLabel:
        text: root.lbl_title
        size_hint_y: None
        height: dp(40)

<AddAccountPopupContent@PopupContent>:
    RightAlignTextInput:
        id: user_input
        hint_text: app.tr('username_hint')
    RightAlignTextInput:
        id: pwd_input
        hint_text: app.tr('password_hint')
        password: True
    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(10)
        RoundedButton:
            id: btn_ok
            text: app.tr('ok')
        RoundedButton:
            id: btn_cancel
            text: app.tr('cancel')

<ApiPrefixPopupContent@PopupContent>:
    Label:
        text: app.tr('enter_variable_api_part')
        font_name: '{DEFAULT_FONT}' # Specific font
        halign: 'right' if app.current_lang == 'ar' else 'left'
    RightAlignTextInput:
        id: input_box
        hint_text: app.tr('enter_api_identifier')
    RoundedButton:
        id: btn_confirm
        text: app.tr('save_and_continue')
        size_hint_y: None
        height: dp(40)

<ServerResponsePopupContent@ScrollView>:
    bar_width: dp(10)
    font_name: '{DEFAULT_FONT}' # Ensure font is inherited
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        padding: dp(10)
        spacing: dp(5)
        NormalLabel:
            id: status_code_label
            bold: True
        NormalLabel:
            id: headers_label
            bold: True
        ScrollView:
            size_hint_y: None
            height: dp(200)
            NormalLabel:
                id: body_label
                text_size: self.width * 0.95, None
                size_hint_y: None
                height: self.texture_size[1]
'''

class CaptchaWidget(BoxLayout):
    current_captcha = ObjectProperty(None, allownone=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {}
        api_prefix = load_api_prefix()
        if not api_prefix:
            Clock.schedule_once(lambda dt: self.ask_api_prefix(), 0.1)
        else:
            global CAPTCHA_API_URL
            CAPTCHA_API_URL = f"https://{api_prefix}.pythonanywhere.com/predict"
            Clock.schedule_once(lambda dt: self.update_notification(tr("api_prefix_loaded"), (0.1, 0.5, 0.8, 1)), 0.1)


    def tr(self, key, **kwargs):
        return tr(key, **kwargs)

    def ask_api_prefix(self):
        content = Factory.ApiPrefixPopupContent(lbl_title=tr("api_setup_title"))
        popup = Popup(title=tr("api_setup_title"), content=content, size_hint=(0.9, 0.5), auto_dismiss=False)
        def on_confirm(instance):
            prefix = content.ids.input_box.text.strip()
            if prefix:
                save_api_prefix(prefix)
                global CAPTCHA_API_URL
                CAPTCHA_API_URL = f"https://{prefix}.pythonanywhere.com/predict"
                self.update_notification(tr("api_prefix_saved"), (0, 0.7, 0.2, 1))
                popup.dismiss()
            else:
                content.ids.input_box.hint_text = tr("api_prefix_empty")
        content.ids.btn_confirm.bind(on_press=on_confirm)
        popup.open()

    def update_notification(self, msg, color, is_success_for_banner=False):
        lbl = self.ids.notification_label
        lbl.text = msg
        lbl.color = color
        banner = self.ids.speed_notification_banner
        if is_success_for_banner:
            banner.banner_color = (0, 1, 0, 0.8)
            banner.opacity = 1
            Clock.schedule_once(lambda dt: setattr(banner, 'opacity', 0), 4)
        elif color[0] > 0.7 and color[1] < 0.5 and color[2] < 0.5: # Primarily red
            banner.banner_color = (1, 0.2, 0.2, 0.8)
            banner.opacity = 1
            Clock.schedule_once(lambda dt: setattr(banner, 'opacity', 0), 4)
        else:
            banner.opacity = 0

    def open_add_account_popup(self):
        content = Factory.AddAccountPopupContent(lbl_title=tr('add_account'))
        popup = Popup(title=tr('add_account'), content=content, size_hint=(0.9, 0.6), auto_dismiss=False)
        def on_ok(instance):
            u = content.ids.user_input.text.strip()
            p = content.ids.pwd_input.text.strip()
            if u and p:
                popup.dismiss()
                threading.Thread(target=self.add_account, args=(u, p), daemon=True).start()
            elif not u:
                 content.ids.user_input.hint_text = tr("username_hint") + " (" + tr("required") + ")"
            elif not p:
                 content.ids.pwd_input.hint_text = tr("password_hint") + " (" + tr("required") + ")"
        content.ids.btn_ok.bind(on_press=on_ok)
        content.ids.btn_cancel.bind(on_press=popup.dismiss)
        popup.open()

    def generate_user_agent(self):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36"
        ]
        return random.choice(ua_list)

    def create_session_requests(self, ua):
        headers = {
            "User-Agent": ua, "Host": "api.ecsc.gov.sy:8443",
            "Accept": "application/json, text/plain, */*", "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
            "Referer": "https://ecsc.gov.sy/login", "Content-Type": "application/json",
            "Source": "WEB", "Origin": "https://ecsc.gov.sy", "Connection": "keep-alive"
        }
        sess = requests.Session()
        sess.headers.update(headers)
        return sess

    def add_account(self, user, pwd):
        sess = self.create_session_requests(self.generate_user_agent())
        t0 = time.time()
        if not self.login(user, pwd, sess):
            Clock.schedule_once(lambda dt: self.update_notification(tr("login_failed_for_user", user=user), (1, 0.2, 0.2, 1)),0)
            return
        Clock.schedule_once(lambda dt: self.update_notification(tr("logged_in_user", user=user, time=(time.time() - t0)), (0.1, 0.7, 0.1, 1)),0)
        self.accounts[user] = {"password": pwd, "session": sess, "_cached_processes": None} # Add cache for processes
        procs = self.fetch_process_ids(sess, user)
        if procs:
            self.accounts[user]["_cached_processes"] = procs # Cache fetched processes
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            Clock.schedule_once(lambda dt: self.update_notification(tr("cant_fetch_process_ids", user=user), (1, 0.5, 0, 1)),0)

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for i in range(retries):
            try:
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False, timeout=10)
                if r.status_code == 200:
                    return True
                Clock.schedule_once(lambda dt: self.update_notification(tr("login_failed_status", status_code=r.status_code), (1,0.2,0.2,1)),0)
                return False
            except requests.exceptions.RequestException as e:
                err_msg = str(e).splitlines()[0] if str(e) else "Request Exception"
                Clock.schedule_once(lambda dt: self.update_notification(tr("login_error", error=err_msg), (1,0.2,0.2,1)),0)
                if i < retries - 1: time.sleep(1)
            except Exception as e:
                err_msg = str(e).splitlines()[0] if str(e) else "Unexpected error"
                Clock.schedule_once(lambda dt: self.update_notification(tr("login_error", error=err_msg), (1,0.2,0.2,1)),0)
                return False
        return False

    def fetch_process_ids(self, sess, user_for_notif):
        try:
            r = sess.post(
                "https://api.ecsc.gov.sy:8443/dbm/db/execute",
                json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                headers={"Content-Type": "application/json", "Alias": "OPkUVkYsyq", "Referer": "https://ecsc.gov.sy/requests", "Origin": "https://ecsc.gov.sy"},
                verify=False, timeout=10
            )
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            Clock.schedule_once(lambda dt: self.update_notification(tr("fetch_ids_failed_status", status_code=r.status_code), (1,0.5,0,1)),0)
        except requests.exceptions.RequestException as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Request Exception"
            Clock.schedule_once(lambda dt: self.update_notification(tr("error_fetching_ids", error=err_msg), (1,0.5,0,1)),0)
        except Exception as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Unexpected error"
            Clock.schedule_once(lambda dt: self.update_notification(tr("error_fetching_ids", error=err_msg), (1,0.5,0,1)),0)
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        # Clear only for this specific user if re-creating (e.g. after language change)
        # For initial creation, this check isn't strictly needed but good for robustness.
        widgets_to_remove = [w for w in layout.children if getattr(w, '_user_tag', None) == user]
        for widget in widgets_to_remove:
            layout.remove_widget(widget)

        user_header = Factory.NormalLabel(
            text=tr("account_label", user=user),
            size_hint_y=None, height=dp(30), bold=True,
            color=(0.2,0.2,0.7,1)
        )
        setattr(user_header, '_user_tag', user) # Tag for removal/update
        layout.add_widget(user_header)

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            name = proc.get("ZCENTER_NAME", tr("unknown_process"))
            item_box = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(5))
            setattr(item_box, '_user_tag', user) # Tag for removal/update

            btn_text = name # tr() will handle RTL if name itself is a key, otherwise direct text
            if CURRENT_LANG == "ar" and isinstance(name, str) and not name.startswith('\u202B'):
                btn_text = wrap_rtl(name)

            btn = RoundedButton(text=btn_text)
            prog = ProgressBar(max=100, value=0, size_hint_x=0.3)
            item_box.add_widget(btn)
            item_box.add_widget(prog)
            layout.add_widget(item_box)
            btn.bind(on_press=lambda instance, u=user, p_id=pid, prg_bar=prog: \
                threading.Thread(target=self._handle_captcha_thread, args=(u, p_id, prg_bar), daemon=True).start())

    def _handle_captcha_thread(self, user, pid, prog_bar):
        Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 10), 0)
        Clock.schedule_once(lambda dt: self.update_notification(tr("fetching_captcha"), (0.1,0.5,0.8,1)),0)
        captcha_b64_data = self.get_captcha(self.accounts[user]["session"], pid, user)
        Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 30), 0) # Increased progress
        if captcha_b64_data:
            self.current_captcha = (user, pid, prog_bar)
            Clock.schedule_once(lambda dt: self._display_and_predict_captcha(captcha_b64_data), 0)
        else:
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 0), 0)

    def get_captcha(self, sess, pid, user):
        url = f"https://api.ecsc.gov.sy:8443/captcha/get/{pid}"
        try:
            for _ in range(3):
                r = sess.get(url, verify=False, timeout=10)
                if r.status_code == 200:
                    return r.json().get("file")
                if r.status_code == 429:
                    time.sleep(0.3)
                    continue
                elif r.status_code in (401, 403):
                    Clock.schedule_once(lambda dt: self.update_notification(tr("login_failed_status", status_code=r.status_code) + " - Relogin", (1,0.2,0.2,1)),0)
                    if not self.login(user, self.accounts[user]["password"], sess): return None
                    continue
                else:
                    Clock.schedule_once(lambda dt: self.update_notification(tr("server_error_status", status_code=r.status_code), (1,0.2,0.2,1)),0)
                    return None
        except requests.exceptions.RequestException as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Request Exception"
            Clock.schedule_once(lambda dt: self.update_notification(tr("captcha_error", error=err_msg), (1,0.2,0.2,1)),0)
        except Exception as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Unexpected error"
            Clock.schedule_once(lambda dt: self.update_notification(tr("captcha_error", error=err_msg), (1,0.2,0.2,1)),0)
        return None

    def predict_captcha_from_api(self, pil_img: PILImage.Image):
        if not CAPTCHA_API_URL:
            Clock.schedule_once(lambda dt: self.update_notification(tr("api_request_error", error="API URL not set"), (1,0.2,0.2,1)),0)
            return None, 0
        t_api_start = time.time()
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            response = requests.post(CAPTCHA_API_URL, files=files, timeout=30)
            response.raise_for_status()
            api_response = response.json()
            predicted_text = api_response.get("result")
            total_api_time_ms = (time.time() - t_api_start) * 1000
            if predicted_text is None: # Check for None or empty string if API might return that for failure
                Clock.schedule_once(lambda dt: self.update_notification(tr("api_error_prediction_missing"), (1,0.5,0,1)),0)
                return None, total_api_time_ms
            return str(predicted_text), total_api_time_ms # Ensure it's a string
        except requests.exceptions.HTTPError as e:
            error_msg = f"API HTTP Error: {e.response.status_code}"
            try: # Try to get more details from response
                error_details = e.response.json().get('error', e.response.text[:100])
                error_msg += f" - {error_details}"
            except: pass
            Clock.schedule_once(lambda dt: self.update_notification(tr("api_request_error", error=error_msg), (1,0.2,0.2,1)),0)
        except requests.exceptions.RequestException as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Request Exception"
            Clock.schedule_once(lambda dt: self.update_notification(tr("api_request_error", error=err_msg), (1,0.2,0.2,1)),0)
        except Exception as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Unexpected API error"
            Clock.schedule_once(lambda dt: self.update_notification(tr("api_request_error", error=err_msg), (1,0.2,0.2,1)),0)
        return None, (time.time() - t_api_start) * 1000

    def _display_and_predict_captcha(self, b64data):
        self.ids.captcha_box.clear_widgets() # Clear previous content (image or old solution)
        try:
            b64 = b64data.split(',')[1] if ',' in b64data else b64data
            raw = base64.b64decode(b64)
            pil_original = PILImage.open(io.BytesIO(raw))

            gray_img = np.array(pil_original.convert('L'))
            median_val = np.median(gray_img)
            threshold = median_val * 0.9
            bin_img_array = (gray_img > threshold).astype(np.uint8) * 255
            bin_pil_img = PILImage.fromarray(bin_img_array)

            # --- MODIFICATION START ---
            # Predict first
            predicted_text, api_ms = self.predict_captcha_from_api(bin_pil_img)
            Clock.schedule_once(lambda dt: setattr(self.ids.speed_label, 'text', tr('api_call_time', time=api_ms)), 0)

            user, pid, prog_bar = self.current_captcha # Unpack current captcha context

            if predicted_text:
                Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 60),0) # Update progress
                Clock.schedule_once(lambda dt: self.update_notification(tr("captcha_solution_displayed"), (0.1,0.5,0.8,1)),0)

                # Display the predicted solution in large yellow text
                solution_label = Label(
                    text=str(predicted_text), # Ensure it's a string
                    font_size='45sp',      # Large font
                    color=(0.9, 0.9, 0.1, 1),  # Yellow color ( একটু কম উজ্জ্বল হলুদ )
                    font_name=DEFAULT_FONT, # Handles Arabic if solution is Arabic (unlikely for CAPTCHA)
                    halign='center',
                    valign='middle',
                    size_hint_y=None,
                    height=self.ids.captcha_box.height * 0.9 # Use most of the allocated height
                )
                self.ids.captcha_box.add_widget(solution_label)
                # Inform the user about what's being sent
                Clock.schedule_once(lambda dt: self.update_notification(tr("predicted_captcha", prediction=predicted_text), (0.1,0.3,0.8,1)),0.1) # Slightly delayed for flow
                self.submit_captcha_solution(predicted_text)
            else:
                # Prediction failed, display error message in captcha_box
                Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 30),0) # Reset progress or set to an intermediate error state
                error_msg_display = tr("api_error_prediction_missing")
                error_label = Label(
                    text=error_msg_display,
                    font_size='18sp', # Smaller font for error
                    color=(1, 0.2, 0.2, 1), # Red color
                    font_name=DEFAULT_FONT,
                    halign='center',
                    valign='middle',
                    text_size=(self.ids.captcha_box.width * 0.9, None), # Allow wrapping for longer error messages
                    size_hint_y=None,
                    height=self.ids.captcha_box.height * 0.9
                )
                self.ids.captcha_box.add_widget(error_label)
                # Also update main notification bar
                Clock.schedule_once(lambda dt: self.update_notification(error_msg_display, (1,0.5,0,1)),0)

            # --- MODIFICATION END ---

        except Exception as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Processing error"
            Clock.schedule_once(lambda dt: self.update_notification(tr("error_processing_captcha", error=err_msg), (1,0.2,0.2,1)),0)
            if self.current_captcha:
                _, _, prog_bar = self.current_captcha
                Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 0), 0)
            # Display error in captcha_box as well
            error_label_exc = Label(
                text=tr("error_processing_captcha", error=err_msg),
                font_size='18sp', color=(1, 0.2, 0.2, 1), font_name=DEFAULT_FONT,
                halign='center', valign='middle', text_size=(self.ids.captcha_box.width * 0.9, None),
                size_hint_y=None, height=self.ids.captcha_box.height * 0.9
            )
            self.ids.captcha_box.add_widget(error_label_exc)


    def submit_captcha_solution(self, solution_text):
        if not self.current_captcha:
            self.update_notification(tr("error_no_captcha_context"), (1,0.2,0.2,1))
            return

        user, pid, prog_bar = self.current_captcha
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={solution_text}"
        Clock.schedule_once(lambda dt: self.update_notification(tr("submitting_captcha"), (0.1,0.5,0.8,1)),0)
        Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 75),0)

        try:
            r = requests.get(url, session=sess, verify=False, timeout=15) # Use the session for submission too
            is_success = (r.status_code == 200)
            Clock.schedule_once(lambda dt: self.update_notification(
                tr("submit_response_short", status=f"{r.status_code} {'OK' if is_success else 'Error'}"),
                (0.1,0.7,0.1,1) if is_success else (1,0.2,0.2,1),
                is_success_for_banner=is_success
            ),0)
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 100 if is_success else 75), 0)

            headers_str = "\n".join([f"  {k}: {v}" for k, v in r.headers.items()])
            content_popup = Factory.ServerResponsePopupContent()
            content_popup.ids.status_code_label.text = tr("status_code") + ": " + str(r.status_code)
            content_popup.ids.headers_label.text = tr("headers") + ":\n" + headers_str
            body_text_to_display = r.text
            if CURRENT_LANG == 'ar':
                if not (body_text_to_display.strip().startswith("{") or body_text_to_display.strip().startswith("[")):
                    body_text_to_display = wrap_rtl(body_text_to_display)
            content_popup.ids.body_label.text = tr("body") + ":\n" + body_text_to_display
            Popup(title=tr("server_response_title"), content=content_popup, size_hint=(0.9, 0.8)).open()

        except requests.exceptions.RequestException as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Submit Request Exception"
            Clock.schedule_once(lambda dt: self.update_notification(tr("submit_error_short") + f": {err_msg}", (1,0.2,0.2,1)),0)
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 60), 0) # Error state for progress
        except Exception as e:
            err_msg = str(e).splitlines()[0] if str(e) else "Unexpected Submit error"
            Clock.schedule_once(lambda dt: self.update_notification(tr("submit_error_short") + f": {err_msg}", (1,0.2,0.2,1)),0)
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 60), 0)
        finally:
            # Do not clear captcha_box here if you want the yellow text to remain
            # self.ids.captcha_box.clear_widgets() # Commented out to keep solution/error visible
            self.current_captcha = None


class CaptchaApp(App):
    current_lang = StringProperty(CURRENT_LANG)

    def build(self):
        self.title = "Captcha Solver" # Or localized title
        return CaptchaWidget()

    def on_start(self):
        self.update_language_in_ui()

    def tr(self, key, **kwargs):
        return tr(key, **kwargs)

    def toggle_language(self):
        global CURRENT_LANG
        CURRENT_LANG = "en" if CURRENT_LANG == "ar" else "ar"
        self.current_lang = CURRENT_LANG
        self.update_language_in_ui()

    def update_language_in_ui(self):
        if self.root:
            self.root.ids.speed_label.text = tr('api_call_time', time=0)
            self.root.ids.lang_button.text = tr('toggle_language')
            # Potentially re-translate notification if needed and key is stored
            # self.root.ids.notification_label.text = tr(self.root.ids.notification_label._last_tr_key, ...)

            # Rebuild account list to apply language changes to dynamic content
            self.root.ids.accounts_layout.clear_widgets() # Clear all first
            for user, data in self.root.accounts.items():
                cached_procs = data.get("_cached_processes")
                if cached_procs: # If we have cached processes, use them to rebuild UI
                    self.root._create_account_ui(user, cached_procs)
                # Else: user will have to re-add or a mechanism to re-fetch processes is needed
                # For simplicity, if not cached, the list for this user won't reappear on lang switch
                # unless they are re-added or login again.

if __name__ == '__main__':
    import kivy
    kivy.require('2.0.0')
    Builder.load_string(KV)
    CaptchaApp().run()
