import os
import threading
import time
import base64
import io
import random
import requests  # تأكد من أن requests مثبت
from PIL import Image as PILImage
import numpy as np
# import onnxruntime as ort # --- لم نعد بحاجة لهذه المكتبة هنا
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

# --- لإضافة دعم الخط العربي ---
from kivy.core.text import LabelBase

# --- للتعامل مع إعدادات التطبيق ---
from kivy.properties import StringProperty
# ConfigParser is usually handled by App.config directly

# --- رابط API الخاص بك ---
# سيتم بناؤه ديناميكياً الآن.
CAPTCHA_API_URL_TEMPLATE = "https://{domain_part}.pythonanywhere.com/predict"
DEFAULT_API_DOMAIN = "0000" # القيمة الافتراضية لجزء الدومين


# --------------------------------------------------
# تصميم الواجهة باستخدام Kivy
# --------------------------------------------------
KV = '''
<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    # --- ثالثاً: مربع نص لإدخال "start code" في بداية التطبيق ---
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: 5
        Label:
            text: 'Start API Code:'
            font_name: 'ArabicFont' # استخدام الخط العربي إذا كان النص عربياً
            size_hint_x: 0.3
        TextInput:
            id: api_code_input
            size_hint_x: 0.5
            multiline: False
            # font_name: 'ArabicFont' # إذا كان الإدخال قد يكون عربياً
        Button:
            text: 'Save Code'
            # font_name: 'ArabicFont' # إذا كان النص عربياً
            size_hint_x: 0.2
            on_press: root.save_api_code(api_code_input.text)

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        Label:
            id: notification_label
            text: ''
            font_name: 'ArabicFont' # --- أولاً: استخدام الخط العربي هنا ---
            font_size: 36
            color: 1,1,1,1

    Button:
        text: 'Add Account' # يمكن ترجمتها واستخدام الخط العربي
        # font_name: 'ArabicFont'
        size_hint_y: None
        height: '40dp'
        on_press: root.open_add_account_popup()

    BoxLayout:
        id: captcha_box # --- ثانياً: هذا الصندوق سيعرض "capatcha recieved" ---
        orientation: 'vertical'
        size_hint_y: None
        # height: '100dp' # يمكنك تحديد ارتفاع ثابت إذا لزم الأمر
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

    # --- ثالثاً: عرض الكود الحالي وزر لتغييره ---
    BoxLayout:
        size_hint_y: None
        height: '30dp'
        spacing: 5
        Label:
            id: current_api_code_display
            text: 'Code is jafgh' # سيتم تحديثه
            font_name: 'ArabicFont' # استخدام الخط العربي إذا كان النص عربياً
        Button:
            text: 'Change' # يمكن ترجمتها واستخدام الخط العربي
            # font_name: 'ArabicFont'
            on_press: api_code_input.focus = True # لنقل التركيز إلى حقل الإدخال في الأعلى
'''


