import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import sys
import uuid
import threading
import socket
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("请安装 requests: pip install requests")
    sys.exit(1)

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

APP_DATA_DIR = os.path.join(os.environ.get('APPDATA', os.path.expanduser('~')), 'ClassNoticeTeacher')
CONFIG_FILE = os.path.join(APP_DATA_DIR, 'config.enc')
ENCRYPTION_KEY = hashlib.sha256(b'classnotice-teacher-encryption-key-2026').digest() if HAS_CRYPTO else None


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


def clear_config():
    if os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)


class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ClassNotice 教师端 - 登录")
        self.geometry("420x380")
        self.resizable(False, False)
        self.configure(bg='#f0f2f5')
        self._center_window()
        self.login_result = None
        self.http_session = None
        self._build_ui()

    def _center_window(self):
        self.update_idletasks()
        w, h = 420, 380
        x = (self.winfo_screenwidth() // 2) - (w // 2)
        y = (self.winfo_screenheight() // 2) - (h // 2)
        self.geometry(f'{w}x{h}+{x}+{y}')

    def _build_ui(self):
        header = tk.Frame(self, bg='#1890ff', height=70)
        header.pack(fill='x')
        header.pack_propagate(False)
        tk.Label(header, text="📢 ClassNotice 教师端",
                 font=("Microsoft YaHei", 16, "bold"),
                 bg='#1890ff', fg='white').pack(pady=18)

        body = tk.Frame(self, bg='#f0f2f5', padx=40, pady=20)
        body.pack(fill='both', expand=True)

        tk.Label(body, text="服务器地址", font=("Microsoft YaHei", 10),
                 bg='#f0f2f5', anchor='w').pack(fill='x')
        self.server_entry = tk.Entry(body, font=("Microsoft YaHei", 11), width=30)
        self.server_entry.pack(fill='x', pady=(0, 12))
        self.server_entry.insert(0, "192.168.1.100:5000")

        tk.Label(body, text="用户名", font=("Microsoft YaHei", 10),
                 bg='#f0f2f5', anchor='w').pack(fill='x')
        self.username_entry = tk.Entry(body, font=("Microsoft YaHei", 11), width=30)
        self.username_entry.pack(fill='x', pady=(0, 12))

        tk.Label(body, text="密码", font=("Microsoft YaHei", 10),
                 bg='#f0f2f5', anchor='w').pack(fill='x')
        self.password_entry = tk.Entry(body, font=("Microsoft YaHei", 11), width=30, show='*')
        self.password_entry.pack(fill='x', pady=(0, 16))

        self.status_label = tk.Label(body, text="", font=("Microsoft YaHei", 9),
                                     bg='#f0f2f5', fg='#ff4d4f', anchor='w')
        self.status_label.pack(fill='x', pady=(0, 8))

        tk.Button(body, text="登录", font=("Microsoft YaHei", 11, "bold"),
                  command=self._do_login, bg='#1890ff', fg='white',
                  relief='flat', padx=20, pady=8).pack(fill='x')

        self.bind('<Return>', lambda e: self._do_login())

    def _do_login(self):
        server_addr = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not server_addr or not username or not password:
            self.status_label.config(text="请填写所有字段")
            return

        self.status_label.config(text="正在连接服务器...", fg='#1890ff')
        self.update()

        try:
            if ':' not in server_addr:
                server_addr = server_addr + ':5000'

            if not server_addr.startswith('http'):
                server_addr = 'http://' + server_addr

            session = requests.Session()
            resp = session.post(f'{server_addr}/auth/login', json={
                'username': username,
                'password': password
            }, timeout=10)
            data = resp.json()

            if data.get('success'):
                user_data = data.get('user', {})
                config = {
                    'server_addr': server_addr.replace('http://', '').replace('https://', '').rstrip('/'),
                    'username': username,
                    'user_id': user_data.get('id'),
                    'role': user_data.get('role'),
                    'display_name': user_data.get('display_name'),
                    'client_id': str(uuid.uuid4())
                }
                save_config(config)
                self.login_result = config
                self.http_session = session
                self.destroy()
            else:
                self.status_label.config(text=data.get('message', '登录失败'))
        except Exception as e:
            self.status_label.config(text=f"连接失败: {str(e)[:50]}")


class TeacherDashboard(tk.Tk):
    def __init__(self, config, http_session=None):
        super().__init__()
        self.config = config
        self.title(f"ClassNotice 教师端 - {config.get('display_name', config.get('username', ''))}")
        self.geometry("960x680")
        self.minsize(800, 600)
        self.configure(bg='#f0f2f5')

        self.http_session = http_session or requests.Session()
        self.sio = None
        self.connected = False
        self.current_tab = None
        self.messages = []
        self.delayed_queue = []
        self.schedule_data = {}
        self.my_class_info = None
        self.online_count = 0

        self._build_ui()
        self._connect_server()

    def _get_server_url(self):
        addr = self.config.get('server_addr', '')
        if not addr.startswith('http'):
            addr = 'http://' + addr
        return addr.rstrip('/')

    def _api_get(self, path, **kwargs):
        try:
            resp = self.http_session.get(f'{self._get_server_url()}{path}', timeout=10, **kwargs)
            return resp.json()
        except Exception as e:
            return {'success': False, 'message': str(e)[:80]}

    def _api_post(self, path, json_data=None, **kwargs):
        try:
            resp = self.http_session.post(f'{self._get_server_url()}{path}', json=json_data, timeout=10, **kwargs)
            return resp.json()
        except Exception as e:
            return {'success': False, 'message': str(e)[:80]}

    def _api_delete(self, path, **kwargs):
        try:
            resp = self.http_session.delete(f'{self._get_server_url()}{path}', timeout=10, **kwargs)
            return resp.json()
        except Exception as e:
            return {'success': False, 'message': str(e)[:80]}

    def _build_ui(self):
        top = tk.Frame(self, bg='#1890ff', height=50)
        top.pack(fill='x')
        top.pack_propagate(False)
        tk.Label(top, text=f"📢 {self.config.get('display_name', '教师')}",
                 font=("Microsoft YaHei", 13, "bold"),
                 bg='#1890ff', fg='white').pack(side='left', padx=16, pady=12)
        self.class_label = tk.Label(top, text="班级: 加载中...",
                                    font=("Microsoft YaHei", 10),
                                    bg='#1890ff', fg='white')
        self.class_label.pack(side='left', padx=8)
        self.status_label = tk.Label(top, text="● 连接中...",
                                     font=("Microsoft YaHei", 9),
                                     bg='#1890ff', fg='white')
        self.status_label.pack(side='right', padx=16)
        tk.Button(top, text="退出", command=self._logout,
                  bg='#ff4d4f', fg='white', relief='flat',
                  font=("Microsoft YaHei", 9), padx=10).pack(side='right', padx=8)

        nb = ttk.Notebook(self)
        nb.pack(fill='both', expand=True, padx=10, pady=10)

        self.send_frame = self._build_send_tab(nb)
        self.history_frame = self._build_history_tab(nb)
        self.schedule_frame = self._build_schedule_tab(nb)
        self.settings_frame = self._build_settings_tab(nb)

        nb.add(self.send_frame, text=" 发送通知 ")
        nb.add(self.history_frame, text=" 发送历史 ")
        nb.add(self.schedule_frame, text=" 课程表 ")
        nb.add(self.settings_frame, text=" 设置 ")

    def _build_send_tab(self, parent):
        frame = tk.Frame(parent, bg='#f0f2f5')
        left = tk.Frame(frame, bg='#fff', padx=20, pady=20)
        left.pack(side='left', fill='both', expand=True, padx=(0, 10))

        tk.Label(left, text="发送通知", font=("Microsoft YaHei", 12, "bold"),
                 bg='#fff', anchor='w').pack(fill='x')

        tk.Label(left, text="通知标题", font=("Microsoft YaHei", 10),
                 bg='#fff', anchor='w').pack(fill='x', pady=(10, 2))
        self.title_entry = tk.Entry(left, font=("Microsoft YaHei", 11))
        self.title_entry.pack(fill='x')

        tk.Label(left, text="通知内容", font=("Microsoft YaHei", 10),
                 bg='#fff', anchor='w').pack(fill='x', pady=(10, 2))
        self.content_text = scrolledtext.ScrolledText(left, font=("Microsoft YaHei", 11),
                                                      height=6, wrap='word')
        self.content_text.pack(fill='x')

        self.urgent_var = tk.BooleanVar(value=False)
        tk.Checkbutton(left, text="⚠️ 紧急消息（无视课程表，立即弹出）",
                       variable=self.urgent_var, font=("Microsoft YaHei", 10),
                       bg='#fff', anchor='w').pack(anchor='w', pady=(10, 0))

        btn_frame = tk.Frame(left, bg='#fff')
        btn_frame.pack(fill='x', pady=(15, 0))
        tk.Button(btn_frame, text="发送通知", command=self._send_message,
                  font=("Microsoft YaHei", 11, "bold"),
                  bg='#1890ff', fg='white', relief='flat',
                  padx=20, pady=6).pack(side='left')
        tk.Button(btn_frame, text="清空", command=self._clear_send,
                  font=("Microsoft YaHei", 10),
                  bg='#f0f0f0', relief='flat', padx=15, pady=6).pack(side='left', padx=(10, 0))

        self.send_status_label = tk.Label(left, text="", font=("Microsoft YaHei", 9),
                                          bg='#fff', fg='#52c41a', anchor='w')
        self.send_status_label.pack(fill='x', pady=(10, 0))

        right = tk.Frame(frame, bg='#fff', padx=20, pady=20)
        right.pack(side='left', fill='both', expand=True)

        tk.Label(right, text="延迟队列", font=("Microsoft YaHei", 12, "bold"),
                 bg='#fff', anchor='w').pack(fill='x')
        tk.Label(right, text="课程时段发送的消息将在适当时间弹出",
                 font=("Microsoft YaHei", 9), fg='#999', bg='#fff', anchor='w').pack(fill='x')

        self.queue_listbox = tk.Listbox(right, font=("Microsoft YaHei", 10),
                                         height=15, bg='#fafafa', relief='flat',
                                         borderwidth=1)
        self.queue_listbox.pack(fill='both', expand=True, pady=(10, 0))

        self.online_label = tk.Label(right, text="在线终端: -",
                                     font=("Microsoft YaHei", 10),
                                     bg='#fff', fg='#52c41a', anchor='w')
        self.online_label.pack(fill='x', pady=(10, 0))

        return frame

    def _build_history_tab(self, parent):
        frame = tk.Frame(parent, bg='#f0f2f5')
        container = tk.Frame(frame, bg='#fff', padx=20, pady=20)
        container.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(container, text="发送历史", font=("Microsoft YaHei", 12, "bold"),
                 bg='#fff', anchor='w').pack(fill='x')

        columns = ('时间', '标题', '内容', '状态', '已读')
        self.history_tree = ttk.Treeview(container, columns=columns,
                                         show='headings', height=20)

        for col in columns:
            self.history_tree.heading(col, text=col)
            self.history_tree.column(col, width=120 if col != '内容' else 250)

        scrollbar = ttk.Scrollbar(container, orient='vertical',
                                   command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side='left', fill='both', expand=True, pady=(10, 0))
        scrollbar.pack(side='right', fill='y', pady=(10, 0))

        return frame

    def _build_schedule_tab(self, parent):
        frame = tk.Frame(parent, bg='#f0f2f5')
        container = tk.Frame(frame, bg='#fff', padx=20, pady=20)
        container.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(container, text="课程表配置", font=("Microsoft YaHei", 12, "bold"),
                 bg='#fff', anchor='w').pack(fill='x')

        info_text = ("配置每周课程时段。上课时段内发送的消息将延迟到下课或次日发送。"
                     "紧急消息无视课程表，立即弹出。")
        tk.Label(container, text=info_text, font=("Microsoft YaHei", 9),
                 fg='#999', bg='#fff', anchor='w', wraplength=600).pack(fill='x')

        self.schedule_canvas = tk.Canvas(container, bg='#fafafa',
                                         height=300, relief='flat')
        self.schedule_canvas.pack(fill='x', pady=(10, 5))

        btn_frame = tk.Frame(container, bg='#fff')
        btn_frame.pack(fill='x')
        tk.Button(btn_frame, text="保存课程表", command=self._save_schedule,
                  font=("Microsoft YaHei", 10, "bold"),
                  bg='#1890ff', fg='white', relief='flat', padx=15, pady=4).pack(side='left')
        tk.Button(btn_frame, text="刷新", command=self._load_schedule,
                  font=("Microsoft YaHei", 10),
                  bg='#f0f0f0', relief='flat', padx=15, pady=4).pack(side='left', padx=(10, 0))

        return frame

    def _build_settings_tab(self, parent):
        frame = tk.Frame(parent, bg='#f0f2f5')
        container = tk.Frame(frame, bg='#fff', padx=30, pady=30)
        container.pack(fill='both', expand=True, padx=10, pady=10)

        tk.Label(container, text="班级设置", font=("Microsoft YaHei", 12, "bold"),
                 bg='#fff', anchor='w').pack(fill='x')

        row1 = tk.Frame(container, bg='#fff')
        row1.pack(fill='x', pady=(15, 5))
        tk.Label(row1, text="课后消息发送时间：", font=("Microsoft YaHei", 10),
                 bg='#fff').pack(side='left')
        self.after_class_time = tk.Entry(row1, font=("Microsoft YaHei", 10), width=10)
        self.after_class_time.pack(side='left', padx=(0, 10))
        self.after_class_time.insert(0, "19:50")
        tk.Label(row1, text="（下午放学后，消息将在次日此时间发送）",
                 font=("Microsoft YaHei", 9), fg='#999', bg='#fff').pack(side='left')
        tk.Button(row1, text="保存", command=self._save_after_class_time,
                  font=("Microsoft YaHei", 9), bg='#1890ff', fg='white',
                  relief='flat', padx=10).pack(side='left')

        sep = ttk.Separator(container, orient='horizontal')
        sep.pack(fill='x', pady=20)

        tk.Label(container, text="修改密码", font=("Microsoft YaHei", 12, "bold"),
                 bg='#fff', anchor='w').pack(fill='x')

        row2 = tk.Frame(container, bg='#fff')
        row2.pack(fill='x', pady=(15, 5))
        tk.Label(row2, text="原密码：", font=("Microsoft YaHei", 10), bg='#fff').pack(side='left')
        self.old_pwd_entry = tk.Entry(row2, font=("Microsoft YaHei", 10),
                                       show='*', width=20)
        self.old_pwd_entry.pack(side='left', padx=(0, 20))
        tk.Label(row2, text="新密码：", font=("Microsoft YaHei", 10), bg='#fff').pack(side='left')
        self.new_pwd_entry = tk.Entry(row2, font=("Microsoft YaHei", 10),
                                       show='*', width=20)
        self.new_pwd_entry.pack(side='left', padx=(0, 10))
        tk.Button(row2, text="修改", command=self._change_password,
                 font=("Microsoft YaHei", 9), bg='#1890ff', fg='white',
                 relief='flat', padx=10).pack(side='left')

        self.settings_status = tk.Label(container, text="", font=("Microsoft YaHei", 9),
                                        bg='#fff', fg='#52c41a', anchor='w')
        self.settings_status.pack(fill='x', pady=(10, 0))

        return frame

    def _connect_server(self):
        server_url = self._get_server_url()

        def connect_thread():
            try:
                self.sio = socketio.Client()
                self.sio.connect(server_url, wait_timeout=10)

                class_number = self.config.get('class_number', 1)
                self.sio.emit('client_register', {
                    'client_id': self.config.get('client_id', str(uuid.uuid4())),
                    'class_number': class_number,
                    'display_name': self.config.get('display_name', '')
                })

                self.sio.on('register_success', self._on_register_success)
                self.sio.on('queue_update', self._on_queue_update)
                self.sio.on('message_sent', self._on_message_sent)

                self.after(0, lambda: self.status_label.config(text="● 已连接", fg='#52c41a'))
                self.connected = True

                self._load_my_class()
                self._load_history()
                self._load_schedule()
                self._load_queue()

            except Exception as e:
                self.after(0, lambda: self.status_label.config(
                    text="● 连接失败", fg='#ff4d4f'))
                self.after(0, lambda: messagebox.showerror("连接失败", f"无法连接到服务器:\n{str(e)}"))

        threading.Thread(target=connect_thread, daemon=True).start()

    def _load_my_class(self):
        data = self._api_get('/teacher/api/my_class')
        if data.get('success'):
            self.my_class_info = data['data']
            class_name = self.my_class_info.get('name', '')
            self.config['class_name'] = class_name
            self.config['class_number'] = self.my_class_info.get('class_number', 1)
            self.after(0, lambda: self.class_label.config(text=f"班级: {class_name}"))
            self.after(0, lambda: self.after_class_time.delete(0, tk.END))
            self.after(0, lambda: self.after_class_time.insert(0, self.my_class_info.get('after_class_send_time', '19:50')))

    def _on_register_success(self, data):
        class_info = data.get('class_info', {})
        class_name = class_info.get('name', '')
        self.config['class_name'] = class_name
        self.after(0, lambda: self.class_label.config(text=f"班级: {class_name}"))

    def _on_queue_update(self, data):
        self.delayed_queue = data.get('queue', [])
        self.after(0, self._refresh_queue_list)

    def _on_message_sent(self, data):
        self.messages.insert(0, data)
        self.after(0, self._refresh_history)

    def _load_history(self):
        data = self._api_get('/teacher/api/messages')
        if data.get('success'):
            self.messages = data.get('data', [])
            self.after(0, self._refresh_history)

    def _load_queue(self):
        data = self._api_get('/teacher/api/delayed_queue')
        if data.get('success'):
            self.delayed_queue = data.get('data', [])
            self.after(0, self._refresh_queue_list)

    def _load_schedule(self):
        data = self._api_get('/teacher/api/schedule')
        if data.get('success'):
            self.schedule_data = {f"{s['day_of_week']}-{s['period']}": s
                                  for s in data.get('data', [])}
            self.after(0, self._draw_schedule)

    def _refresh_history(self):
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
        for msg in self.messages[:50]:
            status = '已发送' if msg.get('status') == 'sent' else '待发送'
            read_count = msg.get('read_count', 0)
            urgent_tag = ' ⚠️' if msg.get('is_urgent') else ''
            self.history_tree.insert('', 0, values=(
                msg.get('sent_time', msg.get('created_at', ''))[:19],
                msg.get('title', '') + urgent_tag,
                msg.get('content', '')[:40],
                status,
                f"{read_count}人"
            ))

    def _refresh_queue_list(self):
        self.queue_listbox.delete(0, tk.END)
        for item in self.delayed_queue:
            time_str = item.get('scheduled_time', '')[:19]
            reason = item.get('reason', '')
            self.queue_listbox.insert(tk.END, f"{time_str} - {reason}")

    def _draw_schedule(self):
        canvas = self.schedule_canvas
        canvas.delete('all')

        DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        PERIODS = 8

        cw = canvas.winfo_width() if canvas.winfo_width() > 1 else 800
        ch = canvas.winfo_height() if canvas.winfo_height() > 1 else 300

        col_w = cw // (len(DAYS) + 1)
        row_h = ch // (PERIODS + 1)

        canvas.create_rectangle(0, 0, col_w, row_h, fill='#fafafa', outline='#e8e8e8')
        canvas.create_text(col_w // 2, row_h // 2, text="节次", font=("Microsoft YaHei", 9, "bold"))

        for i, day in enumerate(DAYS):
            x = (i + 1) * col_w
            canvas.create_rectangle(x, 0, x + col_w, row_h, fill='#fafafa', outline='#e8e8e8')
            canvas.create_text(x + col_w // 2, row_h // 2, text=day, font=("Microsoft YaHei", 9, "bold"))

        for p in range(1, PERIODS + 1):
            y = p * row_h
            canvas.create_rectangle(0, y, col_w, y + row_h, fill='#fafafa', outline='#e8e8e8')

            first_s = self.schedule_data.get(f'1-{p}')
            time_label = f"{first_s['start_time']}-{first_s['end_time']}" if first_s else f"第{p}节"
            canvas.create_text(col_w // 2, y + row_h // 2, text=time_label, font=("Microsoft YaHei", 8))

            for d in range(1, 8):
                x = d * col_w
                s = self.schedule_data.get(f'{d}-{p}')
                canvas.create_rectangle(x, y, x + col_w, y + row_h, fill='#fff', outline='#e8e8e8')
                if s and s.get('subject'):
                    canvas.create_text(x + col_w // 2, y + row_h // 2,
                                       text=s['subject'], font=("Microsoft YaHei", 9))

    def _send_message(self):
        title = self.title_entry.get().strip()
        content = self.content_text.get('1.0', 'end').strip()
        is_urgent = self.urgent_var.get()

        if not title or not content:
            self.send_status_label.config(text="请填写标题和内容", fg='#ff4d4f')
            return

        body = {
            'title': title,
            'content': content,
            'is_urgent': is_urgent
        }

        data = self._api_post('/teacher/api/messages', json_data=body)

        if data.get('need_confirm'):
            if messagebox.askyesno("确认", "⚠️ 紧急消息将立即弹出，确定发送吗？"):
                body['confirm_urgent'] = True
                data = self._api_post('/teacher/api/messages', json_data=body)
                if data.get('success'):
                    self.send_status_label.config(text=data.get('message', '发送成功'), fg='#52c41a')
                    self._clear_send()
                    self._load_history()
                else:
                    self.send_status_label.config(text=data.get('message', '发送失败'), fg='#ff4d4f')
            return

        if data.get('success'):
            self.send_status_label.config(text=data.get('message', '发送成功'), fg='#52c41a')
            self._clear_send()
            self._load_history()
            self._load_queue()
        else:
            self.send_status_label.config(text=data.get('message', '发送失败'), fg='#ff4d4f')

    def _clear_send(self):
        self.title_entry.delete(0, tk.END)
        self.content_text.delete('1.0', tk.END)
        self.urgent_var.set(False)

    def _save_schedule(self):
        self.settings_status.config(text="课程表保存功能请通过Web端操作", fg='#1890ff')

    def _save_after_class_time(self):
        time_val = self.after_class_time.get().strip()
        if not time_val:
            self.settings_status.config(text="请输入有效的时间", fg='#ff4d4f')
            return
        try:
            h, m = map(int, time_val.split(':'))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            self.settings_status.config(text="时间格式无效，请使用 HH:MM 格式", fg='#ff4d4f')
            return

        data = self._api_post('/teacher/api/after_class_time', json_data={
            'after_class_send_time': time_val
        })
        if data.get('success'):
            self.settings_status.config(text=f"已保存，课后消息将在 {time_val} 发送", fg='#52c41a')
        else:
            self.settings_status.config(text=data.get('message', '保存失败'), fg='#ff4d4f')

    def _change_password(self):
        old_pwd = self.old_pwd_entry.get()
        new_pwd = self.new_pwd_entry.get()
        if not old_pwd or not new_pwd:
            self.settings_status.config(text="请填写原密码和新密码", fg='#ff4d4f')
            return
        data = self._api_post('/auth/change_password', json_data={
            'old_password': old_pwd,
            'new_password': new_pwd
        })
        if data.get('success'):
            self.settings_status.config(text="密码修改成功", fg='#52c41a')
            self.old_pwd_entry.delete(0, tk.END)
            self.new_pwd_entry.delete(0, tk.END)
        else:
            self.settings_status.config(text=data.get('message', '修改失败'), fg='#ff4d4f')

    def _logout(self):
        if messagebox.askyesno("退出", "确定退出教师端吗？"):
            self.connected = False
            if self.sio:
                try:
                    self.sio.disconnect()
                except Exception:
                    pass
            try:
                self._api_post('/auth/logout')
            except Exception:
                pass
            clear_config()
            self.destroy()
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
    http_session = None

    if not config or not config.get('user_id'):
        login = LoginWindow()
        login.mainloop()
        config = login.login_result
        http_session = login.http_session

    if not config:
        sys.exit(0)

    if config.get('role') not in ('teacher', 'admin'):
        messagebox.showerror("权限错误", "只有班主任或管理员账号才能使用教师端")
        clear_config()
        sys.exit(1)

    app = TeacherDashboard(config, http_session)
    app.mainloop()


if __name__ == '__main__':
    main()
