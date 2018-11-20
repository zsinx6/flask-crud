import logging
from datetime import datetime

from flask import Flask, request, jsonify  # noqa
from flask_restful import Resource, Api

from flask_sqlalchemy import SQLAlchemy

_formatter = '%(levelname)-8s : %(module)-10s : %(funcName)-25s :%(lineno)-3d : %(message)s'
_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format=_formatter)


app = Flask(__name__)
DB_PARAM = 'postgresql+psycopg2://{user}@{url}/{db}'.format(user="lucas", url="localhost:5432", db="test")
app.config['SQLALCHEMY_DATABASE_URI'] = DB_PARAM
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # silence the deprecation warning
app.config['JSON_AS_ASCII'] = False
api = Api(app)
db = SQLAlchemy(app)


class Brand(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(60), nullable=False, unique=True)


class ItemType(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    brand_id = db.Column(db.Integer, db.ForeignKey("brand.id"), nullable=False)
    brand = db.relationship("Brand", backref=db.backref("itemtypes", lazy=True))
    __table_args__ = (db.UniqueConstraint('name', 'brand_id', name='_type_brand_uc'),)


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, unique=True)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    item_type_id = db.Column(db.Integer, db.ForeignKey("item_type.id"), nullable=False)
    item_type = db.relationship("ItemType", backref=db.backref("items", lazy=True))
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), nullable=False)
    location = db.relationship("Location", backref=db.backref("items", lazy=True))


@app.cli.command()
def resetdb():
    """Destroys and creates the database + tables"""

    from sqlalchemy_utils import database_exists, create_database, drop_database
    if database_exists(DB_PARAM):
        drop_database(DB_PARAM)
    if not database_exists(DB_PARAM):
        create_database(DB_PARAM)

    db.create_all()


class get_all_item_type(Resource):
    """SELECT i.name, i.description, i.brand_id, b.name
    FROM item_type i JOIN brand b ON i.brand_id = b.id;

    create a json with this query then send
    """
    def get(self):
        query = (db.session.query(ItemType.name,
                                  ItemType.description,
                                  ItemType.brand_id,
                                  Brand.name.label("brand_name"),
                                  ItemType.id)
                 .join(Brand, Brand.id == ItemType.brand_id)
                 .order_by(ItemType.name).all())

        json_send = {}
        for result in query:
            json_send[result.id] = {"name": result.name,
                                    "description": result.description,
                                    "brand_id": result.brand_id,
                                    "brand_name": result.brand_name}
        return jsonify(json_send)


api.add_resource(get_all_item_type, "/item_type")
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
