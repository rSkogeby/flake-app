#!/usr/bin/env python3
"""Restaurant menu app for the browser."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, render_template, request, redirect,\
                  url_for, flash, jsonify, make_response
from flask import session as login_session
from werkzeug.datastructures import ImmutableMultiDict
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import random, string
import requests
import copy

from db_setup import Base, Restaurant, MenuItem, User

CLIENT_ID = json.loads(
        open('client_secrets.json', 'r').read()
    )['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"


app = Flask(__name__)
engine = create_engine('sqlite:///restaurantmenuwithusers.db',
                       connect_args={'check_same_thread': False})
Base.metadata.bind = engine


def getUserID(email):
    """Fetch user ID if in DB, else return None."""
    try:
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


def getUserInfo(user_id):
    """Fetch stored info on user."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    user = session.query(User).filter_by(id=user_id).one()
    return user


def createUser(login_session):
    """Add new user to DB."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


@app.route('/privacypolicy/')
def privacyPolicy():
    return render_template('privacy')


@app.route('/login/', methods=['GET', 'POST'])
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/logout/', methods=['GET'])
def showLogout():
    return redirect(url_for('gdisconnect'))


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    # Exchange client token for long-lived server-side token with 
    # GET /oauth/access_token?grant_type=fb_exchange_token&client_id=
    # {app-id}&client_secret={app-secret}&fb_exchange_token={short-lived-token}
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=\
           {}&client_secret={}&fb_exchange_token={}'.\
           format(app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # Use token to get user info from API.
    userinfo_url = 'https://graph.facebook.com/v2.2/me'
    # Strip expire tag from access token.
    token = result.split(',')[0].split(':')[1].replace('"', '')
    url = 'https://graph.facebook.com/v2.8/me?access_token={}&fields=name,id,email'.format(token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data['name']
    login_session['email'] = data['email']
    login_session['facebook_id'] = data['id']
    login_session['access_token'] = token
    # Get user picture
    url = 'https://graph.facebook.com/v2.2/me/picture?{}\
           &redirect=0&height=200&width=200'.format(token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['picture'] = data['data']['url']
    # Check if user exists
    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id
    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash('You are now logged in as {}'.format(login_session['username']))
    print("done!")
    return output




@app.route('/gconnect', methods=['POST'])
def gconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    code = request.data
    try:
        # Upgrade the authorisation code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the\
            authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Check that access token is valid
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'.\
        format(access_token))
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') != None:
        response = make_response(json.dumps(result.get('error')), 501)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401
        )
        response.headers['Content-Type'] = 'application/json'
        return response
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's ID."), 401
        )
        print("Token's client ID doesn't match app's.")
        response.headers['Content-Type'] = 'application/json'
        return response
    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials != None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps("Current user is already connected."), 200
        )
        response.headers['Content-Type'] = 'application/json'
        return response
    # Store the access token in session for later use
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id
    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['provider'] = 'google'
    login_session['username'] = data['email']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # See if user exists if it doesn't, create a new one.

    user_id = getUserID(data['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash('You are now logged in as {}'.format(login_session['username']))
    print("done!")
    return output


def isEmpty(inp):
    """Return true if dict is empty, false if not."""
    empty = ''
    if isinstance(inp, ImmutableMultiDict):
        for k, v in inp.items():
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


@app.route('/disconnect', methods=['POST'])
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['credentials']
            del login_session['gplus_id']
        if login_session['provider'] == 'facebook':
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
    else:
        flash("You were not logged in to begin with!")
    return redirect(url_for('showRestaurants'))

@app.route('/fbdisconnect', methods=['POST'])
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/{}/permissions?access_token={}'.format(facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    response = make_response(json.dumps('Successfully disconnected.'), 200)
    response.headers['Content-Type'] = 'application/json'
    return response



@app.route('/gdisconnect', methods=['POST'])
def gdisconnect():
    access_token = login_session.get('credentials')
    if access_token is None:
        response = make_response(json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
            'Failed to revoke token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/restaurants/')
def showRestaurants():
    """Show list of restaurants."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant_list = session.query(Restaurant).all()
    if 'username' not in login_session:
        return render_template('publicshowrestaurants.html',
                           restaurant_list=restaurant_list)
    else:
        return render_template('showrestaurants.html',
                           restaurant_list=restaurant_list)


