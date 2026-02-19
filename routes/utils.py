def can_mark_attendance(user, target_pic_id):
    if user.role in ['admin', 'pembina']:
        return True

    if user.id == target_pic_id:
        return True

    return False

def is_core_user(user):
    return user.role in ["admin", "ketua"]