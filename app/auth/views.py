import os
from flask import Flask, render_template, redirect, Blueprint, request, flash, url_for, session, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, AnonymousUserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from model import User, Role, Anonymous, Photos, Connection
from forms import LoginForm, RegisterForm, EditForm, SearchForm, PasswordSettingsForm, UsernameSettingsForm
from app import db, app
from decorators import required_roles, get_friends, get_friend_requests, allowed_file, deleteTrip_user, img_folder, is_friends_or_pending
from app.landing.views import landing_blueprint
from werkzeug import secure_filename
from PIL import Image
from app.trips.model import Trips, Itineraries
from app.trips.forms import EditTripForm, ItineraryForm, EditItineraryForm
import datetime
import time
from sqlalchemy_searchable import search
from sqlalchemy import func, desc

auth = Flask(__name__)
auth_blueprint = Blueprint('auth_blueprint', __name__, template_folder='templates', static_folder='static', static_url_path='/static/')

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth_blueprint.login'
login_manager.anonymous_user = Anonymous

POSTS_PER_PAGE = 9

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --------> START ADMIN
@auth_blueprint.route('/admin')
@login_required
@required_roles('Admin')
def addash():
    users = User.query.all()
    trips = Trips.query.all()
    return render_template('admin/admindashboard.html', users=users, trips=trips)

@auth_blueprint.route('/admin/settings/<username>', methods=['GET', 'POST'])
@login_required
@required_roles('Admin')
def settings(username):
    form = PasswordSettingsForm()
    user = User.query.filter_by(username=username).first()
    if request.method == 'POST':
        if form.validate_on_submit():
            if check_password_hash(current_user.password, request.form['currpassword']):
                current_user.password = generate_password_hash(form.newpassword.data)
                db.session.add(current_user)
                db.session.commit()
                flash('Changes saved!')
                result = User.query.all()
                return render_template('admin/users.html', form=form, result=result)
            else:
                flash('Incorrect Password!')
                return render_template('admin/settings.html', form=form, user=user)
        else:
            form.newpassword.data = current_user.password
            return render_template('admin/settings.html', form=form, user=user)
    return render_template('admin/settings.html', form=form, user=user)

@auth_blueprint.route('/admin/settings/username/<username>', methods=['GET', 'POST'])
@login_required
@required_roles('Admin')
def usernamesettings(username):
    form = UsernameSettingsForm()
    form1 = PasswordSettingsForm()
    user = User.query.filter_by(username=username).first()
    if request.method == 'POST':
        if form.validate_on_submit():
            if check_password_hash(current_user.password, request.form['currpassword']):
                current_user.username = form.username.data
                db.session.add(current_user)
                db.session.commit()
                flash('Changes saved!')
                result = User.query.all()
                return render_template('admin/users.html', form=form, result=result)
            else:
                flash('Invalid Username!')
                return render_template('admin/usernamesettings.html', form=form, user=user, form1=form1)
        else:
            form.username.data = current_user.username
            return render_template('admin/usernamesettings.html', form=form, user=user, form1=form1)
    return render_template('admin/usernamesettings.html', form=form, user=user, form1=form1)

@auth_blueprint.route('/admin/users/sort/admin', methods=['GET', 'POST'])
@login_required
@required_roles('Admin')
def sortadmin():
    result = User.query.filter_by(role_id='1')
    return render_template('admin/users.html', result=result)

@auth_blueprint.route('/admin/users/sort/moderator', methods=['GET', 'POST'])
@login_required
@required_roles('Admin')
def sortmod():
    result = User.query.filter_by(role_id='2')
    return render_template('admin/users.html', result=result)

@auth_blueprint.route('/admin/users/sort/member', methods=['GET', 'POST'])
@login_required
@required_roles('Admin')
def sortuser():
    result = User.query.filter_by(role_id='3')
    return render_template('admin/users.html', result=result)

# USERS --> read
@auth_blueprint.route('/admin/users', methods=['GET','POST'])
@login_required
@required_roles('Admin')
def manageusers():
    result = User.query.order_by(User.id)
    return render_template('admin/users.html', result=result)

@auth_blueprint.route('/admin/users/create', methods=['GET','POST'])
@login_required
@required_roles('Admin')
def addusers():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            user = User(username=form.username.data,
                               email=form.email.data,
                               password=form.password.data,
                               role_id = "3")
            db.session.add(user)
            db.session.commit()
            result = User.query.order_by(User.id)
            flash("Your changes have been saved.")
            return render_template('admin/users.html', result=result)
    return render_template('admin/createusers.html', form=form)

