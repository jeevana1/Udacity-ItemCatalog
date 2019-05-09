from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, Item, User

engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)

session = DBSession()
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

category1 = Category(user_id=1,name="Cricket")

session.add(category1)
session.commit()

#Menu

item1 = Item(user_id=1,name="Bat",description="Light weight and comfortable for both handed",category_name='Cricket',category=category1,category_id = category1.id)
session.add(item1)
session.commit()