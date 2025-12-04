import sys
import threading
import requests
import random
import string
import json
from kivy.lang import Builder
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.list import OneLineIconListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.toast import toast
from kivy.clock import Clock
from kivy.properties import StringProperty
from kivy.uix.video import Video

# --- KV DESIGN (Responsive UI) ---
KV = '''
<ChannelItem>:
    theme_text_color: "Custom"
    text_color: 1, 1, 1, 1
    IconLeftWidget:
        icon: "television"
        theme_text_color: "Custom"
        text_color: 0, 0.89, 1, 1  # Cyan

MDScreen:
    name: "home"
    
    MDBoxLayout:
        orientation: 'vertical'
        md_bg_color: 0.06, 0.06, 0.08, 1  # Dark Background

        # --- HEADER ---
        MDTopAppBar:
            title: "RMS Player Mobile"
            elevation: 4
            pos_hint: {"top": 1}
            md_bg_color: 0.1, 0.1, 0.12, 1
            specific_text_color: 0, 0.89, 1, 1
            right_action_items: [["refresh", lambda x: app.refresh_connection()], ["dots-vertical", lambda x: app.open_settings()]]

        # --- VIDEO PLAYER AREA ---
        MDBoxLayout:
            id: video_container
            orientation: 'vertical'
            size_hint_y: 0.40  # Takes 40% of screen height
            padding: 5
            spacing: 5
            md_bg_color: 0, 0, 0, 1
            
            Video:
                id: player
                state: 'stop'
                options: {'allow_stretch': True}

            # Controls
            MDBoxLayout:
                size_hint_y: None
                height: "50dp"
                spacing: 10
                padding: 10
                adaptive_width: True
                pos_hint: {"center_x": .5}

                MDIconButton:
                    icon: "skip-previous"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    on_release: app.play_prev()

                MDIconButton:
                    icon: "play-pause"
                    theme_text_color: "Custom"
                    text_color: 0, 1, 0, 1
                    on_release: app.toggle_play()

                MDIconButton:
                    icon: "stop"
                    theme_text_color: "Custom"
                    text_color: 1, 0, 0, 1
                    on_release: app.stop_play()

                MDIconButton:
                    icon: "skip-next"
                    theme_text_color: "Custom"
                    text_color: 1, 1, 1, 1
                    on_release: app.play_next()

        # --- INPUT & LIST AREA ---
        MDBoxLayout:
            orientation: 'vertical'
            padding: 10
            spacing: 10
            
            # Inputs
            MDBoxLayout:
                size_hint_y: None
                height: "120dp"
                orientation: "vertical"
                spacing: 10
                
                MDTextField:
                    id: url_field
                    hint_text: "Portal URL / M3U Link"
                    text: "http://domain.com/c/"
                    mode: "rectangle"
                    color_mode: 'custom'
                    line_color_focus: 0, 0.89, 1, 1
                    text_color_normal: 1, 1, 1, 1
                    text_color_focus: 1, 1, 1, 1
                    
                MDTextField:
                    id: mac_field
                    hint_text: "MAC Address (00:1A...)"
                    mode: "rectangle"
                    color_mode: 'custom'
                    line_color_focus: 0, 0.89, 1, 1
                    text_color_normal: 1, 1, 1, 1
                    text_color_focus: 1, 1, 1, 1

                MDRaisedButton:
                    text: "CONNECT SECURELY"
                    size_hint_x: 1
                    md_bg_color: 0, 0.89, 1, 1
                    text_color: 0, 0, 0, 1
                    on_release: app.connect_source()

            # Channel List (RecycleView for Speed)
            RecycleView:
                id: rv
                viewclass: 'ChannelItem'
                RecycleBoxLayout:
                    default_size: None, dp(48)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
'''

# --- LIST ITEM CLASS ---
class ChannelItem(OneLineIconListItem):
    url = StringProperty()
    
    def on_release(self):
        # Call the play function in the main app
        app = MDApp.get_running_app()
        app.play_channel(self.text, self.url)

# --- STALKER LOGIC (From Windows Tool) ---
class StalkerClient:
    def __init__(self, url, mac):
        self.mac = mac.upper()
        self.sn = "002021" + ''.join(random.choices(string.digits, k=7))
        self.device_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
        self.base_url = url.split("/c/")[0]
        if not self.base_url.endswith("/"): self.base_url += "/"
        self.api_url = f"{self.base_url}server/load.php"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 2721 Safari/533.3',
            'Cookie': f'mac={self.mac}; stb_lang=en; timezone=Europe/Kiev;',
            'Authorization': f'Bearer {self.mac}',
            'X-User-Agent': 'Model: MAG254; Link: Ethernet'
        })
        self.token = None

    def handshake(self):
        try:
            params = {'type': 'stb', 'action': 'handshake', 'token': '', 'mac': self.mac, 'stb_type': 'MAG254', 'sn': self.sn, 'device_id': self.device_id, 'device_id2': self.device_id}
            r = self.session.get(self.api_url, params=params, timeout=10)
            data = r.json()
            if 'js' in data and 'token' in data['js']:
                self.token = data['js']['token']
                self.session.headers.update({'Authorization': f"Bearer {self.token}"})
                self.session.cookies.set('stb_token', self.token)
                self.session.get(self.api_url, params={'type': 'stb', 'action': 'get_profile'}, timeout=8)
                return True
        except: pass
        return False

    def get_channels(self):
        try:
            r = self.session.get(self.api_url, params={'type': 'itv', 'action': 'get_all_channels'}, timeout=15)
            return r.json().get('js', {}).get('data', [])
        except: return []

    def get_link(self, cmd):
        url = cmd.replace("ffmpeg ", "").replace("auto ", "")
        try:
            r = self.session.get(self.api_url, params={'type': 'itv', 'action': 'create_link', 'cmd': url}, timeout=5)
            data = r.json()
            if 'js' in data and 'cmd' in data['js']: return data['js']['cmd']
        except: pass
        return url

