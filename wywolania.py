from datetime import date
from zespol_C import BankSystem, ZewnetrznyProcesor, wypisz_logi

bank = BankSystem()
A, B, C, D, F = "1234567895", "9876543215", "4444444446", "5555555555", "6666666664"
for num, saldo in [(A, 10000), (B, 0), (C, 0), (D, 0), (F, 20000)]:
    bank.utworz_konto(num, "Test", saldo)


def w(metoda, *args, **kwargs):
    try:
        return getattr(bank, metoda)(*args, **kwargs)
    except Exception:
        pass


dzis = date.today()

# --- utworz_konto ---
w("utworz_konto", "123", "X")                      # powinno: ValueError
w("utworz_konto", A, "X")                          # powinno: ValueError (duplikat)
w("utworz_konto", 1234567895, "X")                 # powinno: ValueError (numer nie-string)
w("utworz_konto", "1111111119", "")                # pusty wlasciciel
w("utworz_konto", "2222222228", "X", -500)         # ujemne saldo poczatkowe
w("utworz_konto", "3333333337", "X", "abc")        # saldo tekstowe

# --- wplac ---
w("wplac", B, -50)                                 # powinno: ValueError
w("wplac", B, "abc")                               # powinno: TypeError
w("wplac", B, 0.1 + 0.2)                           # saldo powinno wzrosnac o 0.30
w("wplac", C, 10**30 + 1)                          # bardzo duza kwota

# --- wyplac ---
w("wyplac", A, 5000)                               # dokladnie limit dzienny -> OK
w("wyplac", A, 1)                                  # powinno: ValueError (limit)
w("wyplac", B, "abc")                              # tekst
bank.zablokuj_konto(A)
w("wyplac", A, 10)                                 # powinno: KontoZablokowane
bank.odblokuj_konto(A)

# --- przelew ---
w("przelew", A, "0000000000", 10)                  # powinno: KontoNieIstnieje
w("przelew", A, A, 10)                             # przelew na to samo konto
w("przelew", F, B, 6000)                           # powyzej limitu dziennego 5000?
bank.zablokuj_konto(F)
w("przelew", F, B, 10)                             # powinno: KontoZablokowane (sprawdz komunikat)
bank.odblokuj_konto(F)

# --- odsetki ---
w("nalicz_odsetki", A, 4, 1)                       # poprawne naliczenie
w("nalicz_odsetki", A, 4, -3)                      # ujemna liczba miesiecy

# --- historia / wyciag / przelew zewnetrzny ---
w("historia_w_okresie", F, dzis, dzis)             # powinno zwrocic dzisiejsze wpisy
w("wyciag_miesieczny", A, 2020, 1)                 # saldo koncowe z 2020?

wypisz_logi()