from rest_framework import permissions

class IsSuperUserOrPostAndRead(permissions.BasePermission):
    """
    Custom permission to only allow superusers to edit or delete.
    General users can create and read.
    """

    def has_permission(self, request, view):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Create permission is allowed for any user.
        if request.method == 'POST':
            return True

        # Update and delete permissions are only allowed for superusers.
        return request.user and request.user.is_superuser
