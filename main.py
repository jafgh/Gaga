import os
import threading
import time
import base64
import io
import random
import requests  # تأكد من أن requests مثبت
from PIL import Image as PILImage
import numpy as np # تأكد من تثبيت numpy: pip install numpy
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
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase
from kivy.properties import StringProperty, ListProperty, NumericProperty
from kivy.utils import get_color_from_hex
from kivy.animation import Animation

# --------------------------------------------------
# تسجيل خط Arabic
# --------------------------------------------------
LabelBase.register(name='Arabic', fn_regular=os.path.join('assets', 'arabic.ttf'))

# --------------------------------------------------
# نظام الترجمة
# --------------------------------------------------
TRANSLATIONS = {
    "en": {
        "add_account_button": "Add Account",
        "notification_label_default": "Notifications will appear here.",
        "api_call_time_label": "API Call Time: {time_ms:.2f} ms",
        "api_prefix_popup_title": "API Setup",
        "api_prefix_popup_label": "Enter the variable part of your API URL (e.g., 'yourname'):",
        "api_prefix_popup_hint": "API identifier (e.g., code)",
        "save_and_continue_button": "Save & Continue",
        "add_account_popup_title": "Add Account",
        "username_hint": "Username",
        "password_hint": "Password",
        "ok_button": "OK",
        "cancel_button": "Cancel",
        "login_failed_user": "Login failed for {user}",
        "logged_in_user_time": "Logged in {user} in {time_s:.2f}s",
        "login_successful": "Login successful.",
        "login_failed_status": "Login failed (Status: {status_code})",
        "login_error": "Login error: {error}",
        "cant_fetch_process_ids": "Can't fetch process IDs for {user}",
        "fetch_ids_failed_status": "Fetch IDs failed (Status: {status_code})",
        "error_fetching_ids": "Error fetching IDs: {error}",
        "account_label": "Account: {user}",
        "unknown_process_name": "Unknown Process",
        "server_error_status": "Server error: {status_code}",
        "captcha_error": "Captcha error: {error}",
        "api_error_prediction_missing": "API Error: Prediction result missing from response.",
        "api_request_error": "API Request Error: {error}",
        "captcha_received_message": "CAPTCHA image received. Awaiting prediction...",
        "predicted_captcha_label": "Predicted CAPTCHA from API: {prediction}",
        "raw_api_response_label": "Raw API Response:\n{response}",
        "error_processing_captcha": "Error processing/predicting captcha: {error}",
        "error_no_captcha_context": "Error: No CAPTCHA context to submit.",
        "submit_response_label": "Submission Response: {response_text}",
        "server_response_popup_title": "Server Response",
        "submit_error": "Submit error: {error}",
        "toggle_language_button": "Toggle Language (العربية)",
        "captcha_submission_successful": "CAPTCHA Submitted Successfully!",
        "captcha_submission_failed": "CAPTCHA Submission Failed.",
    },
    "ar": {
        "add_account_button": "إضافة حساب",
        "notification_label_default": "ستظهر الإشعارات هنا.",
        "api_call_time_label": "زمن استدعاء الواجهة: {time_ms:.2f} مللي ثانية",
        "api_prefix_popup_title": "إعداد API",
        "api_prefix_popup_label": "أدخل الجزء المتغير من رابط API الخاص بك (مثال: 'yourname'):",
        "api_prefix_popup_hint": "معرف API (مثال: code)",
        "save_and_continue_button": "حفظ ومتابعة",
        "add_account_popup_title": "إضافة حساب",
        "username_hint": "اسم المستخدم",
        "password_hint": "كلمة المرور",
        "ok_button": "موافق",
        "cancel_button": "إلغاء",
        "login_failed_user": "فشل تسجيل الدخول للمستخدم {user}",
        "logged_in_user_time": "تم تسجيل دخول {user} في {time_s:.2f} ثانية",
        "login_successful": "تم تسجيل الدخول بنجاح.",
        "login_failed_status": "فشل تسجيل الدخول (الحالة: {status_code})",
        "login_error": "خطأ في تسجيل الدخول: {error}",
        "cant_fetch_process_ids": "لا يمكن جلب معرفات العمليات للمستخدم {user}",
        "fetch_ids_failed_status": "فشل جلب المعرفات (الحالة: {status_code})",
        "error_fetching_ids": "خطأ في جلب المعرفات: {error}",
        "account_label": "حساب: {user}",
        "unknown_process_name": "عملية غير معروفة",
        "server_error_status": "خطأ في الخادم: {status_code}",
        "captcha_error": "خطأ في الكابتشا: {error}",
        "api_error_prediction_missing": "خطأ API: نتيجة التنبؤ مفقودة من الرد.",
        "api_request_error": "خطأ في طلب API: {error}",
        "captcha_received_message": "تم استلام صورة الكابتشا. بانتظار التنبؤ...",
        "predicted_captcha_label": "الكابتشا المتوقعة من الواجهة: {prediction}",
        "raw_api_response_label": "رد الواجهة البرمجية الخام:\n{response}",
        "error_processing_captcha": "خطأ في معالجة/توقع الكابتشا: {error}",
        "error_no_captcha_context": "خطأ: لا يوجد سياق كابتشا للإرسال.",
        "submit_response_label": "رد الإرسال: {response_text}",
        "server_response_popup_title": "رد الخادم",
        "submit_error": "خطأ في الإرسال: {error}",
        "toggle_language_button": "Toggle Language (English)",
        "captcha_submission_successful": "تم إرسال الكابتشا بنجاح!",
        "captcha_submission_failed": "فشل إرسال الكابتشا.",
    }
}
CURRENT_LANG = "ar"  # Default language

