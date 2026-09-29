"""Authorize existing /files/ URLs against database records before offloading I/O."""
import mimetypes
from pathlib import Path
from urllib.parse import quote

from django.apps import apps
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_safe

# Every project FileField has an explicit policy. New/unregistered fields fail closed.
# (model, field, company lookup, existing view permission, package feature)
FILE_POLICIES = (
    ('dokument.Document', 'file', 'company_id', 'dokument.access_documents_list', 'dokumenty'),
    ('serwis.ServiceOrderMedia', 'file', 'service__company_id', 'serwis.access_serwis_detail', 'serwisy'),
    ('protokol.Protocol', 'client_signature', 'company_id', 'protokol.access_protokol_detail', 'protokoly'),
    ('protokol.Protocol', 'employee_signature', 'company_id', 'protokol.access_protokol_detail', 'protokoly'),
    ('protokol.ProtokolImage', 'file', 'protokol__company_id', 'protokol.access_protokol_detail', 'protokoly'),
    ('gwarancja.WarrantyClaimAttachment', 'file', 'claim__company_id', 'gwarancja.access_warranty_detail', 'gwarancje'),
    ('obsluga.ServiceContractMedia', 'file', 'contract__company_id', 'obsluga.access_service_contract_detail', 'obsluga'),
    ('oferta_praca.OfferVariantFile', 'file', 'variant__offer__company_id', 'oferta_praca.access_offer_detail', 'oferty'),
    ('oferta_praca.OfferImage', 'file', 'offer__company_id', 'oferta_praca.access_offer_detail', 'oferty'),
    ('pojazd.Vehicle', 'photo', 'company_id', 'pojazd.access_vehicle_list', 'pojazdy'),
    ('pojazd.VehicleEvent', 'photo', 'vehicle__company_id', 'pojazd.access_vehicle_detail', 'pojazdy'),
    ('sprzet.Tool', 'image', 'company_id', 'sprzet.access_tool_list', 'sprzet'),
    ('sprzet.ToolEventMedia', 'image', 'event__tool__company_id', 'sprzet.access_tool_detail', 'sprzet'),
    ('urzadzenie.Product', 'image', 'company_id', 'urzadzenie.access_product_list', 'urzadzenia'),
    ('core.Company', 'logo', 'pk', None, None),
    ('core.PanelUser', 'avatar', 'company_id', None, None),
    ('uzytkownik.EmployeeTraining', 'certificate_image', 'company_id', 'core.access_profile', None),
    ('uzytkownik.EmployeeContract', 'contract_image', 'company_id', 'core.access_profile', None),
)


def _authorized(user, name, subscription):
    for label, field, company_lookup, permission, feature in FILE_POLICIES:
        if not user.is_superuser:
            if permission and not user.has_perm(permission):
                continue
            if feature and subscription and not subscription.has_feature(feature):
                continue
        model = apps.get_model(label)
        query = model._default_manager.filter(**{field: name})
        if not user.is_superuser:
            if label == 'core.PanelUser':
                scope = Q(pk=user.pk)
                if user.company_id:
                    scope |= Q(company_id=user.company_id)
                query = query.filter(scope)
            else:
                if not user.company_id:
                    continue
                query = query.filter(**{company_lookup: user.company_id})
            if label.startswith('uzytkownik.') and user.role not in {
                user.Role.OWNER, user.Role.MANAGER, user.Role.BIURO,
            }:
                query = query.filter(employee_id=user.pk)
        if label == 'protokol.Protocol':
            query = query.filter(is_active=True)
        elif label == 'protokol.ProtokolImage':
            query = query.filter(protokol__is_active=True)
        if query.exists():
            return True
    return False


@login_required(login_url='login')
@require_safe
def private_media(request, name):
    user = request.user
    if not user.is_active or not getattr(user, 'is_active_employee', True):
        raise Http404
    # Do not normalize traversal or permit symlinks, including ones within MEDIA_ROOT.
    if '\\' in name or any(part in {'', '.', '..'} for part in name.split('/')):
        raise Http404
    root = Path(settings.MEDIA_ROOT).resolve()
    candidate = root
    try:
        for part in name.split('/'):
            candidate /= part
            if candidate.is_symlink():
                raise Http404
        if not candidate.resolve().is_relative_to(root) or not candidate.is_file():
            raise Http404
    except (OSError, ValueError):
        raise Http404 from None
    if not _authorized(user, name, getattr(request, 'current_subscription', None)):
        raise Http404

    content_type = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    inline = content_type in {
        'image/png', 'image/jpeg', 'image/gif', 'image/webp', 'image/avif',
        'application/pdf', 'video/mp4', 'video/webm', 'audio/mpeg', 'audio/ogg',
    }
    if not inline:
        content_type = 'application/octet-stream'
    if settings.DEBUG:
        response = FileResponse(candidate.open('rb'), content_type=content_type)
    else:
        response = HttpResponse(content_type=content_type)
        response['X-Accel-Redirect'] = settings.PRIVATE_MEDIA_INTERNAL_URL + quote(name, safe='/')
    response['Content-Disposition'] = content_disposition_header(not inline, candidate.name)
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "sandbox"
    return response
