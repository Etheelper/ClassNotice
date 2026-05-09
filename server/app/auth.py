from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import db, User, AuditLog
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        username = data.get('username', '')
        password = data.get('password', '')

        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password) and user.is_active:
            login_user(user)
            user.last_login = datetime.now()
            db.session.commit()

            _log_audit(user.id, 'login', 'user', user.id, f'用户 {username} 登录')

            if request.is_json:
                return jsonify({'success': True, 'user': user.to_dict(), 'redirect': _get_redirect_url(user.role)})
            return redirect(_get_redirect_url(user.role))

        if request.is_json:
            return jsonify({'success': False, 'message': '用户名或密码错误'}), 401
        flash('用户名或密码错误', 'error')

    return render_template('login.html')


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    _log_audit(current_user.id, 'logout', 'user', current_user.id, f'用户 {current_user.username} 登出')
    logout_user()
    return jsonify({'success': True})


@auth_bp.route('/change_password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    old_password = data.get('old_password', '')
    new_password = data.get('new_password', '')

    if not current_user.verify_password(old_password):
        return jsonify({'success': False, 'message': '原密码错误'}), 400

    current_user.set_password(new_password)
    db.session.commit()
    _log_audit(current_user.id, 'change_password', 'user', current_user.id)
    return jsonify({'success': True, 'message': '密码修改成功'})


@auth_bp.route('/api/client_auth', methods=['POST'])
def client_auth():
    data = request.get_json()
    server_addr = data.get('server_addr', '')
    class_number = data.get('class_number')
    client_id = data.get('client_id', '')

    if not class_number or not client_id:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400

    from app.models import Class, Student
    cls = Class.query.filter_by(class_number=class_number).first()
    if not cls:
        return jsonify({'success': False, 'message': '班级不存在'}), 404

    student = Student.query.filter_by(client_id=client_id).first()
    if not student:
        student = Student(
            class_id=cls.id,
            client_id=client_id,
            display_name=f'{cls.name}-学生'
        )
        db.session.add(student)
        db.session.commit()

    return jsonify({
        'success': True,
        'class_info': cls.to_dict(),
        'student_id': student.id
    })


def _get_redirect_url(role):
    if role == 'admin':
        return '/admin/dashboard'
    elif role == 'teacher':
        return '/teacher/dashboard'
    return '/'


def _log_audit(user_id, action, target_type=None, target_id=None, detail=None):
    log = AuditLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
        ip_address=request.remote_addr if request else None
    )
    db.session.add(log)
    db.session.commit()
