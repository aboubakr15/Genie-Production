from django.contrib.auth.models import Group

def is_in_group(user, group_name):
    return user.is_authenticated and user.groups.filter(name=group_name).exists()
