from .models import Membership

class SterlingIAM:
    @staticmethod
    def get_role_priority(role):
        priority_map = {
            'OWNER': 50,
            'MANAGER': 40,
            'SUPERVISOR': 30,
            'STAFF': 20,
            'MEMBER': 10,
        }
        return priority_map.get(role, 0)

    @staticmethod
    def has_permission(user, unit_id, minimum_role):
        if user.is_global_admin or user.is_superuser:
            return True
        membership = Membership.objects.filter(user=user, unit_id=unit_id).first()
        if not membership:
            return False
        return SterlingIAM.get_role_priority(membership.role) >= SterlingIAM.get_role_priority(minimum_role)
