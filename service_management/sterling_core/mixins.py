from django.db.models import QuerySet

class TenantScopeMixin:
    """
    Ensures that users only see data associated with their primary unit.
    If the user is a superuser, they see everything.
    """
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return queryset
        
        # Find the primary membership for the current unit
        membership = user.memberships.filter(is_primary=True).first()
        if membership:
            # Assuming the model has a 'unit' field
            if hasattr(queryset.model, 'unit'):
                return queryset.filter(unit=membership.unit)
        
        # Return empty if no primary unit assigned or no unit field exists
        return queryset.none()