# --- MAIN APP ---
class RMSAndroidApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Cyan"
        self.channels = []
        self.current_index = -1
        return Builder.load_string(KV)

    def connect_source(self):
        url = self.root.ids.url_field.text
        mac = self.root.ids.mac_field.text
        
        if not url:
            toast("Please enter a URL")
            return

        toast("Connecting... Please Wait")
        # Run in background to prevent lag
        threading.Thread(target=self.worker_connect, args=(url, mac)).start()

    def worker_connect(self, url, mac):
        self.channels = []
        
        # Logic to choose between Stalker or M3U
        if mac and "/c/" in url:
            # Stalker Mode
            client = StalkerClient(url, mac)
            if client.handshake():
                raw = client.get_channels()
                for ch in raw:
                    name = ch.get('name', 'Unknown')
                    cmd = ch.get('cmd', '')
                    # Store client to resolve link later
                    self.channels.append({'text': name, 'url': cmd, 'client': client})
            else:
                Clock.schedule_once(lambda x: toast("Login Failed!"))
                return
        else:
            # Simple M3U Mode
            try:
                r = requests.get(url, timeout=10)
                lines = r.text.splitlines()
                name = "Channel"
                for line in lines:
                    if line.startswith("#EXTINF"):
                        name = line.split(",", 1)[1]
                    elif line.startswith("http"):
                        self.channels.append({'text': name, 'url': line})
                        name = "Channel"
            except:
                Clock.schedule_once(lambda x: toast("Download Failed!"))
                return

        # Update UI on Main Thread
        Clock.schedule_once(self.update_list)

    def update_list(self, dt):
        self.root.ids.rv.data = self.channels
        toast(f"Loaded {len(self.channels)} Channels")

    def play_channel(self, name, url):
        # Find channel object to check if it needs resolving
        ch_data = next((item for item in self.channels if item["text"] == name), None)
        
        if ch_data and 'client' in ch_data:
             toast(f"Resolving: {name}...")
             threading.Thread(target=self.resolve_and_play, args=(ch_data,)).start()
        else:
             self.start_video(url)

    def resolve_and_play(self, ch_data):
        final_url = ch_data['client'].get_link(ch_data['url'])
        Clock.schedule_once(lambda x: self.start_video(final_url))

    def start_video(self, url):
        player = self.root.ids.player
        player.source = url
        player.state = 'play'
        toast("Playing...")

    def toggle_play(self):
        player = self.root.ids.player
        if player.state == 'play':
            player.state = 'pause'
        else:
            player.state = 'play'

    def stop_play(self):
        self.root.ids.player.state = 'stop'

    def play_next(self):
        toast("Next Channel Logic Here")
        # Implement logic to find current index and increment

    def play_prev(self):
        toast("Prev Channel Logic Here")

    def refresh_connection(self):
        self.connect_source()

    def open_settings(self):
        toast("Settings Menu")

if __name__ == '__main__':
    RMSAndroidApp().run()
```

### **APK Banane Ke Steps (Google Colab Par)**

Kyunki Android apps Windows par compile nahi hote, aapko **Google Colab** use karna padega.

1.  **Google Colab Kholein:** [colab.research.google.com](https://colab.research.google.com)
2.  **Ek nayi cell banayein** aur yeh command paste karein taaki environment ready ho jaye:

```python
!pip install buildozer cython==0.29.33
!sudo apt-get install -y python3-pip build-essential git python3 python3-dev ffmpeg libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libportmidi-dev libswscale-dev libavformat-dev libavcodec-dev zlib1g-dev
```

3.  **Files Upload Karein:**
    * Upar diye gaye code ko **`main.py`** naam se save karein aur Colab ke files section mein upload karein.

4.  **Spec File Banayein:**
    * Colab mein yeh run karein: `!buildozer init`
    * `buildozer.spec` file ban jayegi. Usse edit karein aur requirements line ko change karein:
        `requirements = python3,kivy,kivymd,requests,urllib3,ffpyplayer,openssl`

5.  **APK Build Karein:**
    * Yeh command run karein (approx 15-20 mins lagenge):
    ```bash
    !yes | buildozer android debug