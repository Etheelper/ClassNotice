import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import uuid
import threading
import socket
import struct
import winsound
import time
import math
from datetime import datetime

try:
    import socketio
except ImportError:
    print("请安装 python-socketio: pip install python-socketio")
    sys.exit(1)

try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad, unpad
    import base64
    import hashlib
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

APP_DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ClassNotice')
CONFIG_FILE = os.path.join(APP_DATA_DIR, 'config.enc')
ENCRYPTION_KEY = hashlib.sha256(b'classnotice-client-encryption-key-2026').digest() if HAS_CRYPTO else None


def encrypt_data(data_str):
    if not HAS_CRYPTO or not data_str:
        return data_str or ''
    cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(data_str.encode('utf-8'), AES.block_size))
    iv = cipher.iv
    return base64.b64encode(iv + ct_bytes).decode('utf-8')


def decrypt_data(encrypted_str):
    if not HAS_CRYPTO or not encrypted_str:
        return encrypted_str or ''
    try:
        raw = base64.b64decode(encrypted_str)
        iv = raw[:16]
        ct = raw[16:]
        cipher = AES.new(ENCRYPTION_KEY, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    except Exception:
        return ''


def save_config(config):
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    json_str = json.dumps(config, ensure_ascii=False)
    encrypted = encrypt_data(json_str)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        f.write(encrypted)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return None
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            encrypted = f.read()
        json_str = decrypt_data(encrypted)
        if json_str:
            return json.loads(json_str)
    except Exception:
        pass
    return None


def scan_lan_servers(port=5000, timeout=1):
    results = []
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        parts = local_ip.split('.')
        network_prefix = '.'.join(parts[:3])

        for i in range(1, 255):
            ip = f"{network_prefix}.{i}"
            if ip == local_ip:
                continue
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    results.append(ip)
                sock.close()
            except Exception:
                pass
    except Exception:
        pass
    return results


class ConfigWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ClassNotice 学生端配置向导")
        self.geometry("520x420")
        self.resizable(False, False)
        self.configure(bg='#f0f2f5')

        self.result_config = None
        self._center_window()

        self._build_ui()

    def _center_window(self):
        self.update_idletasks()
        w = 520
        h = 420
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _build_ui(self):
        header = tk.Frame(self, bg='#1890ff', height=60)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(header, text="📢 ClassNotice 学生端配置向导",
                 font=("Microsoft YaHei", 14, "bold"),
                 bg='#1890ff', fg='white').pack(pady=15)

        body = tk.Frame(self, bg='#f0f2f5', padx=30, pady=20)
        body.pack(fill='both', expand=True)

        tk.Label(body, text="1. 服务器地址", font=("Microsoft YaHei", 11),
                 bg='#f0f2f5', anchor='w').pack(fill='x', pady=(0, 4))
        server_frame = tk.Frame(body, bg='#f0f2f5')
        server_frame.pack(fill='x', pady=(0, 4))
        self.server_entry = tk.Entry(server_frame, font=("Microsoft YaHei", 11), width=30)
        self.server_entry.pack(side='left', padx=(0, 8))
        self.server_entry.insert(0, "192.168.1.100:5000")
        tk.Button(server_frame, text="扫描局域网", font=("Microsoft YaHei", 9),
                  command=self._scan_servers, bg='#e6f7ff', relief='flat').pack(side='left')

        self.scan_result_label = tk.Label(body, text="", font=("Microsoft YaHei", 9),
                                          bg='#f0f2f5', fg='#999', anchor='w')
        self.scan_result_label.pack(fill='x', pady=(0, 12))

        tk.Label(body, text="2. 选择班级", font=("Microsoft YaHei", 11),
                 bg='#f0f2f5', anchor='w').pack(fill='x', pady=(0, 4))
        self.class_var = tk.StringVar(value="1班")
        class_combo = ttk.Combobox(body, textvariable=self.class_var,
                                    values=[f"{i}班" for i in range(1, 27)],
                                    state='readonly', font=("Microsoft YaHei", 11), width=28)
        class_combo.pack(fill='x', pady=(0, 12))
        class_combo.current(0)

        tk.Label(body, text="3. 显示设置", font=("Microsoft YaHei", 11),
                 bg='#f0f2f5', anchor='w').pack(fill='x', pady=(0, 4))
        self.autostart_var = tk.BooleanVar(value=True)
        self.sound_var = tk.BooleanVar(value=True)
        tk.Checkbutton(body, text="开机自动启动", variable=self.autostart_var,
                       font=("Microsoft YaHei", 10), bg='#f0f2f5',
                       activebackground='#f0f2f5').pack(anchor='w')
        tk.Checkbutton(body, text="启用声音提醒", variable=self.sound_var,
                       font=("Microsoft YaHei", 10), bg='#f0f2f5',
                       activebackground='#f0f2f5').pack(anchor='w', pady=(0, 16))

        btn_frame = tk.Frame(body, bg='#f0f2f5')
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text="测试连接", font=("Microsoft YaHei", 11),
                  command=self._test_connection, bg='#f0f0f0', width=12,
                  relief='flat', padx=10, pady=6).pack(side='left', padx=(0, 12))
        tk.Button(btn_frame, text="保存并启动", font=("Microsoft YaHei", 11, "bold"),
                  command=self._save_and_start, bg='#1890ff', fg='white', width=12,
                  relief='flat', padx=10, pady=6).pack(side='left')

        self.status_label = tk.Label(body, text="", font=("Microsoft YaHei", 9),
                                     bg='#f0f2f5', fg='#ff4d4f', anchor='w')
        self.status_label.pack(fill='x', pady=(8, 0))

    def _scan_servers(self):
        self.scan_result_label.config(text="正在扫描局域网...")
        self.update()

        def do_scan():
            servers = scan_lan_servers()
            self.after(0, lambda: self._on_scan_complete(servers))

        threading.Thread(target=do_scan, daemon=True).start()

    def _on_scan_complete(self, servers):
        if servers:
            self.scan_result_label.config(
                text=f"发现服务器: {', '.join(servers)}",
                fg='#52c41a'
            )
            self.server_entry.delete(0, 'end')
            self.server_entry.insert(0, f"{servers[0]}:5000")
        else:
            self.scan_result_label.config(text="未发现局域网服务器，请手动输入", fg='#ff4d4f')

    def _test_connection(self):
        server_addr = self.server_entry.get().strip()
        if not server_addr:
            self.status_label.config(text="请输入服务器地址")
            return

        try:
            if ':' in server_addr:
                host, port = server_addr.rsplit(':', 1)
                port = int(port)
            else:
                host = server_addr
                port = 5000

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                self.status_label.config(text="✅ 连接成功！", fg='#52c41a')
            else:
                self.status_label.config(text="❌ 无法连接到服务器", fg='#ff4d4f')
        except Exception as e:
            self.status_label.config(text=f"❌ 连接错误: {str(e)[:50]}", fg='#ff4d4f')

    def _save_and_start(self):
        server_addr = self.server_entry.get().strip()
        if not server_addr:
            self.status_label.config(text="请输入服务器地址")
            return

        class_name = self.class_var.get()
        class_number = int(class_name.replace('班', ''))

        self.result_config = {
            'server_addr': server_addr,
            'class_number': class_number,
            'class_name': class_name,
            'autostart': self.autostart_var.get(),
            'sound_enabled': self.sound_var.get(),
            'client_id': str(uuid.uuid4())
        }

        save_config(self.result_config)
        self.destroy()