class CaptchaWidget(BoxLayout):
    current_api_domain_part = StringProperty(DEFAULT_API_DOMAIN)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {}
        self.current_captcha = None
        self.load_api_code() # تحميل الكود المحفوظ عند البدء
        # تأكد من أن الواجهة تعكس الكود المحمّل
        Clock.schedule_once(self._initialize_api_code_display, 0)

    def _initialize_api_code_display(self, dt=None):
        # التأكد من أن self.ids متاح
        if hasattr(self, 'ids') and self.ids:
            self.ids.api_code_input.text = self.current_api_domain_part
            self.ids.current_api_code_display.text = f'Code is {self.current_api_domain_part}'
        else:
            # إذا لم تكن ids متاحة بعد، حاول مرة أخرى قريباً
            Clock.schedule_once(self._initialize_api_code_display, 0.1)


    def get_full_api_url(self):
        return CAPTCHA_API_URL_TEMPLATE.format(domain_part=self.current_api_domain_part)

    def load_api_code(self):
        app = App.get_running_app()
        # تأكد من أن config مهيأ
        if app and hasattr(app, 'config') and app.config:
            self.current_api_domain_part = app.config.get('appsettings', 'api_domain', fallback=DEFAULT_API_DOMAIN)
        else:
            self.current_api_domain_part = DEFAULT_API_DOMAIN


    def save_api_code(self, new_code):
        new_code = new_code.strip()
        if not new_code:
            self.show_error("API Code cannot be empty.")
            self.ids.api_code_input.text = self.current_api_domain_part # إعادة القيمة الحالية
            return

        app = App.get_running_app()
        if app and hasattr(app, 'config') and app.config:
            app.config.set('appsettings', 'api_domain', new_code)
            app.config.write()
            self.current_api_domain_part = new_code
            self.ids.current_api_code_display.text = f'Code is {self.current_api_domain_part}'
            self.update_notification(f"API Code updated to: {new_code}", (0, 1, 0, 1))
        else:
            self.show_error("Could not save API code due to config error.")


    def show_error(self, msg):
        # مثال على استخدام الخط العربي في النافذة المنبثقة
        content_label = Label(text=msg, font_name='ArabicFont')
        # --- التصحيح هنا ---
        popup = Popup(title='خطأ', content=content_label, size_hint=(0.8, 0.4), title_font='ArabicFont')
        popup.open()

    def update_notification(self, msg, color):
        def _update(dt):
            lbl = self.ids.notification_label
            lbl.text = msg
            lbl.color = color
        Clock.schedule_once(_update, 0)

    def open_add_account_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        # مثال على استخدام الخط العربي للنصوص المؤقتة والأزرار
        user_input = TextInput(hint_text='اسم المستخدم', multiline=False, font_name='ArabicFont')
        pwd_input = TextInput(hint_text='كلمة المرور', password=True, multiline=False, font_name='ArabicFont')
        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        btn_ok, btn_cancel = Button(text='موافق', font_name='ArabicFont'), Button(text='إلغاء', font_name='ArabicFont')
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(user_input)
        content.add_widget(pwd_input)
        content.add_widget(btn_layout)
        # --- التصحيح هنا ---
        popup = Popup(title='إضافة حساب', content=content, size_hint=(0.8, 0.4), title_font='ArabicFont')

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
            # استخدام الخط العربي في أسماء المراكز إذا كانت متاحة
            # for proc in procs:
            #     proc["ZCENTER_NAME_AR"] = ترجمة_اسم_المركز_للعربية(proc.get("ZCENTER_NAME"))
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
                # لا يجب أن يكون return False هنا مباشرة، بل بعد فشل كل المحاولات
            except Exception as e:
                self.update_notification(f"Login error: {e}", (1, 0, 0, 1));
        return False # إرجاع False بعد انتهاء جميع المحاولات

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
        # استخدام الخط العربي لعرض اسم الحساب
        layout.add_widget(Label(text=f"الحساب: {user}", size_hint_y=None, height='25dp', font_name='ArabicFont'))
        for proc in processes:
            pid = proc.get("PROCESS_ID")
            # عرض اسم المركز باللغة العربية إذا كان متاحاً، وإلا الاسم الافتراضي
            center_name = proc.get("ZCENTER_NAME_AR", proc.get("ZCENTER_NAME", "Unknown"))
            btn = Button(text=center_name, font_name='ArabicFont')
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

    def predict_captcha(self, pil_img: PILImage.Image):
        t_api_start = time.time()
        dynamic_api_url = self.get_full_api_url() # --- ثالثاً: استخدام الرابط الديناميكي ---
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            response = requests.post(dynamic_api_url, files=files, timeout=30)
            response.raise_for_status()

            api_response = response.json()
            predicted_text = api_response.get("result")

            if not predicted_text and predicted_text != "": # "" is a valid (but bad) prediction
                self.update_notification(f"API Error: Prediction result is missing or null.", (1, 0.5, 0, 1))
                return None, 0, (time.time() - t_api_start) * 1000

            total_api_time_ms = (time.time() - t_api_start) * 1000
            return predicted_text, 0, total_api_time_ms

        except requests.exceptions.Timeout:
            self.update_notification(f"API Request Error: Timeout connecting to {dynamic_api_url}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except requests.exceptions.ConnectionError:
            self.update_notification(f"API Request Error: Could not connect to {dynamic_api_url}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except requests.exceptions.RequestException as e:
            self.update_notification(f"API Request Error: {e}", (1, 0, 0, 1))
            return None, 0, (time.time() - t_api_start) * 1000
        except ValueError as e: # JSONDecodeError يرث من ValueError
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
            pil_original = PILImage.open(io.BytesIO(raw))

            frames = []
            try:
                while True:
                    frames.append(np.array(pil_original.convert('RGB'), dtype=np.uint8))
                    pil_original.seek(pil_original.tell() + 1)
            except EOFError:
                pass

            if not frames: # إذا لم تكن الصورة GIF أو فشلت قراءة الإطارات
                bg = np.array(pil_original.convert('RGB'), dtype=np.uint8)
            else:
                bg = np.median(np.stack(frames), axis=0).astype(np.uint8)

            gray = (0.2989 * bg[..., 0] + 0.5870 * bg[..., 1] + 0.1140 * bg[..., 2]).astype(np.uint8)
            hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 256))
            total = gray.size; sum_tot = np.dot(np.arange(256), hist)
            sumB = 0; wB = 0; max_var = 0; thresh = 0
            for i, h in enumerate(hist):
                wB += h
                if wB == 0: continue
                wF = total - wB
                if wF == 0: break
                sumB += i * h; mB = sumB / wB; mF = (sum_tot - sumB) / wF
                varBetween = wB * wF * (mB - mF) ** 2
                if varBetween > max_var: max_var = varBetween; thresh = i
            binary_pil_img = PILImage.fromarray(gray, 'L').point(lambda p: 255 if p > thresh else 0)

            # --- ثانياً: استبدال عرض الصورة بنص "capatcha recieved" ---
            captcha_received_label = Label(
                text='capatcha recieved', # يمكن ترجمتها واستخدام الخط العربي
                # font_name='ArabicFont',
                font_size='60sp', # حجم الخط 72
                color=(1, 0.647, 0, 1) # اللون البرتقالي (R, G, B, A)
            )
            self.ids.captcha_box.add_widget(captcha_received_label)
            # يمكنك ضبط ارتفاع captcha_box إذا لزم الأمر ليتناسب مع النص الكبير
            # self.ids.captcha_box.height = '100dp'

            pred_text, pre_ms, api_call_ms = self.predict_captcha(binary_pil_img)

            if pred_text is not None:
                self.update_notification(f"Predicted CAPTCHA (API): {pred_text}", (0, 0, 1, 1))
                Clock.schedule_once(lambda dt: setattr(self.ids.speed_label, 'text',
                                                        f"API Call Time: {api_call_ms:.2f} ms"), 0)
                self.submit_captcha(pred_text)

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
            try: # محاولة فك تشفير النص إذا كان UTF-8 مع رموز غير صالحة
                msg_text = r.content.decode('utf-8', errors='replace')
            except Exception:
                pass # استخدام r.text الأصلي إذا فشل الفك
            self.update_notification(f"Submit response: {msg_text}", col)
        except Exception as e:
            self.update_notification(f"Submit error: {e}", (1, 0, 0, 1))


