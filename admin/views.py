# admin/views.py
from sqladmin import Admin, ModelView
from models import User, Receipt


class UserAdmin(ModelView, model=User):
    column_list = [User.user_id, User.email]
    column_searchable_list = [User.email]
    can_delete = False

class ReceiptAdmin(ModelView, model=Receipt):
    column_list = [Receipt.username, Receipt.name, Receipt.secure_url]
    column_searchable_list = [Receipt.name, Receipt.username]
    can_delete = False

def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    admin.add_view(ReceiptAdmin)
    return admin
