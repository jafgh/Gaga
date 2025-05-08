import os
import threading
import time
import base64
import io
import random
import requests
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
from kivy.graphics import Color, Rectangle
from kivy.storage.jsonstore import JsonStore
from kivy.core.window import Window


assets_dir = os.path.join(os.path.dirname(__file__), 'assets')
if not os.path.exists(assets_dir):
    os.makedirs(assets_dir)
font_path = os.path.join(assets_dir, 'arabic.ttf')

if os.path.exists(font_path):
    LabelBase.register(name='Roboto', fn_regular=font_path)
else:
    print(f"تحذير: ملف الخط العربي {font_path} غير موجود. قد لا يتم عرض النص العربي بشكل صحيح.")
    try:
        LabelBase.register(name='Roboto', fn_regular='Roboto-Regular.ttf') # Fallback
    except Exception as e:
        print(f"Error registering fallback font: {e}")
        # As a last resort, Kivy might use a default system font.


KV = '''
<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10
    font_name: 'Roboto'

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        Label:
            id: notification_label
            text: 'الرجاء تكوين واجهة برمجة التطبيقات إذا لم يتم ذلك بعد.'
            font_name: 'Roboto'
            font_size: 14
            color: 1,1,1,1
            halign: 'right'
            text_size: self.width, None

    Button:
        text: 'إضافة حساب'
        font_name: 'Roboto'
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
            
    BoxLayout:
        id: success_indicator_bar
        size_hint_y: None
        height: '0dp'
        canvas.before:
            Color:
                rgba: 0, 1, 0, 0
            Rectangle:
                pos: self.pos
                size: self.size

    Label:
        id: speed_label
        text: 'وقت استدعاء الواجهة: 0 مل/ث'
        font_name: 'Roboto'
        size_hint_y: None
        height: '30dp'
        font_size: 12
        halign: 'right'
        text_size: self.width, None

<PopupContent@BoxLayout>:
    orientation: 'vertical'
    spacing: 10
    padding: 10
    font_name: 'Roboto'
    user_input: user_input_id
    pwd_input: pwd_input_id

    TextInput:
        id: user_input_id
        hint_text: 'اسم المستخدم'
        font_name: 'Roboto'
        multiline: False
        halign: 'right'
        write_tab: False
    TextInput:
        id: pwd_input_id
        hint_text: 'كلمة المرور'
        font_name: 'Roboto'
        password: True
        multiline: False
        halign: 'right'
        write_tab: False
    BoxLayout:
        size_hint_y: None
        height: '40dp'
        spacing: 10
        Button:
            id: btn_ok
            text: 'موافق'
            font_name: 'Roboto'
        Button:
            id: btn_cancel
            text: 'إلغاء'
            font_name: 'Roboto'

<ErrorPopup@Popup>:
    title: 'خطأ'
    title_font_name: 'Roboto'
    content: error_label
    size_hint: 0.8, 0.4
    title_align: 'right'
    ErrorLabel:
        id: error_label
        font_name: 'Roboto'
        halign: 'right'
        text_size: self.width * 0.9, None

<ErrorLabel@Label>:
    font_name: 'Roboto'
    halign: 'right'
    valign: 'middle'
    padding_x: 10
    size_hint_y: None
    height: self.texture_size[1] if self.text else 0

<ApiConfigPopupContent@BoxLayout>:
    orientation: 'vertical'
    spacing: '10dp'
    padding: '10dp'
    api_part_input: api_part_input_id
    error_display_label: error_label_id

    Label:
        text: "إعداد واجهة برمجة التطبيقات (لأول مرة)"
        font_name: 'Roboto'
        size_hint_y: None
        height: self.texture_size[1]
        halign: 'right'
        text_size: self.width, None
    Label:
        text: 'الرجاء إدخال الجزء المتغير من عنوان URL لواجهة CAPTCHA.\\nمثال: إذا كان الرابط https://jafgh.pythonanywhere.com/predict، أدخل "jafgh".'
        font_name: 'Roboto'
        halign: 'right'
        size_hint_y: None
        height: self.texture_size[1]
        text_size: self.width, None
    TextInput:
        id: api_part_input_id
        hint_text: 'أدخل الجزء هنا (مثال: jafgh)'
        multiline: False
        font_name: 'Roboto'
        halign: 'right'
        write_tab: False
        size_hint_y: None
        height: '40dp'
    Label:
        id: error_label_id # Important: This ID is used in Python code
        text: ""
        font_name: 'Roboto'
        color: 1,0,0,1
        size_hint_y: None
        height: self.texture_size[1] if self.text else 0 # Only take height if text exists
        halign: 'right'
        text_size: self.width, None
    Button:
        id: save_button_id
        text: "حفظ ومتابعة"
        font_name: 'Roboto'
        size_hint_y: None
        height: '40dp'
'''


