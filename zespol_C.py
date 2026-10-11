"""
System zarzadzania kontem bankowym
Wariant: Zespol C
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import date
import threading
import time
import random

LIMIT_DZIENNY_WYPLAT = Decimal("5000")

# ===================== LOGGER AWARII =====================
import functools
import json

LOG_PATH = "awarie.jsonl"
LOGI = []                 # wszystkie wpisy w pamieci
START = time.time()
open(LOG_PATH, "w", encoding="utf-8").close()   # czyscimy plik przy starcie


def loguj(funkcja):
    """Dekorator: zapisuje KAZDE wywolanie metody (OK albo wyjatek)."""
    @functools.wraps(funkcja)
    def wrapper(*args, **kwargs):
        t = time.time()
        wpis = {
            "nr": len(LOGI) + 1,
            "timestamp": t,
            "t_od_startu_s": round(t - START, 6),
            "funkcja": funkcja.__name__,
            "args": repr(args[1:]),        # bez 'self'
            "kwargs": repr(kwargs),
        }
        try:
            wynik = funkcja(*args, **kwargs)
            wpis.update(status="OK", wynik=repr(wynik))
            return wynik
        except Exception as e:
            wpis.update(status="WYJATEK", typ_bledu=type(e).__name__, komunikat=str(e))
            raise
        finally:
            LOGI.append(wpis)
            with open(LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(wpis, ensure_ascii=False) + "\n")
    return wrapper


def wypisz_logi():
    print("\n===== LOGI =====")
    for w in LOGI:
        if w["status"] == "OK":
            print(f'#{w["nr"]:02d} t={w["t_od_startu_s"]:.6f}s OK       {w["funkcja"]}{w["args"]} -> {w["wynik"]}')
        else:
            print(f'#{w["nr"]:02d} t={w["t_od_startu_s"]:.6f}s WYJATEK  {w["funkcja"]}{w["args"]} -> {w["typ_bledu"]}: {w["komunikat"]}')
    bledy = sum(1 for w in LOGI if w["status"] == "WYJATEK")
    print(f"Razem wywolan: {len(LOGI)}, wyjatkow: {bledy}")
# =========================================================



class KontoNieIstnieje(Exception):
    """Wyjatek zglaszany, gdy operacja dotyczy nieistniejacego numeru konta."""
    pass


class ProcesorNiedostepny(Exception):
    """Wyjatek symulujacy niedostepnosc zewnetrznego procesora platnosci."""
    pass


class ZewnetrznyProcesor:
    def __init__(self, prawdopodobienstwo_awarii=0.3, opoznienie_s=0.0, generator=None):
        self.prawdopodobienstwo_awarii = prawdopodobienstwo_awarii
        self.opoznienie_s = opoznienie_s
        self._generator = generator or random.Random()
        self.licznik_wywolan = 0

    def wyslij_przelew(self, numer_konta_docelowego, kwota):
        self.licznik_wywolan += 1
        if self.opoznienie_s:
            time.sleep(self.opoznienie_s)
        if self._generator.random() < self.prawdopodobienstwo_awarii:
            raise ProcesorNiedostepny("Zewnetrzny procesor platnosci nie odpowiada")
        return {"status": "zaksiegowano", "numer_referencyjny": f"REF{self.licznik_wywolan:06d}"}


class KontoZablokowane(Exception):
    """Wyjatek zglaszany przy probie operacji na zablokowanym koncie."""
    pass


class Konto:
    def __init__(self, numer, wlasciciel, saldo_poczatkowe=0):
        self.numer = numer
        self.wlasciciel = wlasciciel
        self.saldo = Decimal(str(saldo_poczatkowe))
        self.historia = []
        self.status = "aktywne"

    def dodaj_wpis(self, typ, kwota, data_operacji=None):
        if data_operacji is None:
            data_operacji = date.today()
        self.historia.append((data_operacji, typ, kwota))


class BankSystem:
    def __init__(self):
        self.konta = {}
        self._lock = threading.Lock()

    @staticmethod
    def _numer_poprawny(numer):
        if not isinstance(numer, str) or len(numer) != 10 or not numer.isdigit():
            return False
        cyfry = [int(c) for c in numer]
        suma_kontrolna = sum(cyfry[:9]) % 10
        return cyfry[9] == suma_kontrolna

    @loguj
    def utworz_konto(self, numer, wlasciciel, saldo_poczatkowe=0):
        if not self._numer_poprawny(numer):
            raise ValueError("Nieprawidlowy numer konta")
        if numer in self.konta:
            raise ValueError(f"Konto {{numer}} juz istnieje")
        konto = Konto(numer, wlasciciel, saldo_poczatkowe)
        self.konta[numer] = konto
        return konto

    def _pobierz_konto(self, numer):
        if numer not in self.konta:
            raise KontoNieIstnieje(f"Konto {numer} nie istnieje")
        return self.konta[numer]

    @loguj
    def zablokuj_konto(self, numer):
        konto = self._pobierz_konto(numer)
        konto.status = "zablokowane"

    @loguj
    def odblokuj_konto(self, numer):
        konto = self._pobierz_konto(numer)
        konto.status = "aktywne"

    def _suma_dzisiejszych_wyplat(self, konto):
        dzis = date.today()
        suma = Decimal("0")
        for data_operacji, typ, kwota in konto.historia:
            if data_operacji == dzis and typ in ("wyplata", "przelew_wychodzacy"):
                suma += kwota
        return suma

    @loguj
    def wplac(self, numer, kwota):
        konto = self._pobierz_konto(numer)
        if not isinstance(kwota, (int, float, Decimal)):
            raise TypeError("Kwota musi byc liczba")
        kwota = Decimal(str(kwota))
        if kwota <= 0:
            raise ValueError("Kwota wplaty musi byc dodatnia")
        konto.saldo += kwota
        konto.dodaj_wpis("wplata", kwota)
        return konto.saldo

    @loguj
    def wyplac(self, numer, kwota):
        konto = self._pobierz_konto(numer)
        if konto.status == "zablokowane":
            raise KontoZablokowane(f"Konto {numer} jest zablokowane")
        kwota = Decimal(str(kwota))
        if kwota <= 0:
            raise ValueError("Kwota wyplaty musi byc dodatnia")
        if kwota > konto.saldo:
            raise ValueError("Niewystarczajace srodki na koncie")
        if self._suma_dzisiejszych_wyplat(konto) + kwota > LIMIT_DZIENNY_WYPLAT:
            raise ValueError("Przekroczono dzienny limit wyplat")
        konto.saldo -= kwota
        konto.dodaj_wpis("wyplata", kwota)
        return konto.saldo

    @loguj
    def przelew(self, numer_z, numer_do, kwota):
        konto_z = self._pobierz_konto(numer_z)
        konto_do = self.konta[numer_do]
        if konto_z.status == "zablokowane":
            raise KontoZablokowane(f"Konto {{numer_z}} jest zablokowane")
        kwota = Decimal(str(kwota))
        with self._lock:
            if kwota <= 0:
                raise ValueError("Kwota przelewu musi byc dodatnia")
            if kwota > konto_z.saldo:
                raise ValueError("Niewystarczajace srodki na koncie zrodlowym")
            if kwota > Decimal("1000000"):
                raise ValueError("Przelew przekracza dzienny limit systemowy")
            konto_z.saldo -= kwota
            konto_do.saldo += kwota
            konto_z.dodaj_wpis("przelew_wychodzacy", kwota)
            konto_do.dodaj_wpis("przelew_przychodzacy", kwota)
        return konto_z.saldo

    @loguj
    def nalicz_odsetki(self, numer, roczna_stopa_procentowa, miesiace):
        konto = self._pobierz_konto(numer)
        stopa_miesieczna = Decimal(str(roczna_stopa_procentowa)) / Decimal("12") / Decimal("100")
        for _ in range(miesiace):
            odsetki = (konto.saldo * stopa_miesieczna).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            konto.saldo += odsetki
            konto.dodaj_wpis("odsetki", odsetki)
        return konto.saldo

    @loguj
    def historia_w_okresie(self, numer, od, do):
        konto = self._pobierz_konto(numer)
        wynik = []
        for data_operacji, typ, kwota in konto.historia:
            if od < data_operacji < do:
                wynik.append((data_operacji, typ, kwota))
        return wynik

    @loguj
    def wyciag_miesieczny(self, numer, rok, miesiac):
        konto = self._pobierz_konto(numer)
        wplaty = Decimal("0")
        wyplaty = Decimal("0")
        for data_operacji, typ, kwota in konto.historia:
            if data_operacji.year == rok and data_operacji.month == miesiac:
                if typ in ("wplata", "przelew_przychodzacy", "odsetki"):
                    wplaty += kwota
                elif typ in ("wyplata", "przelew_wychodzacy"):
                    wyplaty += kwota
        return {"wplaty": wplaty, "wyplaty": wyplaty, "saldo_koncowe": konto.saldo}

    @loguj
    def przelew_zewnetrzny(self, numer_z, numer_konta_docelowego_zewn, kwota, procesor=None):
        konto_z = self._pobierz_konto(numer_z)
        if konto_z.status == "zablokowane":
            raise KontoZablokowane(f"Konto {numer_z} jest zablokowane")
        kwota = Decimal(str(kwota))
        if kwota <= 0:
            raise ValueError("Kwota przelewu musi byc dodatnia")
        if kwota > konto_z.saldo:
            raise ValueError("Niewystarczajace srodki na koncie zrodlowym")
        proc = procesor or ZewnetrznyProcesor()
        wynik = proc.wyslij_przelew(numer_konta_docelowego_zewn, kwota)
        konto_z.saldo -= kwota
        konto_z.dodaj_wpis("przelew_zewnetrzny", kwota)
        return wynik


def _demo():
    """Oryginalny skrypt demonstracyjny z konca pliku (przeniesiony z poziomu modulu,
    zeby import sut nie wykonywal operacji i nie konczyl sie wyjatkiem)."""
    global bank
    bank = BankSystem()
    bank.utworz_konto("1234567895", "Jan Kowalski", saldo_poczatkowe=1000)
    bank.utworz_konto("9876543215", "Anna Nowak")
    bank.wplac("1234567895", 500)
    bank.wyplac("1234567895", 200)
    bank.przelew("1234567895", "9876543215", 300)
    print(bank.konta["1234567895"].saldo)
    print(bank.konta["9876543215"].saldo)
    bank.nalicz_odsetki("1234567895", roczna_stopa_procentowa=4, miesiace=3)
    bank.przelew("1234567895", "9876543215", 800)
    bank.nalicz_odsetki("1234567895", roczna_stopa_procentowa=4, miesiace=3)
    print(bank.konta["1234567895"].saldo)
    bank.przelew("1234567895", "9876543215", 300)


if __name__ == "__main__":
    try:
        _demo()
    finally:
        wypisz_logi()