# ClassNotice 课堂通知系统

一个完整的课堂通知系统，支持三端架构。

## 功能特性

- **后台服务端**：Web 管理界面，管理班级、用户、课程表、消息调度
- **班主任老师端**：发送通知，支持课程时段消息延迟发送
- **学生端**：全屏横向滚动通知展示

## 快速开始

### 服务端

```bash
cd server
pip install -r requirements.txt
python run.py
```

### 客户端

```bash
cd client
pip install -r requirements.txt
python start.py  # 学生端
python teacher_start.py  # 老师端
```

## 技术栈

- 后端：Flask, Flask-SocketIO, APScheduler
- 前端：HTML/CSS/JavaScript
- 客户端：Python Tkinter
- 数据库：SQLite

## 许可证

MIT License
