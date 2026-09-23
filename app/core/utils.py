# app/core/utils.py
from typing import Optional

from app.core.models import PanelUser


def get_profile_completion(user: PanelUser) -> Optional[dict]:
    """
    Zwraca słownik z informacjami o postępie uzupełniania danych
    TYLKO dla właściciela firmy (role=owner).

    Struktura:
    {
        "percent": 70,
        "total": 10,
        "completed": 7,
        "missing": {
            "user": [...],
            "company": [...],
            "address": [...],
        }
    }
    """
    if not user.is_authenticated:
        return None

    if getattr(user, "role", None) != PanelUser.Role.OWNER:
        return None

    company = getattr(user, "company", None)
    if not company:
        return None

    checks = []

    # ---- DANE PRYWATNE ----
    checks.append(("user", "first_name", bool(user.first_name), "Imię"))
    checks.append(("user", "last_name", bool(user.last_name), "Nazwisko"))
    checks.append(("user", "phone_priv", bool(user.phone_priv), "Telefon prywatny"))
    checks.append(("user", "phone", bool(user.phone), "Telefon firmowy"))
    checks.append(("user", "birthday", bool(user.birthday), "Data urodzenia"))
    checks.append(("user", "avatar", bool(user.avatar), "Zdjęcie profilowe"))

    # ---- DANE FIRMOWE ----
    checks.append(("company", "name", bool(company.name), "Nazwa firmy"))
    checks.append(("company", "nip", bool(company.nip), "NIP"))
    checks.append(("company", "email", bool(company.email), "E-mail firmowy"))


    # ---- ADRES FIRMY ----
    addr = company.main_address
    checks.append(("address", "street", bool(addr and addr.street), "Ulica i numer"))
    checks.append(("address", "postcode", bool(addr and addr.postcode), "Kod pocztowy"))
    checks.append(("address", "city", bool(addr and addr.city), "Miasto"))

    total = len(checks)
    completed = sum(1 for _, _, ok, _ in checks if ok)

    missing = {
        "user": [],
        "company": [],
        "address": [],
    }

    for section, key, ok, label in checks:
        if not ok:
            missing[section].append(label)

    percent = int(round((completed / total) * 100)) if total else 0

    return {
        "percent": percent,
        "total": total,
        "completed": completed,
        "missing": missing,
    }


def get_employee_completion(user: PanelUser) -> dict:
    """Return completion progress for one employee's profile data."""
    checks = [
        ("first_name", bool(user.first_name), "Imię"),
        ("last_name", bool(user.last_name), "Nazwisko"),
        ("birthday", bool(user.birthday), "Data urodzenia"),
        ("avatar", bool(user.avatar), "Zdjęcie profilowe"),
        ("wyksztalcenie", bool(user.wyksztalcenie), "Wykształcenie"),
        ("phone_priv", bool(user.phone_priv), "Telefon prywatny"),
        ("phone", bool(user.phone), "Telefon firmowy"),
        ("position", bool(user.position), "Stanowisko"),
        ("employment_start_date", bool(user.employment_start_date), "Data rozpoczęcia pracy"),
        ("employment_fraction", bool(user.employment_fraction), "Wymiar etatu"),
    ]
    completed = sum(1 for _, present, _ in checks if present)
    missing = [label for _, present, label in checks if not present]
    total = len(checks)
    return {
        "percent": int(round(completed / total * 100)) if total else 100,
        "completed": completed,
        "total": total,
        "missing": missing,
    }