class NotificationDisplay:
    def __init__(self, sound_enabled=True):
        self.sound_enabled = sound_enabled
        self.root = None
        self.canvas = None
        self.text_id = None
        self._animation_running = False

    def show_notification(self, message_data):
        if self.root and self.root.winfo_exists():
            self.root.destroy()

        self.root = tk.Toplevel()
        self.root.title("ClassNotice 通知")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.configure(bg='#000000')
        self.root.overrideredirect(True)

        self.root.bind('<Escape>', lambda e: self._close())
        self.root.bind('<Return>', lambda e: self._close())
        self.root.bind('<space>', lambda e: self._close())

        title = message_data.get('title', '')
        content = message_data.get('content', '')
        is_urgent = message_data.get('is_urgent', False)

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        top_frame = tk.Frame(self.root, bg='#000000', height=screen_height // 3)
        top_frame.pack(fill='x', side='top')
        top_frame.pack_propagate(False)

        font_size = max(int(screen_height * 0.15), 24)

        self.canvas = tk.Canvas(top_frame, bg='#000000', highlightthickness=0,
                                width=screen_width, height=screen_height // 3)
        self.canvas.pack(fill='both', expand=True)

        display_text = f"【{title}】{content}" if title else content
        if is_urgent:
            display_text = f"⚠️ 紧急通知 ⚠️ {display_text}"

        self.text_id = self.canvas.create_text(
            screen_width, screen_height // 6,
            text=display_text,
            font=("Microsoft YaHei", font_size, "bold"),
            fill='#FFCC00',
            anchor='center'
        )

        bottom_frame = tk.Frame(self.root, bg='#000000')
        bottom_frame.pack(fill='both', expand=True)

        detail_font_size = max(font_size // 3, 14)
        tk.Label(bottom_frame, text=content,
                 font=("Microsoft YaHei", detail_font_size),
                 fg='#CCCCCC', bg='#000000',
                 wraplength=screen_width - 100).pack(pady=30)

        time_str = datetime.now().strftime('%H:%M')
        tk.Label(bottom_frame, text=f"收到时间: {time_str}  |  按 ESC/回车/空格 关闭",
                 font=("Microsoft YaHei", 12),
                 fg='#666666', bg='#000000').pack(side='bottom', pady=20)

        if self.sound_enabled:
            self._play_sound(is_urgent)

        self._start_scroll_animation(screen_width, scroll_count=3)

        self.root.focus_force()
        self.root.grab_set()

    def _start_scroll_animation(self, screen_width, scroll_count=3):
        self._animation_running = True
        self._scroll_count = 0
        self._max_scrolls = scroll_count
        self._animate_scroll(screen_width)

    def _animate_scroll(self, screen_width):
        if not self._animation_running or not self.canvas or not self.text_id:
            return

        if self._scroll_count >= self._max_scrolls:
            self._animation_running = False
            return

        try:
            bbox = self.canvas.bbox(self.text_id)
            if bbox:
                text_width = bbox[2] - bbox[0]
            else:
                text_width = screen_width

            start_x = screen_width + text_width // 2
            end_x = -text_width // 2
            current_x = self.canvas.coords(self.text_id)[0]

            step = max(screen_width // 200, 3)

            new_x = current_x - step
            if new_x <= end_x:
                new_x = start_x
                self._scroll_count += 1

            self.canvas.coords(self.text_id, new_x, self.canvas.coords(self.text_id)[1])

            if self._scroll_count < self._max_scrolls:
                self.root.after(16, lambda: self._animate_scroll(screen_width))
            else:
                self._animation_running = False
        except tk.TclError:
            self._animation_running = False

    def _play_sound(self, is_urgent=False):
        def _sound_thread():
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                time.sleep(0.1)
                frequency = 1500 if is_urgent else 1000
                duration = 500 if is_urgent else 300
                winsound.Beep(frequency, duration)
                if is_urgent:
                    time.sleep(0.2)
                    winsound.Beep(frequency, duration)
            except Exception:
                pass

        threading.Thread(target=_sound_thread, daemon=True).start()

    def _close(self):
        self._animation_running = False
        if self.root:
            try:
                self.root.grab_release()
                self.root.destroy()
            except Exception:
                pass
            self.root = None


class ClassNoticeClient:
    def __init__(self, config):
        self.config = config
        self.client_id = config.get('client_id', str(uuid.uuid4()))
        self.server_addr = config.get('server_addr', 'localhost:5000')
        self.class_number = config.get('class_number', 1)
        self.sound_enabled = config.get('sound_enabled', True)
        self.sio = None
        self.connected = False
        self.notification_display = NotificationDisplay(sound_enabled=self.sound_enabled)
        self.main_window = None
        self.status_var = None
        self.tray_icon = None

    def _get_server_url(self):
        addr = self.server_addr
        if not addr.startswith('http'):
            addr = f'http://{addr}'
        return addr

    def start(self):
        self._create_main_window()
        self._connect_server()
        self.main_window.mainloop()

    def _create_main_window(self):
        self.main_window = tk.Tk()
        self.main_window.title("ClassNotice 学生端")
        self.main_window.geometry("360x200")
        self.main_window.resizable(False, False)
        self.main_window.configure(bg='#f0f2f5')

        self.main_window.protocol("WM_DELETE_WINDOW", self._on_minimize)

        header = tk.Frame(self.main_window, bg='#1890ff', height=40)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="📢 ClassNotice 学生端",
                 font=("Microsoft YaHei", 11, "bold"),
                 bg='#1890ff', fg='white').pack(pady=8)

        body = tk.Frame(self.main_window, bg='#f0f2f5', padx=20, pady=15)
        body.pack(fill='both', expand=True)

        self.status_var = tk.StringVar(value="正在连接服务器...")
        tk.Label(body, textvariable=self.status_var,
                 font=("Microsoft YaHei", 10),
                 bg='#f0f2f5', anchor='w').pack(fill='x')

        tk.Label(body, text=f"班级: {self.config.get('class_name', str(self.class_number) + '班')}",
                 font=("Microsoft YaHei", 10),
                 bg='#f0f2f5', anchor='w').pack(fill='x', pady=(4, 0))

        tk.Label(body, text=f"服务器: {self.server_addr}",
                 font=("Microsoft YaHei", 9),
                 bg='#f0f2f5', fg='#999', anchor='w').pack(fill='x', pady=(4, 0))

        btn_frame = tk.Frame(body, bg='#f0f2f5')
        btn_frame.pack(fill='x', pady=(10, 0))
        tk.Button(btn_frame, text="重新配置", font=("Microsoft YaHei", 9),
                  command=self._reconfigure, bg='#f0f0f0', relief='flat').pack(side='left')
        tk.Button(btn_frame, text="退出", font=("Microsoft YaHei", 9),
                  command=self._quit, bg='#fff2f0', fg='#ff4d4f', relief='flat').pack(side='right')

        self.main_window.bind('<Map>', self._on_restore)

    def _connect_server(self):
        server_url = self._get_server_url()

        self.sio = socketio.SimpleClient()

        def connect_thread():
            try:
                self.sio.connect(server_url)
                self.connected = True
                self.main_window.after(0, lambda: self.status_var.set("✅ 已连接服务器"))

                self.sio.emit('client_register', {
                    'client_id': self.client_id,
                    'class_number': self.class_number,
                    'display_name': f"{self.config.get('class_name', '')}-学生"
                })

                while self.connected:
                    try:
                        event_data = self.sio.receive(timeout=30)
                        if event_data:
                            event_name = event_data[0]
                            data = event_data[1] if len(event_data) > 1 else {}
                            self.main_window.after(0, lambda e=event_name, d=data: self._handle_event(e, d))
                    except socketio.exceptions.ConnectionError:
                        self.connected = False
                        self.main_window.after(0, lambda: self.status_var.set("❌ 连接断开，尝试重连..."))
                        break
                    except Exception:
                        pass

            except Exception as e:
                self.main_window.after(0, lambda: self.status_var.set(f"❌ 连接失败: {str(e)[:30]}"))

        threading.Thread(target=connect_thread, daemon=True).start()

        self._start_heartbeat()

    def _start_heartbeat(self):
        def heartbeat_loop():
            while True:
                time.sleep(30)
                if self.connected and self.sio:
                    try:
                        self.sio.emit('heartbeat', {'client_id': self.client_id})
                    except Exception:
                        pass

        threading.Thread(target=heartbeat_loop, daemon=True).start()

    def _handle_event(self, event_name, data):
        if event_name == 'new_message':
            self._on_new_message(data)
        elif event_name == 'register_success':
            self.status_var.set(f"✅ 已连接 - {data.get('class_info', {}).get('name', '')}")
        elif event_name == 'register_error':
            self.status_var.set(f"❌ 注册失败: {data.get('message', '')}")

    def _on_new_message(self, message_data):
        self.notification_display.show_notification(message_data)

        if self.sio:
            try:
                self.sio.emit('message_read', {'message_id': message_data.get('id')})
            except Exception:
                pass

    def _on_minimize(self):
        self.main_window.withdraw()

    def _on_restore(self, event=None):
        pass

    def _reconfigure(self):
        if messagebox.askyesno("重新配置", "确定要重新配置吗？将断开当前连接。"):
            self.connected = False
            if self.sio:
                try:
                    self.sio.disconnect()
                except Exception:
                    pass
            self.main_window.destroy()

            config_file = CONFIG_FILE
            if os.path.exists(config_file):
                os.remove(config_file)

            wizard = ConfigWizard()
            wizard.mainloop()

            if wizard.result_config:
                new_client = ClassNoticeClient(wizard.result_config)
                new_client.start()
            else:
                sys.exit(0)

    def _quit(self):
        self.connected = False
        if self.sio:
            try:
                self.sio.disconnect()
            except Exception:
                pass
        self.main_window.destroy()
        sys.exit(0)


def main():
    if getattr(sys, 'frozen', False):
        try:
            import multiprocessing
            multiprocessing.freeze_support()
        except Exception:
            pass

    os.makedirs(APP_DATA_DIR, exist_ok=True)

    config = load_config()

    if not config:
        wizard = ConfigWizard()
        wizard.mainloop()
        config = wizard.result_config

    if not config:
        sys.exit(0)

    client = ClassNoticeClient(config)
    client.start()


if __name__ == '__main__':
    main()
