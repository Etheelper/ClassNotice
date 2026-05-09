import os
import sys
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from app.scheduler_engine import process_delayed_queue

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()


def init_scheduler(app):
    scheduler.add_job(
        func=lambda: process_delayed_queue(app),
        trigger=CronTrigger(second='*/30'),
        id='process_delayed_queue',
        name='process_delayed_queue',
        replace_existing=True
    )

    scheduler.add_job(
        func=lambda: _backup_database(app),
        trigger=CronTrigger(hour=2, minute=0),
        id='daily_backup',
        name='daily_backup',
        replace_existing=True
    )

    scheduler.add_job(
        func=lambda: _cleanup_offline_clients(app),
        trigger=CronTrigger(minute='*/5'),
        id='cleanup_offline',
        name='cleanup_offline',
        replace_existing=True
    )

    scheduler.start()
    logger.info("Scheduler started")


def _backup_database(app):
    with app.app_context():
        try:
            db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
            if db_uri.startswith('sqlite:///'):
                db_path = db_uri.replace('sqlite:///', '')
                if os.path.exists(db_path):
                    import shutil
                    from datetime import datetime
                    backup_dir = os.path.join(os.path.dirname(db_path), 'backups')
                    os.makedirs(backup_dir, exist_ok=True)
                    backup_name = "classnotice_{}.db".format(datetime.now().strftime('%Y%m%d_%H%M%S'))
                    backup_path = os.path.join(backup_dir, backup_name)
                    shutil.copy2(db_path, backup_path)
                    logger.info("Database backup completed: " + backup_path)

                    _cleanup_old_backups(backup_dir, keep=7)
        except Exception as e:
            logger.error("Database backup failed: " + str(e))


def _cleanup_old_backups(backup_dir, keep=7):
    try:
        files = sorted(
            [f for f in os.listdir(backup_dir) if f.startswith('classnotice_') and f.endswith('.db')],
            reverse=True
        )
        for f in files[keep:]:
            os.remove(os.path.join(backup_dir, f))
            logger.info("Removed old backup: " + f)
    except Exception as e:
        logger.error("Cleanup old backups failed: " + str(e))


def _cleanup_offline_clients(app):
    with app.app_context():
        from app.models import Student, db
        from datetime import datetime, timedelta

        threshold = datetime.now() - timedelta(minutes=10)
        students = Student.query.filter(
            Student.is_online == True,
            Student.last_seen < threshold
        ).all()

        for s in students:
            s.is_online = False

        if students:
            db.session.commit()
            logger.info("Cleaned {} offline clients".format(len(students)))
