import logging
from datetime import datetime

from flask import Flask, jsonify
from flask_restful import Resource, Api, reqparse, abort

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

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
    address = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(255), nullable=False, unique=True)
    __table_args__ = (db.UniqueConstraint('name', 'city', name='_name_city_uc'),)


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expiration_date = db.Column(db.DateTime, nullable=False)

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


class get_all_item_type_brand(Resource):
    """SELECT i.name, i.description, i.brand_id, b.name
    FROM item_type i JOIN brand b ON i.brand_id = b.id;

    create a json with this query then returns
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


class item_type_id(Resource):
    """For requests with an id
    methods: get, delete and patch

    the patch doesn't return anything, just updates the db
    """
    error_message = "ItemType id {} doesn't exists"

    def get(self, _id):
        query = ItemType.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        json_send = {}
        json_send[query.id] = {"name": query.name,
                               "description": query.description,
                               "brand_id": query.brand_id}
        return jsonify(json_send)

    def delete(self, _id):
        query = ItemType.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        db.session.delete(query)
        db.session.commit()
        json_send = {}
        json_send[query.id] = {"name": query.name,
                               "description": query.description,
                               "brand_id": query.brand_id}
        return jsonify(json_send)

    def patch(self, _id):
        query = ItemType.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))

        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str)
        parser.add_argument("description", type=str)
        parser.add_argument("brand_id", type=int, help="Must match an existing brand")
        document = parser.parse_args()

        name = document.get("name")
        description = document.get("description")
        brand_id = document.get("brand_id")

        if name:
            query.name = name
        if description:
            query.description = description
        if brand_id:
            if not Brand.query.get(brand_id):
                abort(404, message="brand_id {} doesn't exists".format(brand_id))
            query.brand_id = brand_id
        try:
            db.session.commit()
        except IntegrityError as ex:  # for constraint violation
            abort(400, message=str(ex))


class new_item_type(Resource):
    """Create a new entry with post method
    the name, description and brand_id must be in the json
    """
    parser = reqparse.RequestParser()
    parser.add_argument("name", type=str)
    parser.add_argument("description", type=str)
    parser.add_argument("brand_id", type=int, help="Must match an existing brand")

    def post(self):
        document = self.parser.parse_args(strict=True)
        name = document.get("name")
        description = document.get("description")
        brand_id = document.get("brand_id")

        query_brand = Brand.query.get(brand_id)
        if not query_brand:
            abort(404, message="brand_id {} doesn't exists".format(brand_id))

        item_type = ItemType(name=name, description=description, brand_id=brand_id)
        db.session.add(item_type)
        try:
            db.session.commit()
        except IntegrityError as ex:
            abort(400, message=str(ex))

        json_send = {}
        json_send[item_type.id] = {"name": name, "description": description, "brand_id": brand_id}
        return jsonify(json_send)


class brand_id(Resource):
    error_message = "Brand id {} doesn't exists"

    def get(self, _id):
        query = Brand.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        json_send = {}
        json_send[query.id] = {"name": query.name}
        return jsonify(json_send)

    def delete(self, _id):
        query = Brand.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        db.session.delete(query)
        db.session.commit()
        json_send = {}
        json_send[query.id] = {"name": query.name}
        return jsonify(json_send)

    def patch(self, _id):
        query = Brand.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))

        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str)
        document = parser.parse_args()

        name = document.get("name")

        if name:
            query.name = name
        try:
            db.session.commit()
        except IntegrityError as ex:  # for constraint violation
            abort(400, message=str(ex))


class new_brand(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument("name", type=str)

    def post(self):
        document = self.parser.parse_args(strict=True)
        name = document.get("name")

        brand = Brand(name=name)
        db.session.add(brand)
        try:
            db.session.commit()
        except IntegrityError as ex:
            abort(400, message=str(ex))

        json_send = {}
        json_send[brand.id] = {"name": name}
        return jsonify(json_send)


class location_id(Resource):
    error_message = "Location id {} doesn't exists"

    def get(self, _id):
        query = Location.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        json_send = {}
        json_send[query.id] = {"name": query.name, "address": query.address, "city": query.city}
        return jsonify(json_send)

    def delete(self, _id):
        query = Location.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        db.session.delete(query)
        db.session.commit()
        json_send = {}
        json_send[query.id] = {"name": query.name, "address": query.address, "city": query.city}
        return jsonify(json_send)

    def patch(self, _id):
        query = Location.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))

        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str)
        parser.add_argument("address", type=str)
        parser.add_argument("city", type=str)
        document = parser.parse_args()

        name = document.get("name")
        address = document.get("address")
        city = document.get("city")

        if name:
            query.name = name
        if address:
            query.address = address
        if city:
            query.city = city
        try:
            db.session.commit()
        except IntegrityError as ex:  # for constraint violation
            abort(400, message=str(ex))


class new_location(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument("name", type=str)
    parser.add_argument("address", type=str)
    parser.add_argument("city", type=str)

    def post(self):
        document = self.parser.parse_args(strict=True)
        name = document.get("name")
        address = document.get("address")
        city = document.get("city")

        location = Location(name=name, address=address, city=city)
        db.session.add(location)
        try:
            db.session.commit()
        except IntegrityError as ex:
            abort(400, message=str(ex))

        json_send = {}
        json_send[location.id] = {"name": name, "address": address, "city": city}
        return jsonify(json_send)


class item_id(Resource):
    error_message = "Item id {} doesn't exists"

    def get(self, _id):
        query = Item.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        json_send = {}
        json_send[query.id] = {"created_at": query.created_at,
                               "expiration_date": query.expiration_date,
                               "item_type_id": query.item_type_id,
                               "location_id": query.location_id}
        return jsonify(json_send)

    def delete(self, _id):
        query = Item.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))
        db.session.delete(query)
        db.session.commit()
        json_send = {}
        json_send[query.id] = {"created_at": query.created_at,
                               "expiration_date": query.expiration_date,
                               "item_type_id": query.item_type_id,
                               "location_id": query.location_id}
        return jsonify(json_send)

    def patch(self, _id):
        query = Item.query.get(_id)
        if not query:
            abort(404, message=self.error_message.format(_id))

        parser = reqparse.RequestParser()
        parser.add_argument("expiration_date", type=datetime.date)
        parser.add_argument("item_type_id", type=int)
        parser.add_argument("location_id", type=int)
        document = parser.parse_args()

        expiration_date = document.get("expiration_date")
        item_type_id = document.get("item_type_id")
        location_id = document.get("location_id")

        if expiration_date:
            query.expiration_date = expiration_date
        if item_type_id:
            query.item_type_id = item_type_id
        if location_id:
            query.location_id = location_id
        try:
            db.session.commit()
        except IntegrityError as ex:  # for constraint violation
            abort(400, message=str(ex))


class new_item(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument("expiration_date", type=datetime.date)
    parser.add_argument("item_type_id", type=int, help="Must match an existing item_type")
    parser.add_argument("location_id", type=int, help="Must match an existing location")

    def post(self):
        document = self.parser.parse_args(strict=True)
        expiration_date = document.get("expiration_date")
        item_type_id = document.get("item_type_id")
        location_id = document.get("location_id")

        query_item_type = ItemType.query.get(item_type_id)
        if not query_item_type:
            abort(404, message="item_type_id {} doesn't exists".format(item_type_id))
        query_location = Location.query.get(location_id)
        if not query_location:
            abort(404, message="location_id {} doesn't exists".format(location_id))

        item = Item(expiration_date=expiration_date, item_type_id=item_type_id, location_id=location_id)
        db.session.add(item)
        try:
            db.session.commit()
        except IntegrityError as ex:
            abort(400, message=str(ex))

        json_send = {}
        json_send[item.id] = {"created_at": item.created_at,
                              "expiration_date": item.expiration_date,
                              "item_type_id": item.item_type_id,
                              "location_id": item.location_id}
        return jsonify(json_send)


api.add_resource(get_all_item_type_brand, "/all_item_type_brand")
api.add_resource(item_type_id, "/id_item_type/<_id>")
api.add_resource(new_item_type, "/new_item_type")
api.add_resource(brand_id, "/id_brand/<_id>")
api.add_resource(new_brand, "/new_brand")
api.add_resource(location_id, "/id_location/<_id>")
api.add_resource(new_location, "/new_location")
api.add_resource(item_id, "/id_item/<_id>")
api.add_resource(new_item, "/new_item")
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