class CaptchaWidget(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.accounts = {}
        self.current_captcha = None
        self.success_bar_color_instruction = self.ids.success_indicator_bar.canvas.before.children[0]
        app = App.get_running_app()
        if not getattr(app, 'CAPTCHA_API_URL', None):
            self.ids.notification_label.text = 'الرجاء تكوين واجهة API أولاً من خلال إعدادات التطبيق.'
            self.ids.notification_label.color = (1, 0.6, 0, 1) # Orange warning

    def show_error(self, msg):
        content_label = ErrorLabel(text=msg)
        popup = ErrorPopup(content=content_label)
        content_label.bind(texture_size=content_label.setter('size'))
        popup.open()

    def update_notification(self, msg, color):
        def _update(dt):
            lbl = self.ids.notification_label
            lbl.text = msg
            lbl.color = color
        Clock.schedule_once(_update, 0)

    def open_add_account_popup(self):
        app = App.get_running_app()
        if not getattr(app, 'CAPTCHA_API_URL', None):
            self.show_error("يجب تكوين واجهة برمجة التطبيقات أولاً قبل إضافة حساب.")
            return

        content = Builder.load_string('PopupContent:')
        popup = Popup(title='إضافة حساب جديد', content=content, size_hint=(0.9, 0.5), title_font_name='Roboto', title_align='right')

        def on_ok(instance):
            u = content.user_input.text.strip()
            p = content.pwd_input.text.strip()
            popup.dismiss()
            if u and p:
                threading.Thread(target=self.add_account, args=(u, p), daemon=True).start()

        content.ids.btn_ok.bind(on_press=on_ok)
        content.ids.btn_cancel.bind(on_press=lambda x: popup.dismiss())
        popup.open()

    def generate_user_agent(self):
        ua_list = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:100.0) Gecko/20100101 Firefox/100.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36",
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
            self.update_notification(f"فشل تسجيل الدخول للمستخدم {user}", (1, 0, 0, 1));
            return
        self.update_notification(f"تم تسجيل دخول {user} في {time.time() - t0:.2f} ثانية", (0, 1, 0, 1))
        self.accounts[user] = {"password": pwd, "session": sess}
        procs = self.fetch_process_ids(sess)
        if procs:
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            self.update_notification(f"لا يمكن جلب معرفات العمليات للمستخدم {user}", (1, 0, 0, 1))

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for _ in range(retries):
            try:
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False, timeout=10)
                if r.status_code == 200:
                    self.update_notification("تم تسجيل الدخول بنجاح.", (0, 1, 0, 1));
                    return True
                self.update_notification(f"فشل تسجيل الدخول (الرمز: {r.status_code})", (1, 0, 0, 1));
                return False
            except requests.exceptions.RequestException as e:
                self.update_notification(f"خطأ في تسجيل الدخول: {e}", (1, 0, 0, 1));
            except Exception as e:
                self.update_notification(f"خطأ غير متوقع في تسجيل الدخول: {e}", (1,0,0,1))
        return False


    def fetch_process_ids(self, sess):
        try:
            r = sess.post("https://api.ecsc.gov.sy:8443/dbm/db/execute",
                          json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                          headers={"Content-Type": "application/json", "Alias": "OPkUVkYsyq",
                                   "Referer": "https://ecsc.gov.sy/requests", "Origin": "https://ecsc.gov.sy"},
                          verify=False, timeout=10)
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            self.update_notification(f"فشل جلب المعرفات (الرمز: {r.status_code})", (1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(f"خطأ في جلب المعرفات: {e}", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"خطأ غير متوقع في جلب المعرفات: {e}", (1,0,0,1))
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        user_label = Label(text=f"حساب: {user}", size_hint_y=None, height='25dp', font_name='Roboto', halign='right')
        user_label.bind(width=lambda instance, value: setattr(instance, 'text_size', (value * 0.95, None)))
        layout.add_widget(user_label)

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            center_name = proc.get("ZCENTER_NAME", "غير معروف")
            btn = Button(text=center_name, font_name='Roboto', halign='right')
            btn.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width * 0.9, None)))

            prog = ProgressBar(max=1, value=0)
            box = BoxLayout(size_hint_y=None, height='40dp', spacing=5)
            box.add_widget(btn);
            box.add_widget(prog)
            layout.add_widget(box)
            btn.bind(on_press=lambda inst, u=user, p=pid, pr=prog: threading.Thread(target=self._handle_captcha,
                                                                                      args=(u, p, pr), daemon=True).start())

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
                r = sess.get(url, verify=False, timeout=10)
                if r.status_code == 200:
                    return r.json().get("file")
                if r.status_code == 429:
                    self.update_notification("طلبات كثيرة جدًا، يتم الانتظار...", (1, 0.5, 0, 1))
                    time.sleep(1)
                elif r.status_code in (401, 403):
                    self.update_notification("جلسة غير صالحة، محاولة تسجيل الدخول مجددًا...", (1, 0.5, 0, 1))
                    if not self.login(user, self.accounts[user]["password"], sess): return None
                else:
                    self.update_notification(f"خطأ من الخادم عند جلب الكابتشا (الرمز: {r.status_code})", (1, 0, 0, 1))
                    return None
        except requests.exceptions.RequestException as e:
            self.update_notification(f"خطأ في جلب الكابتشا: {e}", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"خطأ غير متوقع في جلب الكابتشا: {e}", (1,0,0,1))
        return None

    def predict_captcha(self, pil_img: PILImage.Image):
        t_api_start = time.time()
        app = App.get_running_app()
        current_captcha_api_url = getattr(app, 'CAPTCHA_API_URL', None)

        if not current_captcha_api_url:
            self.update_notification("خطأ: لم يتم تكوين عنوان URL لواجهة برمجة التطبيقات.", (1,0,0,1))
            return None, 0, (time.time() - t_api_start) * 1000
        
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)

            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            response = requests.post(current_captcha_api_url, files=files, timeout=30)
            response.raise_for_status()

            api_response = response.json()
            predicted_text = api_response.get("result")

            if predicted_text is None:
                self.update_notification("خطأ من الواجهة: نتيجة التنبؤ مفقودة أو فارغة.", (1, 0.5, 0, 1))
                return None, 0, (time.time() - t_api_start) * 1000

            total_api_time_ms = (time.time() - t_api_start) * 1000
            return predicted_text, 0, total_api_time_ms

        except requests.exceptions.Timeout:
            self.update_notification(f"مهلة الاتصال بواجهة التنبؤ: {current_captcha_api_url}", (1, 0, 0, 1))
        except requests.exceptions.ConnectionError:
            self.update_notification(f"خطأ اتصال بواجهة التنبؤ: {current_captcha_api_url}", (1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(f"خطأ طلب من واجهة التنبؤ: {e}", (1, 0, 0, 1))
        except ValueError as e:
            self.update_notification(f"خطأ في استجابة واجهة التنبؤ: JSON غير صالح. {e}", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"خطأ باستدعاء واجهة التنبؤ: {e}", (1, 0, 0, 1))
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

            if not frames:
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

            buf = io.BytesIO(); binary_pil_img.save(buf, format='PNG'); buf.seek(0)
            core_img = CoreImage(buf, ext='png')
            img_w = KivyImage(texture=core_img.texture, size_hint_y=None, height='90dp')
            self.ids.captcha_box.add_widget(img_w)

            pred_text, pre_ms, api_call_ms = self.predict_captcha(binary_pil_img)

            Clock.schedule_once(lambda dt: setattr(self.ids.speed_label, 'text',
                                                  f"وقت استدعاء الواجهة: {api_call_ms:.2f} مل/ث"), 0)
            if pred_text is not None:
                self.update_notification(f"الكابتشا المتوقعة (API): {pred_text}", (0, 0, 1, 1))
                self.submit_captcha(pred_text)

        except Exception as e:
            self.update_notification(f"خطأ في معالجة/عرض الكابتشا: {e}", (1, 0, 0, 1))
            import traceback
            print(f"Detailed error in _display_captcha: {traceback.format_exc()}")


    def submit_captcha(self, sol):
        bar_container = self.ids.success_indicator_bar
        if not hasattr(self, 'success_bar_color_instruction'):
             self.success_bar_color_instruction = bar_container.canvas.before.children[0]

        bar_container.height = '0dp'
        self.success_bar_color_instruction.rgba = (0, 1, 0, 0)

        if not self.current_captcha:
            self.update_notification("خطأ: لا يوجد سياق كابتشا حالي للإرسال.", (1, 0, 0, 1))
            return

        user, pid = self.current_captcha;
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"
        try:
            r = sess.get(url, verify=False, timeout=15)
            
            msg_text = f"(الرمز: {r.status_code}) "
            try:
                msg_text += r.content.decode('utf-8', errors='replace')
            except Exception as decode_err:
                msg_text += f"[خطأ في فك التشفير: {decode_err}] " + str(r.content)

            if r.status_code == 200:
                col = (0, 1, 0, 1)
                self.update_notification(f"رد الخادم: {msg_text}", col)
                bar_container.height = '5dp'
                self.success_bar_color_instruction.rgba = (0, 1, 0, 1)
                Clock.schedule_once(self.hide_success_bar, 5)
            else:
                col = (1, 0, 0, 1)
                self.update_notification(f"رد الخادم: {msg_text}", col)

        except requests.exceptions.RequestException as e:
            self.update_notification(f"خطأ في الإرسال: {e}", (1, 0, 0, 1))
        except Exception as e:
            self.update_notification(f"خطأ غير متوقع في الإرسال: {e}", (1,0,0,1))

    def hide_success_bar(self, dt=None):
        self.ids.success_indicator_bar.height = '0dp'
        if hasattr(self, 'success_bar_color_instruction'):
            self.success_bar_color_instruction.rgba = (0, 1, 0, 0)


class CaptchaApp(App):
    CAPTCHA_API_URL = None 

    def build(self):
        self.load_api_config()
        Builder.load_string(KV)
        self.root_widget = CaptchaWidget() # Store reference
        return self.root_widget

    def load_api_config(self):
        # Use self.user_data_dir for storing app-specific data
        store_path = os.path.join(self.user_data_dir, 'app_settings.json')
        self.store = JsonStore(store_path)
        if self.store.exists('config') and 'api_dynamic_part' in self.store.get('config'):
            dynamic_part = self.store.get('config')['api_dynamic_part']
            if dynamic_part and dynamic_part.strip(): # Ensure it's not empty or just whitespace
                self.CAPTCHA_API_URL = f"https://{dynamic_part.strip()}.pythonanywhere.com/predict"
                print(f"Using saved API URL: {self.CAPTCHA_API_URL}")
                return
        self.CAPTCHA_API_URL = None 

    def on_start(self):
        if self.CAPTCHA_API_URL is None:
            self.show_api_config_popup()
        elif self.root_widget: # If API is already configured, update notification
             self.root_widget.ids.notification_label.text = "تم تحميل إعدادات الواجهة بنجاح."
             self.root_widget.ids.notification_label.color = (0,1,0,1)


    def _save_and_set_api_url(self, dynamic_part_text, popup_instance):
        dynamic_part = dynamic_part_text.strip()
        if not dynamic_part:
            if hasattr(popup_instance.content, 'error_display_label'):
                 popup_instance.content.error_display_label.text = "الحقل لا يمكن أن يكون فارغًا!"
                 popup_instance.content.error_display_label.height = popup_instance.content.error_display_label.texture_size[1]
            return

        self.store.put('config', api_dynamic_part=dynamic_part)
        self.CAPTCHA_API_URL = f"https://{dynamic_part}.pythonanywhere.com/predict"
        print(f"API URL configured to: {self.CAPTCHA_API_URL}")
        popup_instance.dismiss()
        
        if self.root_widget: # self.root is the root widget instance
            self.root_widget.ids.notification_label.text = "تم تكوين واجهة برمجة التطبيقات بنجاح!"
            self.root_widget.ids.notification_label.color = (0,1,0,1) # Green

    def show_api_config_popup(self):
        # Use the KV-defined ApiConfigPopupContent
        content = Builder.load_string('ApiConfigPopupContent:')
        
        popup = Popup(title="إعداد الواجهة", content=content, size_hint=(0.9, 0.6),
                      auto_dismiss=False, title_font_name='Roboto', title_align='right')
        
        # Bind the save button from the content
        save_button = content.ids.save_button_id
        save_button.bind(on_press=lambda x: self._save_and_set_api_url(content.api_part_input.text, popup))
        popup.open()


if __name__ == '__main__':
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    CaptchaApp().run()
