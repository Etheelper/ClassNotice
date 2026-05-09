from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Class, Schedule, Message, Student, ReadRecord, DelayedQueue
from app.scheduler_engine import ScheduleEngine, MessageDispatcher
from functools import wraps
from datetime import datetime

teacher_bp = Blueprint('teacher', __name__)


def teacher_required(f):
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if current_user.role not in ('teacher', 'admin'):
            return jsonify({'success': False, 'message': '权限不足'}), 403
        return f(*args, **kwargs)
    return decorated


@teacher_bp.route('/dashboard')
@teacher_required
def dashboard():
    return render_template('teacher/dashboard.html')


@teacher_bp.route('/api/my_class')
@teacher_required
def get_my_class():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404
    return jsonify({'success': True, 'data': cls.to_dict()})


@teacher_bp.route('/api/schedule', methods=['GET'])
@teacher_required
def get_schedule():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    day = request.args.get('day', type=int)
    query = Schedule.query.filter_by(class_id=cls.id)
    if day is not None:
        query = query.filter_by(day_of_week=day)

    schedules = query.order_by(Schedule.day_of_week, Schedule.start_time).all()
    return jsonify({
        'success': True,
        'data': [s.to_dict() for s in schedules]
    })


@teacher_bp.route('/api/schedule', methods=['POST'])
@teacher_required
def save_schedule():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    data = request.get_json()
    schedules_data = data.get('schedules', [])

    Schedule.query.filter_by(class_id=cls.id).delete()

    for s in schedules_data:
        schedule = Schedule(
            class_id=cls.id,
            day_of_week=s.get('day_of_week', 1),
            period=s.get('period', 1),
            start_time=s.get('start_time', '08:00'),
            end_time=s.get('end_time', '08:45'),
            subject=s.get('subject', ''),
            is_holiday=s.get('is_holiday', False)
        )
        db.session.add(schedule)

    db.session.commit()
    return jsonify({'success': True, 'message': '课程表保存成功'})


@teacher_bp.route('/api/schedule/copy_week', methods=['POST'])
@teacher_required
def copy_week_schedule():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    data = request.get_json()
    source_day = data.get('source_day')
    target_days = data.get('target_days', [])

    source_schedules = Schedule.query.filter_by(
        class_id=cls.id, day_of_week=source_day
    ).all()

    for target_day in target_days:
        Schedule.query.filter_by(class_id=cls.id, day_of_week=target_day).delete()
        for s in source_schedules:
            new_s = Schedule(
                class_id=cls.id,
                day_of_week=target_day,
                period=s.period,
                start_time=s.start_time,
                end_time=s.end_time,
                subject=s.subject,
                is_holiday=s.is_holiday
            )
            db.session.add(new_s)

    db.session.commit()
    return jsonify({'success': True, 'message': '课程表复制成功'})


@teacher_bp.route('/api/schedule/export', methods=['GET'])
@teacher_required
def export_schedule():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    schedules = Schedule.query.filter_by(class_id=cls.id).order_by(
        Schedule.day_of_week, Schedule.start_time
    ).all()

    return jsonify({
        'success': True,
        'data': {
            'class_name': cls.name,
            'schedules': [s.to_dict() for s in schedules]
        }
    })


@teacher_bp.route('/api/schedule/import', methods=['POST'])
@teacher_required
def import_schedule():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    data = request.get_json()
    schedules_data = data.get('schedules', [])

    Schedule.query.filter_by(class_id=cls.id).delete()

    for s in schedules_data:
        schedule = Schedule(
            class_id=cls.id,
            day_of_week=s.get('day_of_week', 1),
            period=s.get('period', 1),
            start_time=s.get('start_time', '08:00'),
            end_time=s.get('end_time', '08:45'),
            subject=s.get('subject', ''),
            is_holiday=s.get('is_holiday', False)
        )
        db.session.add(schedule)

    db.session.commit()
    return jsonify({'success': True, 'message': '课程表导入成功'})


