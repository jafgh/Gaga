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
# KivyImage is not directly used to display captcha image anymore
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage  # Still needed for processing image data
from kivy.storage.jsonstore import JsonStore

# --- مكتبة bidi تم حذفها بناءً على الطلب ---

# --- تعريف الخط الافتراضي ---
DEFAULT_FONT_NAME = 'Arial'  # أو Tahoma, Noto Sans Arabic, etc.

# --- وظيفة is_arabic_string تم حذفها بناءً على الطلب ---


# --------------------------------------------------
# تصميم الواجهة باستخدام Kivy
# --------------------------------------------------
KV = '''
#:import App kivy.app.App

# BaseLabel and EnglishLabel are now effectively the same without bidi
<DefaultLabel@Label>:
    font_name: App.get_running_app().DEFAULT_FONT_NAME
    halign: 'left' # Default alignment, adjust as needed per instance
    text_language: '' # Kivy default LTR rendering

<DefaultButton@Button>:
    font_name: App.get_running_app().DEFAULT_FONT_NAME

<DefaultTextInput@TextInput>:
    font_name: App.get_running_app().DEFAULT_FONT_NAME
    halign: 'left' # Default alignment
    write_tab: False

<CaptchaWidget>:
    orientation: 'vertical'
    padding: 10
    spacing: 10

    BoxLayout:
        size_hint_y: None
        height: '30dp'
        DefaultLabel:
            id: notification_label
            text: ''
            font_size: '16sp'
            color: 1,1,1,1
            # halign will be set in update_notification if needed, or keep 'left'/'center'

    DefaultButton:
        text: 'Add Account' # Static English
        size_hint_y: None
        height: '40dp'
        on_press: root.open_add_account_popup()

    BoxLayout:
        id: captcha_display_area
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        padding: [0, 10]

    ScrollView:
        GridLayout:
            id: accounts_layout
            cols: 1
            size_hint_y: None
            height: self.minimum_height
            row_default_height: '40dp'
            row_force_default: False
            spacing: 5

    DefaultLabel:
        id: speed_label
        text: 'API Call Time: 0.00 ms' # Static English
        size_hint_y: None
        height: '30dp'
        font_size: '13sp'

    BoxLayout: # For displaying current API and reset button
        size_hint_y: None
        height: '40dp'
        spacing: 10
        padding: [0, 5] # Add a little top/bottom padding for this new section
        DefaultLabel:
            id: current_api_code_label
            text: 'API Code: ' # Will be updated from Python
            font_size: '13sp'
            size_hint_x: 0.7
        DefaultButton:
            text: 'Change code' # Static English text
            # text: 'تغيير الواجهة' # Arabic alternative (would require font support)
            size_hint_x: 0.3
            on_press: root.confirm_reset_api_code()


<StartCodeInputWidget>:
    orientation: 'vertical'
    padding: 30
    spacing: 15
    DefaultLabel:
        text: 'Please enter your API Start Code (e.g.,  55542):' # Static English
        font_size: '20sp'
        halign: 'center'
        text_size: self.width, None
    DefaultTextInput:
        id: start_code_input
        hint_text: 'Start Code here' # Static English
        multiline: False
        font_size: '18sp'
        halign: 'center'
    DefaultButton:
        text: 'Save and Start' # Static English
        font_size: '18sp'
        size_hint_y: None
        height: '50dp'
        on_press: app.save_start_code_and_load_main_app(start_code_input.text)
'''


