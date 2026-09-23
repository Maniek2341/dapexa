# app/core/context_processors.py
from .utils import get_profile_completion


def profile_completion(request):
    """
    Dodaje do kontekstu zmienną 'profile_completion' dla zalogowanego OWNERA.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    completion = get_profile_completion(user)
    return {
        "profile_completion": completion
    }

def current_subscription(request):
    """
    Dodaje do kontekstu aktualną subskrypcję firmy użytkownika,
    aby można było ją wyświetlać np. w topbarze.
    """
    user = request.user

    if not user.is_authenticated:
        return {}

    company = getattr(user, "company", None)
    if not company:
        return {}

    subscription = getattr(request, "current_subscription", None)
    if subscription is None:
        subscription = company.subscriptions.order_by("-created_at").first()

    return {
        "current_subscription": subscription
    }
