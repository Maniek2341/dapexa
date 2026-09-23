from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


def normalize_nip(value):
    return re.sub(r"[\s-]", "", value or "")


def is_valid_polish_nip(value):
    nip = normalize_nip(value)
    if len(nip) != 10 or not nip.isdigit() or len(set(nip)) == 1:
        return False
    weights = (6, 5, 7, 2, 3, 4, 5, 6, 7)
    checksum = sum(int(digit) * weight for digit, weight in zip(nip[:9], weights)) % 11
    return checksum != 10 and checksum == int(nip[-1])


def validate_polish_nip(value):
    if not is_valid_polish_nip(value):
        raise ValidationError(
            _("Podaj prawidłowy polski NIP (10 cyfr z poprawną sumą kontrolną)."),
            code="invalid_nip",
        )


class CustomMinimumLengthValidator:
    """
    Własny walidator długości hasła.
    """
    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        if len(password) < self.min_length:
            raise ValidationError(
                _("Hasło musi mieć co najmniej %(min_length)d znaków."),
                code="password_too_short",
                params={"min_length": self.min_length},
            )

    def get_help_text(self):
        return _("Hasło musi mieć co najmniej %(min_length)d znaków.") % {
            "min_length": self.min_length
        }


class UppercaseValidator:
    """
    Wymaga co najmniej jednej wielkiej litery.
    """
    def validate(self, password, user=None):
        if not any(c.isupper() for c in password):
            raise ValidationError(
                _("Hasło musi zawierać co najmniej jedną wielką literę."),
                code="password_no_upper",
            )

    def get_help_text(self):
        return _("Hasło musi zawierać co najmniej jedną wielką literę.")


class DigitValidator:
    """
    Wymaga co najmniej jednej cyfry.
    """
    def validate(self, password, user=None):
        if not any(c.isdigit() for c in password):
            raise ValidationError(
                _("Hasło musi zawierać co najmniej jedną cyfrę."),
                code="password_no_digit",
            )

    def get_help_text(self):
        return _("Hasło musi zawierać co najmniej jedną cyfrę.")


class NoRepeatedCharsValidator:
    """
    Blokuje zbyt długie sekwencje tego samego znaku,
    np. 'aaaa' lub '1111' (domyślnie max 3 pod rząd).
    """

    def __init__(self, max_repeats=3):
        self.max_repeats = max_repeats

    def validate(self, password, user=None):
        if not password:
            return

        current_char = password[0]
        count = 1

        for c in password[1:]:
            if c == current_char:
                count += 1
                if count > self.max_repeats:
                    raise ValidationError(
                        _(
                            "Hasło nie może zawierać więcej niż %(max_repeats)d "
                            "takich samych znaków pod rząd."
                        ),
                        code="password_too_many_repeats",
                        params={"max_repeats": self.max_repeats},
                    )
            else:
                current_char = c
                count = 1

    def get_help_text(self):
        return _(
            "Hasło nie może zawierać długich sekwencji powtarzających się znaków."
        )


class UserAttributeProhibitionValidator:
    """
    Sprawdza, czy hasło nie zawiera danych użytkownika:
    imię, nazwisko, username, fragment email itd.
    Podobne do domyślnego UserAttributeSimilarityValidator, ale bardziej "twarde".
    """

    def __init__(self, max_similarity=0.7):
        # ten parametr można wykorzystać, jeśli będziesz chciał rozbudować logikę
        self.max_similarity = float(max_similarity)

    def _normalize(self, value):
        if not value:
            return ""
        return value.strip().lower()

    def validate(self, password, user=None):
        if not user:
            return

        password_lower = password.lower()

        attributes = [
            getattr(user, "first_name", ""),
            getattr(user, "last_name", ""),
            getattr(user, "username", ""),
            getattr(user, "email", ""),
        ]

        # osobno lokalna część emaila
        email = getattr(user, "email", "")
        if email and "@" in email:
            local_part = email.split("@", 1)[0]
            attributes.append(local_part)

        for attr in attributes:
            norm = self._normalize(attr)
            if norm and len(norm) >= 3 and norm in password_lower:
                raise ValidationError(
                    _(
                        "Hasło nie może zawierać danych użytkownika, takich jak "
                        "imię, nazwisko, login czy część adresu email."
                    ),
                    code="password_too_similar_to_user_data",
                )

    def get_help_text(self):
        return _(
            "Hasło nie może zawierać danych użytkownika (imię, nazwisko, login, email)."
        )


class CommonPasswordListValidator:
    """
    Sprawdza, czy hasło nie jest jednym z najpopularniejszych i najprostszych.
    W realnym projekcie warto wczytywać długą listę z pliku tekstowego.
    """

    # Krótka przykładowa lista. Możesz ją zastąpić listą z pliku.
    COMMON_PASSWORDS = {
        "123456",
        "123456789",
        "12345678",
        "12345",
        "qwerty",
        "password",
        "haslo",
        "admin",
        "abc123",
        "111111",
        "123123",
        "qwerty123",
        "letmein",
    }

    def __init__(self, common_passwords_file=None):
        self.common_passwords_file = common_passwords_file
        self._loaded_passwords = None

    def _load_passwords(self):
        if self._loaded_passwords is not None:
            return self._loaded_passwords

        passwords = set(self.COMMON_PASSWORDS)

        if self.common_passwords_file:
            try:
                with open(self.common_passwords_file, encoding="utf-8") as f:
                    for line in f:
                        pwd = line.strip()
                        if pwd:
                            passwords.add(pwd.lower())
            except OSError:
                # Jeśli plik nie istnieje – używamy tylko wbudowanej listy
                pass

        self._loaded_passwords = passwords
        return passwords

    def validate(self, password, user=None):
        passwords = self._load_passwords()
        if password.lower() in passwords:
            raise ValidationError(
                _("Hasło jest zbyt popularne i niebezpieczne."),
                code="password_too_common",
            )

    def get_help_text(self):
        return _("Hasło nie może być jednym z najczęściej używanych haseł.")


class ComplexityScoreValidator:
    """
    Prosty „score” złożoności hasła:
    - długość
    - małe litery
    - wielkie litery
    - cyfry
    - znaki specjalne

    Wymagamy osiągnięcia minimalnego wyniku.
    """

    def __init__(self, min_score=4):
        self.min_score = int(min_score)

    def validate(self, password, user=None):
        score = 0

        # 1) długość
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1

        # 2) małe litery
        if re.search(r"[a-z]", password):
            score += 1

        # 3) wielkie litery
        if re.search(r"[A-Z]", password):
            score += 1

        # 4) cyfry
        if re.search(r"\d", password):
            score += 1

        # 5) znaki specjalne
        if re.search(r"[^\w]", password):
            score += 1

        if score < self.min_score:
            raise ValidationError(
                _(
                    "Hasło jest zbyt słabe. Użyj kombinacji małych i wielkich liter, "
                    "cyfr oraz znaków specjalnych i zadbaj o jego długość."
                ),
                code="password_too_weak",
            )

    def get_help_text(self):
        return _(
            "Hasło powinno być odpowiednio złożone: długość, małe/wielkie litery, "
            "cyfry i znaki specjalne."
        )
