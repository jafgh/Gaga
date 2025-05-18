import os
import threading
import time
import base64
import io
import random
import requests
from PIL import Image as PILImage, ImageOps
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
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.properties import StringProperty

import queue # لإدارة طابور الرسائل

# --- Telegram Bot Configuration ---
TELEGRAM_BOT_TOKEN = "7851426078:AAENCSk-nP4FuvQX6JyXUJxG7Ckgz_MbXcE" # استبدل هذا بالرمز الخاص بك
TELEGRAM_CHAT_ID = "6695330017" # استبدل هذا بمعرف الدردشة الخاص بك
TELEGRAM_RETRY_INTERVAL = 60 # الفترة الزمنية (بالثواني) بين محاولات إعادة الإرسال

# --- API Configuration ---
CAPTCHA_API_URL_TEMPLATE = "https://{domain_part}.pythonanywhere.com/predict"
DEFAULT_API_DOMAIN = "00000"

# --- طابور رسائل تيليجرام العام ---
telegram_message_queue = queue.Queue()

# --- دالة مساعدة لإرسال رسائل تيليجرام (الجزء المتزامن) ---
def send_telegram_message_sync(message_text):
    """
    ترسل رسالة تيليجرام بشكل متزامن.
    تعيد True في حال النجاح، و False في حال الفشل.
    """
    api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown'
    }
    try:
        # إضافة مهلة زمنية للاتصال والقراءة بشكل منفصل
        response = requests.post(api_url, data=payload, timeout=(5, 10)) # (connect_timeout, read_timeout)
        response.raise_for_status() # سيثير استثناء لأكواد الخطأ HTTP (4xx, 5xx)
        print(f"تم إرسال رسالة تيليجرام بنجاح: {message_text[:100]}...") # تسجيل جزء من الرسالة
        return True
    except requests.exceptions.Timeout as e:
        print(f"خطأ أثناء إرسال رسالة تيليجرام (Timeout): {e}")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"خطأ أثناء إرسال رسالة تيليجرام (Connection Error): {e}. تحقق من الاتصال بالإنترنت.")
        return False
    except requests.exceptions.HTTPError as e:
        print(f"خطأ أثناء إرسال رسالة تيليجرام (HTTP Error {e.response.status_code}): {e}")
        # يمكن عدم إعادة المحاولة لبعض أخطاء العميل مثل 400 (Bad Request) أو 403 (Forbidden)
        # إذا كانت المشكلة في رمز البوت أو معرف الدردشة.
        # حاليًا، سيعيد المعالج المحاولة، لكن من الجيد الانتباه لذلك.
        return False
    except requests.exceptions.RequestException as e:
        print(f"خطأ أثناء إرسال رسالة تيليجرام (Generic RequestException): {e}")
        return False

# --- دالة لإضافة الرسائل إلى طابور تيليجرام ---
def send_telegram_message_async(message_text):
    """
    تضيف رسالة إلى الطابور ليتم إرسالها بشكل غير متزامن.
    """
    print(f"إضافة رسالة تيليجرام إلى الطابور: {message_text[:100]}...")
    telegram_message_queue.put(message_text)

# --- معالج طابور رسائل تيليجرام ---
def telegram_queue_processor():
    """
    يعالج طابور رسائل تيليجرام، محاولًا إرسال الرسائل
    وإعادة المحاولة عند الفشل. يعمل في خيط منفصل.
    """
    print("بدء معالج طابور رسائل تيليجرام.")
    while True:
        try:
            message_text = telegram_message_queue.get() # ينتظر حتى تتوفر رسالة
            print(f"معالجة رسالة من الطابور: {message_text[:100]}...")
            
            attempt = 0
            while True: # حلقة إعادة المحاولة للرسالة الحالية
                attempt += 1
                if send_telegram_message_sync(message_text):
                    print(f"تمت معالجة وإرسال الرسالة من الطابور: {message_text[:100]}...")
                    telegram_message_queue.task_done() # للإشارة إلى أن المهمة الحالية قد انتهت
                    break # الانتقال إلى الرسالة التالية في الطابور
                else:
                    print(f"فشل إرسال الرسالة (المحاولة {attempt}). إعادة المحاولة بعد {TELEGRAM_RETRY_INTERVAL} ثانية...")
                    time.sleep(TELEGRAM_RETRY_INTERVAL)
        except Exception as e:
            # هذا للتعامل مع الأخطاء غير المتوقعة في المعالج نفسه
            print(f"خطأ حرج في معالج طابور تيليجرام: {e}. سيتم إعادة تشغيل الحلقة للرسالة التالية.")
            # قد نفقد الرسالة الحالية إذا حدث خطأ هنا.
            # لمنع الفقدان، يمكن تسجيلها في ملف أو إعادة إضافتها للطابور بحذر.
            # للتبسيط الآن، نسجل الخطأ ونستمر.
            time.sleep(5) # توقف قصير قبل محاولة الحصول على الرسالة التالية

