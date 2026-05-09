from datetime import datetime, timedelta
from app.models import db, Schedule, Message, DelayedQueue, Class
import logging

logger = logging.getLogger(__name__)


class ScheduleEngine:
    @staticmethod
    def get_current_period(class_id):
        now = datetime.now()
        day_of_week = now.isoweekday()
        current_time = now.strftime('%H:%M')

        schedules = Schedule.query.filter_by(
            class_id=class_id,
            day_of_week=day_of_week
        ).order_by(Schedule.start_time).all()

        if not schedules:
            return {'in_class': False, 'schedule': None, 'is_last': False}

        for i, s in enumerate(schedules):
            if s.start_time <= current_time <= s.end_time:
                is_last = (i == len(schedules) - 1)
                return {'in_class': True, 'schedule': s, 'is_last': is_last}

        return {'in_class': False, 'schedule': None, 'is_last': False}

    @staticmethod
    def is_after_last_class(class_id):
        now = datetime.now()
        day_of_week = now.isoweekday()
        current_time = now.strftime('%H:%M')

        schedules = Schedule.query.filter_by(
            class_id=class_id,
            day_of_week=day_of_week
        ).order_by(Schedule.end_time.desc()).all()

        if not schedules:
            return False

        last_end = schedules[0].end_time
        return current_time > last_end

    @staticmethod
    def get_last_period_end(class_id, date=None):
        if date is None:
            date = datetime.now()
        day_of_week = date.isoweekday()

        schedules = Schedule.query.filter_by(
            class_id=class_id,
            day_of_week=day_of_week
        ).order_by(Schedule.end_time.desc()).all()

        if not schedules:
            return None
        return schedules[0].end_time

    @staticmethod
    def get_first_period_start(class_id, date=None):
        if date is None:
            date = datetime.now()
        day_of_week = date.isoweekday()

        schedules = Schedule.query.filter_by(
            class_id=class_id,
            day_of_week=day_of_week
        ).order_by(Schedule.start_time).all()

        if not schedules:
            return None
        return schedules[0].start_time

    @staticmethod
    def calculate_send_time(class_id, is_urgent=False):
        if is_urgent:
            return datetime.now()

        now = datetime.now()
        period_info = ScheduleEngine.get_current_period(class_id)

        if period_info['in_class']:
            schedule = period_info['schedule']
            if period_info['is_last']:
                next_day = now + timedelta(days=1)
                first_start = ScheduleEngine.get_first_period_start(class_id, next_day)
                if first_start:
                    h, m = map(int, first_start.split(':'))
                    send_min = max(m - 5, 0)
                    send_time = next_day.replace(hour=h, minute=send_min, second=0, microsecond=0)
                    return send_time
                else:
                    return now + timedelta(hours=1)
            else:
                h, m = map(int, schedule.end_time.split(':'))
                return now.replace(hour=h, minute=m, second=0, microsecond=0)

        elif ScheduleEngine.is_after_last_class(class_id):
            cls = Class.query.get(class_id)
            after_time = cls.after_class_send_time if cls else '19:50'
            h, m = map(int, after_time.split(':'))
            next_day = now + timedelta(days=1)
            return next_day.replace(hour=h, minute=m, second=0, microsecond=0)

        else:
            return now


class MessageDispatcher:
    @staticmethod
    def dispatch_message(message, app):
        with app.app_context():
            from app.ws_handlers import send_message_to_class
            msg = Message.query.get(message.id)
            if not msg:
                return

            msg.status = 'sent'
            msg.sent_time = datetime.now()
            db.session.commit()

            send_message_to_class(msg.class_id, msg.to_dict())
            logger.info("消息已发送: ID={}, 班级ID={}".format(msg.id, msg.class_id))

    @staticmethod
    def schedule_message(message_id, class_id, scheduled_time, reason=''):
        delayed = DelayedQueue(
            message_id=message_id,
            class_id=class_id,
            scheduled_time=scheduled_time,
            reason=reason
        )
        db.session.add(delayed)
        db.session.commit()
        logger.info("消息已加入延迟队列: 消息ID={}, 计划发送时间={}, 原因={}".format(
            message_id, scheduled_time, reason))


def process_delayed_queue(app):
    with app.app_context():
        now = datetime.now()
        pending = DelayedQueue.query.filter(
            DelayedQueue.scheduled_time <= now,
            DelayedQueue.is_processed == False
        ).all()

        for item in pending:
            msg = Message.query.get(item.message_id)
            if msg and msg.status == 'pending':
                MessageDispatcher.dispatch_message(msg, app)
            item.is_processed = True
            db.session.commit()

        if pending:
            logger.info("已处理 {} 条延迟消息".format(len(pending)))