#update
@auth_blueprint.route('/admin/users/edit/<username>', methods = ['GET', 'POST'])
@login_required
@required_roles('Admin')
def editusers(username):
    user = User.query.filter_by(username=username).first()
    form = EditForm()
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.address = form.address.data
        user.city = form.city.data
        user.country = form.country.data
        user.birth_date = form.birth_date.data
        user.contact_num = form.contact_num.data
        user.description = form.description.data

        now_loc = img_folder + str(user.id)
        if os.path.isdir(now_loc) == False:
            os.makedirs(now_loc)

        if form.file.data.filename == None or form.file.data.filename == '':
            user.profile_pic = user.profile_pic
        else:
            if form.file.data and allowed_file(form.file.data.filename):
                filename = secure_filename(form.file.data.filename)
                form.file.data.save(os.path.join(now_loc + '/', filename))

                uploadFolder = now_loc + '/'
                nameNow = str(int(time.time())) + '.' + str(os.path.splitext(filename)[1][1:])
                os.rename(uploadFolder + filename, uploadFolder + nameNow)

            date = datetime.datetime.today().strftime('%m/%d/%y')
            photo = Photos(photoName=nameNow, photoDate=date, photoLocation=now_loc, userID=user.id)
            db.session.add(photo)
            db.session.commit()

            ph_1 = Photos.query.filter_by(userID=user.id).all()
            for p in ph_1:
                if p.photoName == str(nameNow):
                    user.profile_pic = p.id

        db.session.add(user)
        db.session.commit()

        ph = Photos.query.filter_by(id=user.profile_pic).first()
        if ph is None:
            cas = 'default'
        else:
            cas = ph.photoName

        flash("Your changes have been saved.")
        result = User.query.all()
        return render_template('admin/users.html', result=result, user=user, csID=str(user.id), csPic=str(cas))
    else:
        form.first_name.data = user.first_name
        form.last_name.data = user.last_name
        form.address.data = user.address
        form.city.data = user.city
        form.country.data = user.country
        form.birth_date.data = user.birth_date
        form.contact_num.data = user.contact_num
        form.description.data = user.description

        ph = Photos.query.filter_by(id=user.profile_pic).first()
        if ph is None:
            cas = 'default'
        else:
            cas = ph.photoName
        return render_template('admin/editusers.html', user=user, form=form, csID=str(user.id),
                               csPic=str(cas))

#delete
@auth_blueprint.route('/admin/users/remove/<username>', methods=['GET','POST'])
@login_required
@required_roles('Admin')
def deleteusers(username):
    user = User.query.filter_by(username=username).first()
    deleteTrip_user(user.id)
    if user.profile_pic!='default':
        os.remove(img_folder+str(user.profile_pic))
    db.session.delete(user)
    db.session.commit()
    result = User.query.all()
    return render_template('admin/users.html', result = result)

# TRIPS --> read
@auth_blueprint.route('/admin/trips')
@login_required
@required_roles('Admin')
def managetrips():
    result = Trips.query.all()
    return render_template('admin/trips.html', result=result)

#delete
@auth_blueprint.route('/admin/trips/remove/<tripName>', methods=['GET','POST'])
@login_required
@required_roles('Admin')
def removetrips(tripName):
    trips = Trips.query.filter_by(tripName=tripName).first()
    os.remove('app/trips/static/images/trips/'+trips.img_thumbnail)
    db.session.delete(trips)
    db.session.commit()
    result = Trips.query.all()
    return render_template('admin/trips.html', result=result)

# update
@auth_blueprint.route('/admin/trips/edit/<tripName>', methods=['GET','POST'])
def editTrips(tripName):
    tripname = Trips.query.filter_by(tripName=tripName).first()
    form = EditTripForm()
    trips = Trips.query.all()
    if request.method == 'POST':
        if form.validate_on_submit():
            tripname.tripName = form.trip_name.data
            tripname.tripDateFrom = form.trip_date_from.data
            tripname.tripDateTo = form.trip_date_to.data
            db.session.add(tripname)
            db.session.commit()
            return redirect(url_for("auth_blueprint.managetrips"))
        return render_template('/admin/trip.html', trips=trips)
    else:
        form.trip_name.data = tripname.tripName
        form.trip_date_from.data = tripname.tripDateFrom
        form.trip_date_to.data = tripname.tripDateTo
    return render_template('/admin/edittrips.html', form=form, tripname=tripname)

