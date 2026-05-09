from flask import Blueprint, request, jsonify
from app.models import db, Class, Schedule, Student, Message, ReadRecord
from datetime import datetime

api_bp = Blueprint('api', __name__)


@api_bp.route('/classes', methods=['GET'])
def get_classes():
    classes = Class.query.order_by(Class.class_number).all()
    return jsonify({
        'success': True,
        'data': [c.to_dict() for c in classes]
    })


@api_bp.route('/classes/<int:class_id>/schedule', methods=['GET'])
def get_class_schedule(class_id):
    day = request.args.get('day', type=int)
    query = Schedule.query.filter_by(class_id=class_id)
    if day is not None:
        query = query.filter_by(day_of_week=day)

    schedules = query.order_by(Schedule.start_time).all()
    return jsonify({
        'success': True,
        'data': [s.to_dict() for s in schedules]
    })


@api_bp.route('/classes/<int:class_id>/online_count', methods=['GET'])
def get_online_count(class_id):
    count = Student.query.filter_by(class_id=class_id, is_online=True).count()
    total = Student.query.filter_by(class_id=class_id).count()
    return jsonify({
        'success': True,
        'data': {'online': count, 'total': total}
    })


@api_bp.route('/students/<int:student_id>/messages', methods=['GET'])
def get_student_messages(student_id):
    student = Student.query.get_or_404(student_id)
    limit = request.args.get('limit', 20, type=int)

    messages = Message.query.filter_by(
        class_id=student.class_id,
        status='sent'
    ).order_by(Message.sent_time.desc()).limit(limit).all()

    result = []
    for msg in messages:
        msg_dict = msg.to_dict()
        read = ReadRecord.query.filter_by(
            message_id=msg.id,
            student_id=student_id
        ).first()
        msg_dict['is_read'] = read is not None
        if read:
            msg_dict['read_time'] = read.read_time.isoformat()
        result.append(msg_dict)

    return jsonify({
        'success': True,
        'data': result
    })


@api_bp.route('/server_info', methods=['GET'])
def server_info():
    return jsonify({
        'success': True,
        'data': {
            'name': 'ClassNotice Server',
            'version': '1.2',
            'status': 'running',
            'timestamp': datetime.now().isoformat()
        }
    })


@api_bp.route('/scan', methods=['GET'])
def scan_server():
    return jsonify({
        'success': True,
        'name': 'ClassNotice Server',
        'version': '1.2',
        'port': 5000
    })
