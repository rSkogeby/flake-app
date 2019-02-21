from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.datastructures import ImmutableMultiDict
app = Flask(__name__) 
import copy

from db_setup import Base, Restaurant, MenuItem

engine = create_engine('sqlite:///restaurantmenu.db', connect_args={'check_same_thread': False})
Base.metadata.bind = engine


def isEmpty(inp):
    """Return true if dict is empty, false if not."""
    empty = ''
    if isinstance(inp, ImmutableMultiDict):
        for k,v in inp.items():
            if v is empty:
                continue
            return False
        return True
    else:
        for item in inp:
            if item is empty:                
                continue
            return False
        return True

@app.route('/restaurant/<int:restaurant_id>/')
def restaurantMenu(restaurant_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant.id)
    return render_template('menu.html', restaurant=restaurant, items=items)


# Create route for newMenuItem function
@app.route('/restaurant/<int:restaurant_id>/create/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    if request.method == 'POST':
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           restaurant_id=restaurant_id)
        session.add(newItem)
        session.commit()
        flash('New menu item created!')
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
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    edited_menu_item = session.query(MenuItem).filter_by(id=menu_id, restaurant_id=restaurant_id).one()
    old = copy.deepcopy(edited_menu_item)
    flash_string = ''
    if request.method == 'POST':
        if isEmpty(request.form):
            return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
        if isEmpty(request.form['name']) == False:
            edited_menu_item.name=request.form['name']
            flash_string += 'Name: {}->{} '.format(old.name, edited_menu_item.name)
        if isEmpty(request.form['description']) == False:
            edited_menu_item.description=request.form['description']
            flash_string += 'Description: {}->{} '.format(old.description, edited_menu_item.description)
        if isEmpty(request.form['price']) == False:
            edited_menu_item.price=request.form['price']
            flash_string += 'Price: {}->{} '.format(old.price, edited_menu_item.description)
        session.add(edited_menu_item)
        session.commit()

        flash('{} has been edited: {}'.format(edited_menu_item.name, flash_string))
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    elif request.method == 'GET':
        return render_template('editmenuitem.html', restaurant_id=restaurant_id, 
                                                    menu_id=menu_id,
                                                    i=edited_menu_item)


# Create a route for deleteMenuItem function
@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/', methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    deletion_item = session.query(MenuItem).filter_by(id=menu_id, restaurant_id=restaurant_id).one()
    if request.method == 'POST':
        session.delete(deletion_item)
        session.commit()
        flash('{} has been deleted'.format(deletion_item.name))
        return redirect(url_for('restaurantMenu', restaurant_id=restaurant_id))
    elif request.method == 'GET':
        return render_template('deletemenuitem.html', item=deletion_item)
    

if __name__ == "__main__":
    app.secret_key = 'a_very_secret_key'
    app.debug = True
    app.run(host='127.0.0.1', port=5000)