@auth_blueprint.route('/admin/trips/<tripName>/itineraries', methods=['GET'])
def itineraries(tripName):
    tripid = Trips.query.filter_by(tripName=tripName).first()
    itinerary = Itineraries.query.filter_by(tripID=tripid.tripID)
    trip = Trips.query.filter_by(userID=current_user.id, tripName=tripName).first()
    return render_template('/admin/itineraries.html', trip=trip, itineraries=itinerary)

@auth_blueprint.route('/admin/trips/<tripName>/<itineraryName>/edit', methods=['GET', 'POST'])
def editItineraries(tripName, itineraryName):
    tripname = Trips.query.filter_by(tripName=tripName).first()
    itineraryname = Itineraries.query.filter_by(tripID=tripname.tripID, itineraryName=itineraryName).first()
    itineraries = Itineraries.query.all()
    form = EditItineraryForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            itineraryname.itineraryName = form.itinerary_name.data
            itineraryname.itineraryDateFrom = form.itinerary_date_from.data
            itineraryname.itineraryDateTo = form.itinerary_date_to.data
            itineraryname.itineraryDesc = form.itinerary_desc.data
            itineraryname.itineraryLocation = form.itinerary_location.data
            itineraryname.locationTypeID = form.itinerary_location_type.data
            itineraryname.itineraryTimeFrom = form.itinerary_time_from.data
            itineraryname.itineraryTimeTo = form.itinerary_time_to.data
            db.session.add(itineraryname)
            db.session.commit()
            return redirect(url_for("auth_blueprint.itineraries", tripName=tripName))
        return render_template('/admin/itineraries.html', trip=tripname, itineraries=itineraries)
    else:
        form.itinerary_name.data = itineraryname.itineraryName
        form.itinerary_date_from.data = itineraryname.itineraryDateFrom
        form.itinerary_date_to.data = itineraryname.itineraryDateTo
        form.itinerary_desc.data = itineraryname.itineraryDesc
        form.itinerary_location_type.data = itineraryname.locationTypeID
        form.itinerary_location.data = itineraryname.itineraryLocation
        form.itinerary_time_from.data = itineraryname.itineraryTimeFrom
        form.itinerary_time_to.data = itineraryname.itineraryTimeTo
    return render_template('/admin/edititinerary.html', form=form, tripname=tripname)
# END ADMIN <----------


@auth_blueprint.route('/home')
@login_required
@required_roles('User')
def home():
    ph = Photos.query.filter_by(id=current_user.profile_pic).first()
    user = db.session.query(User).filter(User.id == current_user.id).one()

    if ph is None:
        cas = 'default'
    else:
        cas = ph.photoName

    received_friend_requests, sent_friend_requests = get_friend_requests(current_user.id)
    num_received_requests = len(received_friend_requests)
    num_sent_requests = len(sent_friend_requests)
    num_total_requests = num_received_requests + num_sent_requests

                        # Use a nested dictionary for session["current_user"] to store more than just user_id
    session["current_user"] = {
        "first_name": current_user.first_name,
        "id": current_user.id,
        "num_received_requests": num_received_requests,
        "num_sent_requests": num_sent_requests,
        "num_total_requests": num_total_requests
    }

    return render_template('users/dashboard.html', username=current_user.username, csID=str(current_user.id), csPic=str(cas), user=user)


@auth_blueprint.route("/users/<int:id>")
@login_required
@required_roles('User')
def users(id):
    """Show user profile."""

    user = db.session.query(User).filter(User.id == id).one()

    ph = Photos.query.filter_by(id=user.profile_pic).first()
    if ph is None:
        cas = 'default'
    else:
        cas = ph.photoName

    total_friends = len(get_friends(user.id).all())

    user_a_id = session["current_user"]["id"]
    user_b_id = user.id

    # Check connection status between user_a and user_b
    friends, pending_request = is_friends_or_pending(user_a_id, user_b_id)

    return render_template("users/user.html",
                           user=user,
                           total_friends=total_friends,
                           friends=friends,
                           pending_request=pending_request,
                           csID=str(user.id), csPic=str(cas))


