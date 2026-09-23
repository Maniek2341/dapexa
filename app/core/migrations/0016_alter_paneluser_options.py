from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_alter_paneluser_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='paneluser',
            options={'permissions': [('delete_company_employee', 'Może usuwać pracowników swojej firmy'), ('access_dashboard', 'Dostęp do widoku: dashboard'), ('access_create_checkout_session', 'Dostęp do widoku: create checkout session'), ('access_checkout_success', 'Dostęp do widoku: checkout success'), ('access_checkout_cancel', 'Dostęp do widoku: checkout cancel'), ('access_stripe_webhook', 'Dostęp do widoku: stripe webhook'), ('access_select_plan', 'Dostęp do widoku: select plan'), ('access_user_calendar', 'Dostęp do widoku: user calendar'), ('access_user_calendar_events', 'Dostęp do widoku: user calendar events'), ('access_ajax_products', 'Dostęp do widoku: ajax products'), ('access_ajax_clients', 'Dostęp do widoku: ajax clients'), ('access_ajax_services', 'Dostęp do widoku: ajax services'), ('access_login', 'Dostęp do widoku: login'), ('access_register', 'Dostęp do widoku: register'), ('access_logout', 'Dostęp do widoku: logout'), ('access_forgot', 'Dostęp do widoku: forgot'), ('access_setpassword', 'Dostęp do widoku: setpassword'), ('access_resetpassword', 'Dostęp do widoku: resetpassword'), ('access_profile', 'Dostęp do widoku: profile'), ('access_user_activate', 'Dostęp do widoku: user activate'), ('access_employee_add', 'Dostęp do widoku: employee add'), ('access_employee_edit', 'Dostęp do widoku: employee edit'), ('access_employee_delete', 'Dostęp do widoku: employee delete'), ('access_employee_list', 'Dostęp do widoku: employee list'), ('access_employee_permission_list', 'Dostęp do widoku: employee permission list'), ('access_employee_permission_edit', 'Dostęp do widoku: employee permission edit'), ('access_employee_set_password', 'Dostęp do widoku: employee set password')], 'verbose_name': 'Użytkownik', 'verbose_name_plural': 'Użytkownicy'},
        ),
    ]
