# Profile kategorii sprzedażowych

Profile są częścią działania programu, a nie tylko podpowiedzią dla użytkowniczki.
`config/category_profiles.yaml` dopisuje do planu wyszukiwania pola identyfikacyjne,
pułapki wariantów, wykluczenia i reguły prywatności. Nadal obowiązuje zasada: cecha
staje się faktem dopiero po zatwierdzeniu przez człowieka.

## Obiektywy Fujifilm X

Najpierw trzeba przepisać pełne oznaczenie z tubusu. `XF 23mm F1.4 R`,
`XF 23mm F1.4 R LM WR` i `XF 23mm F2 R WR` to trzy różne produkty. Bot pyta o:

- pełną nazwę, mocowanie X oraz wersję I/II;
- stan optyki: rysy, grzyb, mgła i pył;
- AF, pierścienie, przysłonę, OIS i mechanikę zoomu;
- dekielki, osłonę, filtr, pudełko i dowód zakupu.

Do wyceny nie wolno mieszać korpusów, adapterów, samych dekielków, części ani innej
wersji obiektywu. Oznaczenia XF/XC oraz R, WR, OIS, LM, PZ i Macro są cechami
porównywalności, nie ozdobnikami tytułu. Oficjalny katalog potwierdza, że XF i XC
należą do systemu X i pokazuje pełne nazewnictwo wariantów:
[Fujifilm X lenses](https://www.fujifilm-x.com/en-us/products/lenses/).

## Nintendo Switch — konsole

Bot odróżnia Switch, Switch OLED i Switch Lite oraz pyta o kod modelu, pamięć,
Joy-Cony, dock, ładowarkę, przewody, pudełko, stan ekranu i drift analogów. Lite nie
jest cenowym odpowiednikiem OLED, a sam dock lub zestaw Joy-Conów nie jest konsolą.

Przed sprzedażą trzeba usunąć konto i wykonać reset. Pełny numer seryjny nie trafia
do zapytań ani ogłoszenia. Oficjalne FAQ opisuje trzy rodziny sprzętu i ograniczenie
Lite do gier obsługujących tryb przenośny:
[Nintendo Switch FAQ](https://www.nintendo.com/us/gaming-systems/switch/faq/).

## Nintendo Switch — gry

Tożsamość gry obejmuje dokładny tytuł, edycję, nośnik, pudełko, region i ewentualny
zużyty kod/DLC. Samo pudełko, kod cyfrowy, konto i wydanie na inną platformę są
odrzucane. Kartridże są co do zasady niezależne od regionu poza Chinami, ale DLC może
zależeć od regionu — dlatego region nadal jest użytecznym polem:
[Nintendo Support](https://en-americas-support.nintendo.com/app/answers/detail/a_id/22283/).

## Elektronika Apple

Do ceny potrzebne są rodzina produktu, dokładny wariant, numer modelu Axxxx, rok,
chip, RAM, pamięć, ekran, bateria i komplet. Podobna nazwa handlowa nie wystarcza —
np. kolejne generacje MacBooka Air mają różne parametry i cenę.

Numer seryjny może pomóc właścicielce w identyfikacji, ale pełny numer oraz IMEI są
automatycznie usuwane z danych przeznaczonych do wyszukiwarki. Przed sprzedażą należy
wyłączyć Find My/blokadę aktywacji i wyczyścić urządzenie. Oficjalna instrukcja Apple
pokazuje identyfikację modelu po danych systemowych, numerze seryjnym lub numerze
części: [Identify your MacBook](https://support.apple.com/en-euro/102767).

## Jak rozwijać profile

Nową kategorię dodajemy dopiero po zebraniu słownika wariantów i co najmniej kilku
par pułapek „podobne, ale nieporównywalne”. Każda zmiana dostaje przypadek golden:
identyfikacja faktów, audyt porównywalności i bezpieczny opis. Profile nie kodują cen;
kodują warunki, pod jakimi obserwowana cena jest sensownym dowodem.
