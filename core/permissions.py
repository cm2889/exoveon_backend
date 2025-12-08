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


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    Assumes the model instance has a `created_by` attribute.
    """
    def has_object_permission(self, request, view, obj):

        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Superusers can do anything.
        if request.user and request.user.is_superuser:
            return True

        # Write permissions are only allowed to the owner of the object.
        return obj.created_by == request.user


class IsOwnerOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        # Superusers can access everything
        if request.user and request.user.is_superuser:
            return True

        owner = None

        # Most models use created_by
        owner = getattr(obj, 'created_by', None)
        if owner is None:
            # Some models use a direct user field
            owner = getattr(obj, 'user', None)
        if owner is None:
            # Nested ownership via related session
            session = getattr(obj, 'session', None)
            if session is not None:
                owner = getattr(session, 'user', None) or getattr(session, 'created_by', None)

        return owner is not None and owner == request.user
