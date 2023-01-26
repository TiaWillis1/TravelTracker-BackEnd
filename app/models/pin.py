from app import db


class Pin(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    profile_id = db.Column(db.Integer, db.ForeignKey('profile.id'))
    profile = db.relationship("Profile", back_populates="pins")
    longitude = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    location_name = db.Column(db.String, nullable=False)
    date = db.Column(db.Date)

    @classmethod
    def from_json(cls, req_body):
        return cls(
            longitude = req_body['longitude'],
            latitude = req_body['latitude'],
            location_name = req_body["location_name"],
            date = req_body["date"],

        )

    def to_dict_pins(self):
        return { "pin":{
                "id":self.id,
                "longitude": self.longitude,
                "latitude": self.latitude,
                "location_name": self.location_name,
                "date": self.date,
                }
                }


