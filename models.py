from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False) 
    must_change_password = db.Column(db.Boolean, default=True)
    class_name = db.Column(db.String(50))
    profile_picture = db.Column(db.String(255), default='default.png')
    profile_picture_data = db.Column(db.LargeBinary, nullable=True)
    profile_picture_filename = db.Column(db.String(255), default='default.png')
    pic_id = db.Column(db.Integer, db.ForeignKey('pic.id', name='fk_user_pic'), nullable=True)
    division_id = db.Column(db.Integer, db.ForeignKey('division.id'), nullable=True)
    can_mark_attendance = db.Column(db.Boolean, default=False)

class SessionPIC(db.Model):
    """Links sessions with PICs (divisions) - allows multiple PICs per session"""
    __tablename__ = 'session_pic'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id', ondelete='CASCADE'), nullable=False)
    pic_id = db.Column(db.Integer, db.ForeignKey('pic.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    session = db.relationship('Session', backref='session_pics')
    pic = db.relationship('Pic', backref='session_assignments')
    
    __table_args__ = (
        db.UniqueConstraint('session_id', 'pic_id', name='unique_session_pic'),
    )
    
    def __repr__(self):
        return f'<SessionPIC Session:{self.session_id} PIC:{self.pic_id}>'


class Session(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    is_locked = db.Column(db.Boolean, default=False)
    session_type = db.Column(db.String(50), default='all', nullable=False)  # 'all', 'core', 'event'
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def assigned_pics(self):
        """Get list of Pic objects assigned to this session"""
        return [sp.pic for sp in self.session_pics]


class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('session.id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    status = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    attendance_type = db.Column(db.String(50), default='regular', nullable=False)
    
    session = db.relationship('Session', backref='attendances')
    user = db.relationship('User', backref='attendances')

    __table_args__ = (
        db.UniqueConstraint('session_id', 'user_id', name='unique_session_user'),
    )


class Pic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)  # Description of PIC responsibilities
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    members = db.relationship('User', backref='pic', lazy=True)
    def __repr__(self):
        return f'<Pic {self.name}>'


class Division(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True, nullable=False)
    members = db.relationship('User', backref='division', lazy=True)


class Notulensi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey("session.id", ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    session = db.relationship("Session", backref="notulensi")


class JadwalPiket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)  
    day_name = db.Column(db.String(20), nullable=False)  
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    
    assignments = db.relationship('PiketAssignment', backref='jadwal', lazy=True, cascade='all, delete-orphan')
    
    __table_args__ = (
        db.UniqueConstraint('day_of_week', name='unique_day_of_week'),
    )
    
    def __repr__(self):
        return f'<JadwalPiket {self.day_name}>'


class PiketAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jadwal_id = db.Column(db.Integer, db.ForeignKey('jadwal_piket.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='piket_assignments')
    
    __table_args__ = (
        db.UniqueConstraint('jadwal_id', 'user_id', name='unique_jadwal_user'),
    )
    
    def __repr__(self):
        return f'<PiketAssignment Day:{self.jadwal_id} User:{self.user_id}>'


class EmailReminderLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_of_week = db.Column(db.Integer, nullable=False)
    day_name = db.Column(db.String(20), nullable=False)
    recipients_count = db.Column(db.Integer, default=0)
    recipients = db.Column(db.Text)
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='success')
    error_message = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<EmailReminderLog {self.day_name} - {self.sent_at}>'