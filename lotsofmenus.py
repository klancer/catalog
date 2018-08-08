from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Store, Base, MenuItem, User

engine = create_engine('sqlite:///storemenuwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Lance Ko",
             email="klancer747@gmail.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')  # noqa
session.add(User1)
session.commit()

# Menu for UrbanBurger
store1 = Store(user_id=1, name="Octagon Store")

session.add(store1)
session.commit()

menuItem2 = MenuItem(user_id=1,
                     name="Dell XPS 15 Laptop",
                     description="Small 15-inch laptop packs powerhouse \
                     performance and a stunning InfinityEdge display \
                     with an optional touch screen",
                     price="$1000.50",
                     product="Computer",
                     store=store1)

session.add(menuItem2)
session.commit()


menuItem1 = MenuItem(user_id=1,
                     name="Samsung Galaxy S7",
                     description="Hugely powerful processor (Exynos in \
                     Europe, Snapdragon in US), Excellent speed at opening \
                     and closing apps, TouchWiz interface is refined again, \
                     and is much slicker, MicroSD slot is back for \
                     expanded memory",
                     price="$600.00",
                     product="Mobile",
                     store=store1)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(user_id=1,
                     name="Netgear router",
                     description="Netgear NightHawk router",
                     price="$200",
                     product="Network",
                     store=store1)

session.add(menuItem2)
session.commit()

menuItem3 = MenuItem(user_id=1,
                     name="Anker PowerLine 3ft Micro USB",
                     description="Durable Charging Cable, with Aramid \
                     Fiber and 5000+ Bend Lifespan for Samsung, Nexus, \
                     LG, Motorola, Android Smartphones and More",
                     price="$25.00",
                     product="Accessory",
                     store=store1)

session.add(menuItem3)
session.commit()

store2 = Store(user_id=1, name="eCircuit Store")
session.add(store2)
session.commit()

menuItem4 = MenuItem(user_id=1,
                     name="TP-Link Router AC1750",
                     description="TP-Link AC1750 Smart WiFi Router - \
                     Dual Band.",
                     price="$40.00",
                     product="Network",
                     store=store2)
session.add(menuItem4)
session.commit()

print "added menu items!"
