from app import db


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sub = db.Column(db.Integer)
    pins = db.relationship("Pin", back_populates="profile")
    name = db.Column(db.String) 

    @classmethod 
    def from_json(cls, req_body):
        return cls(
            sub = req_body["sub"], 
            name = req_body["name"],
        )