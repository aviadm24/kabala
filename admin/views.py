# admin/views.py
from sqladmin import Admin, ModelView
from models import User


class UserAdmin(ModelView, model=User):
    column_list = [User.user_id, User.email]
    column_searchable_list = [User.email]
    can_delete = False


def setup_admin(app, engine):
    admin = Admin(app, engine)
    admin.add_view(UserAdmin)
    return admin