@teacher_bp.route('/api/after_class_time', methods=['POST'])
@teacher_required
def set_after_class_time():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    data = request.get_json()
    time_str = data.get('after_class_send_time', '19:50')

    try:
        h, m = map(int, time_str.split(':'))
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except (ValueError, AttributeError):
        return jsonify({'success': False, 'message': '时间格式无效'}), 400

    cls.after_class_send_time = time_str
    db.session.commit()
    return jsonify({'success': True, 'message': f'课后消息发送时间已设置为 {time_str}'})


@teacher_bp.route('/api/messages', methods=['GET'])
@teacher_required
def get_messages():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    pagination = Message.query.filter_by(class_id=cls.id).order_by(
        Message.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': [m.to_dict() for m in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    })


@teacher_bp.route('/api/messages', methods=['POST'])
@teacher_required
def send_message():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    is_urgent = data.get('is_urgent', False)
    priority = data.get('priority', 'normal')

    if not title or not content:
        return jsonify({'success': False, 'message': '标题和内容不能为空'}), 400

    if is_urgent:
        data_confirm = data.get('confirm_urgent', False)
        if not data_confirm:
            return jsonify({'success': False, 'message': '紧急消息需二次确认', 'need_confirm': True}), 200

    msg = Message(
        sender_id=current_user.id,
        class_id=cls.id,
        title=title,
        content=content,
        priority='high' if is_urgent else priority,
        is_urgent=is_urgent
    )

    send_time = ScheduleEngine.calculate_send_time(cls.id, is_urgent)

    if send_time <= datetime.now():
        msg.status = 'sent'
        msg.sent_time = datetime.now()
        db.session.add(msg)
        db.session.commit()

        from app.ws_handlers import send_message_to_class
        send_message_to_class(cls.id, msg.to_dict())

        return jsonify({
            'success': True,
            'message': '消息已立即发送',
            'data': msg.to_dict()
        })
    else:
        msg.status = 'pending'
        msg.scheduled_time = send_time
        db.session.add(msg)
        db.session.commit()

        MessageDispatcher.schedule_message(
            msg.id, cls.id, send_time,
            reason='课程时段延迟发送'
        )

        return jsonify({
            'success': True,
            'message': f'消息已加入延迟队列，将于 {send_time.strftime("%H:%M")} 发送',
            'data': msg.to_dict()
        })


@teacher_bp.route('/api/messages/<int:message_id>', methods=['DELETE'])
@teacher_required
def delete_message(message_id):
    msg = Message.query.get_or_404(message_id)
    cls = Class.query.filter_by(teacher_id=current_user.id).first()

    if not cls or msg.class_id != cls.id:
        return jsonify({'success': False, 'message': '权限不足'}), 403

    DelayedQueue.query.filter_by(message_id=message_id).delete()
    ReadRecord.query.filter_by(message_id=message_id).delete()
    db.session.delete(msg)
    db.session.commit()

    return jsonify({'success': True, 'message': '消息已删除'})


@teacher_bp.route('/api/messages/<int:message_id>/read_status')
@teacher_required
def get_read_status(message_id):
    msg = Message.query.get_or_404(message_id)
    cls = Class.query.filter_by(teacher_id=current_user.id).first()

    if not cls or msg.class_id != cls.id:
        return jsonify({'success': False, 'message': '权限不足'}), 403

    total_students = Student.query.filter_by(class_id=cls.id).count()
    read_records = ReadRecord.query.filter_by(message_id=message_id).all()
    read_students = [r.student.to_dict() for r in read_records if r.student]

    return jsonify({
        'success': True,
        'data': {
            'total_students': total_students,
            'read_count': len(read_records),
            'read_students': read_students
        }
    })


@teacher_bp.route('/api/students')
@teacher_required
def get_students():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    students = Student.query.filter_by(class_id=cls.id).all()
    return jsonify({
        'success': True,
        'data': [s.to_dict() for s in students]
    })


@teacher_bp.route('/api/delayed_queue')
@teacher_required
def get_delayed_queue():
    cls = Class.query.filter_by(teacher_id=current_user.id).first()
    if not cls:
        return jsonify({'success': False, 'message': '未分配班级'}), 404

    items = DelayedQueue.query.filter_by(
        class_id=cls.id,
        is_processed=False
    ).order_by(DelayedQueue.scheduled_time).all()

    return jsonify({
        'success': True,
        'data': [item.to_dict() for item in items]
    })
