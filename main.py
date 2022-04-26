import os
from flask import Flask
from app.models import db, DB_NAME, user
from flask_login import LoginManager


current_dir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)
app.config['SECRET_KEY'] = 'this is a secret key'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///" + os.path.join(current_dir,DB_NAME)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
db.init_app(app)


if not os.path.exists(os.path.join(current_dir,DB_NAME)):
    db.create_all(app=app)
    print(db.create_all(app=app))

app.app_context().push()

from app.controllers import *

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)
@login_manager.user_loader
def load_user(user_id):
    return user.query.get(int(user_id))



if __name__ == "__main__":
  app.run(
    host="0.0.0.0",
    debug=True,
    port=8080
  )