@auth_blueprint.route('/add-friend', methods=["POST"])
@login_required
@required_roles('User')
def add_friend():
    """Send a friend request to another user."""

    user_a_id = session["current_user"]["id"]
    #user_b_id = request.form.get("user_b_id")
    user_b_id = request.form['button_for_add']
    print user_b_id
    # Check connection status between user_a and user_b
    is_friends, is_pending = is_friends_or_pending(user_a_id, user_b_id)

    if user_a_id == user_b_id:
        return "You cannot add yourself as a friend."
    elif is_friends:
        return "You are already friends."
    elif is_pending:
        return "Your friend request is pending."
    else:
        requested_connection = Connection(user_a_id=user_a_id,
                                          user_b_id=user_b_id,
                                          status="Requested")
        db.session.add(requested_connection)
        db.session.commit()
        print "User ID %s has sent a friend request to User ID %s" % (user_a_id, user_b_id)
        return "Request Sent"


@auth_blueprint.route('/friends')
@auth_blueprint.route('/friends/<int:page>', methods=['GET', 'POST'])
@login_required
@required_roles('User')
def show_friends(page=1):
    """Show friend requests and list of all friends"""
    cas = []
    usID = []
    users = User.query.order_by(desc(User.id)).paginate(page, POSTS_PER_PAGE, False)
    print users
    for user in users.items:
        ph = Photos.query.filter_by(id=user.profile_pic).first()
        usID.append(str(user.id))
        if ph is None:
            cas.append('default')
        else:
            cas.append(str(ph.photoName))

    #users = User.query.order_by(desc(User.id)).paginate(page, POSTS_PER_PAGE, False)

    # This returns User objects for current user's friend requests
    received_friend_requests, sent_friend_requests = get_friend_requests(session["current_user"]["id"])

    # This returns a query for current user's friends (not User objects), but adding .all() to the end gets list of User objects
    friends = get_friends(session["current_user"]["id"]).all()

    return render_template("users/friends.html",
                           received_friend_requests=received_friend_requests,
                           sent_friend_requests=sent_friend_requests,
                           friends=friends,
                           users=users,
                           page=page, csPic=cas, usID=usID)


@auth_blueprint.route("/friends/search/", methods=["GET"])
@login_required
@required_roles('User')
def search_users():
    """Search for a user and return results."""

    ph = Photos.query.filter_by(id=current_user.profile_pic).first()
    if ph is None:
        cas = 'default'
    else:
        cas = ph.photoName

    # Returns users for current user's friend requests
    received_friend_requests, sent_friend_requests = get_friend_requests(session["current_user"]["id"])

    # Returns query for current user's friends (not User objects) so add .all() to the end to get list of User objects
    friends = get_friends(session["current_user"]["id"]).all()

    user_input = request.args.get("q")

    # Search user's query in users table of db and return all search results
    search_results = search(db.session.query(User), user_input).all()

    return render_template("users/browse_friends.html",
                           received_friend_requests=received_friend_requests,
                           sent_friend_requests=sent_friend_requests,
                           friends=friends,
                           search_results=search_results, csID=str(current_user.id), csPic=str(cas))

@auth_blueprint.route('/userprofile/<username>')
@login_required
@required_roles('User')
def user_profile(username):
    ph = Photos.query.filter_by(id=current_user.profile_pic).first()
    if ph is None:
        cas = 'default'
    else:
        cas = ph.photoName
    user = User.query.filter_by(username=username).first()
    return render_template('users/userprofile.html', user=user, csID=str(current_user.id), csPic=str(cas))

@auth_blueprint.route('/userprofile/<username>/edit', methods=['GET', 'POST'])
@login_required
@required_roles('User')
def edit(username):
    user = User.query.filter_by(username=username).first()
    form = EditForm()
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.address = form.address.data
        current_user.city = form.city.data
        current_user.country = form.country.data
        current_user.birth_date = form.birth_date.data
        current_user.contact_num = form.contact_num.data
        current_user.description = form.description.data

        now_loc = img_folder+str(current_user.id)
        if os.path.isdir(now_loc)==False:
            os.makedirs(now_loc)

        if form.file.data.filename==None or form.file.data.filename=='':
            current_user.profile_pic = current_user.profile_pic
        else:  
            if form.file.data and allowed_file(form.file.data.filename):
                filename = secure_filename(form.file.data.filename)
                form.file.data.save(os.path.join(now_loc+'/', filename))

                uploadFolder = now_loc+'/'
                nameNow = str(int(time.time()))+'.'+str(os.path.splitext(filename)[1][1:])
                os.rename(uploadFolder+filename, uploadFolder+nameNow)

            date = datetime.datetime.today().strftime('%m/%d/%y')
            photo = Photos(photoName=nameNow, photoDate=date, photoLocation=now_loc, userID=current_user.id)          
            db.session.add(photo)
            db.session.commit()

            ph_1 = Photos.query.filter_by(userID=current_user.id).all()
            for p in ph_1:
                if p.photoName==str(nameNow):
                    current_user.profile_pic=p.id

        db.session.add(current_user)
        db.session.commit()

        ph = Photos.query.filter_by(id=current_user.profile_pic).first()
        if ph is None:
            cas = 'default'
        else:
            cas = ph.photoName

        flash("Your changes have been saved.")
        return render_template('users/userprofile.html', user=user, csID=str(current_user.id), csPic=str(cas))
    else:
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.address.data = current_user.address
        form.city.data = current_user.city
        form.country.data = current_user.country
        form.birth_date.data = current_user.birth_date
        form.contact_num.data = current_user.contact_num
        form.description.data = current_user.description

        ph = Photos.query.filter_by(id=current_user.profile_pic).first()
        if ph is None:
            cas = 'default'
        else:
            cas = ph.photoName
        return render_template('users/edit_profile.html', user=user, form=form, csID=str(current_user.id), csPic=str(cas))

