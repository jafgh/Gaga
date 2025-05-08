import os
import threading
import time
import base64
import io
import random
import requests  # تأكد من أن requests ومكتبات arabic_reshaper و python-bidi مثبتة
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
from kivy.config import ConfigParser
from arabic_reshaper import reshape
from bidi.algorithm import get_display

# تسجيل خط arabic.ttf كخط افتراضي (Roboto) لجميع عناصر النص
LabelBase.register(name='Roboto', fn_regular=os.path.join('assets', 'arabic.ttf'))

# --------------------------------------------------
# تحميل إعدادات API من ملف config.ini أو سؤال المستخدم في أول تشغيل
# --------------------------------------------------
config = ConfigParser()
config_file = os.path.join(App.get_running_app().user_data_dir if App.get_running_app() else os.getcwd(), 'config.ini')
config.read(config_file)
if not config.has_section('api'):
    config.add_section('api')
subdomain = config.get('api', 'subdomain', fallback=None)

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
            color: 1,1,1,1
            halign: 'right'
            text_size: self.size

    Button:
        text: root.translate('Add Account')
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
        text: root.translate('API Call Time:') + ' 0 ms'
        size_hint_y: None
        height: '30dp'
        font_size: 12
        halign: 'right'
        text_size: self.size
'''

class CaptchaWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {}
        self.current_captcha = None
        self.api_subdomain = subdomain
        # إذا لم يُحدد المجلد الفرعي لواجهة API، نفتح مربع نص للسؤال
        if not self.api_subdomain:
            Clock.schedule_once(lambda dt: self.open_api_popup(), 0)

    def translate(self, text):
        # إذا كان النص عربي، نعيد تشكيله ودعمه RTL
        try:
            # تحقق من وجود حروف عربية
            if any('\u0600' <= c <= '\u06FF' for c in text):
                reshaped = reshape(text)
                return get_display(reshaped)
        except Exception:
            pass
        return text

    def open_api_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        hint = 'مثال: 5543f' if any(c.isalpha() for c in 'مثال') else 'e.g. 5543f'
        sub_input = TextInput(hint_text=hint, multiline=False)
        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        btn_ok = Button(text=self.translate('OK'))
        btn_layout.add_widget(btn_ok)
        content.add_widget(Label(text=self.translate('Enter API subdomain:'), size_hint_y=None, height='30dp', halign='right', text_size=(None, None)))
        content.add_widget(sub_input)
        content.add_widget(btn_layout)
        popup = Popup(title=self.translate('Configure API'), content=content, size_hint=(0.8, 0.4), auto_dismiss=False)

        def on_ok(instance):
            sd = sub_input.text.strip()
            if sd:
                self.api_subdomain = sd
                config.set('api', 'subdomain', sd)
                with open(config_file, 'w') as f:
                    config.write(f)
                popup.dismiss()
        btn_ok.bind(on_press=on_ok)
        popup.open()

    @property
    def CAPTCHA_API_URL(self):
        return f"https://{self.api_subdomain}.pythonanywhere.com/predict"

    def show_error(self, msg):
        Popup(title='Error', content=Label(text=msg), size_hint=(0.8, 0.4)).open()

    def update_notification(self, msg, color):
        def _update(dt):
            lbl = self.ids.notification_label
            lbl.text = msg
            lbl.color = color

        Clock.schedule_once(_update, 0)

    def open_add_account_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        user_input = TextInput(hint_text='Username', multiline=False)
        pwd_input = TextInput(hint_text='Password', password=True, multiline=False)
        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
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
                    self.update_notification("Login successful.", (0, 1, 0, 1));
                    return True
                self.update_notification(f"Login failed ({r.status_code})", (1, 0, 0, 1));
                return False
            except Exception as e:
                self.update_notification(f"Login error: {e}", (1, 0, 0, 1));
                return False
        return False

    def fetch_process_ids(self, sess):
        try:
            r = sess.post("https://api.ecsc.gov.sy:8443/dbm/db/execute",
                          json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                          headers={"Content-Type": "application/json", "Alias": "OPkUVkYsyq",
                                   "Referer": "https://ecsc.gov.sy/requests", "Origin": "https://ecsc.gov.sy"},
                          verify=False)
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            self.update_notification(f"Fetch IDs failed ({r.status_code})", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"Error fetching IDs: {e}", (1, 0, 0, 1))
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        layout.add_widget(Label(text=f"Account: {user}", size_hint_y=None, height='25dp'))
        for proc in processes:
            pid = proc.get("PROCESS_ID")
            btn = Button(text=proc.get("ZCENTER_NAME", "Unknown"))
            prog = ProgressBar(max=1, value=0)
            box = BoxLayout(size_hint_y=None, height='40dp', spacing=5)
            box.add_widget(btn);
            box.add_widget(prog)
            layout.add_widget(box)
            btn.bind(on_press=lambda inst, u=user, p=pid, pr=prog: threading.Thread(target=self._handle_captcha,
                                                                                    args=(u, p, pr)).start())

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
                    if not self.login(user, self.accounts[user]["password"], sess): return None
                else:
                    self.update_notification(f"Server error: {r.status_code}", (1, 0, 0, 1))
                    return None
        except Exception as e:
            self.update_notification(f"Captcha error: {e}", (1, 0, 0, 1))
        return None

    # --- تعديل دالة predict_captcha لاستخدام API ---
    def predict_captcha(self, pil_img: PILImage.Image):
        """
        يرسل صورة PIL إلى API التنبؤ بالكابتشا.
        pil_img: كائن صورة PIL (يفضل أن تكون الصورة المعالجة بطريقة Otsu).
        يعيد: (النص المتوقع, وقت المعالجة (0 حاليا), وقت استدعاء API بالمللي ثانية)
        """
        t_api_start = time.time()
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')  # إرسال الصورة بصيغة PNG
            img_byte_arr.seek(0)  # العودة إلى بداية المخزن المؤقت

            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            # استخدم CAPTCHA_API_URL المعرف في الأعلى
            response = requests.post(CAPTCHA_API_URL, files=files, timeout=30)  # إضافة مهلة زمنية
            response.raise_for_status()  # إطلاق استثناء لأخطاء HTTP (4xx أو 5xx)

            api_response = response.json()
            predicted_text = api_response.get("result")

            if not predicted_text and predicted_text != "":  # "" is a valid (but bad) prediction
                self.update_notification(f"API Error: Prediction result is missing or null.", (1, 0.5, 0, 1))
                return None, 0, (time.time() - t_api_start) * 1000

            total_api_time_ms = (time.time() - t_api_start) * 1000
            return predicted_text, 0, total_api_time_ms  # (prediction, preprocess_time_ms = 0, api_call_time_ms)

        except requests.exceptions.Timeout:
            self.update_notification(f"API Request Error: Timeout connecting to {CAPTCHA_API_URL}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except requests.exceptions.ConnectionError:
            self.update_notification(f"API Request Error: Could not connect to {CAPTCHA_API_URL}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except requests.exceptions.RequestException as e:
            self.update_notification(f"API Request Error: {e}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except ValueError as e:  # JSONDecodeError يرث من ValueError
            self.update_notification(f"API Response Error: Invalid JSON received. {e}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except Exception as e:
            self.update_notification(f"Error calling prediction API: {e}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000

    def _display_captcha(self, b64data):
        try:
            self.ids.captcha_box.clear_widgets()
            b64 = b64data.split(',')[1] if ',' in b64data else b64data
            raw = base64.b64decode(b64)
            pil_original = PILImage.open(io.BytesIO(raw))  # الصورة الأصلية قد تكون GIF

            # معالجة Otsu (تبقى كما هي لإنتاج الصورة الثنائية)
            frames = []
            try:
                while True:
                    frames.append(np.array(pil_original.convert('RGB'), dtype=np.uint8))
                    pil_original.seek(pil_original.tell() + 1)
            except EOFError:
                pass

            if not frames:  # إذا لم تكن الصورة GIF أو فشلت قراءة الإطارات
                bg = np.array(pil_original.convert('RGB'), dtype=np.uint8)
            else:
                bg = np.median(np.stack(frames), axis=0).astype(np.uint8)

            gray = (0.2989 * bg[..., 0] + 0.5870 * bg[..., 1] + 0.1140 * bg[..., 2]).astype(np.uint8)
            hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 256))
            total = gray.size;
            sum_tot = np.dot(np.arange(256), hist)
            sumB = 0;
            wB = 0;
            max_var = 0;
            thresh = 0
            for i, h in enumerate(hist):
                wB += h
                if wB == 0: continue
                wF = total - wB
                if wF == 0: break
                sumB += i * h;
                mB = sumB / wB;
                mF = (sum_tot - sumB) / wF
                varBetween = wB * wF * (mB - mF) ** 2
                if varBetween > max_var: max_var = varBetween; thresh = i

            # 'binary' هي الصورة التي سترسل إلى API
            binary_pil_img = PILImage.fromarray(gray, 'L').point(lambda p: 255 if p > thresh else 0)

            # عرض الصورة المعالجة في الواجهة (اختياري لكن مفيد للمستخدم)
            buf = io.BytesIO();
            binary_pil_img.save(buf, format='PNG');
            buf.seek(0)
            core_img = CoreImage(buf, ext='png')
            img_w = KivyImage(texture=core_img.texture, size_hint_y=None, height='90dp')
            self.ids.captcha_box.add_widget(img_w)

            # استدعاء دالة التنبؤ الجديدة التي تستخدم API
            # `binary_pil_img` هي الصورة بعد معالجة Otsu
            pred_text, pre_ms, api_call_ms = self.predict_captcha(binary_pil_img)

            if pred_text is not None:  # التحقق من أن التنبؤ لم يفشل
                self.update_notification(f"Predicted CAPTCHA (API): {pred_text}", (0, 0, 1, 1))
                # تحديث label الوقت ليعكس وقت استدعاء API
                Clock.schedule_once(lambda dt: setattr(self.ids.speed_label, 'text',
                                                       f"API Call Time: {api_call_ms:.2f} ms"), 0)
                self.submit_captcha(pred_text)
            # else: تم عرض رسالة الخطأ بالفعل من داخل predict_captcha

        except Exception as e:
            self.update_notification(f"Error processing/displaying captcha: {e}", (1, 0, 0, 1))

    def submit_captcha(self, sol):
        if not self.current_captcha:
            self.update_notification("Error: No current CAPTCHA context for submission.", (1, 0, 0, 1))
            return
        user, pid = self.current_captcha;
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"
        try:
            r = sess.get(url, verify=False)
            col = (0, 1, 0, 1) if r.status_code == 200 else (1, 0, 0, 1)
            msg_text = r.text
            try:  # محاولة فك تشفير النص إذا كان UTF-8 مع رموز غير صالحة
                msg_text = r.content.decode('utf-8', errors='replace')
            except Exception:
                pass  # استخدام r.text الأصلي إذا فشل الفك
            self.update_notification(f"Submit response: {msg_text}", col)
        except Exception as e:
            self.update_notification(f"Submit error: {e}", (1, 0, 0, 1))


class CaptchaApp(App):
    def build(self):
        Builder.load_string(KV)
        return CaptchaWidget()


if __name__ == '__main__':
    CaptchaApp().run()
