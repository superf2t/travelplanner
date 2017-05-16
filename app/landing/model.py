from flask_login import UserMixin, AnonymousUserMixin

class Anonymous(AnonymousUserMixin):
    def __init__(self):
        self.username = 'Guest'

    def isAuthenticated(self):
        return False
 
    def is_active(self):
        return False
 
    def is_anonymous(self):
        return True