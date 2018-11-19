from crud import Brand, ItemType, Location, Item, db

brand_nestle = Brand(name="Nestlé")
db.session.add(brand_nestle)
brand_crystal = Brand(name="Crystal")
db.session.add(brand_crystal)
db.session.commit()

agua1 = ItemType(name="Água", description="garrafa 500ml", brand_id=Brand.query.get(1).id)
db.session.add(agua1)
agua2 = ItemType(name="Água", description="garrafa 500ml", brand_id=Brand.query.get(2).id)
db.session.add(agua2)
db.session.commit()