@auth_blueprint.route('/user/photos')
@login_required
@required_roles('User')
def select_photo():
    ph = Photos.query.filter_by(id=current_user.profile_pic).first()
    user = db.session.query(User).filter(User.id == current_user.id).one()

    if ph is None:
        cas = 'default'
    else:
        cas = ph.photoName

    photos = Photos.query.filter_by(userID=current_user.id).all()

    return render_template('users/photos.html', username=current_user.username, csID=str(current_user.id), csPic=str(cas), user=user, photos=photos)

@auth_blueprint.route('/set_profile')
@login_required
@required_roles('User')
def modify_prophoto():
    current_user.profile_pic = int(request.args.get('id'))
    db.session.add(current_user)
    db.session.commit()

    ph = Photos.query.filter_by(id=current_user.profile_pic).first()

    if ph is None:
        cas = 'default'
    else:
        cas = ph.photoName 
    return jsonify(response='ok', userid=current_user.id, filename=cas)

@auth_blueprint.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = LoginForm()
    if current_user.is_active():
        return redirect(url_for('landing_blueprint.index'))
    else:
        if request.method == 'POST':
            if form.validate_on_submit():
                user = User.query.filter_by(username=request.form['username']).first()
                if user.role_id == 3:
                    if user is not None and check_password_hash(user.password, request.form['password']):
                        login_user(user)
                        flash('You are now logged in!')

                    # Get current user's friend requests and number of requests to display in badges
                    received_friend_requests, sent_friend_requests = get_friend_requests(current_user.id)
                    num_received_requests = len(received_friend_requests)
                    num_sent_requests = len(sent_friend_requests)
                    num_total_requests = num_received_requests + num_sent_requests

                        # Use a nested dictionary for session["current_user"] to store more than just user_id
                    session["current_user"] = {
                        "first_name": current_user.first_name,
                        "id": current_user.id,
                        "num_received_requests": num_received_requests,
                        "num_sent_requests": num_sent_requests,
                        "num_total_requests": num_total_requests
                    }
                    if user.first_login == True:
                        user.first_login = False
                        db.session.add(user)
                        db.session.commit()
                        return redirect(url_for('auth_blueprint.edit', username=request.form['username']))

                    

                    return redirect(url_for('auth_blueprint.home', name=request.form['username']))
                elif user.role_id == 1:
                    if user is not None and check_password_hash(user.password, request.form['password']):
                        login_user(user)
                        flash('You are now logged in!')
                    return redirect(url_for('auth_blueprint.addash', name=request.form['username']))
                else:
                    return redirect(url_for('landing_blueprint.index'))
            else:
                error = 'Invalid username or password'
                return render_template('users/signin.html', form=form, error=error)
        else:
            error = 'Invalid username or password'
        return render_template('users/signin.html', form=form, error=error)

@auth_blueprint.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    Role.insert_roles()
    if current_user.is_active():
        return redirect(url_for('landing_blueprint.index'))
    else:
        if form.validate_on_submit():
            user = User(username=request.form['username'], email=request.form['email'], password=request.form['password'], role_id=3)          
            db.session.add(user)
            db.session.commit()

            # Add same info to session for new user as per /login route
            session["current_user"] = {
                "first_name": user.first_name,
                "id": user.id,
                "num_received_requests": 0,
                "num_sent_requests": 0,
                "num_total_requests": 0
            }

            flash('Log In')
            return redirect(url_for('auth_blueprint.login'))
        return render_template('users/registration.html', form=form)

@auth_blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You were logged out.')
    return redirect(url_for('auth_blueprint.login'))