# All menus
@app.route('/restaurant/<int:restaurant_id>/')
def showMenu(restaurant_id):
    """Display a restaurant's menu."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    creator = getUserInfo(restaurant.user_id)
    items = session.query(MenuItem).filter_by(restaurant_id=restaurant_id).all()
    if 'username' not in login_session or\
        creator.id != login_session.get('user_id'):
        return render_template('publicshowmenu.html', restaurant=restaurant,
                               items=items, creator=creator)
    else:
        return render_template('showmenu.html', restaurant=restaurant,
                               items=items, creator=creator)


@app.route('/restaurant/new/', methods=['GET', 'POST'])
def newRestaurant():
    """Create new restaurant."""
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        DBSession = sessionmaker(bind=engine)
        session = DBSession()
        newRestaurant = Restaurant(name=request.form['name'], 
            user_id=login_session['user_id'])
        session.add(newRestaurant)
        session.commit()
        flash('New restaurant created!')
        return redirect(url_for('showRestaurants'),
                        code=301)
    elif request.method == 'GET':
        return render_template('newrestaurant.html')
    else:
        return redirect(url_for('showRestaurants'),
                        code=301)


@app.route('/restaurant/<int:restaurant_id>/delete/', methods=['GET', 'POST'])
def deleteRestaurant(restaurant_id):
    """Delete menu entry."""
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    deletion_item = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if deletion_item.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to delete this restaurant. Please create your own restaurant in order to delete.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(deletion_item)
        session.commit()
        flash('{} has been deleted'.format(deletion_item.name))
        return redirect(url_for('showRestaurants'), code=301)
    elif request.method == 'GET':
        return render_template('deleterestaurant.html', item=deletion_item)


@app.route('/restaurant/<int:restaurant_id>/edit/', methods=['GET', 'POST'])
def editRestaurant(restaurant_id):
    """Edit restaurant name."""
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    edited_restaurant = session.query(Restaurant).\
        filter_by(id=restaurant_id).one()
    old = copy.deepcopy(edited_restaurant)
    flash_string = ''
    if edited_restaurant.user_id != login_session['user_id']:
        return "<script>function myFunction() {alert('You are not authorized to edit this restaurant. Please create your own restaurant in order to edit.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if isEmpty(request.form):
            return redirect(url_for('showMenu', restaurant_id=restaurant_id))
        if isEmpty(request.form['name']) is False:
            edited_restaurant.name = request.form['name']
            flash_string += 'Name: {}->{} '.format(old.name,
                                                   edited_restaurant.name)
        session.add(edited_restaurant)
        session.commit()
        flash('{} has been edited: {}'.format(edited_restaurant.name,
                                              flash_string))
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    elif request.method == 'GET':
        return render_template('editrestaurant.html',
                               restaurant=edited_restaurant)


@app.route('/restaurant/<int:restaurant_id>/new/', methods=['GET', 'POST'])
def newMenuItem(restaurant_id):
    """Create new menu entry."""
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    if login_session['user_id'] != restaurant.user_id:
        return "<script>function myFunction() {alert('You are not authorized to add menu items to this restaurant. Please create your own restaurant in order to add items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           restaurant_id=restaurant_id,
                           user_id=restaurant.user_id)
        session.add(newItem)
        session.commit()
        flash('New menu item created!')
        return redirect(url_for('showMenu', restaurant_id=restaurant_id),
                        code=301)
    elif request.method == 'GET':
        return render_template('newmenuitem.html', restaurant_id=restaurant_id)
    else:
        return redirect(url_for('showMenu', restaurant_id=restaurant_id), 
            code=301)



@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/edit/',
           methods=['GET', 'POST'])
def editMenuItem(restaurant_id, menu_id):
    """Edit menu entry."""
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    edited_menu_item = session.query(MenuItem).\
        filter_by(id=menu_id, restaurant_id=restaurant_id).one()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    old = copy.deepcopy(edited_menu_item)
    flash_string = ''
    if login_session['user_id'] != restaurant.user_id:
        return "<script>function myFunction() {alert('You are not authorized to edit menu items to this restaurant. Please create your own restaurant in order to edit items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        if isEmpty(request.form):
            return redirect(url_for('showMenu', restaurant_id=restaurant_id))
        if isEmpty(request.form['name']) is False:
            edited_menu_item.name = request.form['name']
            flash_string += 'Name: {}->{} '.\
                format(old.name, edited_menu_item.name)
        if isEmpty(request.form['description']) is False:
            edited_menu_item.description = request.form['description']
            flash_string += 'Description: {}->{} '.\
                format(old.description, edited_menu_item.description)
        if isEmpty(request.form['price']) is False:
            edited_menu_item.price = request.form['price']
            flash_string += 'Price: {}->{} '.\
                format(old.price, edited_menu_item.description)
        session.add(edited_menu_item)
        session.commit()

        flash('{} has been edited: {}'.format(edited_menu_item.name,
                                              flash_string))
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    elif request.method == 'GET':
        return render_template('editmenuitem.html',
                               restaurant_id=restaurant_id,
                               menu_id=menu_id,
                               i=edited_menu_item)


@app.route('/restaurant/<int:restaurant_id>/<int:menu_id>/delete/',
           methods=['GET', 'POST'])
def deleteMenuItem(restaurant_id, menu_id):
    """Delete menu entry."""
    if 'username' not in login_session:
        return redirect('/login')
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    deletion_item = session.query(MenuItem).\
        filter_by(id=menu_id, restaurant_id=restaurant_id).one()
    if login_session['user_id'] != restaurant.user_id:
        return "<script>function myFunction() {alert('You are not authorized to delete menu items to this restaurant. Please create your own restaurant in order to delete items.');}</script><body onload='myFunction()''>"
    if request.method == 'POST':
        session.delete(deletion_item)
        session.commit()
        flash('{} has been deleted'.format(deletion_item.name))
        return redirect(url_for('showMenu', restaurant_id=restaurant_id))
    elif request.method == 'GET':
        return render_template('deletemenuitem.html', item=deletion_item)


# API endpoint
@app.route('/restaurants/JSON/')
def showRestaurantsJSON():
    """API endpoint for displaying the restaurants."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurants = session.query(Restaurant).all()
    return jsonify(Restaurants=[i.serialize for i in restaurants])


# API endpoint
@app.route('/restaurant/<int:restaurant_id>/menu/JSON/')
def restaurantMenuJSON(restaurant_id):
    """API endpoint for displaying the menu of a restaurant."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    items = session.query(MenuItem).\
        filter_by(restaurant_id=restaurant.id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


# API endpoint
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON/')
def menuItemJSON(restaurant_id, menu_id):
    """API endpoint for displaying a menu item."""
    DBSession = sessionmaker(bind=engine)
    session = DBSession()
    restaurant = session.query(Restaurant).filter_by(id=restaurant_id).one()
    item = session.query(MenuItem).filter_by(id=menu_id).one()
    return jsonify(MenuItem=item.serialize)


if __name__ == "__main__":
    app.secret_key = 'a_very_secret_key'
    app.run(host='localhost', port=5000, debug=True)
