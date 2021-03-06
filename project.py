from flask import Flask,render_template,request,redirect,url_for,jsonify,flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Category, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(
    open('client_secret.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Restaurant Menu Application"

app = Flask(__name__)
# Connect to Database and create database session
engine = create_engine('sqlite:///itemcatalog.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)

@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response 
    access_token = request.data

    print access_token
    app_id = json.loads(open('fb_client_secrets.json', 'r').read())[
        'web']['app_id']
    app_secret = json.loads(
        open('fb_client_secrets.json', 'r').read())['web']['app_secret']
    url = 'https://graph.facebook.com/oauth/access_token?grant_type=fb_exchange_token&client_id=%s&client_secret=%s&fb_exchange_token=%s' % (
        app_id, app_secret, access_token)
    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    token = result.split(',')[0].split(':')[1].replace('"', '')

    url = 'https://graph.facebook.com/v2.8/me?access_token=%s&fields=name,id,email' % token

    h = httplib2.Http()
    result = h.request(url, 'GET')[1]

    data = json.loads(result)
    login_session['provider'] = "facebook"
    login_session['username'] = data['name']
    login_session['facebook_id'] = data["id"]
    login_session['email'] = data["email"]

    # The token must be stored in the login_session in order to properly logout
    login_session['access_token'] = token

    # Get user picture
    url = 'https://graph.facebook.com/v2.8/me/picture?access_token=%s&redirect=0&height=200&width=200' % token
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
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '

    flash("Now logged in as %s" % login_session['username'])
    return output


@app.route('/fbdisconnect')
def fbdisconnect():
    facebook_id = login_session['facebook_id']
    # The access token must me included to successfully logout
    access_token = login_session['access_token']
    url = 'https://graph.facebook.com/%s/permissions?access_token=%s' % (facebook_id,access_token)
    h = httplib2.Http()
    result = h.request(url, 'DELETE')[1]
    return "you have been logged out"


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
        return redirect(url_for('catalogMenu'))
    else:
        flash("You were not logged in")
        return redirect(url_for('catalogMenu'))


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data
    print "hello"
    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secret.json', scope='')
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
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
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

    login_session['provider'] = 'google'
    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

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
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output

# User Helper Functions


def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
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
    except:
        return None


# DISCONNECT - Revoke a current user's token and reset their login_session
@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]

    if result['status'] == '200':
        # Reset the user's sesson.
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/')
@app.route('/showCategories/')
def catalogMenu():
    catalogItems = session.query(Category).all()
    return render_template('newMenu.html', items = catalogItems)

@app.route('/add/', methods=['GET', 'POST'])
def addCategory():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Category(name = request.form['name'])
        session.add(newItem)
        session.commit()
        catalogItems = session.query(Category).all()
        return render_template('newMenu.html', items=catalogItems)
    if request.method == 'GET':
        return render_template('addCategory.html')

@app.route('/edit/<int:category_id>/', methods=['GET','POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        editedItem = session.query(Category).filter_by(id=category_id).one()
        if request.form['name']:
            editedItem.name = request.form['name']
        session.add(editedItem)
        session.commit()
        catalogItems = session.query(Category).all()
        return render_template('newMenu.html', items=catalogItems)
    if request.method == 'GET':
        item = session.query(Category).filter_by(id=category_id).one()
        return render_template('editCategory.html', item = item)

@app.route('/catalog/<int:category_id>/')
def listMenu(category_id):
    listItems = session.query(Item).filter_by(category_id=category_id)
    for i in listItems:
        print i.name
        print i.description
    return render_template('listMenu.html', items = listItems, id = category_id)

@app.route('/delete/<int:category_id>/', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Category).filter_by(id=category_id).one()
    catalogItems = session.query(Category).all()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return render_template('newMenu.html', items=catalogItems)
    else:
        return render_template('deleteCategory.html', item=itemToDelete)


@app.route('/catalog/<int:category_id>/new/', methods = ['GET','POST'])
def addMenuItem(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        catalogItem = session.query(Category).filter_by(id=category_id).one()
        if request.form['name'] and request.form['description']:
            newItem = Item(name = request.form['name'], description = request.form['description'],category_name = catalogItem.name, category_id = category_id)
            session.add(newItem)
            session.commit()
        catalogItems = session.query(Category).all()
        return render_template('newMenu.html', items = catalogItems)
    if request.method == 'GET':
        catalogItem = session.query(Category).filter_by(id=category_id).one()
        catalogItems = session.query(Category).all()
        return render_template('addMenuItem.html', item = catalogItem, categories = catalogItems)


@app.route('/catalog/<int:item_id>/edit/', methods = ['GET', 'POST'])
def editMenuItem(item_id):
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        catalogItems = session.query(Category).all()
        editedItem = session.query(Item).filter_by(id=item_id).one()
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['category_name']:
            editedItem.category_name = request.form['category_name']
        if request.form['description']:
            editedItem.category_name = request.form['description']
        session.add(editedItem)
        session.commit()
        return render_template('newMenu.html', items = catalogItems)
    if request.method == 'GET':
        item = session.query(Item).filter_by(id=item_id).one()
        print item.name
        categories = session.query(Category).all()
        return render_template('editMenuItem.html', item = item, categories = categories)    

@app.route('/catalog/<int:item_id>/delete/', methods=['GET', 'POST'])
def deleteMenuItem(item_id):
    if 'username' not in login_session:
        return redirect('/login')
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        return redirect(url_for('listMenu', category_id=itemToDelete.category_id))
    else:
        return render_template('deleteItem.html', item=itemToDelete)
    
@app.route('/catalog/<int:category_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Category).filter_by(id=category_id).one()
    items = session.query(Item).filter_by(
        category_id=category_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/catalog/<int:category_id>/menu/<int:item_id>/JSON')
def menuItemJSON(category_id, menu_id):
    Menu_Item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Menu_Item=Menu_Item.serialize)


@app.route('/catalog/JSON')
def CategoriesJSON():
    categories = session.query(Category).all()
    return jsonify(restaurants=[c.serialize for c in categories])

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)