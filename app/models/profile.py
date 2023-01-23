from app import db


class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String)
    cards = db.relationship("Pin", back_populates="profile")


# reference for method
#     @classmethod
# def from_dict(cls, board_data):
#     new_board = Board(title=board_data["title"],
#                 owner_name=board_data["owner_name"])
#     return new_board