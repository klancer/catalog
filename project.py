from flask import (
     Flask,
     render_template,
     request,
     redirect,
     jsonify,
     url_for,
     flash
)
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import scoped_session, sessionmaker
from database_setup import Base, Store, MenuItem, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
import re

app = Flask(__name__)

CLIENT_ID = json.loads(open('client_secrets.json',
                            'r').read())['web']['client_id']
APPLICATION_NAME = "Store Menu Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///storemenuwithusers.db')
Base.metadata.bind = engine

session = scoped_session(sessionmaker(bind=engine))


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    access_token = request.data
    print "access token received %s " % access_token
    app_id = json.loads(open('fb_client_secrets.json',
                             'r').read())['web']['app_id']
    app_secret = json.loads(open('fb_client_secrets.json',
                                 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (app_id, app_secret, access_token)  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    # Use token to get user info from API
    userinfo_url = "https://graph.facebook.com/v3.1/me"
    '''
        Due to the formatting for the result from the server
token exchange we have to split the token first on commas and
select the first index which gives us the key : value for the
server access token then we split it on colons to pull out the
actual token value and replace the remaining quotes with nothing
so that it can be used directly in the graph api calls
    '''
    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v3.1/me?access_token=%s&fields=name,id,email' % token  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    # print "url sent for API access:%s"% url
    # print "API JSON result: %s" % result
    data = json.loads(result)
    login_session['provider'] = 'facebook'
    login_session['username'] = data["name"]
    login_session['email'] = data["email"]
    login_session['facebook_id'] = data["id"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v3.1/me/picture?access_token=%s&redirect=0&height=200&width=200' % token  # noqa
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]
    data = json.loads(result)
    login_session['picture'] = data["data"]["url"]
    # see if user exists
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']

    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;\
border-radius: 150px;-webkit-border-radius: 150px;\
-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' \
          % (facebook_id, access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user \
                   is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    # ADD PROVIDER TO LOGIN SESSION
    login_session['provider'] = 'google'

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(data["email"])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px; \
              border-radius: 150px; -webkit-border-radius: 150px; \
              -moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:  # noqa
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
    # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(json.dumps('Current user \
                   not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' \
          % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully \
                   disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps('Failed to revoke \
                   token for given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Store Information
@app.route('/store/<int:store_id>/menu/JSON')
def storeMenuJSON(store_id):
    store_id1 = str(store_id)
    if not re.match(r"\d+", store_id1):
        response = make_response(json.dumps('store_id incorect'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        store = session.query(Store).filter_by(id=store_id).one()
        items = session.query(MenuItem).filter_by(
            store_id=store_id).all()
        return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/store/<int:store_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(store_id, menu_id):
    store_id1 = str(store_id)
    if not re.match(r"\d+", store_id1):
        response = make_response(json.dumps('store_id incorect'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        Menu_Item = session.query(MenuItem).filter_by(id=menu_id).one()
        return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/store/JSON')
def storesJSON():
    stores = session.query(Store).all()
    return jsonify(stores=[r.serialize for r in stores])


# Show all stores
@app.route('/')
@app.route('/store/')
def showStores():
    stores = session.query(Store).order_by(asc(Store.name))
    if 'username' not in login_session:
        return render_template('publicstores.html', stores=stores)
    else:
        return render_template('stores.html', stores=stores)

# Create a new store


@app.route('/store/new/', methods=['GET', 'POST'])
def newStore():
    if 'username' not in login_session:
        return redirect('/login')
        if request.method == 'POST':
            newStore = Store(
                   name=request.form['name'],
                   user_id=login_session['user_id'])
            session.add(newStore)
            session.commit()
            flash('New Store %s Successfully Created' % newStore.name)
            return redirect(url_for('showStores'))
    else:
        return render_template('newStore.html')

# Edit a store


@app.route('/store/<int:store_id>/edit/', methods=['GET', 'POST'])
def editStore(store_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedStore = session.query(Store).filter_by(id=store_id).one()
    if editedStore.user_id != login_session['user_id']:
        return "<script>function myFunction(){alert('You are not \
                authorized to edit this store. Please create your \
                own store in order to edit.');}</script>\
                <body onload='myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            name1 = request.form['name']
            if name1 == ' ':
                flash("Name field cannot be empty")
                return redirect(url_for('showStores'))
            else:
                editedStore.name = request.form['name']
                session.add(editedStore)
                session.commit()
                flash('Store Successfully Edited %s' % editedStore.name)
            return redirect(url_for('showStores'))
    else:
        return render_template('editStore.html', store=editedStore)


# Delete a store

@app.route('/store/<int:store_id>/delete/', methods=['GET', 'POST'])
def deleteStore(store_id):
    if 'username' not in login_session:
        return redirect('/login')
    storeToDelete = session.query(
        Store).filter_by(id=store_id).one()
    if storeToDelete.user_id != login_session['user_id']:
        return "<script>function myFunction(){alert('You are not \
                authorized to delete this store. Please create your \
                own store in order to delete.');} </script>\
                <body onload='myFunction()'>"
    if request.method == 'POST':
        session.delete(storeToDelete)
        session.commit()
        flash('%s Successfully Deleted' % storeToDelete.name)
        return redirect(url_for('showStores', store_id=store_id))
    else:
        return render_template('deleteStore.html', store=storeToDelete)

# Show a store menu


@app.route('/store/<int:store_id>/')
@app.route('/store/<int:store_id>/menu/')
def showMenu(store_id):
    store = session.query(Store).filter_by(id=store_id).one()
    creator = getUserInfo(store.user_id)
    items = session.query(MenuItem).filter_by(
        store_id=store_id).all()
    if 'username' not in login_session or \
       creator.id != login_session['user_id']:
        return render_template('publicmenu.html', items=items,
                               store=store, creator=creator)
    else:
        return render_template('menu.html', items=items,
                               store=store, creator=creator)


# Create a new menu item

@app.route('/store/<int:store_id>/menu/new/', methods=['GET', 'POST'])
def newMenuItem(store_id):
    if 'username' not in login_session:
        return redirect('/login')
    store = session.query(Store).filter_by(id=store_id).one()
    if login_session['user_id'] != store.user_id:
        return "<script>function myFunction() {alert('You are not \
                authorized to add menu items to this store. \
                Please create your own store in order to add \
                items.');}</script><body onload='myFunction()'>"
    if request.method == 'POST':
        newItem = MenuItem(name=request.form['name'],
                           description=request.form['description'],
                           price=request.form['price'],
                           product=request.form['product'],
                           store_id=store_id,
                           user_id=store.user_id)
        session.add(newItem)
        session.commit()
        flash('New Menu %s Item Successfully Created' % (newItem.name))
        return redirect(url_for('showMenu', store_id=store_id))
    else:
        return render_template('newmenuitem.html', store_id=store_id)
    return render_template('newmenuitem.html', store_id=store)

# Edit a menu item


@app.route('/store/<int:store_id>/menu/<int:menu_id>/edit',
           methods=['GET', 'POST'])
def editMenuItem(store_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    editedItem = session.query(MenuItem).filter_by(id=menu_id).one()
    store = session.query(Store).filter_by(id=store_id).one()
    if login_session['user_id'] != store.user_id:
        return "<script>function myFunction() {alert ('You are not \
                authorized to edit menu items to this store. Please \
                create your own store in order to \
                edit items.');}</script><body onload = 'myFunction()'>"
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['product']:
            editedItem.product = request.form['product']
        session.add(editedItem)
        session.commit()
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showMenu', store_id=store_id))
    else:
        return render_template('editmenuitem.html', store_id=store_id,
                               menu_id=menu_id, item=editedItem)


# Delete a menu item

@app.route('/store/<int:store_id>/menu/<int:menu_id>/delete',
           methods=['GET', 'POST'])
def deleteMenuItem(store_id, menu_id):
    if 'username' not in login_session:
        return redirect('/login')
    store = session.query(Store).filter_by(id=store_id).one()
    itemToDelete = session.query(MenuItem).filter_by(id=menu_id).one()
    if login_session['user_id'] != store.user_id:
        return "<script>function myFunction() {alert('You are not \
                authorized to delete menu items to this store. \
                Please create your own store in order to delete \
                items.');}</script><body onload = 'myFunction()'>"
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showMenu', store_id=store_id))
    else:
        return render_template('deleteMenuItem.html', item=itemToDelete)


# Disconnect based on provider

@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        if login_session['provider'] == 'google':
            gdisconnect()
            del login_session['gplus_id']
            del login_session['access_token']
        if login_session['provider'] == 'facebook':
            fbdisconnect()
            del login_session['facebook_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showStores'))
    else:
        flash("You were not logged in")
        return redirect(url_for('showStores'))


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