# --------------------------------------------------
# Kivy UI Design
# --------------------------------------------------
KV = '''
<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: 5
        Label:
            text: 'Start API Code:'
            size_hint_x: 0.3
        TextInput:
            id: api_code_input
            size_hint_x: 0.5
            multiline: False
        Button:
            text: 'Save Code'
            size_hint_x: 0.2
            on_press: root.save_api_code(api_code_input.text)

    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: 5
        Label:
            text: 'Telegram User:'
            size_hint_x: 0.3
        TextInput:
            id: telegram_user_input
            hint_text: 'Enter Telegram username here'
            size_hint_x: 0.5
            multiline: False
        Button:
            text: 'Save User'
            size_hint_x: 0.2
            on_press: root.save_telegram_username(telegram_user_input.text)

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        Label:
            id: notification_label
            text: ''
            font_size: 36
            color: 1,1,1,1

    Button:
        text: 'Add Account'
        size_hint_y: None
        height: '40dp'
        on_press: root.open_add_account_popup()

    BoxLayout:
        id: captcha_box
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height

    ScrollView:
        GridLayout:
            id: accounts_layout
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            row_default_height: '40dp'
            row_force_default: False
            spacing: 5

    Label:
        id: speed_label
        text: 'API Call Time: 0 ms'
        size_hint_y: None
        height: '30dp'
        font_size: 25

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        spacing: 5
        Label:
            id: current_api_code_display
            text: 'API Code: Not Set'
        Button:
            text: 'Change'
            on_press: api_code_input.focus = True

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        Label:
            id: current_telegram_user_display
            text: ' User: Not Set'
'''


