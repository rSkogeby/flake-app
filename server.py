from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, render_template, request, redirect, url_for
app = Flask(__name__) 

from db_setup import Base, Restaurant, MenuItem

engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/restaurant/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return render_template('menu.html', restaurant=restaurant, items=items)


# Create route for newMenuItem function
@app.route('/restaurant/<int:restaurant_id>/create/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           restaurant_id=restaurant_id)
        session.add(newItem)
        session.commit()
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id),
                        code=301)
    elif request.method == 'GET':
        return render_template('newmenuitem.html', restaurant_id=
            restaurant_id)
    else:
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id),
                        code=301)


# Create route for editMenuItem function
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/', methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    edited_menu_item = session.query(MenuItem).filter_by(id=menu_id).one()
    if request.method == 'POST':
        pass #Edit fields, name, price, description
    session.add(edited_menu_item)
    session.commit()
    return redirect(url_for(restaurantMenu, restaurant_id=restaurant_id))

# Create a route for deleteMenuItem function
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/')
def deleteMenuItem(restaurant_id, menu_id):
    return "page to delete a menu item. Task 3 complete!"


if __name__ == "__main__":
    app.debug = True
    app.run(host='127.0.0.1', port=5000)
