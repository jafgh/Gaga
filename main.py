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
from kivy.clock import Clock
from kivy.core.text import LabelBase

# ---------------------
# تسجيل خط Arabic من ملف assets/arabic.ttf
# ---------------------
LabelBase.register(name='Arabic', fn_regular=os.path.join('assets', 'arabic.ttf'))

# ---------------------
# دالة لوضع النص في سياق RTL دون قلب الأحرف، مع الحفاظ على الإنجليزية LTR
# ---------------------
def wrap_rtl(text):
    RLE = '\u202B'  # Right-to-Left Embedding
    PDF = '\u202C'  # Pop Directional Formatting
    return RLE + text + PDF

# ---------------------
# ملف الإعدادات لحفظ جزء الـ API
# ---------------------
CONFIG_FILE = "config.txt"

def load_api_prefix():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_api_prefix(prefix):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        f.write(prefix)

# ---------------------
# رابط الـ CAPTCHA API (سيُعدل عند التشغيل)
# ---------------------
CAPTCHA_API_URL = None

# ---------------------
# تصميم الواجهة باستخدام Kivy مع halign: 'right'
# ---------------------
KV = '''
<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    # شريط حالة استجابة الخادم (مخفي افتراضيًا)
    BoxLayout:
        id: status_bar
        size_hint_y: None
        height: '6dp'
        canvas.before:
            Color:
                rgba: (0, 1, 0, 1) if root.success_status else (1, 0, 0, 1)
            Rectangle:
                pos: self.pos
                size: self.size
        opacity: 0

    # اشعارات
    Label:
        id: notification_label
        size_hint_y: None
        height: '60dp'
        text: ''
        font_size: 16
        font_name: 'Arabic'
        text_size: self.width, None
        halign: 'right'
        valign: 'middle'

    Button:
        text: root.wrap_rtl('Add Account / إضافة حساب')
        size_hint_y: None
        height: '40dp'
        on_press: root.open_add_account_popup()

    ScrollView:
        GridLayout:
            id: accounts_layout
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            row_default_height: '40dp'
            spacing: 5

    Label:
        id: speed_label
        size_hint_y: None
        height: '30dp'
        text: root.wrap_rtl('API Call Time: 0 ms')
        font_size: 14
        font_name: 'Arabic'
        text_size: self.width, None
        halign: 'right'
        valign: 'middle'
'''

class CaptchaWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {}
        self.current_captcha = None
        self.success_status = False

        api_prefix = load_api_prefix()
        if not api_prefix:
            Clock.schedule_once(lambda dt: self.ask_api_prefix(), 0)
        else:
            global CAPTCHA_API_URL
            CAPTCHA_API_URL = f"https://{api_prefix}.pythonanywhere.com/predict"

    def wrap_rtl(self, text):
        return wrap_rtl(text)

    def update_notification(self, msg, color, success=False):
        def _update(dt):
            lbl = self.ids.notification_label
            lbl.text = wrap_rtl(msg)
            lbl.color = color
            # تحديث شريط الحالة
            bar = self.ids.status_bar
            bar.opacity = 1
            bar.canvas.before.children[1].rgba = (0,1,0,1) if success else (1,0,0,1)
            # إخفاء بعد ثانيتين
            Clock.schedule_once(lambda dt: setattr(bar, 'opacity', 0), 2)
        Clock.schedule_once(_update, 0)

     def open_add_account_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        user_input = TextInput(hint_text=wrap_rtl('Username'), multiline=False, halign='right')
        pwd_input = TextInput(hint_text=wrap_rtl('Password'), password=True, multiline=False, halign='right')
        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        btn_ok = Button(text=wrap_rtl('OK'))
        btn_cancel = Button(text=wrap_rtl('Cancel'))
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(user_input)
        content.add_widget(pwd_input)
        content.add_widget(btn_layout)

        popup = Popup(title=wrap_rtl('Add Account'), content=content, size_hint=(0.8, 0.4))

        def on_ok(instance):
            u, p = user_input.text.strip(), pwd_input.text.strip()
            popup.dismiss()
            if u and p:
                threading.Thread(target=self.add_account, args=(u, p)).start()

        btn_ok.bind(on_press=on_ok)
        btn_cancel.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def generate_user_agent(self):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.5005.61 Mobile Safari/537.36",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0"
        ]
        return random.choice(ua_list)

    def create_session_requests(self, ua):
        headers = {
            "User-Agent": ua,
            "Host": "api.ecsc.gov.sy:8443",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "ar,en-US;q=0.7,en;q=0.3",
            "Referer": "https://ecsc.gov.sy/login",
            "Content-Type": "application/json",
            "Source": "WEB",
            "Origin": "https://ecsc.gov.sy",
            "Connection": "keep-alive"
        }
        sess = requests.Session()
        sess.headers.update(headers)
        return sess

    def add_account(self, user, pwd):
        sess = self.create_session_requests(self.generate_user_agent())
        t0 = time.time()
        if not self.login(user, pwd, sess):
            self.update_notification(f"Login failed for {user}", (1, 0, 0, 1))
            return
        self.update_notification(f"Logged in {user} in {time.time() - t0:.2f}s", (0, 1, 0, 1))
        self.accounts[user] = {"password": pwd, "session": sess}
        procs = self.fetch_process_ids(sess)
        if procs:
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            self.update_notification(f"Can't fetch process IDs for {user}", (1, 0, 0, 1))

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for _ in range(retries):
            try:
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False)
                if r.status_code == 200:
                    self.update_notification("Login successful.", (0, 1, 0, 1))
                    return True
                self.update_notification(f"Login failed ({r.status_code})", (1, 0, 0, 1))
                return False
            except Exception as e:
                self.update_notification(f"Login error: {e}", (1, 0, 0, 1))
                return False
        return False

    def fetch_process_ids(self, sess):
        try:
            r = sess.post(
                "https://api.ecsc.gov.sy:8443/dbm/db/execute",
                json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                headers={
                    "Content-Type": "application/json",
                    "Alias": "OPkUVkYsyq",
                    "Referer": "https://ecsc.gov.sy/requests",
                    "Origin": "https://ecsc.gov.sy"
                },
                verify=False
            )
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            self.update_notification(f"Fetch IDs failed ({r.status_code})", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"Error fetching IDs: {e}", (1, 0, 0, 1))
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        lbl = Label(
            text=wrap_rtl(f"Account: {user}"),
            size_hint_y=None, height='25dp', font_name='Arabic', text_size=(self.width, None), halign='right', valign='middle'
        )
        layout.add_widget(lbl)

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            name = proc.get("ZCENTER_NAME", "Unknown")
            btn = Button(text=wrap_rtl(name), font_name='Arabic', halign='right')
            btn.bind(size=lambda inst, val: setattr(inst, 'text_size', (inst.width, None)))
            prog = ProgressBar(max=1, value=0)
            box = BoxLayout(size_hint_y=None, height='40dp', spacing=5)
            box.add_widget(btn)
            box.add_widget(prog)
            layout.add_widget(box)
            btn.bind(on_press=lambda inst, u=user, p=pid, pr=prog: threading.Thread(
                target=self._handle_captcha, args=(u, p, pr)
            ).start())

    def _handle_captcha(self, user, pid, prog):
        Clock.schedule_once(lambda dt: setattr(prog, 'value', 0), 0)
        data = self.get_captcha(self.accounts[user]["session"], pid, user)
        Clock.schedule_once(lambda dt: setattr(prog, 'value', prog.max), 0)
        if data:
            self.current_captcha = (user, pid)
            Clock.schedule_once(lambda dt: self._display_captcha(data), 0)

    def get_captcha(self, sess, pid, user):
        url = f"https://api.ecsc.gov.sy:8443/captcha/get/{pid}"
        try:
            while True:
                r = sess.get(url, verify=False)
                if r.status_code == 200:
                    return r.json().get("file")
                if r.status_code == 429:
                    time.sleep(0.1)
                elif r.status_code in (401, 403):
                    if not self.login(user, self.accounts[user]["password"], sess):
                        return None
                else:
                    self.update_notification(f"Server error: {r.status_code}", (1, 0, 0, 1))
                    return None
        except Exception as e:
            self.update_notification(f"Captcha error: {e}", (1, 0, 0, 1))
        return None

    def predict_captcha(self, pil_img: PILImage.Image):
        t_api_start = time.time()
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            files = {"image": ("captcha.png", img_byte_arr, "image/png")}

            response = requests.post(CAPTCHA_API_URL, files=files, timeout=30)
            api_time = (time.time() - t_api_start) * 1000

            full_json = response.json()
            # عرض كامل الرد بدلاً من الصورة
            self.update_notification(f"captcha received: {full_json}", (0,0,1,1))
            return full_json.get('result'), api_time
        except Exception as e:
            self.update_notification(f"API Request Error: {e}", (1, 0, 0, 1))
            return None, (time.time() - t_api_start) * 1000

    def _display_captcha(self, b64data):
        # تجاوز عرض الصورة، نعرض نص فقط بعد استلام الرد
        pass

    def submit_captcha(self, sol):
        # كما في الكود الأصلي، عرض كامل نص الخادم في Popup
        if not self.current_captcha:
            self.update_notification("Error: No CAPTCHA context.", (1, 0, 0, 1))
            return
        user, pid = self.current_captcha
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"
        try:
            r = sess.get(url, verify=False)
            full_text = r.text
            success = (r.status_code == 200)
            self.update_notification(f"Submit response: {r.status_code}", (0,1,0,1) if success else (1,0,0,1), success=success)
            lbl = Label(
                text=wrap_rtl(full_text),
                font_name='Arabic',
                text_size=(self.width*0.9, None),
                halign='right',
                valign='top',
                size_hint_y=None
            )
            lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
            Popup(title=wrap_rtl('Server Response / رد الخادم'), content=lbl, size_hint=(0.9, 0.6)).open()
        except Exception as e:
            self.update_notification(f"Submit error: {e}", (1, 0, 0, 1))

class CaptchaApp(App):
    def build(self):
        Builder.load_string(KV)
        return CaptchaWidget()

if __name__ == '__main__':
    CaptchaApp().run()
