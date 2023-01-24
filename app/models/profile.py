from app import db


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String)
    cards = db.relationship("Pin", back_populates="profile")
    name = db.Column(db.String) 