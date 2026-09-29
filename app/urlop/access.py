from django.contrib.auth.mixins import LoginRequiredMixin
from app.urlop.services import require_leave_permission


class LeavePermissionMixin(LoginRequiredMixin):
    leave_permission = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if self.leave_permission:
            require_leave_permission(request.user, self.leave_permission)
            if self.leave_permission == "generate_leave_allowances" and request.user.role != "owner":
                from django.core.exceptions import PermissionDenied

                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
