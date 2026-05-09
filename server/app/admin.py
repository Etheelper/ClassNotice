from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, User, Class, AuditLog, Message, Student, Config
from functools import wraps
from datetime import datetime

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            return jsonify({'success': False, 'message': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated


@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')


@admin_bp.route('/api/stats')
@admin_required
def get_stats():
    total_classes = Class.query.count()
    total_students = Student.query.count()
    online_students = Student.query.filter_by(is_online=True).count()
    total_messages = Message.query.count()
    today_messages = Message.query.filter(
        db.func.date(Message.created_at) == datetime.now().date()
    ).count()

    return jsonify({
        'success': True,
        'data': {
            'total_classes': total_classes,
            'total_students': total_students,
            'online_students': online_students,
            'total_messages': total_messages,
            'today_messages': today_messages
        }
    })


@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    role_filter = request.args.get('role', '')

    query = User.query
    if role_filter:
        query = query.filter_by(role=role_filter)

    pagination = query.order_by(User.id.desc()).paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'success': True,
        'data': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@admin_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '')
    role = data.get('role', 'teacher')
    display_name = data.get('display_name', '')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    user = User(username=username, role=role, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    if role == 'teacher' and data.get('class_id'):
        cls = Class.query.get(data.get('class_id'))
        if cls:
            cls.teacher_id = user.id
            db.session.commit()

    return jsonify({'success': True, 'data': user.to_dict()})


@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    if 'display_name' in data:
        user.display_name = data['display_name']
    if 'role' in data:
        user.role = data['role']
    if 'is_active' in data:
        user.is_active = data['is_active']
    if 'password' in data and data['password']:
        user.set_password(data['password'])

    db.session.commit()
    return jsonify({'success': True, 'data': user.to_dict()})


@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.username == 'admin':
        return jsonify({'success': False, 'message': '不能删除默认管理员'}), 400
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True})


@admin_bp.route('/api/classes', methods=['GET'])
@admin_required
def get_classes():
    classes = Class.query.order_by(Class.class_number).all()
    return jsonify({
        'success': True,
        'data': [c.to_dict() for c in classes]
    })


@admin_bp.route('/api/audit_logs', methods=['GET'])
@admin_required
def get_audit_logs():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    pagination = AuditLog.query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    return jsonify({
        'success': True,
        'data': [l.to_dict() for l in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@admin_bp.route('/api/broadcast', methods=['POST'])
@admin_required
def broadcast_message():
    data = request.get_json()
    title = data.get('title', '')
    content = data.get('content', '')

    if not title or not content:
        return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400

    classes = Class.query.all()
    messages = []
    for cls in classes:
        msg = Message(
            sender_id=current_user.id,
            class_id=cls.id,
            title=title,
            content=content,
            priority='high',
            is_urgent=True,
            status='sent',
            sent_time=datetime.now()
        )
        db.session.add(msg)
        messages.append(msg)

    db.session.commit()

    from app.ws_handlers import send_message_to_class
    for msg in messages:
        send_message_to_class(msg.class_id, msg.to_dict())

    return jsonify({'success': True, 'message': f'全校广播已发送至 {len(messages)} 个班级'})


@admin_bp.route('/api/assign_class', methods=['POST'])
@admin_required
def assign_class():
    data = request.get_json()
    user_id = data.get('user_id')
    class_id = data.get('class_id')

    if not user_id or not class_id:
        return jsonify({'success': False, 'message': '参数不完整'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    cls = Class.query.get(class_id)
    if not cls:
        return jsonify({'success': False, 'message': '班级不存在'}), 404

    old_class = Class.query.filter_by(teacher_id=user_id).first()
    if old_class:
        old_class.teacher_id = None

    cls.teacher_id = user_id
    db.session.commit()

    return jsonify({'success': True, 'message': f'已将 {cls.name} 分配给 {user.display_name or user.username}'})


@admin_bp.route('/api/config', methods=['GET'])
@admin_required
def get_config():
    configs = Config.query.all()
    return jsonify({
        'success': True,
        'data': {c.key: c.value for c in configs}
    })


@admin_bp.route('/api/config', methods=['POST'])
@admin_required
def update_config():
    data = request.get_json()
    for key, value in data.items():
        config = Config.query.filter_by(key=key).first()
        if config:
            config.value = str(value)
        else:
            config = Config(key=key, value=str(value))
            db.session.add(config)
    db.session.commit()
    return jsonify({'success': True})
