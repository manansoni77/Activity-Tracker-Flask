from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()
DB_NAME = 'database.sqlite3'

class credentials(db.Model):
    __tablename__ = 'credentials'
    login_id = db.Column(db.String,primary_key=True,nullable=False,unique=True)
    password = db.Column(db.String,nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey("user.user_id"),nullable=False,unique=True)

class user(db.Model,UserMixin):
    __tablename__ = 'user'
    user_id = db.Column(db.Integer,primary_key=True,nullable=False,unique=True,autoincrement=True)
    first_name = db.Column(db.String,nullable=False)
    last_name = db.Column(db.String,nullable=False)
    dob = db.Column(db.String,nullable=False)
    def get_id(self):
        return self.user_id

class trackers(db.Model):
    __tablename__ = 'trackers'
    track_id = db.Column(db.Integer,primary_key=True,nullable=False,unique=True,autoincrement=True)
    user_id = db.Column(db.Integer,db.ForeignKey("user.user_id"),nullable=False)
    track_name = db.Column(db.String,nullable=False)
    track_desc = db.Column(db.String,nullable=False)
    track_type = db.Column(db.String,db.CheckConstraint("track_type in ('num','mcq','time','bool')"),nullable=False)
    options = db.Column(db.String,nullable=False)

class logs(db.Model):
    __tablename__ = 'logs'
    track_id = db.Column(db.Integer,db.ForeignKey("trackers.track_id"),nullable=False,primary_key=True)
    time = db.Column(db.DateTime,nullable=False,primary_key=True)
    info = db.Column(db.String,nullable=False)