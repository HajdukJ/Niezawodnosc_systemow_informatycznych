# python -m pytest wywolania_P2_test.py --cov=zespol_C --cov-report=html

import pytest
from decimal import Decimal
from zespol_C import BankSystem, KontoNieIstnieje, KontoZablokowane, ZewnetrznyProcesor, ProcesorNiedostepny

KONTO_A = "1234567895"
KONTO_B = "9876543215"

@pytest.fixture
def bank():
    b = BankSystem()
    b.utworz_konto(KONTO_A, "Jan Kowalski", saldo_poczatkowe=1000)
    b.utworz_konto(KONTO_B, "Anna Nowak", saldo_poczatkowe=500)
    return b


# ── wplac ────────────────────────────────────────────────────

def test_wplac_poprawna(bank):
    saldo = bank.wplac(KONTO_A, 200)
    assert saldo == Decimal("1201")

def test_wplac_kwota_zero(bank):
    with pytest.raises(ValueError):
        bank.wplac(KONTO_A, 0)

def test_wplac_kwota_ujemna(bank):
    with pytest.raises(ValueError):
        bank.wplac(KONTO_A, -100)

def test_wplac_zly_typ(bank):
    with pytest.raises(TypeError):
        bank.wplac(KONTO_A, "sto")

def test_wplac_konto_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.wplac("1111111113", 100)


# ── wyplac ───────────────────────────────────────────────────

def test_wyplac_poprawna(bank):
    saldo = bank.wyplac(KONTO_A, 300)
    assert saldo == Decimal("700")

def test_wyplac_konto_zablokowane(bank):
    bank.zablokuj_konto(KONTO_A)
    with pytest.raises(KontoZablokowane):
        bank.wyplac(KONTO_A, 100)

def test_wyplac_kwota_zero(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, 0)

def test_wyplac_kwota_ujemna(bank):
    with pytest.raises(ValueError):
        bank.wyplac(KONTO_A, -50)

def test_wyplac_niewystarczajace_srodki(bank):
    with pytest.raises(ValueError, match="Niewystarczajace"):
        bank.wyplac(KONTO_A, 9999)

def test_wyplac_przekroczony_limit_dzienny(bank):
    bank.wplac(KONTO_A, 10000)
    bank.wyplac(KONTO_A, 4000)
    with pytest.raises(ValueError, match="limit"):
        bank.wyplac(KONTO_A, 2000)

def test_wyplac_konto_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.wyplac("1111111113", 100)


# ── przelew ──────────────────────────────────────────────────

def test_przelew_poprawny(bank):
    saldo = bank.przelew(KONTO_A, KONTO_B, 250)
    assert saldo == Decimal("750")
    assert bank.konta[KONTO_B].saldo == Decimal("750")

def test_przelew_kwota_zero(bank):
    with pytest.raises(ValueError):
        bank.przelew(KONTO_A, KONTO_B, 0)

def test_przelew_kwota_ujemna(bank):
    with pytest.raises(ValueError):
        bank.przelew(KONTO_A, KONTO_B, -20)

def test_przelew_niewystarczajace_srodki(bank):
    with pytest.raises(ValueError, match="Niewystarczajace"):
        bank.przelew(KONTO_A, KONTO_B, 2000)

def test_przelew_konto_zablokowane(bank):
    bank.zablokuj_konto(KONTO_A)
    with pytest.raises(KontoZablokowane):
        bank.przelew(KONTO_A, KONTO_B, 100)

def test_przelew_przekroczony_limit_systemowy(bank):
    bank.konta[KONTO_A].saldo = Decimal("2000000")
    with pytest.raises(ValueError, match="limit systemowy"):
        bank.przelew(KONTO_A, KONTO_B, 1000001)

def test_przelew_konto_zrodlowe_nie_istnieje(bank):
    with pytest.raises(KontoNieIstnieje):
        bank.przelew("1111111113", KONTO_B, 100)

def test_przelew_konto_docelowe_nie_istnieje(bank):
    with pytest.raises(KeyError):
        bank.przelew(KONTO_A, "1111111113", 100)

def test_przelew_na_to_samo_konto(bank):
    saldo_przed = bank.konta[KONTO_A].saldo
    saldo = bank.przelew(KONTO_A, KONTO_A, 100)
    assert saldo == saldo_przed
    assert bank.konta[KONTO_A].saldo == saldo_przed

# ── P3 do zabijania mutantów ──────────────────────────────────

# sprawdza że wynik nie jest None
def test_przelew_zewnetrzny_zwraca_wynik(bank):
    procesor = ZewnetrznyProcesor(prawdopodobienstwo_awarii=0.0)
    wynik = bank.przelew_zewnetrzny(KONTO_A, "DE123", 100, procesor=procesor)
    assert wynik["status"] == "zaksiegowano"

# sprawdza że procesor rzuca wyjątek gdy zawsze pada
def test_przelew_zewnetrzny_procesor_niedostepny(bank):
    procesor = ZewnetrznyProcesor(prawdopodobienstwo_awarii=1.0)
    with pytest.raises(ProcesorNiedostepny):
        bank.przelew_zewnetrzny(KONTO_A, "DE123", 100, procesor=procesor)