class CaptchaWidget(BoxLayout):
    def __init__(self, captcha_api_url_dynamic, start_code, **kwargs):
        self.app = App.get_running_app()
        super().__init__(**kwargs)
        self.captcha_api_url = captcha_api_url_dynamic
        self.accounts = {}
        self.current_captcha = None
        self._captcha_status_label = None
        self._predicted_text_label = None
        self.displayed_start_code = start_code  # Store the start code

        Clock.schedule_once(self._initial_ui_update)

    def _initial_ui_update(self, dt=0):
        # Update the label showing the current API start code
        if self.ids.current_api_code_label:
            self.ids.current_api_code_label.text = f' Code: {self.displayed_start_code}'

    def confirm_reset_api_code(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        # Static English text for confirmation
        msg = Label(text='Change  code and clear accounts?', font_name=self.app.DEFAULT_FONT_NAME, halign='center')
        # msg_ar = Label(text='هل تريد تغيير رمز الواجهة ومسح الحسابات؟', font_name=self.app.DEFAULT_FONT_NAME, halign='center')

        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        # Static English text for buttons
        yes_button = Button(text='Yes', font_name=self.app.DEFAULT_FONT_NAME)
        no_button = Button(text='No', font_name=self.app.DEFAULT_FONT_NAME)

        btn_layout.add_widget(yes_button)
        btn_layout.add_widget(no_button)
        content.add_widget(msg)
        content.add_widget(btn_layout)

        popup_title = 'Confirm API Change'  # Static English
        popup = Popup(title=popup_title, content=content,
                      size_hint=(0.8, 0.4), title_font=self.app.DEFAULT_FONT_NAME,
                      title_align='center')  # Center align title

        def on_yes(instance):
            popup.dismiss()
            self.app.reset_and_go_to_start_code_input()

        yes_button.bind(on_press=on_yes)
        no_button.bind(on_press=popup.dismiss)
        popup.open()

    def show_error(self, msg_text_raw):
        # Without bidi, text is displayed as is. Alignment is kept simple.
        display_text = msg_text_raw
        halign = 'center'  # Or 'left', depending on preference for error messages

        content_label = Label(text=display_text, font_name=self.app.DEFAULT_FONT_NAME,
                              halign=halign, text_size=(None, None))
        content_label.bind(size=lambda *x: content_label.setter('text_size')(content_label, (
        content_label.width * 0.9, None)))  # Allow wrapping

        popup_title = "Error"  # Static English
        popup = Popup(title=popup_title, content=content_label,
                      size_hint=(0.8, 0.4), title_font=self.app.DEFAULT_FONT_NAME,
                      title_align='center')
        popup.open()

    def update_notification(self, raw_message_text, color=(1, 1, 1, 1)):
        # Without bidi, text is displayed as is.
        display_text = raw_message_text
        # Defaulting to center alignment for notifications, can be 'left'
        halign = 'center'

        def _update(dt):
            lbl = self.ids.notification_label
            if lbl:
                lbl.text = display_text
                lbl.font_name = self.app.DEFAULT_FONT_NAME
                lbl.halign = halign
                lbl.text_language = ''  # Ensure Kivy default LTR rendering
                lbl.color = color

        Clock.schedule_once(_update, 0)

    def open_add_account_popup(self):
        content = BoxLayout(orientation='vertical', spacing=10, padding=10)
        user_input = TextInput(hint_text='Username', multiline=False,
                               font_name=self.app.DEFAULT_FONT_NAME, halign='left', write_tab=False)
        pwd_input = TextInput(hint_text='Password', password=True, multiline=False,
                              font_name=self.app.DEFAULT_FONT_NAME, halign='left', write_tab=False)
        btn_layout = BoxLayout(size_hint_y=None, height='40dp', spacing=10)
        btn_ok = Button(text='OK', font_name=self.app.DEFAULT_FONT_NAME)
        btn_cancel = Button(text='Cancel', font_name=self.app.DEFAULT_FONT_NAME)
        btn_layout.add_widget(btn_ok)
        btn_layout.add_widget(btn_cancel)
        content.add_widget(user_input)
        content.add_widget(pwd_input)
        content.add_widget(btn_layout)

        popup_title = 'Add Account'  # Static English
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
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.127 Safari/537.36"
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
        login_success, login_message_raw = self.login(user, pwd, sess)  # login_message_raw is server response

        if not login_success:
            # Message from login() can be complex, display as is.
            # Example: "Login failed for user: Raw server message"
            # If login_message_raw is Arabic, it will be displayed LTR without bidi.
            self.update_notification(f"Login failed for {user}: {login_message_raw}", color=(1, 0, 0, 1))
            return

        time_taken = time.time() - t0
        self.update_notification(f"Logged in {user} in {time_taken:.2f}s", color=(0, 1, 0, 1))  # Static English
        self.accounts[user] = {"password": pwd, "session": sess}
        procs = self.fetch_process_ids(sess)
        if procs:
            Clock.schedule_once(lambda dt: self._create_account_ui(user, procs), 0)
        else:
            self.update_notification(f"Can't fetch process IDs for {user}", color=(1, 0, 0, 1))  # Static English

    def login(self, user, pwd, sess, retries=3):
        url = "https://api.ecsc.gov.sy:8443/secure/auth/login"
        for i in range(retries):
            try:
                r = sess.post(url, json={"username": user, "password": pwd}, verify=False, timeout=15)
                if r.status_code == 200:
                    return True, "Login successful."  # Static English

                error_message_text = r.text  # Default to raw text
                try:
                    error_message_text = r.json().get("message", r.text)  # This could be Arabic
                except ValueError:
                    pass
                return False, f"Status {r.status_code}: {error_message_text}"  # Raw error message
            except requests.exceptions.Timeout:
                msg = f"Login error: Connection timed out (Attempt {i + 1})"  # Static English
                if i == retries - 1: return False, "Connection timed out"
                self.update_notification(msg, color=(1, 0, 0, 1))  # Show intermediate errors
            except requests.exceptions.RequestException as e:
                return False, f"Login error: {e}"  # Static English
            time.sleep(0.5)
        return False, "Login failed after multiple attempts"  # Static English

    def fetch_process_ids(self, sess):
        try:
            r = sess.post("https://api.ecsc.gov.sy:8443/dbm/db/execute",
                          json={"ALIAS": "OPkUVkYsyq", "P_USERNAME": "WebSite", "P_PAGE_INDEX": 0, "P_PAGE_SIZE": 100},
                          headers={"Content-Type": "application/json", "Alias": "OPkUVkYsyq",
                                   "Referer": "https://ecsc.gov.sy/requests", "Origin": "https://ecsc.gov.sy"},
                          verify=False, timeout=15)
            if r.status_code == 200:
                return r.json().get("P_RESULT", [])  # P_RESULT can contain ZCENTER_NAME (Arabic)
            self.update_notification(f"Fetch IDs failed ({r.status_code})", color=(1, 0, 0, 1))  # Static English
        except requests.exceptions.Timeout:
            self.update_notification("Error fetching IDs: Connection timed out", color=(1, 0, 0, 1))  # Static English
        except requests.exceptions.RequestException as e:
            self.update_notification(f"Error fetching IDs: {e}", color=(1, 0, 0, 1))  # Static English
        return []

    def _create_account_ui(self, user, processes):
        layout = self.ids.accounts_layout
        if not layout: return

        account_label_text = f"Account: {user}"  # Static English format
        account_label = Label(text=account_label_text, size_hint_y=None, height='25dp',
                              font_name=self.app.DEFAULT_FONT_NAME, halign='left')
        layout.add_widget(account_label)

        for proc in processes:
            pid = proc.get("PROCESS_ID")
            center_name_raw = proc.get("ZCENTER_NAME", "Unknown Center")  # Can be Arabic

            # Without bidi, Arabic names will be displayed as LTR and possibly disconnected.
            # The mixed string "(ID: {pid})" will also follow LTR rules.
            if pid:
                btn_text_final = f"{center_name_raw} (ID: {pid})"
            else:
                btn_text_final = center_name_raw

            # Default alignment for buttons is center, halign might not apply directly to button text alignment easily.
            # Kivy buttons tend to center their text.
            btn = Button(text=btn_text_final, font_name=self.app.DEFAULT_FONT_NAME)
            prog = ProgressBar(max=1, value=0)
            box = BoxLayout(size_hint_y=None, height='40dp', spacing=5)
            box.add_widget(btn);
            box.add_widget(prog)
            layout.add_widget(box)
            btn.bind(on_press=lambda inst, u=user, p_id=pid, pr=prog: threading.Thread(target=self._handle_captcha,
                                                                                       args=(u, p_id, pr),
                                                                                       daemon=True).start())

    def _handle_captcha(self, user, pid, prog):
        if pid is None:
            self.update_notification("Error: Process ID is missing.", color=(1, 0, 0, 1))  # Static English
            return
        Clock.schedule_once(lambda dt: setattr(prog, 'value', 0), 0)
        captcha_data = self.get_captcha(self.accounts[user]["session"], pid, user)
        Clock.schedule_once(lambda dt: setattr(prog, 'value', prog.max), 0)
        if captcha_data:
            self.current_captcha = (user, pid)
            Clock.schedule_once(lambda dt: self._display_captcha(captcha_data), 0)

    def get_captcha(self, sess, pid, user):
        url = f"https://api.ecsc.gov.sy:8443/captcha/get/{pid}"
        retries = 0;
        max_retries = 5
        while retries < max_retries:
            try:
                r = sess.get(url, verify=False, timeout=10)
                if r.status_code == 200: return r.json().get("file")

                error_message_text = f"Server error {r.status_code}"
                try:
                    error_message_text = r.json().get("message", r.text)  # Could be Arabic
                except ValueError:
                    error_message_text = r.text

                if r.status_code == 429:
                    msg_raw = f"Rate limit, waiting: {error_message_text}"  # error_message_text displayed raw
                    self.update_notification(msg_raw, color=(1, 0.5, 0, 1))
                    time.sleep(random.uniform(1.5, 3.0));
                    retries += 1;
                    continue
                elif r.status_code in (401, 403):
                    self.update_notification(f"Session invalid ({r.status_code}), re-login: {error_message_text}",
                                             color=(1, 0.5, 0, 1))
                    login_success, login_msg = self.login(user, self.accounts[user]["password"], sess)
                    if not login_success:
                        self.update_notification(f"Re-login failed for {user}: {login_msg}", color=(1, 0, 0, 1))
                        return None
                    retries += 1;
                    continue
                else:
                    self.update_notification(f"CAPTCHA fetch failed: {error_message_text}", color=(1, 0, 0, 1))
                    return None
            except requests.exceptions.Timeout:
                self.update_notification(f"Timeout fetching CAPTCHA for {user} (attempt {retries + 1})",
                                         color=(1, 0, 0, 1))
            except requests.exceptions.RequestException as e:
                self.update_notification(f"Request error CAPTCHA: {e}", color=(1, 0, 0, 1));
                return None
            retries += 1
            if retries < max_retries: time.sleep(0.5)
        self.update_notification(f"Failed to get CAPTCHA for {user} after {max_retries} attempts.", color=(1, 0, 0, 1))
        return None

    def predict_captcha(self, pil_img: PILImage.Image):
        t_api_start = time.time()
        try:
            img_byte_arr = io.BytesIO();
            pil_img.save(img_byte_arr, format='PNG');
            img_byte_arr.seek(0)
            files = {"image": ("captcha.png", img_byte_arr, "image/png")}
            response = requests.post(self.captcha_api_url, files=files, timeout=30)
            response.raise_for_status()
            api_response = response.json()
            predicted_text = api_response.get("result")  # Assumed LTR

            if predicted_text is None:
                self.update_notification("API Error: Prediction result is missing (null).",
                                         color=(1, 0.5, 0, 1))  # Static English
                return None, 0, (time.time() - t_api_start) * 1000
            total_api_time_ms = (time.time() - t_api_start) * 1000
            return str(predicted_text), 0, total_api_time_ms
        except requests.exceptions.Timeout:
            self.update_notification(f"API Timeout: {self.captcha_api_url}", color=(1, 0, 0, 1))  # Static English
        except requests.exceptions.ConnectionError:
            self.update_notification(f"API Connection Error: {self.captcha_api_url}",
                                     color=(1, 0, 0, 1))  # Static English
        except requests.exceptions.HTTPError as e:
            self.update_notification(f"API HTTP Error: {e.response.status_code} - {e.response.text}",
                                     color=(1, 0, 0, 1))  # Raw response text
        except requests.exceptions.RequestException as e:
            self.update_notification(f"API Request Error: {e}", color=(1, 0, 0, 1))  # Static English
        except ValueError:
            self.update_notification(f"API JSON Error: Invalid JSON from {self.captcha_api_url}",
                                     color=(1, 0, 0, 1))  # Static English
        return None, 0, (time.time() - t_api_start) * 1000

    def _display_captcha(self, b64data):
        captcha_display_widget = self.ids.get('captcha_display_area')
        if not captcha_display_widget:
            self.update_notification("UI Error: Captcha display area not found.", color=(1, 0, 0, 1))
            return
        captcha_display_widget.clear_widgets()

        # 1. Display "CAPTCHA RECIEVED" (Static English)
        status_text_to_display = "CAPTCHA RECIEVED"
        status_halign = 'center'

        self._captcha_status_label = Label(
            text=status_text_to_display, font_size='72sp', color=(1, 0.647, 0, 1),
            size_hint_y=None, font_name=self.app.DEFAULT_FONT_NAME, halign=status_halign
        )
        self._captcha_status_label.bind(texture_size=self._captcha_status_label.setter('size'))
        captcha_display_widget.add_widget(self._captcha_status_label)

        try:  # Image processing
            b64 = b64data.split(',')[1] if ',' in b64data else b64data
            raw = base64.b64decode(b64);
            pil_original = PILImage.open(io.BytesIO(raw))
            frames = [];
            try:
                while True: frames.append(np.array(pil_original.convert('RGB'), dtype=np.uint8)); pil_original.seek(
                    pil_original.tell() + 1)
            except EOFError:
                pass
            bg = np.median(np.stack(frames), axis=0).astype(np.uint8) if frames else np.array(
                pil_original.convert('RGB'), dtype=np.uint8)
            gray = (0.2989 * bg[..., 0] + 0.5870 * bg[..., 1] + 0.1140 * bg[..., 2]).astype(np.uint8)
            hist, _ = np.histogram(gray.flatten(), bins=256, range=(0, 256));
            total = gray.size;
            sum_tot = np.dot(np.arange(256), hist)
            sumB = 0;
            wB = 0;
            max_var = 0;
            thresh = 0
            for i, h in enumerate(hist):
                wB += h;
                if wB == 0: continue
                wF = total - wB;
                if wF == 0: break
                sumB += i * h;
                mB = sumB / wB;
                mF = (sum_tot - sumB) / wF;
                varBetween = wB * wF * (mB - mF) ** 2
                if varBetween > max_var: max_var = varBetween; thresh = i
            binary_pil_img = PILImage.fromarray(gray, 'L').point(lambda p: 255 if p > thresh else 0)
        except Exception as e:
            err_msg = f"Image processing error: {e}"  # Static English
            self.update_notification(err_msg, color=(1, 0, 0, 1))
            if self._captcha_status_label:
                error_label = Label(text=f"Image Error: {e}",  # Static English
                                    font_size='18sp', color=(1, 0, 0, 1), size_hint_y=None, height='30dp',
                                    font_name=self.app.DEFAULT_FONT_NAME, halign='center')
                captcha_display_widget.add_widget(error_label)
            return

        pred_text, pre_ms, api_call_ms = self.predict_captcha(binary_pil_img)

        if pred_text is not None:
            self.update_notification(f"Predicted: {pred_text if pred_text else '[empty]'}",
                                     color=(0, 0, 1, 1))  # Static English
            if self.ids.speed_label: self.ids.speed_label.text = f"API Time: {api_call_ms:.2f} ms"

            self._predicted_text_label = Label(
                text=str(pred_text), font_size='36sp', color=(0.9, 0.9, 0.9, 1),
                size_hint_y=None, font_name=self.app.DEFAULT_FONT_NAME, halign='center'
            )
            self._predicted_text_label.bind(texture_size=self._predicted_text_label.setter('size'))
            captcha_display_widget.add_widget(self._predicted_text_label)
            self.submit_captcha(pred_text)
        else:
            self.update_notification("CAPTCHA prediction failed by API.", color=(1, 0, 0, 1))  # Static English
            if self._captcha_status_label:
                fail_text_display = "Prediction API failed"  # Static English
                prediction_fail_label = Label(
                    text=fail_text_display, font_size='20sp', color=(1, 0.5, 0, 1),
                    size_hint_y=None, font_name=self.app.DEFAULT_FONT_NAME, halign='center'
                )
                prediction_fail_label.bind(texture_size=prediction_fail_label.setter('size'))
                captcha_display_widget.add_widget(prediction_fail_label)

    def submit_captcha(self, sol):
        if not self.current_captcha:
            self.update_notification("Error: No current CAPTCHA context.", color=(1, 0, 0, 1))  # Static English
            return
        user, pid = self.current_captcha;
        sess = self.accounts[user]["session"]
        url = f"https://api.ecsc.gov.sy:8443/rs/reserve?id={pid}&captcha={sol}"
        try:
            r = sess.get(url, verify=False, timeout=20)
            col = (0, 1, 0, 1) if r.status_code == 200 else (1, 0, 0, 1)
            msg_text_raw = r.text  # Server response, could be Arabic, displayed raw
            try:
                msg_text_raw = r.content.decode('utf-8', errors='replace')
            except Exception:
                pass
            self.update_notification(f"Submit: {msg_text_raw}", color=col)  # Raw display
        except requests.exceptions.Timeout:
            self.update_notification("Submit error: Connection timed out", color=(1, 0, 0, 1))  # Static English
        except requests.exceptions.RequestException as e:
            self.update_notification(f"Submit error: {e}", color=(1, 0, 0, 1))  # Static English
        finally:
            self.current_captcha = None


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
            # Pass start_code to CaptchaWidget so it can display it
            return CaptchaWidget(captcha_api_url_dynamic=self.captcha_api_url_dynamic, start_code=start_code)
        else:
            return StartCodeInputWidget()

    def build(self):
        self.store_path = os.path.join(self.user_data_dir, 'app_settings.json')
        self.store = JsonStore(self.store_path)
        Builder.load_string(KV)
        self.title = "Captcha Automation Tool"  # Static English
        self.root = self._get_root_widget()  # Set initial root
        return self.root

    def _save_start_code(self, start_code_val):
        app_config = self.store.get('app_config') if self.store.exists('app_config') else {}
        app_config['start_code'] = start_code_val
        self.store.put('app_config', **app_config)

    def save_start_code_and_load_main_app(self, start_code_text):
        start_code = start_code_text.strip()
        if not start_code:
            popup_content_text = 'Start Code cannot be empty!'  # Static English
            popup_title_text = 'Input Error'  # Static English
            content_label = Label(text=popup_content_text, font_name=self.DEFAULT_FONT_NAME)
            popup = Popup(title=popup_title_text, content=content_label,
                          size_hint=(0.7, 0.3), title_font=self.DEFAULT_FONT_NAME, title_align='left')
            popup.open()
            return

        self._save_start_code(start_code)
        self.captcha_api_url_dynamic = f"{self.API_URL_PREFIX}{start_code}{self.API_URL_SUFFIX}"

        # Transition UI by replacing the root widget
        if self.root:
            self.root_window.remove_widget(self.root)  # Remove old root (StartCodeInputWidget)
        main_widget = CaptchaWidget(captcha_api_url_dynamic=self.captcha_api_url_dynamic, start_code=start_code)
        self.root_window.add_widget(main_widget)
        self.root = main_widget  # Update app's root reference

    def reset_and_go_to_start_code_input(self):
        # Clear stored start code
        app_config = self.store.get('app_config') if self.store.exists('app_config') else {}
        if 'start_code' in app_config:
            del app_config['start_code']
        self.store.put('app_config', **app_config)
        self.captcha_api_url_dynamic = None

        # Transition UI back to StartCodeInputWidget
        if self.root:
            self.root_window.remove_widget(self.root)  # Remove old root (CaptchaWidget)
        new_root = StartCodeInputWidget()
        self.root_window.add_widget(new_root)
        self.root = new_root  # Update app's root reference


if __name__ == '__main__':
    try:
        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except ImportError:
        # Fallback for older requests versions
        if hasattr(requests, 'packages') and hasattr(requests.packages, 'urllib3'):
            requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    CaptchaApp().run()
