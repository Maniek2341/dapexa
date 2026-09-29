from django.urls import path

from app.core.views.views_calendar import user_calendar_events
from app.core.views.select_plan_view import select_plan
from app.core.views.views_stripe import checkout_cancel, checkout_success, create_checkout_session, create_billing_portal_session, stripe_webhook
from app.core.views.billing_management_view import billing_management, billing_invoice_pdf, create_billing_setup_intent, save_billing_payment_method
from app.core.views import CancelSubscriptionView, ChangePackageView, CompanySettingsView, DashboardView, DeleteCompanyAccountView, PersonalCalendarEventCreateView, PersonalCalendarEventDeleteView, PersonalCalendarEventShareView, PurchaseExtraUsersView, UserCalendarView
from app.core.views.cancel_subscription_view import ResumeSubscriptionView
from app.core.views.ajax import ProductAjaxSelectView, ClientAjaxSelectView, ServiceAjaxSelectView
from app.core.views import ClientDocumentationView, DocumentationIndexView, DocumentationModuleView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path("stripe/create-checkout-session/", create_checkout_session, name="create_checkout_session"),
    path("stripe/success/", checkout_success, name="checkout_success"),
    path("stripe/cancel/", checkout_cancel, name="checkout_cancel"),
    path("stripe/webhook/", stripe_webhook, name="stripe_webhook"),
    path("stripe/portal/", create_billing_portal_session, name="stripe_billing_portal"),
    path("rozliczenia/", billing_management, name="billing_management"),
    path("rozliczenia/setup-intent/", create_billing_setup_intent, name="billing_setup_intent"),
    path("rozliczenia/metoda-platnosci/", save_billing_payment_method, name="billing_save_payment_method"),
    path("rozliczenia/faktura/<str:invoice_id>/pdf/", billing_invoice_pdf, name="billing_invoice_pdf"),
    path("wybierz-pakiet/", select_plan, name="select_plan"),
    path("pakiet/zmien/", ChangePackageView.as_view(), name="change_package"),
    path("pakiet/anuluj/", CancelSubscriptionView.as_view(), name="cancel_subscription"),
    path("pakiet/wznow/", ResumeSubscriptionView.as_view(), name="resume_subscription"),
    path("pakiet/dokup-uzytkownikow/", PurchaseExtraUsersView.as_view(), name="purchase_extra_users"),
    path("kalendarz/", UserCalendarView.as_view(), name="user_calendar"),
    path("kalendarz/wydarzenie/dodaj/", PersonalCalendarEventCreateView.as_view(), name="calendar_personal_event_add"),
    path("kalendarz/wydarzenie/<int:pk>/usun/", PersonalCalendarEventDeleteView.as_view(), name="calendar_personal_event_delete"),
    path("kalendarz/wydarzenie/<int:pk>/udostepnij/", PersonalCalendarEventShareView.as_view(), name="calendar_personal_event_share"),
    path("kalendarz/events/", user_calendar_events, name="user_calendar_events"),
    path("ustawienia/", CompanySettingsView.as_view(), name="company_settings"),
    path("ustawienia/usun-konto/", DeleteCompanyAccountView.as_view(), name="delete_company_account"),
    path("dokumentacja/", DocumentationIndexView.as_view(), name="documentation_index"),
    path("dokumentacja/<slug:slug>/", DocumentationModuleView.as_view(), name="documentation_module"),
    path("dokumentacja/klienci/legacy/", ClientDocumentationView.as_view(), name="documentation_clients"),
    path("ajax/products/", ProductAjaxSelectView.as_view(), name="ajax_products"),
    path("ajax/clients/", ClientAjaxSelectView.as_view(), name="ajax_clients"),
    path("ajax/services/", ServiceAjaxSelectView.as_view(), name="ajax_services"),
]
