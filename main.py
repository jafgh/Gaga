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
from kivy.uix.image import Image as KivyImage
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.core.text import LabelBase

# --------------------------------------------------
# تسجيل خط Arabic من ملف assets/arabic.ttf
# --------------------------------------------------
LabelBase.register(name='Arabic', fn_regular=os.path.join('assets', 'arabic.ttf'))

# --------------------------------------------------
# دالة لوضع النص في سياق RTL دون قلب الأحرف، مع الحفاظ على الإنجليزية LTR
# --------------------------------------------------
def wrap_rtl(text):
    RLE = '\u202B'  # Right-to-Left Embedding
    PDF = '\u202C'  # Pop Directional Formatting
    return RLE + text + PDF

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

# --------------------------------------------------
# رابط الـ CAPTCHA API (سيُعدل عند التشغيل)
# --------------------------------------------------
CAPTCHA_API_URL = None

# --------------------------------------------------
# تصميم الواجهة باستخدام Kivy مع halign: 'right'
# --------------------------------------------------
KV = '''
<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        Label:
            id: notification_label
            text: ''
            font_size: 14
            font_name: 'Arabic'
            text_size: self.width, None
            halign: 'right'
            valign: 'middle'

    Button:
        text: root.wrap_rtl('Add Account')
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
        text: root.wrap_rtl('API Call Time: 0 ms')
        size_hint_y: None
        height: '30dp'
        font_size: 12
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

        api_prefix = load_api_prefix()
        if not api_prefix:
            Clock.schedule_once(lambda dt: self.ask_api_prefix(), 0)
        else:
            global CAPTCHA_API_URL
            CAPTCHA_API_URL = f"https://{api_prefix}.pythonanywhere.com/predict"

    def wrap_rtl(self, text):
        return wrap_rtl(text)

    def ask_api_prefix(self):
        layout = BoxLayout(orientation='vertical', spacing=10, padding=10)
        input_box = TextInput(hint_text=wrap_rtl("أدخل معرف API مثل: code"), multiline=False, halign='right')
        btn = Button(text=wrap_rtl("حفظ ومتابعة"), size_hint_y=None, height='40dp')

        layout.add_widget(Label(
            text=wrap_rtl("أدخل الجزء المتغير من رابط API:"),
            font_name='Arabic', text_size=(self.width, None), halign='right', valign='middle'))
        layout.add_widget(input_box)
        layout.add_widget(btn)

        popup = Popup(title=wrap_rtl("إعداد API"), content=layout, size_hint=(0.8, 0.4))

        def on_confirm(instance):
            prefix = input_box.text.strip()
            if prefix:
                save_api_prefix(prefix)
                global CAPTCHA_API_URL
                CAPTCHA_API_URL = f"https://{prefix}.pythonanywhere.com/predict"
                popup.dismiss()

        btn.bind(on_press=on_confirm)
        popup.open()

    def update_notification(self, msg, color):
        def _update(dt):
            lbl = self.ids.notification_label
            lbl.text = wrap_rtl(msg)
            lbl.color = color
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
            response.raise_for_status()
            api_response = response.json()
            predicted_text = api_response.get("result")
            total_api_time_ms = (time.time() - t_api_start) * 1000
            if predicted_text is None:
                self.update_notification("API Error: Prediction result missing.", (1, 0.5, 0, 1))
                return None, total_api_time_ms
            return predicted_text, total_api_time_ms
        except Exception as e:
            self.update_notification(f"API Request Error: {e}", (1, 0, 0, 1))
            return None, (time.time() - t_api_start) * 1000

    def _display_captcha(self, b64data):
        try:
            self.ids.captcha_box.clear_widgets()
            b64 = b64data.split(',')[1] if ',' in b64data else b64data
            raw = base64.b64decode(b64)
            pil = PILImage.open(io.BytesIO(raw))

            gray = np.array(pil.convert('L'))
            thresh = np.median(gray)
            bin_img = PILImage.fromarray((gray > thresh).astype(np.uint8) * 255)

            buf = io.BytesIO()
            bin_img.save(buf, format='PNG')
            buf.seek(0)
            core = CoreImage(buf, ext='png')
            img_w = KivyImage(texture=core.texture, size_hint_y=None, height='90dp')
            self.ids.captcha_box.add_widget(img_w)

            pred, api_ms = self.predict_captcha(bin_img)
            Clock.schedule_once(lambda dt: setattr(self.ids.speed_label, 'text',
                                                   wrap_rtl(f"API Call Time: {api_ms:.2f} ms")), 0)
            if pred:
                self.update_notification(f"Predicted CAPTCHA: {pred}", (0, 0, 1, 1))
                self.submit_captcha(pred)
        except Exception as e:
            self.update_notification(f"Error processing captcha: {e}", (1, 0, 0, 1))

    def submit_captcha(self, sol):
        if not self.current_captcha:
            self.update_notification("Error: No CAPTCHA context.", (1, 0, 0, 1))
            return
        user, pid = self.current_captcha
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"
        try:
            r = sess.get(url, verify=False)
            msg_text = r.text
            success = (r.status_code == 200)
            self.update_notification(f"Submit response: {msg_text}", (0, 1, 0, 1) if success else (1, 0, 0, 1))
            lbl = Label(
                text=wrap_rtl(msg_text),
                font_name='Arabic',
                text_size=(self.width*0.9, None),
                halign='right',
                valign='top',
                size_hint_y=None
            )
            lbl.bind(texture_size=lambda inst, val: setattr(inst, 'height', val[1]))
            Popup(title=wrap_rtl("Server Response"), content=lbl, size_hint=(0.9, 0.6)).open()
        except Exception as e:
            self.update_notification(f"Submit error: {e}", (1, 0, 0, 1))

class CaptchaApp(App):
    def build(self):
        Builder.load_string(KV)
        return CaptchaWidget()

if __name__ == '__main__':
    CaptchaApp().run()