def tr(key, **kwargs):
    text = TRANSLATIONS[CURRENT_LANG].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    if CURRENT_LANG == "ar":
        RLE = '\u202B'  # Right-to-Left Embedding
        PDF = '\u202C'  # Pop Directional Formatting
        # Basic check to avoid wrapping already wrapped or pure LTR
        if not any(c in text for c in [RLE, PDF]) and any('\u0600' <= char <= '\u06FF' for char in text):
            return RLE + text + PDF
    return text

# --------------------------------------------------
# ملف الإعدادات لحفظ جزء الـ API
# --------------------------------------------------
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

# --------------------------------------------------
# تصميم الواجهة
# --------------------------------------------------
KV = '''
<TranslatedLabel@Label>:
    font_name: 'Arabic'
    text_size: self.width, None
    halign: 'right' if app.current_language == 'ar' else 'left'
    valign: 'middle'

<TranslatedButton@Button>:
    font_name: 'Arabic'
    # text_size: self.width, None # Often not needed for buttons, can cause issues
    # halign: 'center' # Default for button

<CaptchaWidget>:
    orientation: 'vertical'
    padding: dp(15) # Increased padding
    spacing: dp(10)
    canvas.before:
        Color:
            rgba: get_color_from_hex('#f0f0f0') if app.current_language == 'en' else get_color_from_hex('#e8f5e9') # Light gray or light green
        Rectangle:
            pos: self.pos
            size: self.size

    BoxLayout: # Notification area
        size_hint_y: None
        height: dp(60) # Increased height
        TranslatedLabel:
            id: notification_label
            text: app.translate('notification_label_default')
            font_size: sp(16) # Increased font size

    BoxLayout: # Success bar for 200 OK
        id: success_bar
        size_hint_y: None
        height: dp(0) # Initially hidden
        opacity: 0
        canvas.before:
            Color:
                rgba: get_color_from_hex('#4CAF50AA') # Green with some transparency
            Rectangle:
                pos: self.pos
                size: self.size
        TranslatedLabel:
            id: success_bar_label
            text: '' # Will be set on success
            bold: True
            color: 1,1,1,1


    TranslatedButton:
        id: add_account_btn
        text: app.translate('add_account_button')
        size_hint_y: None
        height: dp(45) # Slightly taller button
        on_press: root.open_add_account_popup()
        background_color: get_color_from_hex('#2196F3') # Blue
        color: 1,1,1,1


    BoxLayout: # Area for CAPTCHA display (text now)
        id: captcha_display_box # Renamed from captcha_box for clarity
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        padding: dp(5)
        spacing: dp(5)
        # KivyImage: # No longer displaying image directly here
        #     id: captcha_image_display 
        #     size_hint_y: None
        #     height: dp(90) 
        TranslatedLabel:
            id: captcha_status_label 
            text: ""
            font_size: sp(15)
        ScrollView: # To scroll potentially long API response
            size_hint_y: None
            height: dp(100) # Fixed height for scrollable area
            TranslatedLabel:
                id: captcha_api_response_label
                text: ""
                font_size: sp(13)
                size_hint_y: None
                height: self.texture_size[1]


    ScrollView:
        GridLayout:
            id: accounts_layout
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            row_default_height: dp(40)
            row_force_default: True # Ensure default height is used
            spacing: dp(8)

    TranslatedLabel:
        id: speed_label
        text: app.translate('api_call_time_label', time_ms=0)
        size_hint_y: None
        height: dp(30)
        font_size: sp(12)

    TranslatedButton:
        id: toggle_lang_btn
        text: app.translate('toggle_language_button')
        size_hint_y: None
        height: dp(40)
        on_press: app.toggle_language()
        background_color: get_color_from_hex('#757575') # Gray
        color: 1,1,1,1

<ApiPrefixPopupContent@BoxLayout>:
    orientation: 'vertical'
    spacing: dp(10)
    padding: dp(10)
    api_prefix_input: api_prefix_input_id
    TranslatedLabel:
        text: app.translate('api_prefix_popup_label')
        font_size: sp(15)
    TextInput:
        id: api_prefix_input_id
        hint_text: app.translate('api_prefix_popup_hint')
        font_name: 'Arabic' # Ensure hint text can also be Arabic if needed
        multiline: False
        halign: 'right' if app.current_language == 'ar' else 'left'
        font_size: sp(15)
    TranslatedButton:
        text: app.translate('save_and_continue_button')
        size_hint_y: None
        height: dp(40)
        on_press: root.save_prefix(api_prefix_input_id.text)

<AddAccountPopupContent@BoxLayout>:
    orientation: 'vertical'
    spacing: dp(10)
    padding: dp(10)
    user_input: user_input_id
    pwd_input: pwd_input_id

    TextInput:
        id: user_input_id
        hint_text: app.translate('username_hint')
        font_name: 'Arabic'
        multiline: False
        halign: 'right' if app.current_language == 'ar' else 'left'
        font_size: sp(15)
    TextInput:
        id: pwd_input_id
        hint_text: app.translate('password_hint')
        font_name: 'Arabic'
        password: True
        multiline: False
        halign: 'right' if app.current_language == 'ar' else 'left'
        font_size: sp(15)
    BoxLayout:
        size_hint_y: None
        height: dp(40)
        spacing: dp(10)
        TranslatedButton:
            text: app.translate('ok_button')
            on_press: root.confirm_add(user_input_id.text, pwd_input_id.text)
        TranslatedButton:
            text: app.translate('cancel_button')
            on_press: root.dismiss_popup()
'''

