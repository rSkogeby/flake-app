from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask
app = Flask(__name__) 

from db_setup import Base, Restaurant, MenuItem

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/restaurant/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant.id)
    output = ''
    for item in items:
        output += '<p>'
        output += item.name
        output += '<br />'
        output += item.description
        output += '<br />'
        output += item.price
        output += '<br />'
        output += '</p>'
    return output


# Create route for newMenuItem function 
def newMenuItem(restaurant_id):
    return "page to create a new menu item. Task 1 complete!"


# Create route for editMenuItem function 
def editMenuItem(restaurant_id, menu_id):
    return "page to edit a menu item. Task 2 complete!"


# Create a route for deleteMenuItem function
def deleteMenuItem(restaurant_id, menu_id):
    return "page to delete a menu item. Task 3 complete!"


if __name__ == "__main__":
    app.debug = True
    app.run(host='127.0.0.1', port=5000)