class CaptchaWidget(BoxLayout):
    current_api_domain_part = StringProperty(DEFAULT_API_DOMAIN)
    telegram_username_prop = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {}
        self.current_captcha = None
        self.current_captcha_process_details = {}

        self.load_api_code()
        self.load_telegram_username()

        Clock.schedule_once(self._initialize_ui_displays, 0)
        self.send_app_start_notification()

    def _initialize_ui_displays(self, dt=None):
        if hasattr(self, 'ids') and self.ids:
            self.ids.api_code_input.text = self.current_api_domain_part
            self.ids.current_api_code_display.text = f'API Code: {self.current_api_domain_part if self.current_api_domain_part else "Not Set"}'

            self.ids.telegram_user_input.text = self.telegram_username_prop
            self.ids.current_telegram_user_display.text = f'Telegram User: {self.telegram_username_prop if self.telegram_username_prop else "Not Set"}'
        else:
            Clock.schedule_once(self._initialize_ui_displays, 0.1)

    def get_full_api_url(self):
        return CAPTCHA_API_URL_TEMPLATE.format(domain_part=self.current_api_domain_part)

    def load_api_code(self):
        app = App.get_running_app()
        if app and hasattr(app, 'config') and app.config:
            self.current_api_domain_part = app.config.get('appsettings', 'api_domain', fallback=DEFAULT_API_DOMAIN)
        else:
            self.current_api_domain_part = DEFAULT_API_DOMAIN

    def save_api_code(self, new_code):
        new_code = new_code.strip()
        if not new_code:
            self.show_error("API Code cannot be empty.")
            self.ids.api_code_input.text = self.current_api_domain_part
            return

        app = App.get_running_app()
        if app and hasattr(app, 'config') and app.config:
            app.config.set('appsettings', 'api_domain', new_code)
            app.config.write()
            self.current_api_domain_part = new_code
            self.ids.current_api_code_display.text = f'API Code: {self.current_api_domain_part}'
            self.update_notification(f"API Code updated to: {new_code}", (0, 1, 0, 1))
        else:
            self.show_error("Could not save API code due to config error.")

    def load_telegram_username(self):
        app = App.get_running_app()
        if app and hasattr(app, 'config') and app.config:
            self.telegram_username_prop = app.config.get('appsettings', 'telegram_username', fallback="")
        else:
            self.telegram_username_prop = ""

    def save_telegram_username(self, username):
        username = username.strip()
        app = App.get_running_app()
        if app and hasattr(app, 'config') and app.config:
            app.config.set('appsettings', 'telegram_username', username)
            app.config.write()
            self.telegram_username_prop = username
            self.ids.current_telegram_user_display.text = f'Telegram User: {username if username else "Not Set"}'
            self.update_notification(f"Telegram username set to: {username if username else 'None'}", (0, 1, 0, 1))

            if username:
                send_telegram_message_async(f"📱 User '{username}' has set their Telegram username in the app.")
            else:
                send_telegram_message_async("📱 A user has cleared their Telegram username in the app.")
        else:
            self.show_error("Could not save Telegram username due to config error.")

    def send_app_start_notification(self):
        if self.telegram_username_prop:
            send_telegram_message_async(f"🚀 User '{self.telegram_username_prop}' started the application.")
        else:
            send_telegram_message_async("🚀 An anonymous user started the application (Telegram username not set).")

    def show_error(self, msg):
        content_label = Label(text=msg)
        popup = Popup(title='Error', content=content_label, size_hint=(0.8, 0.4))
        popup.open()

    def update_notification(self, msg, color):
        def _update(dt):
            if hasattr(self, 'ids') and self.ids.get('notification_label'):
                lbl = self.ids.notification_label
                lbl.text = msg
                lbl.color = color

        Clock.schedule_once(_update, 0)

    def open_add_account_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        user_input = TextInput(hint_text='Username', multiline=False)
        pwd_input = TextInput(hint_text='Password', password=True, multiline=False)
        btn_layout = BoxLayout(size_hint_y=None, height='60dp', spacing=10)
        btn_ok, btn_cancel = Button(text='OK'), Button(text='Cancel')
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(user_input)
        content.add_widget(pwd_input)
        content.add_widget(btn_layout)
        popup = Popup(title='Add Account', content=content, size_hint=(0.8, 0.4))

        def on_ok(instance):
            u, p = user_input.text.strip(), pwd_input.text.strip()
            popup.dismiss()
            if u and p:
                threading.Thread(target=self.add_account, args=(u, p), daemon=True).start()

        btn_ok.bind(on_press=on_ok)
        btn_cancel.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def generate_user_agent(self):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:115.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.63 Safari/537.36",
            "Mozilla/5.0 (iPad; CPU OS 15_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.199 Safari/537.36 Edg/114.0.1823.67",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.5615.138 Safari/537.36",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.5790.102 Mobile Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:108.0) Gecko/20100101 Firefox/108.0",
            "Mozilla/5.0 (Linux; U; Android 12; zh-cn; SM-S918U Build/SP1A.210812.016) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/114.0.5735.199 Mobile Safari/537.36",
        ]
        return random.choice(ua_list)

    def create_session_requests(self, ua):
        headers = {"User-Agent": ua, "Host": "api.ecsc.gov.sy:8443",
                   "Accept": "application/json, text/plain, */*", "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
                   "Referer": "https://ecsc.gov.sy/login", "Content-Type": "application/json",
                   "Source": "WEB", "Origin": "https://ecsc.gov.sy", "Connection": "keep-alive",
                   "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-site",
                   "Priority": "u=1"}
        sess = requests.Session()
        sess.headers.update(headers)
        return sess

    def add_account(self, user, pwd):
        sess = self.create_session_requests(self.generate_user_agent())
        t0 = time.time()
        if not self.login(user, pwd, sess):
            self.update_notification(f"Login failed for {user}", (1, 0, 0, 1));
            return
        self.update_notification(f"Logged in {user} in {time.time() - t0:.2f}s", (0, 1, 0, 1))

        if user not in self.accounts:
            self.accounts[user] = {}
        self.accounts[user].update({"password": pwd, "session": sess, "process_info": {}})

        procs = self.fetch_process_ids(sess)
        if procs:
            for proc_data in procs:
                pid = proc_data.get("PROCESS_ID")
                if pid:
                    self.accounts[user]["process_info"][pid] = {
                        "ZCENTER_NAME": proc_data.get("ZCENTER_NAME_AR",
                                                      proc_data.get("ZCENTER_NAME", "Unknown Center")),
                        "COPIES": proc_data.get("COPIES", "N/A")
                    }
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            self.update_notification(f"Can't fetch process IDs for {user}", (1, 0, 0, 1))

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for _ in range(retries):
            try:
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False, timeout=15)
                if r.status_code == 200:
                    self.update_notification("Login successful.", (0, 1, 0, 1));
                    return True
                self.update_notification(f"Login failed (Status: {r.status_code})", (1, 0, 0, 1));
            except requests.exceptions.Timeout:
                self.update_notification(f"Login timeout for {user}.", (1, 0, 0, 1))
            except Exception as e:
                self.update_notification(f"Login error: {e}", (1, 0, 0, 1));
        return False

    def fetch_process_ids(self, sess):
        try:
            r = sess.post("https://api.ecsc.gov.sy:8443/dbm/db/execute",
                          json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                          headers={"Content-Type": "application/json", "Alias": "OPkUVkYsyq",
                                   "Referer": "https://ecsc.gov.sy/requests", "Origin": "https://ecsc.gov.sy"},
                          verify=False, timeout=15)
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            self.update_notification(f"Fetch Process IDs failed (Status: {r.status_code})", (1, 0, 0, 1))
        except requests.exceptions.Timeout:
            self.update_notification("Timeout fetching process IDs.", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"Error fetching Process IDs: {e}", (1, 0, 0, 1))
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        layout.add_widget(Label(text=f"Account: {user}", size_hint_y=None, height='35dp'))

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            center_name = proc.get("ZCENTER_NAME_AR", proc.get("ZCENTER_NAME", "Unknown Branch"))
            copies = proc.get("COPIES", "N/A")

            btn_text = f"{center_name} ( {copies})"
            btn = Button(text=btn_text, font_name='ArabicFont')
            prog = ProgressBar(max=1, value=0)
            box = BoxLayout(size_hint_y=None, height='60dp', spacing=2)
            box.add_widget(btn);
            box.add_widget(prog)
            layout.add_widget(box)

            btn.bind(on_press=lambda instance, u=user, p_id=pid, prg=prog, cn=center_name, cp=copies: \
                threading.Thread(target=self._handle_captcha,
                                 args=(u, p_id, prg, cn, cp),
                                 daemon=True).start())

    def _handle_captcha(self, user, pid, prog, center_name_for_captcha, copies_for_captcha):
        Clock.schedule_once(lambda dt: setattr(prog, 'value', 0), 0)
        if user not in self.accounts or "session" not in self.accounts[user]:
            self.update_notification(f"Session for user {user} not found for captcha.", (1, 0, 0, 1))
            return

        data = self.get_captcha(self.accounts[user]["session"], pid, user)
        Clock.schedule_once(lambda dt: setattr(prog, 'value', prog.max), 0)
        if data:
            self.current_captcha = (user, pid)
            self.current_captcha_process_details = {
                "center_name": center_name_for_captcha,
                "copies": copies_for_captcha,
                "user_login": user
            }
            Clock.schedule_once(lambda dt: self._display_captcha(data), 0)

    def get_captcha(self, sess, pid, user):
        url = f"https://api.ecsc.gov.sy:8443/captcha/get/{pid}"
        try:
            while True:
                r = sess.get(url, verify=False, timeout=10)
                if r.status_code == 200:
                    return r.json().get("file")
                if r.status_code == 429:
                    time.sleep(0.2)
                elif r.status_code in (401, 403):
                    self.update_notification(f"Re-logging in for {user} (Captcha Auth)", (1, 0.5, 0, 1))
                    if not self.login(user, self.accounts[user]["password"], sess):
                        self.update_notification(f"Re-login failed for {user}. Cannot get CAPTCHA.", (1, 0, 0, 1))
                        return None
                else:
                    self.update_notification(f"ECSC Server error: {r.status_code}", (1, 0, 0, 1))
                    return None
        except requests.exceptions.Timeout:
            self.update_notification("Timeout getting CAPTCHA.", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"Get CAPTCHA error: {e}", (1, 0, 0, 1))
        return None

    def predict_captcha(self, pil_img: PILImage.Image):
        t_api_start = time.time()
        dynamic_api_url = self.get_full_api_url()
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            response = requests.post(dynamic_api_url, files=files, timeout=30)
            response.raise_for_status()

            api_response = response.json()
            predicted_text = api_response.get("result")

            if not predicted_text and predicted_text != "": # Check if None, not just empty
                self.update_notification(f"API Error: Prediction result is missing or null.", (1, 0.5, 0, 1))
                return None, 0, (time.time() - t_api_start) * 1000
            
            total_api_time_ms = (time.time() - t_api_start) * 1000
            return predicted_text, 0, total_api_time_ms # Assuming pre_ms is 0 or not calculated here

        except requests.exceptions.Timeout:
            self.update_notification(f"API Request Error: Timeout connecting to {dynamic_api_url}", (1, 0, 0, 1))
        except requests.exceptions.ConnectionError:
            self.update_notification(f"API Request Error: Could not connect to {dynamic_api_url}", (1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(f"API Request Error: {e}", (1, 0, 0, 1))
        except ValueError as e: # For JSON decoding errors
            self.update_notification(f"API Response Error: Invalid JSON received. {e}", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"Error calling prediction API: {e}", (1, 0, 0, 1))
        return None, 0, (time.time() - t_api_start if t_api_start else 0) * 1000


    def _display_captcha(self, b64data):
        try:
            self.ids.captcha_box.clear_widgets()
            b64 = b64data.split(',', 1)[1] if ',' in b64data else b64data
            raw = base64.b64decode(b64)
            pil = PILImage.open(io.BytesIO(raw))

            frames = []
            try:
                pil.seek(0)
                while True:
                    arr = np.array(pil.convert("RGB"), dtype=np.float32)
                    frames.append(arr)
                    pil.seek(pil.tell() + 1)
            except EOFError:
                pass

            if not frames:
                pil.seek(0)
                frames = [np.array(pil.convert("RGB"), dtype=np.float32)]

            stack = np.stack(frames, axis=0)
            summed = np.sum(stack, axis=0)
            summed_norm = np.clip(summed / summed.max() * 255.0, 0, 255).astype(np.uint8)
            gray_pil = PILImage.fromarray(summed_norm).convert("L")

            auto = ImageOps.autocontrast(gray_pil, cutoff=1)
            equalized = ImageOps.equalize(auto)
            binary = equalized.point(lambda p: 255 if p > 128 else 0)
            processed_pil_img = binary

            captcha_received_label = Label(
                text='CAPTCHA Received',
                font_size='42sp',
                color=(1, 0.647, 0, 1)
            )
            self.ids.captcha_box.add_widget(captcha_received_label)

            pred_text, pre_ms, api_call_ms = self.predict_captcha(processed_pil_img)

            if pred_text is not None:
                self.update_notification(f"Predicted CAPTCHA (API): {pred_text}", (0, 0, 1, 1))
                Clock.schedule_once(lambda dt: setattr(
                    self.ids.speed_label, 'text',
                    f"Preproc: {pre_ms:.1f} ms | API Call: {api_call_ms:.1f} ms"
                ), 0)
                self.submit_captcha(pred_text)
            else:
                self.update_notification(
                    f"CAPTCHA prediction failed. API Time: {api_call_ms:.2f} ms",
                    (1, 0, 0, 1)
                )

        except Exception as e:
            self.update_notification(f"Error processing/displaying CAPTCHA: {e}", (1, 0, 0, 1))


    def submit_captcha(self, sol):
        if not self.current_captcha:
            self.update_notification("Error: No current CAPTCHA context for submission.", (1, 0, 0, 1))
            return

        user_login_for_captcha = self.current_captcha_process_details.get("user_login", "N/A")
        if user_login_for_captcha not in self.accounts or "session" not in self.accounts[user_login_for_captcha]:
            self.update_notification(f"Error: Session not found for user {user_login_for_captcha}.", (1, 0, 0, 1))
            send_telegram_message_async(
                f"⚠️ Submission Error: Session for service user {user_login_for_captcha} not found.")
            return
        
        user_account_pid_unused, pid = self.current_captcha # user_account_pid is not used here, pid is the one we need
        sess = self.accounts[user_login_for_captcha]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"

        telegram_user_for_message = self.telegram_username_prop if self.telegram_username_prop else "Unspecified User"
        center_name = self.current_captcha_process_details.get("center_name", "Unknown Branch")
        copies = self.current_captcha_process_details.get("copies", "N/A")

        try:
            r = sess.get(url, verify=False, timeout=20)
            col = (0, 1, 0, 1) if r.status_code == 200 else (1, 0, 0, 1)
            msg_text = r.text
            try:
                msg_text = r.content.decode('utf-8', errors='replace')
            except Exception:
                pass
            self.update_notification(f"Submit response (Status: {r.status_code}): {msg_text}", col)

            if r.status_code == 200:
                telegram_message = (
                    f"✅ *Transaction Confirmed Successfully!*\n\n"
                    f"🔑 *كود API التطبيق:* `{self.current_api_domain_part}`\n"   
                    f"👤 *By App User:* `{telegram_user_for_message}`\n"
                    f"🔑 *Service Account:* `{user_login_for_captcha}`\n"
                    f"🏢 *Branch:* `{center_name}`\n"
                    f"📄 *Copies:* `{copies}`\n"
                    f"🆔 *Process ID (PID):* `{pid}`\n"
                    f"📝 *Submitted Solution:* `{sol}`\n\n"
                    f"📜 *Server Response:* ```\n{msg_text}\n```"
                )
                send_telegram_message_async(telegram_message)
            else:
                telegram_message = (
                    f"❌ *Transaction Confirmation Failed.*\n\n"
                    f"👤 *By App User:* `{telegram_user_for_message}`\n"
                    f"🔑 *Service Account:* `{user_login_for_captcha}`\n"
                    f"🏢 *Branch:* `{center_name}`\n"
                    f"🆔 *Process ID (PID):* `{pid}`\n"
                    f"📝 *Submitted Solution:* `{sol}`\n"
                    f"⚠️ *Status Code:* `{r.status_code}`\n\n"
                    f"📜 *Server Response:* ```\n{msg_text}\n```"
                )
                send_telegram_message_async(telegram_message)

        except requests.exceptions.Timeout:
            self.update_notification("Timeout during CAPTCHA submission.", (1, 0, 0, 1))
            send_telegram_message_async(
                f"⏳ *Timeout During Transaction Submission.*\n\n"
                f"👤 *By App User:* `{telegram_user_for_message}`\n"
                f"🔑 *Service Account:* `{user_login_for_captcha}`\n"
                f"🆔 *Process ID (PID):* `{pid}`"
            )
        except Exception as e:
            self.update_notification(f"Submit error: {e}", (1, 0, 0, 1))
            error_telegram_message = (
                f"🚨 *Critical Error During Transaction Submission.*\n\n"
                f"👤 *By App User:* `{telegram_user_for_message}`\n"
                f"🔑 *Service Account:* `{user_login_for_captcha}`\n"
                f"🏢 *Branch:* `{center_name}`\n"
                f"🆔 *Process ID (PID):* `{pid}`\n"
                f"📝 *Submitted Solution:* `{sol}`\n"
                f"🔥 *Error Details:* ```\n{str(e)}\n```"
            )
            send_telegram_message_async(error_telegram_message)
        finally:
            self.current_captcha = None
            self.current_captcha_process_details = {}


class CaptchaApp(App):
    def build_config(self, config):
        config.setdefaults('appsettings', {
            'api_domain': DEFAULT_API_DOMAIN,
            'telegram_username': ''
        })

    def build(self):
        font_path = ""
        possible_paths = [
            os.path.join(os.path.dirname(__file__), 'assets', 'arabic.ttf'),
            os.path.join(os.getcwd(), 'assets', 'arabic.ttf'),
            'assets/arabic.ttf',
            'arabic.ttf'
        ]
        for path_option in possible_paths:
            if os.path.exists(path_option):
                font_path = path_option
                break

        if font_path:
            LabelBase.register(name='ArabicFont', fn_regular=font_path)
            print(f"ArabicFont registered from: {font_path}")
        else:
            print(f"Warning: Arabic font file 'arabic.ttf' not found in expected paths. Arabic text may not render correctly.")
            print(f"Checked paths: {possible_paths}")

        # --- بدء خيط معالج طابور تيليجرام ---
        processor_thread = threading.Thread(target=telegram_queue_processor, daemon=True)
        processor_thread.start()
        print("تم بدء خيط معالج طابور تيليجرام.")
        # ------------------------------------

        Builder.load_string(KV)
        widget = CaptchaWidget()
        return widget

    def on_stop(self):
        print("إيقاف تطبيق CaptchaApp. سينتهي معالج طابور تيليجرام (إذا كان daemon).")
        # إذا كنت تريد انتظار إفراغ الطابور (قد يكون معقدًا ويجعل الإغلاق بطيئًا):
        # print("انتظار إفراغ طابور تيليجرام...")
        # telegram_message_queue.join()
        # print("تم إفراغ طابور تيليجرام.")
        pass


if __name__ == '__main__':
    import urllib3

    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except AttributeError:
        pass
    except Exception as e_urllib:
        print(f"Could not disable urllib3 warnings: {e_urllib}")
    CaptchaApp().run()
