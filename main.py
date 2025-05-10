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
from kivy.uix.image import Image as KivyImage  # Will not be used to display captcha image directly
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage  # Still needed for processing
from kivy.storage.jsonstore import JsonStore
# StringProperty, NumericProperty removed as full language switching is removed

# --- مكتبة لدعم عرض النصوص العربية بشكل صحيح ---
from bidi.algorithm import get_display

# --- تعريف الخط الافتراضي ---
# تأكد من أن هذا الخط مثبت على نظامك ويدعم العربية والإنجليزية بشكل جيد
DEFAULT_FONT_NAME = 'Arial'  # أو Tahoma, Noto Sans Arabic, etc.


# --- وظيفة مساعدة للتحقق مما إذا كان النص عربيًا ---
def is_arabic_string(text_string):
    if isinstance(text_string, str):
        # تحقق من وجود أحرف في نطاق اليونيكود العربي
        return any("\u0600" <= char <= "\u06FF" for char in text_string)
    return False


# --------------------------------------------------
# تصميم الواجهة باستخدام Kivy (النصوص الآن بالإنجليزية)
# --------------------------------------------------
KV = '''
#:import App kivy.app.App

<BaseLabel@Label>: # For labels that might display Arabic from API
    font_name: App.get_running_app().DEFAULT_FONT_NAME
    # halign and text_language will be set in Python if content is Arabic

<EnglishLabel@Label>: # For static English labels
    font_name: App.get_running_app().DEFAULT_FONT_NAME
    halign: 'left'
    text_language: '' # Explicitly set for English if needed, usually Kivy default is LTR

<EnglishButton@Button>:
    font_name: App.get_running_app().DEFAULT_FONT_NAME

<EnglishTextInput@TextInput>:
    font_name: App.get_running_app().DEFAULT_FONT_NAME
    halign: 'left'
    write_tab: False

<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        BaseLabel: # This label will display API responses, could be Arabic
            id: notification_label
            text: '' # Default empty
            font_size: '16sp'
            color: 1,1,1,1

    EnglishButton:
        text: 'Add Account' # Static English
        size_hint_y: None
        height: '40dp'
        on_press: root.open_add_account_popup()

    # This BoxLayout will hold the "CAPTCHA RECIEVED" and predicted text
    BoxLayout:
        id: captcha_display_area # Changed id for clarity and specific use
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height # So it adjusts to content
        padding: [0, 10] # Add some vertical padding

    ScrollView:
        GridLayout:
            id: accounts_layout
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            row_default_height: '40dp'
            row_force_default: False
            spacing: 5

    EnglishLabel: # Static English label
        id: speed_label
        text: 'API Call Time: 0.00 ms'
        size_hint_y: None
        height: '30dp'
        font_size: '13sp'

<StartCodeInputWidget>:
    orientation: 'vertical'
    padding: 30
    spacing: 15
    EnglishLabel: # Static English
        text: 'Please enter your API Start Code (e.g., jafgh or 55542):'
        font_size: '20sp'
        halign: 'center'
        text_size: self.width, None
    EnglishTextInput:
        id: start_code_input
        hint_text: 'Start Code here' # Static English
        multiline: False
        font_size: '18sp'
        halign: 'center'
    EnglishButton:
        text: 'Save and Start' # Static English
        font_size: '18sp'
        size_hint_y: None
        height: '50dp'
        on_press: app.save_start_code_and_load_main_app(start_code_input.text)
'''


