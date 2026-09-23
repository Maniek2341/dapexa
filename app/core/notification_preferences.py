NOTIFICATION_MODULE_CHOICES = (
    ("klient", "Klienci"),
    ("serwis", "Serwisy i obsługa"),
    ("protokol", "Protokoły"),
    ("oferta_praca", "Oferty"),
    ("praca", "Prace"),
    ("zadanie", "Zadania"),
    ("rcp", "RCP"),
    ("urlop", "Urlopy"),
    ("gwarancja", "Gwarancje"),
    ("magazyn", "Magazyn"),
    ("dokument", "Dokumenty"),
    ("urzadzenie", "Urządzenia"),
    ("pojazd", "Pojazdy"),
    ("sprzet", "Sprzęt"),
    ("obsluga", "Obsługa cykliczna"),
)


def default_notification_modules():
    # Powiadomienia e-mail są opt-in, żeby nowe konta nie dostawały
    # niezamówionych wiadomości ze wszystkich modułów.
    return []
