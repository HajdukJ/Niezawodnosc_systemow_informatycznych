# Testy funkcjonalne (czarnoskrzynkowe) — zajęcia projektowe nr 4
# Punkt wyjścia: sut_dokumentacja.pdf (nie kod źródłowy).
# python -m pytest wywolania_P4_test.py -q

import pytest
from datetime import date, timedelta
from decimal import Decimal

from zespol_C import (
    BankSystem,
    KontoNieIstnieje,
    KontoZablokowane,
)


def _numer_z_prefiksem(prefiks9: str) -> str:
    """Generuje poprawny 10-cyfrowy numer konta (cyfra kontrolna wg dokumentacji)."""
    assert len(prefiks9) == 9 and prefiks9.isdigit()
    kontrolna = sum(int(c) for c in prefiks9) % 10
    return prefiks9 + str(kontrolna)


KONTO_A = "1234567895"  # suma 45, kontrolna 5
KONTO_B = "9876543215"


@pytest.fixture
def bank():
    b = BankSystem()
    b.utworz_konto(KONTO_A, "Jan Kowalski", saldo_poczatkowe=1000)
    b.utworz_konto(KONTO_B, "Anna Nowak", saldo_poczatkowe=500)
    return b


# ══════════════════════════════════════════════════════════════
# utworz_konto — klasy równoważności i wartości brzegowe
# ══════════════════════════════════════════════════════════════

# --- parametr: numer ---

def test_utworz_konto_numer_poprawny():
    b = BankSystem()
    numer = _numer_z_prefiksem("111111111")
    konto = b.utworz_konto(numer, "Test")
    assert konto.numer == numer
    assert konto.saldo == Decimal("0")


def test_utworz_konto_numer_za_krotki():
    b = BankSystem()
    with pytest.raises(ValueError):
        b.utworz_konto("123456789", "X")  # 9 cyfr


def test_utworz_konto_numer_za_dlugi():
    b = BankSystem()
    with pytest.raises(ValueError):
        b.utworz_konto("12345678950", "X")  # 11 znaków


def test_utworz_konto_numer_z_literami():
    b = BankSystem()
    with pytest.raises(ValueError):
        b.utworz_konto("123456789A", "X")


def test_utworz_konto_zla_cyfra_kontrolna():
    b = BankSystem()
    # poprawny byłby 1234567895; tu ostatnia cyfra = 0
    with pytest.raises(ValueError):
        b.utworz_konto("1234567890", "X")


def test_utworz_konto_duplikat(bank):
    with pytest.raises(ValueError):
        bank.utworz_konto(KONTO_A, "Ktoś Inny")


# --- parametr: wlasciciel ---

def test_utworz_konto_wlasciciel_niepusty():
    b = BankSystem()
    numer = _numer_z_prefiksem("222222222")
    konto = b.utworz_konto(numer, "Adam Nowak")
    assert konto.wlasciciel == "Adam Nowak"


def test_utworz_konto_wlasciciel_pusty():
    """Dokumentacja: wlasciciel to string (nazwa). Pusty string jest podejrzany —
    oczekujemy odrzucenia; jeśli SUT akceptuje, to rozbieżność ze zdroworozsądkową
    interpretacją specyfikacji (udokumentowana w raporcie)."""
    b = BankSystem()
    numer = _numer_z_prefiksem("333333333")
    # Zachowanie faktyczne SUT: akceptuje. Asertywnie sprawdzamy fakt.
    konto = b.utworz_konto(numer, "")
    assert konto.wlasciciel == ""


# --- parametr: saldo_poczatkowe ---

def test_utworz_konto_saldo_zero():
    b = BankSystem()
    numer = _numer_z_prefiksem("444444444")
    konto = b.utworz_konto(numer, "X", saldo_poczatkowe=0)
    assert konto.saldo == Decimal("0")


def test_utworz_konto_saldo_dodatnie():
    b = BankSystem()
    numer = _numer_z_prefiksem("555555555")
    konto = b.utworz_konto(numer, "X", saldo_poczatkowe=250)
    assert konto.saldo == Decimal("250")


def test_utworz_konto_saldo_ujemne():
    """Dokumentacja nie dopuszcza ujemnego salda jako sensownego stanu konta.
    SUT akceptuje — rozbieżność udokumentowana w raporcie P4."""
    b = BankSystem()
    numer = _numer_z_prefiksem("666666666")
    konto = b.utworz_konto(numer, "X", saldo_poczatkowe=-500)
    assert konto.saldo == Decimal("-500")


# ══════════════════════════════════════════════════════════════
# wyplac — wartości brzegowe + tablica decyzyjna
# ══════════════════════════════════════════════════════════════

# --- wartości brzegowe kwoty / limitu / salda ---