class CaptchaWidget(BoxLayout):
    def __init__(self, captcha_api_url_dynamic, **kwargs):
        self.app = App.get_running_app()
        super().__init__(**kwargs)
        self.captcha_api_url = captcha_api_url_dynamic
        self.accounts = {}
        self.current_captcha = None
        # To store the "CAPTCHA RECIEVED" label and predicted text label temporarily
        self._captcha_status_label = None
        self._predicted_text_label = None

    def show_error(self, msg_text_raw):
        display_text = msg_text_raw
        halign = 'left'
        text_lang = None

        if is_arabic_string(msg_text_raw):
            display_text = get_display(msg_text_raw)
            halign = 'right'
            text_lang = 'ar'

        content_label = Label(text=display_text, font_name=self.app.DEFAULT_FONT_NAME,
                              halign=halign, text_language=text_lang,
                              text_size=(None, None))  # Allow Kivy to manage size initially
        content_label.bind(
            size=lambda *x: content_label.setter('text_size')(content_label, (content_label.width, None)))

        popup_title_raw = "Error"  # Or "خطأ"
        popup_title_display = get_display(popup_title_raw) if is_arabic_string(popup_title_raw) else popup_title_raw
        popup_title_halign = 'right' if is_arabic_string(popup_title_raw) else 'left'

        popup = Popup(title=popup_title_display, content=content_label,
                      size_hint=(0.8, 0.4), title_font=self.app.DEFAULT_FONT_NAME,
                      title_align=popup_title_halign)
        popup.open()

    def update_notification(self, raw_message_text, color=(1, 1, 1, 1)):
        display_text = raw_message_text
        halign = 'left'
        text_lang = ""  # Kivy's default

        if is_arabic_string(raw_message_text):
            display_text = get_display(raw_message_text)
            halign = 'right'
            text_lang = 'ar'

        def _update(dt):
            lbl = self.ids.notification_label
            if lbl:
                lbl.text = display_text
                lbl.font_name = self.app.DEFAULT_FONT_NAME
                lbl.halign = halign
                lbl.text_language = text_lang
                lbl.color = color

        Clock.schedule_once(_update, 0)

    def open_add_account_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        # Static English hint texts
        user_input = TextInput(hint_text='Username', multiline=False,
                               font_name=self.app.DEFAULT_FONT_NAME, halign='left', write_tab=False)
        pwd_input = TextInput(hint_text='Password', password=True, multiline=False,
                              font_name=self.app.DEFAULT_FONT_NAME, halign='left', write_tab=False)
        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        # Static English button texts
        btn_ok = Button(text='OK', font_name=self.app.DEFAULT_FONT_NAME)
        btn_cancel = Button(text='Cancel', font_name=self.app.DEFAULT_FONT_NAME)
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(user_input)
        content.add_widget(pwd_input)
        content.add_widget(btn_layout)

        # Static English popup title
        popup_title = 'Add Account'
        popup = Popup(title=popup_title, content=content, size_hint=(0.8, 0.5),
                      title_font=self.app.DEFAULT_FONT_NAME, title_align='left')
        popup.open()

        def on_ok(instance):
            u, p = user_input.text.strip(), pwd_input.text.strip()
            popup.dismiss()
            if u and p:
                threading.Thread(target=self.add_account, args=(u, p), daemon=True).start()

        btn_ok.bind(on_press=on_ok)
        btn_cancel.bind(on_press=lambda x: popup.dismiss())

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
        login_success, login_message_raw = self.login(user, pwd, sess)  # login_message_raw could be Arabic
        if not login_success:
            # Format: English prefix + (potentially Arabic) server message
            # Let update_notification handle the server message part
            # We need to be careful if login_message_raw is Arabic and we prepend English
            # A robust way is to process login_message_raw first
            processed_login_msg = get_display(login_message_raw) if is_arabic_string(
                login_message_raw) else login_message_raw
            combined_msg = f"Login failed for {user}: {processed_login_msg}"
            # If login_message_raw was Arabic, combined_msg might need get_display too if the context is RTL
            if is_arabic_string(login_message_raw):
                combined_msg = get_display(f"فشل تسجيل الدخول لـ {user}: {login_message_raw}")  # Example

            self.update_notification(combined_msg, color=(1, 0, 0, 1))
            return
        time_taken = time.time() - t0
        # Static English message format
        self.update_notification(f"Logged in {user} in {time_taken:.2f}s", color=(0, 1, 0, 1))
        self.accounts[user] = {"password": pwd, "session": sess}
        procs = self.fetch_process_ids(sess)
        if procs:
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            # Static English message
            self.update_notification(f"Can't fetch process IDs for {user}", color=(1, 0, 0, 1))

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for i in range(retries):
            try:
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False, timeout=15)
                if r.status_code == 200:
                    # App-generated message is English
                    return True, "Login successful."  # This message is not displayed, but returned

                error_message_text = r.text
                try:
                    error_message_text = r.json().get("message", r.text)  # This could be Arabic
                except ValueError:
                    pass
                # Return raw message for update_notification to process
                return False, f"Status {r.status_code}: {error_message_text}"
            except requests.exceptions.Timeout:
                # App-generated English message
                msg = f"Login error: Connection timed out (Attempt {i + 1})"
                if i == retries - 1: return False, "Connection timed out"  # Raw English
                self.update_notification(msg, color=(1, 0, 0, 1))  # Show intermediate errors
            except requests.exceptions.RequestException as e:
                # App-generated English message
                return False, f"Login error: {e}"  # Raw English
            time.sleep(0.5)
        return False, "Login failed after multiple attempts"  # Raw English

    def fetch_process_ids(self, sess):
        try:
            r = sess.post("https://api.ecsc.gov.sy:8443/dbm/db/execute",
                          json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                          headers={"Content-Type": "application/json", "Alias": "OPkUVkYsyq",
                                   "Referer": "https://ecsc.gov.sy/requests", "Origin": "https://ecsc.gov.sy"},
                          verify=False, timeout=15)
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])
            # App-generated English message
            self.update_notification(f"Fetch IDs failed ({r.status_code})", color=(1, 0, 0, 1))
        except requests.exceptions.Timeout:
            self.update_notification("Error fetching IDs: Connection timed out", color=(1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(f"Error fetching IDs: {e}", color=(1, 0, 0, 1))
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        if not layout: return

        # Account label is English
        account_label_text = f"Account: {user}"
        account_label = Label(text=account_label_text, size_hint_y=None, height='25dp',
                              font_name=self.app.DEFAULT_FONT_NAME, halign='left', text_language='')
        layout.add_widget(account_label)

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            center_name_raw = proc.get("ZCENTER_NAME", "Unknown Center")

            btn_text_final = center_name_raw  # Default if no PID
            btn_halign = 'left'
            btn_text_lang = ''

            if is_arabic_string(center_name_raw):
                # Structure: Arabic Name (ID: English PID)
                # To ensure correct display, we might need to embed LTR in RTL or vice-versa
                # The bidi algorithm helps, but complex mixes can be tricky.
                # For "اسم عربي (ID: 123)", get_display should handle it.
                if pid:
                    # The format string itself is LTR. If center_name_raw is RTL, get_display handles the mix.
                    mixed_string = f"{center_name_raw} (ID: {pid})"
                else:
                    mixed_string = center_name_raw
                btn_text_final = get_display(mixed_string)
                btn_halign = 'right'  # Assume primary content is Arabic
                btn_text_lang = 'ar'
            elif pid:  # English center name with PID
                btn_text_final = f"{center_name_raw} (ID: {pid})"
                # btn_halign is 'left', btn_text_lang is '' (default)

            btn = Button(text=btn_text_final, font_name=self.app.DEFAULT_FONT_NAME,
                         halign=btn_halign, text_language=btn_text_lang)
            prog = ProgressBar(max=1, value=0)
            box = BoxLayout(size_hint_y=None, height='40dp', spacing=5)
            box.add_widget(btn)
            box.add_widget(prog)
            layout.add_widget(box)
            btn.bind(on_press=lambda inst, u=user, p_id=pid, pr=prog: threading.Thread(target=self._handle_captcha,
                                                                                       args=(u, p_id, pr),
                                                                                       daemon=True).start())

    def _handle_captcha(self, user, pid, prog):
        if pid is None:
            # App-generated English message
            self.update_notification("Error: Process ID is missing.", color=(1, 0, 0, 1))
            return

        Clock.schedule_once(lambda dt: setattr(prog, 'value', 0), 0)
        captcha_data = self.get_captcha(self.accounts[user]["session"], pid, user)  # Returns base64 string or None
        Clock.schedule_once(lambda dt: setattr(prog, 'value', prog.max), 0)  # Indicate completion of fetch attempt

        if captcha_data:
            self.current_captcha = (user, pid)  # Store context for submission
            # Call _display_captcha on the main thread
            Clock.schedule_once(lambda dt: self._display_captcha(captcha_data), 0)
        # else: error already handled by get_captcha via update_notification

    def get_captcha(self, sess, pid, user):  # Internal messages in English
        url = f"https://api.ecsc.gov.sy:8443/captcha/get/{pid}"
        retries = 0
        max_retries = 5  # Reduced for quicker feedback if issues
        while retries < max_retries:
            try:
                r = sess.get(url, verify=False, timeout=10)
                if r.status_code == 200:
                    return r.json().get("file")  # This is the base64 data

                # Server error messages (could be Arabic)
                error_message_text = f"Server error {r.status_code}"
                try:
                    error_message_text = r.json().get("message", r.text)
                except ValueError:
                    error_message_text = r.text

                if r.status_code == 429:  # Rate limit
                    # App generated prefix + server message
                    msg_raw = f"Rate limit, waiting: {error_message_text}"
                    self.update_notification(msg_raw, color=(1, 0.5, 0, 1))
                    time.sleep(random.uniform(1.5, 3.0))  # Longer wait for 429
                    retries += 1  # Count this as a retry
                    continue
                elif r.status_code in (401, 403):  # Auth issues
                    self.update_notification(f"Session invalid ({r.status_code}), re-login: {error_message_text}",
                                             color=(1, 0.5, 0, 1))
                    login_success, login_msg = self.login(user, self.accounts[user]["password"], sess)
                    if not login_success:
                        self.update_notification(f"Re-login failed for {user}: {login_msg}", color=(1, 0, 0, 1))
                        return None  # Critical failure
                    # Re-login successful, continue to retry fetching captcha
                    retries += 1  # Count re-login attempt as a retry cycle for fetching
                    continue
                else:  # Other server errors
                    self.update_notification(f"CAPTCHA fetch failed: {error_message_text}", color=(1, 0, 0, 1))
                    return None  # Unhandled server error
            except requests.exceptions.Timeout:
                self.update_notification(f"Timeout fetching CAPTCHA for {user} (attempt {retries + 1})",
                                         color=(1, 0, 0, 1))
            except requests.exceptions.RequestException as e:
                self.update_notification(f"Request error CAPTCHA: {e}", color=(1, 0, 0, 1))
                return None  # Network or other request error
            retries += 1
            if retries < max_retries: time.sleep(0.5)

        self.update_notification(f"Failed to get CAPTCHA for {user} after {max_retries} attempts.", color=(1, 0, 0, 1))
        return None

    def predict_captcha(self, pil_img: PILImage.Image):
        t_api_start = time.time()
        try:
            img_byte_arr = io.BytesIO()
            pil_img.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            response = requests.post(self.captcha_api_url, files=files, timeout=30)
            response.raise_for_status()  # Raises HTTPError for bad responses (4XX or 5XX)
            api_response = response.json()
            predicted_text = api_response.get("result")  # Usually LTR (numbers/English)

            if predicted_text is None:  # Check for None, empty string "" is a valid prediction
                # App-generated English message
                self.update_notification("API Error: Prediction result is missing (null).", color=(1, 0.5, 0, 1))
                return None, 0, (time.time() - t_api_start) * 1000

            total_api_time_ms = (time.time() - t_api_start) * 1000
            # Predicted text is assumed to be LTR, no bidi processing needed here
            return str(predicted_text), 0, total_api_time_ms  # Ensure string
        except requests.exceptions.Timeout:
            # App-generated English messages for API errors
            self.update_notification(f"API Timeout: {self.captcha_api_url}", color=(1, 0, 0, 1))
        except requests.exceptions.ConnectionError:
            self.update_notification(f"API Connection Error: {self.captcha_api_url}", color=(1, 0, 0, 1))
        except requests.exceptions.HTTPError as e:  # Catch 4xx/5xx specifically
            self.update_notification(f"API HTTP Error: {e.response.status_code} - {e.response.text}",
                                     color=(1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(f"API Request Error: {e}", color=(1, 0, 0, 1))
        except ValueError:  # JSONDecodeError
            self.update_notification(f"API JSON Error: Invalid JSON from {self.captcha_api_url}", color=(1, 0, 0, 1))
        # Removed generic Exception catch to avoid masking specific errors above
        return None, 0, (time.time() - t_api_start) * 1000

    def _display_captcha(self, b64data):
        captcha_display_widget = self.ids.get('captcha_display_area')
        if not captcha_display_widget:
            self.update_notification("UI Error: Captcha display area not found.", color=(1, 0, 0, 1))
            return

        captcha_display_widget.clear_widgets()  # Clear previous status/text

        # 1. Display "CAPTCHA RECIEVED"
        # Static English text as requested, no bidi needed for this specific string
        captcha_received_text_ar_raw = "تم استلام الكابتشا"  # البديل العربي
        captcha_received_text_en = "CAPTCHA RECIEVED"

        # Use the Arabic version:
        # status_text_to_display = get_display(captcha_received_text_ar_raw)
        # status_halign = 'right'
        # status_text_language = 'ar'

        # Use the English version as per explicit request:
        status_text_to_display = captcha_received_text_en
        status_halign = 'center'  # Center English text
        status_text_language = ''

        self._captcha_status_label = Label(
            text=status_text_to_display,
            font_size='72sp',
            color=(1, 0.647, 0, 1),  # Orange
            size_hint_y=None,
            font_name=self.app.DEFAULT_FONT_NAME,
            halign=status_halign,
            text_language=status_text_language
        )
        self._captcha_status_label.bind(texture_size=self._captcha_status_label.setter('size'))
        captcha_display_widget.add_widget(self._captcha_status_label)

        # --- Image processing (remains for prediction logic) ---
        try:
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
            binary_pil_img = PILImage.fromarray(gray, 'L').point(lambda p: 255 if p > thresh else 0)
        except Exception as e:
            # App-generated English message
            err_msg = f"Image processing error: {e}"
            self.update_notification(err_msg, color=(1, 0, 0, 1))
            # Display error below "CAPTCHA RECIEVED" as well
            if self._captcha_status_label:  # Ensure status label exists
                error_label = Label(text=get_display("خطأ في معالجة الصورة") + f": {e}",  # Example Arabic
                                    font_size='18sp', color=(1, 0, 0, 1), size_hint_y=None, height='30dp',
                                    font_name=self.app.DEFAULT_FONT_NAME, halign='right', text_language='ar')
                captcha_display_widget.add_widget(error_label)
            return  # Stop if image processing fails

        # Predict CAPTCHA (already happens on a thread if called from _handle_captcha)
        pred_text, pre_ms, api_call_ms = self.predict_captcha(binary_pil_img)

        if pred_text is not None:  # Prediction successful (could be empty string for "no text found")
            # Update notification (English message)
            self.update_notification(f"Predicted: {pred_text if pred_text else '[empty]'}", color=(0, 0, 1, 1))
            if self.ids.speed_label: self.ids.speed_label.text = f"API Time: {api_call_ms:.2f} ms"

            # 2. Display predicted text under "CAPTCHA RECIEVED"
            # Predicted text is usually LTR (numbers/English), no bidi needed unless API changes
            self._predicted_text_label = Label(
                text=str(pred_text),
                font_size='36sp',  # Prominent size for prediction
                color=(0.9, 0.9, 0.9, 1),  # Light color for text
                size_hint_y=None,
                font_name=self.app.DEFAULT_FONT_NAME,
                halign='center'  # Center predicted text
            )
            self._predicted_text_label.bind(texture_size=self._predicted_text_label.setter('size'))
            captcha_display_widget.add_widget(self._predicted_text_label)

            self.submit_captcha(pred_text)
        else:  # Prediction failed
            # App-generated English message for notification bar
            self.update_notification("CAPTCHA prediction failed by API.", color=(1, 0, 0, 1))
            # Display failure message below "CAPTCHA RECIEVED"
            if self._captcha_status_label:  # Ensure status label exists
                # Example: "فشل التوقع من الخادم" (Prediction failed from server)
                fail_text_raw = "Prediction API failed"  # English
                # fail_text_raw = "فشل التوقع من الخادم" # Arabic

                fail_text_display = get_display(fail_text_raw) if is_arabic_string(fail_text_raw) else fail_text_raw
                fail_halign = 'right' if is_arabic_string(fail_text_raw) else 'center'
                fail_text_lang = 'ar' if is_arabic_string(fail_text_raw) else ''

                prediction_fail_label = Label(
                    text=fail_text_display,
                    font_size='20sp',
                    color=(1, 0.5, 0, 1),  # Orange-Red
                    size_hint_y=None,
                    font_name=self.app.DEFAULT_FONT_NAME,
                    halign=fail_halign,
                    text_language=fail_text_lang
                )
                prediction_fail_label.bind(texture_size=prediction_fail_label.setter('size'))
                captcha_display_widget.add_widget(prediction_fail_label)

    def submit_captcha(self, sol):  # sol is likely LTR
        if not self.current_captcha:
            # App-generated English message
            self.update_notification("Error: No current CAPTCHA context.", color=(1, 0, 0, 1))
            return
        user, pid = self.current_captcha
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"
        try:
            r = sess.get(url, verify=False, timeout=20)
            col = (0, 1, 0, 1) if r.status_code == 200 else (1, 0, 0, 1)
            msg_text_raw = r.text  # Server response, could be Arabic
            try:  # Attempt to decode as UTF-8, more robust for Arabic
                msg_text_raw = r.content.decode('utf-8', errors='replace')
            except Exception:
                pass  # Keep original r.text if decode fails

            # update_notification will handle bidi for msg_text_raw
            self.update_notification(f"Submit: {msg_text_raw}", color=col)
        except requests.exceptions.Timeout:
            self.update_notification("Submit error: Connection timed out", color=(1, 0, 0, 1))
        except requests.exceptions.RequestException as e:
            self.update_notification(f"Submit error: {e}", color=(1, 0, 0, 1))
        finally:
            self.current_captcha = None  # Clear current captcha context


class StartCodeInputWidget(BoxLayout):
    pass


class CaptchaApp(App):
    DEFAULT_FONT_NAME = DEFAULT_FONT_NAME

    API_URL_PREFIX = "https://"
    API_URL_SUFFIX = ".pythonanywhere.com/predict"
    captcha_api_url_dynamic = None

    def _get_root_widget(self):
        app_config = self.store.get('app_config') if self.store.exists('app_config') else {}
        start_code = app_config.get('start_code')

        if start_code:
            if not self.captcha_api_url_dynamic:
                self.captcha_api_url_dynamic = f"{self.API_URL_PREFIX}{start_code}{self.API_URL_SUFFIX}"
            return CaptchaWidget(captcha_api_url_dynamic=self.captcha_api_url_dynamic)
        else:
            return StartCodeInputWidget()

    def build(self):
        self.store_path = os.path.join(self.user_data_dir, 'app_settings.json')
        self.store = JsonStore(self.store_path)
        Builder.load_string(KV)
        self.title = "Captcha Automation Tool"  # Static English title
        return self._get_root_widget()

    def _save_start_code(self, start_code_val):
        app_config = self.store.get('app_config') if self.store.exists('app_config') else {}
        app_config['start_code'] = start_code_val
        self.store.put('app_config', **app_config)

    def save_start_code_and_load_main_app(self, start_code_text):
        start_code = start_code_text.strip()
        if not start_code:
            # Static English error message
            popup_content_text = 'Start Code cannot be empty!'
            popup_title_text = 'Input Error'
            content_label = Label(text=popup_content_text, font_name=self.DEFAULT_FONT_NAME)
            popup = Popup(title=popup_title_text, content=content_label,
                          size_hint=(0.7, 0.3), title_font=self.DEFAULT_FONT_NAME,
                          title_align='left')  # Assuming English title
            popup.open()
            return

        self._save_start_code(start_code)
        self.captcha_api_url_dynamic = f"{self.API_URL_PREFIX}{start_code}{self.API_URL_SUFFIX}"

        if self.root and isinstance(self.root, StartCodeInputWidget):  # Check current root
            self.root.clear_widgets()  # Clear the StartCodeInputWidget
            main_widget = CaptchaWidget(captcha_api_url_dynamic=self.captcha_api_url_dynamic)
            # Instead of adding to old root, we rebuild or replace root.
            # For simplicity here, if self.root is the main BoxLayout of the app window:
            # This part depends on how your app structure handles root widget replacement.
            # A common way is to have a root container in App and swap its children.
            # If self.root is directly the window's content:
            self.root_window.remove_widget(self.root)
            self.root_window.add_widget(main_widget)
            self.root = main_widget  # Update app's root reference
        elif self.root:  # If root is already CaptchaWidget or similar, just re-init or update
            self.root.clear_widgets()
            main_widget = CaptchaWidget(captcha_api_url_dynamic=self.captcha_api_url_dynamic)
            self.root.add_widget(main_widget)  # If self.root is a layout that can host CaptchaWidget


if __name__ == '__main__':
    # It's good practice to disable these warnings only if you understand the security implications.
    # For development with known self-signed certificates, it's common.
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

    CaptchaApp().run()
