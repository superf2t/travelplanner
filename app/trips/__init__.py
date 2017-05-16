from flask import Blueprint

trips = Blueprint('trips', __name__, template_folder='templates', static_folder='static')