class CaptchaApp(App):
    def build_config(self, config):
        # --- ثالثاً: تحديد القيم الافتراضية لإعدادات التطبيق ---
        config.setdefaults('appsettings', {
            'api_domain': DEFAULT_API_DOMAIN
        })

    # يمكنك إضافة لوحة إعدادات Kivy إذا أردت واجهة مستخدم أكثر تقدماً للإعدادات
    # def build_settings(self, settings):
    #     settings.add_json_panel('App Settings', self.config, data='''
    #         [
    #             {"type": "string", "title": "API Domain Code",
    #              "desc": "The subdomain for the CAPTCHA API (e.g., jafgh)",
    #              "section": "appsettings", "key": "api_domain"}
    #         ]
    #     ''')

    def build(self):
        # --- أولاً: إضافة دعم للغة العربية ---
        # تأكد من أن مجلد assets وملف arabic.ttf في المسار الصحيح
        # (يفترض أنهما في نفس مستوى ملف .py الرئيسي أو في مجلد assets)
        font_path = os.path.join(os.path.dirname(__file__), 'assets', 'arabic.ttf')
        if not os.path.exists(font_path): # إذا كان في جذر المشروع مباشرة
            font_path_alt = 'assets/arabic.ttf'
            if os.path.exists(font_path_alt):
                font_path = font_path_alt
            else: # إذا كان السكربت في مجلد والمجلد assets في الجذر
                # هذا الجزء قد يحتاج تعديل بناءً على هيكل مشروعك الفعلي عند التشغيل على أندرويد
                # المسار التالي يفترض أن 'assets' في نفس مستوى مجلد السكربت الرئيسي.
                # إذا كان السكربت في مجلد فرعي والمجلد assets في جذر المشروع، ستحتاج لتعديل المسار.
                # على سبيل المثال، إذا كان main.py داخل مجلد app، و assets في نفس مستوى app:
                # base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                # font_path_alt_2 = os.path.join(base_dir, 'assets', 'arabic.ttf')
                # if os.path.exists(font_path_alt_2):
                #     font_path = font_path_alt_2
                # في Pydroid3، قد يكون المسار الحالي هو جذر المشروع المؤقت
                 pass # اترك font_path كما هو، يفترض أن assets/arabic.ttf موجودة بالنسبة للملف


        if os.path.exists(font_path):
            LabelBase.register(name='ArabicFont', fn_regular=font_path)
            # يمكنك جعل الخط العربي هو الخط الافتراضي لجميع الـ Labels إذا أردت:
            # from kivy.uix.label import Label
            # Label.font_name = 'ArabicFont'
        else:
            print(f"تحذير: ملف الخط العربي غير موجود في المسار المتوقع: {font_path}. قد لا يتم عرض النصوص العربية بشكل صحيح.")
            # يمكنك إضافة رسالة خطأ للمستخدم هنا إذا أردت

        # --- ثالثاً: تهيئة وتحميل إعدادات التطبيق ---
        # self.config يتم تهيئته تلقائياً بواسطة Kivy App
        # استدعاء build_config لضمان وجود القيم الافتراضية
        # self.config.read(self.get_application_config()) # تحميل الإعدادات الموجودة
        # build_config سيتم استدعاؤها تلقائياً إذا لم يتم العثور على ملف الإعدادات


        Builder.load_string(KV)
        widget = CaptchaWidget()
        # استدعاء load_api_code بعد بناء الودجت بالكامل لضمان توفر ids
        # widget.load_api_code() # تم نقلها إلى __init__ مع جدولة
        return widget

    def on_stop(self):
        # عادةً ما يتم حفظ الإعدادات عند تغييرها مباشرة بواسطة app.config.write()
        pass


if __name__ == '__main__':
    # لتعطيل تحذيرات طلبات HTTPS غير الموثقة من مكتبة requests
    import urllib3
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except AttributeError: # قد يكون اسم الاستثناء مختلفًا في إصدارات أقدم
        pass
    CaptchaApp().run()