class CaptchaWidget(BoxLayout):
    current_captcha_context = ListProperty([None, None]) # user, pid
    raw_api_prediction_response = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {} # {user: {"password": pwd, "session": sess}}
        self.app = App.get_running_app() # Get reference to the app instance

        api_prefix = load_api_prefix()
        if not api_prefix:
            Clock.schedule_once(lambda dt: self.ask_api_prefix(), 0.1)
        else:
            self.set_api_url(api_prefix)

    def set_api_url(self, prefix):
        global CAPTCHA_API_URL
        CAPTCHA_API_URL = f"https://{prefix}.pythonanywhere.com/predict"
        # print(f"API URL set to: {CAPTCHA_API_URL}") # For debugging

    def ask_api_prefix(self):
        content = ApiPrefixPopupContent()
        self._popup = Popup(
            title=self.app.translate('api_prefix_popup_title'),
            content=content,
            size_hint=(0.9, 0.5),
            auto_dismiss=False
        )
        content.save_prefix = self._save_api_prefix_and_dismiss
        self._popup.open()

    def _save_api_prefix_and_dismiss(self, prefix_text):
        prefix = prefix_text.strip()
        if prefix:
            save_api_prefix(prefix)
            self.set_api_url(prefix)
            if hasattr(self, '_popup') and self._popup:
                self._popup.dismiss()
                self._popup = None
        else:
            self.update_notification(self.app.translate("api_prefix_popup_hint"), (1,0.5,0,1))


    def update_notification(self, msg, color=(0,0,0,1)): # Default to black
        Clock.schedule_once(lambda dt: self._do_update_notification(msg, color), 0)

    def _do_update_notification(self, msg, color):
        lbl = self.ids.notification_label
        lbl.text = msg # Already translated and wrapped by app.translate
        lbl.color = color

    def show_success_bar(self, message):
        bar = self.ids.success_bar
        bar.ids.success_bar_label.text = message
        anim = Animation(height=dp(30), opacity=1, duration=0.3)
        anim.bind(on_complete=lambda *args: Clock.schedule_once(self.hide_success_bar, 3))
        anim.start(bar)

    def hide_success_bar(self, dt=None):
        bar = self.ids.success_bar
        anim = Animation(height=dp(0), opacity=0, duration=0.3)
        anim.start(bar)


    def open_add_account_popup(self):
        content = AddAccountPopupContent()
        self._popup = Popup(
            title=self.app.translate('add_account_popup_title'),
            content=content,
            size_hint=(0.9, 0.5),
            auto_dismiss=False
        )
        content.confirm_add = self._confirm_add_account
        content.dismiss_popup = lambda: self._popup.dismiss()
        self._popup.open()

    def _confirm_add_account(self, user_text, pwd_text):
        u, p = user_text.strip(), pwd_text.strip()
        if hasattr(self, '_popup') and self._popup:
            self._popup.dismiss()
            self._popup = None
        if u and p:
            threading.Thread(target=self.add_account, args=(u, p), daemon=True).start()
        else:
            self.update_notification(self.app.translate("username_hint") + ", " + self.app.translate("password_hint"), (1,0.5,0,1))


    def generate_user_agent(self):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
        ]
        return random.choice(ua_list)

    def create_session_requests(self, ua):
        headers = {
            "User-Agent": ua, "Host": "api.ecsc.gov.sy:8443", "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ar,en-US;q=0.7,en;q=0.3", "Referer": "https://ecsc.gov.sy/login",
            "Content-Type": "application/json", "Source": "WEB", "Origin": "https://ecsc.gov.sy",
            "Connection": "keep-alive"
        }
        sess = requests.Session()
        sess.headers.update(headers)
        return sess

    def add_account(self, user, pwd):
        sess = self.create_session_requests(self.generate_user_agent())
        t0 = time.time()
        if not self.login(user, pwd, sess):
            self.update_notification(self.app.translate('login_failed_user', user=user), (1, 0, 0, 1))
            return
        self.update_notification(self.app.translate('logged_in_user_time', user=user, time_s=time.time() - t0), (0, 0.7, 0, 1))
        self.accounts[user] = {"password": pwd, "session": sess}
        procs = self.fetch_process_ids(sess, user)
        if procs:
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            self.update_notification(self.app.translate('cant_fetch_process_ids', user=user), (1, 0.5, 0, 1)) # Orange for warning

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for i in range(retries):
            try:
                # print(f"Attempting login for {user}, attempt {i+1}")
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False, timeout=15)
                if r.status_code == 200:
                    self.update_notification(self.app.translate('login_successful'), (0, 0.7, 0, 1))
                    return True
                else:
                    # print(f"Login failed for {user} with status {r.status_code}: {r.text}")
                    self.update_notification(self.app.translate('login_failed_status', status_code=r.status_code), (1, 0, 0, 1))
                    return False # Don't retry on non-200 HTTP errors unless specific
            except requests.exceptions.RequestException as e:
                # print(f"Login attempt {i+1} for {user} failed with exception: {e}")
                if i == retries - 1: # Last retry
                    self.update_notification(self.app.translate('login_error', error=str(e)), (1, 0, 0, 1))
                time.sleep(1) # Wait before retrying on connection errors
        return False

    def fetch_process_ids(self, sess, user_for_relogin_context):
        try:
            r = sess.post(
                "https://api.ecsc.gov.sy:8443/dbm/db/execute",
                json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                verify=False, timeout=15
            )
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            elif r.status_code in (401, 403): # Unauthorized or Forbidden
                self.update_notification("Session expired, attempting re-login...", (1,0.5,0,1))
                if self.login(user_for_relogin_context, self.accounts[user_for_relogin_context]["password"], sess):
                    return self.fetch_process_ids(sess, user_for_relogin_context) # Retry fetching
                else:
                    self.update_notification(f"Re-login failed for {user_for_relogin_context}",(1,0,0,1))
                    return []
            else:
                self.update_notification(self.app.translate('fetch_ids_failed_status', status_code=r.status_code), (1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(self.app.translate('error_fetching_ids', error=str(e)), (1, 0, 0, 1))
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        user_label_text = self.app.translate('account_label', user=user)
        lbl = TranslatedLabel(text=user_label_text, size_hint_y=None, height=dp(30), font_size=sp(16))
        layout.add_widget(lbl)

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            name = proc.get("ZCENTER_NAME", self.app.translate('unknown_process_name'))
            
            btn_text = f"{name} (ID: {pid})" # Include PID for clarity
            btn = TranslatedButton(text=btn_text, font_size=sp(14))
            btn.bind(size=lambda inst, val: setattr(inst, 'text_size', (inst.width - dp(20), None))) # Adjust for padding
            
            prog = ProgressBar(max=100, value=0, size_hint_x=0.3)
            box = BoxLayout(size_hint_y=None, height=dp(45), spacing=dp(5)) # Taller box for items
            box.add_widget(btn)
            box.add_widget(prog)
            layout.add_widget(box)
            
            btn.bind(on_press=lambda instance, u=user, p_id=pid, prg_bar=prog: \
                     threading.Thread(target=self._handle_captcha_request, args=(u, p_id, prg_bar), daemon=True).start())

    def _handle_captcha_request(self, user, pid, prog_bar):
        Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 10), 0) # Initial progress
        
        if not CAPTCHA_API_URL:
            self.update_notification("CAPTCHA API URL not configured. Please set it up.", (1,0,0,1))
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 0), 0)
            return

        captcha_b64_data = self.get_captcha_image_data(self.accounts[user]["session"], pid, user)
        Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 50 if captcha_b64_data else 0), 0)

        if captcha_b64_data:
            self.current_captcha_context = [user, pid] # Store context
            Clock.schedule_once(lambda dt: self._process_and_predict_captcha(captcha_b64_data, prog_bar), 0)
        else:
            self.update_notification(self.app.translate('captcha_error', error="Failed to retrieve image data"), (1,0,0,1))
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 0), 0)


    def get_captcha_image_data(self, sess, pid, user_for_relogin):
        url = f"https://api.ecsc.gov.sy:8443/captcha/get/{pid}"
        try:
            retries = 3
            for attempt in range(retries):
                r = sess.get(url, verify=False, timeout=10)
                if r.status_code == 200:
                    return r.json().get("file") # Base64 data
                elif r.status_code == 429: # Too many requests
                    self.update_notification(f"Rate limited (429) on attempt {attempt+1}. Retrying...", (1,0.5,0,1))
                    time.sleep(random.uniform(0.5, 1.5)) # Random backoff
                elif r.status_code in (401, 403): # Unauthorized or Forbidden
                    self.update_notification("Session expired while fetching CAPTCHA. Re-logging in...", (1,0.5,0,1))
                    if self.login(user_for_relogin, self.accounts[user_for_relogin]["password"], sess):
                        continue # Retry the get_captcha call immediately after successful re-login
                    else:
                        self.update_notification(f"Re-login failed for {user_for_relogin}", (1,0,0,1))
                        return None
                else:
                    self.update_notification(self.app.translate('server_error_status', status_code=r.status_code) + f" ({r.text})", (1,0,0,1))
                    return None # Other server errors
            self.update_notification("Failed to get CAPTCHA after multiple retries (rate limit/other).", (1,0,0,1))
            return None
        except requests.exceptions.RequestException as e:
            self.update_notification(self.app.translate('captcha_error', error=str(e)), (1,0,0,1))
        return None

    def _process_and_predict_captcha(self, b64data, prog_bar):
        self.ids.captcha_status_label.text = self.app.translate('captcha_received_message')
        self.ids.captcha_api_response_label.text = "" # Clear previous response

        try:
            b64_clean = b64data.split(',')[1] if ',' in b64data else b64data
            raw_image_bytes = base64.b64decode(b64_clean)
            pil_original_image = PILImage.open(io.BytesIO(raw_image_bytes))

            # Simple preprocessing (convert to grayscale and binarize)
            # This might need adjustment based on the CAPTCHA characteristics
            gray_image = pil_original_image.convert('L')
            threshold = np.median(np.array(gray_image)) # Adaptive threshold using median
            binarized_image = gray_image.point(lambda p: 255 if p > threshold else 0, '1')
            
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 75), 0)

            # Send binarized image for prediction
            predicted_text, full_api_response_text, api_call_duration_ms = self.predict_captcha_with_api(binarized_image)
            
            Clock.schedule_once(lambda dt: setattr(self.ids.speed_label, 'text',
                                       self.app.translate('api_call_time_label', time_ms=api_call_duration_ms)), 0)
            
            # Display raw API response
            self.ids.captcha_api_response_label.text = self.app.translate('raw_api_response_label', response=full_api_response_text)

            if predicted_text:
                self.ids.captcha_status_label.text = self.app.translate('predicted_captcha_label', prediction=predicted_text)
                self.update_notification(self.app.translate('predicted_captcha_label', prediction=predicted_text), (0,0,0.7,1)) # Dark blue
                self.submit_captcha_solution(predicted_text)
            else:
                # Error message already shown by predict_captcha_with_api or response was empty
                self.ids.captcha_status_label.text = self.app.translate('api_error_prediction_missing')
                self.update_notification(self.app.translate('api_error_prediction_missing'), (1,0.5,0,1))

            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 100), 0)

        except Exception as e:
            # print(f"Error in _process_and_predict_captcha: {e}")
            self.update_notification(self.app.translate('error_processing_captcha', error=str(e)), (1,0,0,1))
            self.ids.captcha_status_label.text = self.app.translate('error_processing_captcha', error=str(e))
            Clock.schedule_once(lambda dt: setattr(prog_bar, 'value', 0), 0) # Reset progress on error


    def predict_captcha_with_api(self, pil_image: PILImage.Image):
        api_start_time = time.time()
        full_response_text = "No response"
        try:
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG') # Ensure PNG format as expected by many APIs
            img_byte_arr.seek(0)
            
            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            
            if not CAPTCHA_API_URL: # Guard against missing URL
                self.update_notification("CAPTCHA API URL is not set.", (1,0,0,1))
                return None, "API URL not set", (time.time() - api_start_time) * 1000

            response = requests.post(CAPTCHA_API_URL, files=files, timeout=30)
            api_call_duration_ms = (time.time() - api_start_time) * 1000
            full_response_text = response.text # Store full text for display

            response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
            
            api_json_response = response.json()
            predicted_text = api_json_response.get("result")

            if predicted_text is None:
                self.update_notification(self.app.translate('api_error_prediction_missing'), (1,0.5,0,1))
                return None, full_response_text, api_call_duration_ms
            
            return str(predicted_text), full_response_text, api_call_duration_ms

        except requests.exceptions.HTTPError as http_err:
            # print(f"HTTP error during CAPTCHA prediction: {http_err} - Response: {full_response_text}")
            self.update_notification(self.app.translate('api_request_error', error=f"HTTP {http_err.response.status_code}: {full_response_text}"), (1,0,0,1))
        except requests.exceptions.RequestException as req_err:
            # print(f"Request error during CAPTCHA prediction: {req_err}")
            self.update_notification(self.app.translate('api_request_error', error=str(req_err)), (1,0,0,1))
        except Exception as e: # Catch other errors like JSONDecodeError
            # print(f"Generic error during CAPTCHA prediction: {e} - Response was: {full_response_text}")
            self.update_notification(self.app.translate('api_request_error', error=f"{type(e).__name__}: {e}. Response: {full_response_text[:200]}..."), (1,0,0,1))
            
        return None, full_response_text, (time.time() - api_start_time) * 1000


    def submit_captcha_solution(self, solution_text):
        user, pid = self.current_captcha_context
        if not user or not pid:
            self.update_notification(self.app.translate('error_no_captcha_context'), (1,0,0,1))
            return

        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={solution_text}"
        try:
            r = sess.get(url, verify=False, timeout=20)
            response_text_to_display = r.text
            
            # Attempt to pretty-print if JSON, otherwise show raw text
            try:
                import json
                parsed_json = json.loads(r.text)
                response_text_to_display = json.dumps(parsed_json, indent=2, ensure_ascii=False)
            except json.JSONDecodeError:
                pass # It's not JSON, or malformed, show raw

            if r.status_code == 200:
                self.update_notification(self.app.translate('captcha_submission_successful'), (0,0.7,0,1))
                self.show_success_bar(self.app.translate('captcha_submission_successful')) # Show green bar
            else:
                self.update_notification(
                    self.app.translate('captcha_submission_failed') + f" (Status: {r.status_code})", (1,0,0,1)
                )

            # Create a ScrollView for the popup content if text is long
            scroll_content = ScrollView(size_hint=(1, 1))
            popup_label = TranslatedLabel(
                text=self.app.translate('submit_response_label', response_text=response_text_to_display),
                size_hint_y=None,
                font_size=sp(13)
            )
            popup_label.bind(texture_size=lambda instance, size: setattr(instance, 'height', size[1]))
            scroll_content.add_widget(popup_label)
            
            Popup(title=self.app.translate('server_response_popup_title'),
                  content=scroll_content,
                  size_hint=(0.9, 0.7)).open()

        except requests.exceptions.RequestException as e:
            self.update_notification(self.app.translate('submit_error', error=str(e)), (1,0,0,1))
        finally:
            self.current_captcha_context = [None, None] # Clear context


