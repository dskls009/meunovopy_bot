from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from variaveis import DATABASE

app = Flask(__name__)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE

db = SQLAlchemy(app)

db.init_app

class Awa_Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(255))
    chat_id = db.Column(db.String(255))