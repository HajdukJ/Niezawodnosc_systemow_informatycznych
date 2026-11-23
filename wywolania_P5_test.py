# python -m pytest wywolania_P5_test.py -v -s

import threading
import time
from decimal import Decimal
from zespol_C import BankSystem

NR_SEKWENCYJNY = "1234567895"
NR_ROWNOLEGLE = "9876543215"
LICZBA_OPERACJI = 10_000
LICZBA_WATKOW = 10
LICZBA_POWTORZEN = 20
KWOTA = Decimal("1")


def wplaty(bank, numer, ile):
    for _ in range(ile):
        bank.wplac(numer, KWOTA)


def test_obciazenie():
    sekwencyjny = BankSystem()
    sekwencyjny.utworz_konto(NR_SEKWENCYJNY, "Sekwencja", 0)

    start = time.perf_counter()
    wplaty(sekwencyjny, NR_SEKWENCYJNY, LICZBA_OPERACJI)
    czas_sekwencyjny = time.perf_counter() - start

    rownolegly = BankSystem()
    rownolegly.utworz_konto(NR_ROWNOLEGLE, "Rownolegle", 0)
    na_watek = LICZBA_OPERACJI // LICZBA_WATKOW

    watki = [
        threading.Thread(
            target=wplaty,
            args=(rownolegly, NR_ROWNOLEGLE, na_watek)
        )
        for _ in range(LICZBA_WATKOW)
    ]

    start = time.perf_counter()
    for watek in watki:
        watek.start()
    for watek in watki:
        watek.join()
    czas_rownolegly = time.perf_counter() - start

    przepustowosc_sekwencyjna = LICZBA_OPERACJI / czas_sekwencyjny
    przepustowosc_rownolegla = LICZBA_OPERACJI / czas_rownolegly
    oczekiwane = Decimal(LICZBA_OPERACJI)

    assert sekwencyjny.konta[NR_SEKWENCYJNY].saldo == oczekiwane
    assert rownolegly.konta[NR_ROWNOLEGLE].saldo == oczekiwane

    print(
        f"\n{LICZBA_OPERACJI} wplat sekwencyjnie: "
        f"{czas_sekwencyjny:.4f} s "
        f"({przepustowosc_sekwencyjna:.0f} op/s)"
    )
    print(
        f"{LICZBA_OPERACJI} wplat rownolegle "
        f"({LICZBA_WATKOW} watkow): "
        f"{czas_rownolegly:.4f} s "
        f"({przepustowosc_rownolegla:.0f} op/s)"
    )


def test_wspolbieznosc():
    poprawne = 0

    for numer in range(1, LICZBA_POWTORZEN + 1):
        bank = BankSystem()
        bank.utworz_konto(NR_ROWNOLEGLE, "Wspolbieznosc", 0)

        start = threading.Barrier(LICZBA_WATKOW)

        def wykonaj_wplate():
            start.wait()
            wplaty(bank, NR_ROWNOLEGLE, 100)

        watki = [
            threading.Thread(target=wykonaj_wplate)
            for _ in range(LICZBA_WATKOW)
        ]

        for watek in watki:
            watek.start()
        for watek in watki:
            watek.join()

        oczekiwane = Decimal(LICZBA_WATKOW * 100)
        saldo = bank.konta[NR_ROWNOLEGLE].saldo

        if saldo == oczekiwane:
            poprawne += 1

        print(
            f"Powtorzenie {numer}: "
            f"saldo={saldo}, oczekiwano={oczekiwane}"
        )

    print(
        f"\nWspolbieznosc: {poprawne}/{LICZBA_POWTORZEN} "
        "przebiegow poprawnych"
    )

    assert poprawne == LICZBA_POWTORZEN