class CaptchaApp(App):
    current_language = StringProperty(CURRENT_LANG)

    def build(self):
        # Ensure assets directory and arabic.ttf exist
        if not os.path.exists("assets") or not os.path.exists(os.path.join("assets", "arabic.ttf")):
            print("ERROR: 'assets' directory or 'assets/arabic.ttf' not found.")
            print("Please create an 'assets' folder in the same directory as the script,")
            print("and place an Arabic TTF font file named 'arabic.ttf' inside it.")
            # Optionally, create a dummy popup or exit
            # return Label(text="Font file missing. Check console.")
            # For now, let it try and potentially crash if font isn't truly registered.

        Builder.load_string(KV)
        self.widget = CaptchaWidget()
        self.update_ui_translations() # Initial translation
        return self.widget

    def translate(self, key, **kwargs):
        return tr(key, **kwargs) # Use the global tr function

    def toggle_language(self):
        global CURRENT_LANG
        if self.current_language == "en":
            self.current_language = "ar"
            CURRENT_LANG = "ar"
        else:
            self.current_language = "en"
            CURRENT_LANG = "en"
        self.update_ui_translations()

    def update_ui_translations(self, widget_tree=None):
        if widget_tree is None:
            widget_tree = self.root # Start from the root widget

        if widget_tree is None: # If root is not yet available
            return

        # Update specific known text properties that need translation
        if hasattr(widget_tree, 'ids'):
            for id_name, child_widget in widget_tree.ids.items():
                if id_name == "notification_label" and child_widget.text == TRANSLATIONS["en"]["notification_label_default"] or child_widget.text == TRANSLATIONS["ar"]["notification_label_default"] :
                     child_widget.text = self.translate('notification_label_default')
                elif id_name == "add_account_btn":
                    child_widget.text = self.translate('add_account_button')
                elif id_name == "speed_label": # Assuming it always contains a placeholder
                    current_time_ms_text = child_widget.text.split(':')[-1].strip().split(' ')[0]
                    try:
                        current_time_ms = float(current_time_ms_text)
                    except ValueError:
                        current_time_ms = 0
                    child_widget.text = self.translate('api_call_time_label', time_ms=current_time_ms)
                elif id_name == "toggle_lang_btn":
                    child_widget.text = self.translate('toggle_language_button')
                
                # For popup titles (which are not in ids, need to handle when they are created)
                # This is a bit more complex, usually handled by re-creating or directly updating them if a reference is kept.

        # Recursively update children, especially for custom TranslatedLabel/Button
        for child in widget_tree.children:
            if isinstance(child, (Label, Button, TextInput)): # General update for Kivy widgets
                if hasattr(child, '_translation_key'): # If we assign a key during creation
                    child.text = self.translate(child._translation_key)
                if hasattr(child, '_hint_translation_key') and isinstance(child, TextInput):
                     child.hint_text = self.translate(child._hint_translation_key)
            
            # Special handling for alignment based on language
            if isinstance(child, Label) or (isinstance(child, TextInput) and hasattr(child, 'halign')):
                child.halign = 'right' if self.current_language == 'ar' else 'left'
            
            self.update_ui_translations(child) # Recurse

        # Force refresh of the layout to reflect text changes and alignments
        if self.root:
            self.root.do_layout()


# Custom Kivy widget classes used in KV need to be defined if they have Python logic
# For this case, Popup contents are defined in KV, their logic is handled by CaptchaWidget.
class ApiPrefixPopupContent(BoxLayout):
    pass
class AddAccountPopupContent(BoxLayout):
    pass


if __name__ == '__main__':
    # Disable SSL warnings for requests (common in these scenarios, but be aware of implications)
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        pass
    CaptchaApp().run()
