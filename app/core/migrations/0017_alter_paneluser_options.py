from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_alter_paneluser_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='paneluser',
            options={'permissions': [('delete_company_employee', 'Może usuwać pracowników swojej firmy'), ('access_dashboard', 'Wyświetlanie panelu głównego'), ('access_create_checkout_session', 'Rozpoczynanie płatności za pakiet'), ('access_checkout_success', 'Wyświetlanie potwierdzenia udanej płatności'), ('access_checkout_cancel', 'Wyświetlanie informacji o anulowanej płatności'), ('access_stripe_webhook', 'Obsługa powiadomień operatora płatności'), ('access_select_plan', 'Wybieranie pakietu abonamentowego'), ('access_user_calendar', 'Wyświetlanie kalendarza użytkownika'), ('access_user_calendar_events', 'Pobieranie zdarzeń kalendarza użytkownika'), ('access_ajax_products', 'Wyszukiwanie urządzeń w formularzach'), ('access_ajax_clients', 'Wyszukiwanie klientów w formularzach'), ('access_ajax_services', 'Wyszukiwanie zgłoszeń serwisowych w formularzach'), ('access_login', 'Logowanie do systemu'), ('access_register', 'Rejestrowanie konta'), ('access_logout', 'Wylogowywanie z systemu'), ('access_forgot', 'Wysyłanie prośby o odzyskanie hasła'), ('access_setpassword', 'Ustawianie hasła do konta'), ('access_resetpassword', 'Resetowanie zapomnianego hasła'), ('access_profile', 'Wyświetlanie i edytowanie własnego profilu'), ('access_user_activate', 'Aktywowanie konta użytkownika'), ('access_employee_add', 'Dodawanie nowych pracowników'), ('access_employee_edit', 'Edytowanie danych pracowników'), ('access_employee_delete', 'Usuwanie pracowników'), ('access_employee_list', 'Wyświetlanie listy pracowników'), ('access_employee_permission_list', 'Wyświetlanie uprawnień pracowników'), ('access_employee_permission_edit', 'Nadawanie i odbieranie uprawnień pracownikom'), ('access_employee_set_password', 'Ustawianie pierwszego hasła pracownika')], 'verbose_name': 'Użytkownik', 'verbose_name_plural': 'Użytkownicy'},
        ),
    ]