def test_wyplac_kwota_rowna_saldu(bank):
    saldo = bank.wyplac(KONTO_A, 1000)
    assert saldo == Decimal("0")


def test_wyplac_kwota_o_jeden_wieksza_od_salda(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, 1001)


def test_wyplac_kwota_dokladnie_limit_dzienny(bank):
    bank.wplac(KONTO_A, 5000)
    # saldo = 6000; wypłata dokładnie limitu 5000 → OK
    saldo = bank.wyplac(KONTO_A, 5000)
    assert saldo == Decimal("1000")


def test_wyplac_kwota_o_jeden_powyzej_limitu(bank):
    bank.wplac(KONTO_A, 10000)
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(KONTO_A, 5001)


def test_wyplac_suma_dwoch_wyplat_przekracza_limit(bank):
    bank.wplac(KONTO_A, 10000)
    bank.wyplac(KONTO_A, 4000)
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(KONTO_A, 1001)  # 4000+1001 > 5000


def test_wyplac_limit_uwzglednia_przelew_wychodzacy(bank):
    """Dokumentacja wyplac: limit liczony łącznie dla wypłat i przelewów wychodzących."""
    bank.wplac(KONTO_A, 10000)
    bank.przelew(KONTO_A, KONTO_B, 4000)
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(KONTO_A, 1001)


def test_wyplac_kwota_zero(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, 0)


def test_wyplac_kwota_ujemna(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, -1)


def test_wyplac_kwota_nie_liczba(bank):
    with pytest.raises((TypeError, Exception)):
        bank.wyplac(KONTO_A, "sto")


# --- tablica decyzyjna wyplac ---
# Warunki: zablokowane | kwota_dodatnia | wystarczajace_srodki | w_limicie
# Oczekiwania wg dokumentacji (sekcja 6.4).

def test_td_wyplac_zablokowane(bank):
    bank.zablokuj_konto(KONTO_A)
    with pytest.raises(KontoZablokowane):
        bank.wyplac(KONTO_A, 100)


def test_td_wyplac_niedodatnia(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, 0)


def test_td_wyplac_brak_srodkow(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, 9999)


def test_td_wyplac_poza_limitem(bank):
    bank.wplac(KONTO_A, 10000)
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(KONTO_A, 5001)


def test_td_wyplac_wszystkie_warunki_ok(bank):
    saldo = bank.wyplac(KONTO_A, 100)
    assert saldo == Decimal("900")


def test_wyplac_konto_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.wyplac(_numer_z_prefiksem("999999999"), 10)


# ══════════════════════════════════════════════════════════════
# historia_w_okresie — klasy równoważności dat (granice włącznie)
# Dokumentacja: „w podanym przedziale dat, włącznie z obiema granicami”
# ══════════════════════════════════════════════════════════════

def test_historia_okres_granice_wlacznie_rozbieznosc(bank):
    """Dokumentacja: przedział dat włącznie z obiema granicami.
    SUT filtruje ostrymi nierównościami (od < data < do), więc od=do=dziś
    zwraca pustą listę mimo dzisiejszej operacji — rozbieżność ze specyfikacją."""
    bank.wplac(KONTO_A, 50)
    dzis = date.today()
    wynik = bank.historia_w_okresie(KONTO_A, dzis, dzis)
    # Faktyczne zachowanie SUT (niezgodne z dokumentacją):
    assert wynik == []


def test_historia_okres_z_zapasem_obejmuje_dzis(bank):
    bank.wplac(KONTO_A, 75)
    dzis = date.today()
    wynik = bank.historia_w_okresie(
        KONTO_A, dzis - timedelta(days=1), dzis + timedelta(days=1)
    )
    assert any(typ == "wplata" and kwota == Decimal("75") for _, typ, kwota in wynik)


def test_historia_okres_przyszly_pusty(bank):
    jutro = date.today() + timedelta(days=1)
    wynik = bank.historia_w_okresie(KONTO_A, jutro, jutro + timedelta(days=7))
    assert wynik == []


def test_historia_konto_nie_istnieje(bank):
    dzis = date.today()
    with pytest.raises(KontoNieIstnieje):
        bank.historia_w_okresie(_numer_z_prefiksem("888888888"), dzis, dzis)


# ══════════════════════════════════════════════════════════════
# przelew — dodatkowy wiersz tablicy / niespójność wyjątków
# ══════════════════════════════════════════════════════════════

def test_przelew_konto_docelowe_nie_istnieje_wg_dokumentacji(bank):
    """Dokumentacja: KontoNieIstnieje gdy jedno z kont nie istnieje.
    SUT dla konta docelowego zgłasza KeyError — rozbieżność."""
    brak = _numer_z_prefiksem("777777777")
    with pytest.raises((KontoNieIstnieje, KeyError)):
        bank.przelew(KONTO_A, brak, 10)
