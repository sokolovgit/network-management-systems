# Системи управління мережами (СУМ)

Навчальний репозиторій: КПІ, ФІОТ, 4 курс, 1 семестр. Методички лаб від
В. А. Нікітіна (судячи з промптів `vnikitin@vnikitin` на скрінах).

## Ключові домовленості

- **Лаби виконуються по-справжньому:** команди запускаються в Debian-машині OrbStack,
  скріни знімаються з реального вікна Terminal.app. Ніяких згенерованих «терміналів».
  ЛР1–2 зняті Shottr (активне вікно), з ЛР3 – фоново через `screencapture -l`
  (неактивне вікно: сірі кнопки, порожній курсор), щоб Terminal не вискакував наперед.
- **Заголовок вікна зі скріну не прибирати.** Там видно `qwertannov@sum`, це доказ,
  що лабу виконував користувач.
- **Усі скріни одного розміру:** одне вікно 112×20, висоту під вивід не підганяти.
  Перед кожним кроком `clear`, тому команди завжди починаються згори.
- **Виділення: червона рамка (`-b`),** як у методичках. Тільки на справді важливому
  (`UP`, `metric`, `ttl 64`, `100% packet loss`), не більше 1–2 на скрін. Стрілка (`-a`)
  лише коли рамкою нема що обвести.
- **Економія токенів:** результат кроку перевіряти по тексту, який друкує `termshot step`.
  Картинку відкривати вибірково: скріни з рамками або якщо щось підозріле.
  Незалежні кроки виконувати одним викликом Bash.
- **Нова сесія на кожну лабу.**
- Звіт: скіл `kpi-lab-report`. Вимоги методички до звіту: назва, мета, постановка
  завдання й алгоритм розв'язання, хід виконання зі скрінами, відповіді на контрольні.
  У звіті одним рядком вказати середовище: Debian 12 (OrbStack, macOS).
- Ніколи не комітити й не пушити без явного прохання.

## Середовище

- Машина OrbStack `sum`: Debian 12 bookworm, arm64. Доставлено `ifupdown`, `net-tools`,
  `tcpdump`, `vim`. Нові пакети ставити через
  `orb run -m sum -u root apt-get install -y …`.
- `eth0` машини налаштовує OrbStack через systemd-networkd: адреса 192.168.139.x,
  default-маршрут з `metric 1024`. Сам `eth0` не чіпати, інакше пропаде мережа.
  Всі експерименти робити на dummy-інтерфейсах.
- Службові дії, які не треба фотографувати (прибрати інтерфейс, перевірити стан),
  робити повз вікно: `orb run -m sum -u root <cmd>`.
- Якщо машина зламалась: `orb delete sum && orb create debian sum`, потім доставити пакети.

## Скріни: `tools/termshot.py`

```
uv run tools/termshot.py open         # нове вікно Terminal 112×20, root-shell у sum
uv run tools/termshot.py calibrate    # після open: міряє сітку символів для рамок
uv run tools/termshot.py run "cmd"    # виконати у вікні без скріну (--no-wait: у vim)
uv run tools/termshot.py shot out.png [-b …]   # зняти як є, без clear (напр. у vim)
uv run tools/termshot.py esc          # натиснути Esc у вікні (вихід з insert у vim)
uv run tools/termshot.py step labs/NN-slug/img/NN-name.png \
    -c "cmd1" -c "cmd2" -b ',(UP),' [-b '2:metric \d+'] [--no-wait-last]
```

- `step` робить `clear`, вводить команди, чекає на промпт після кожної, знімає вікно й
  малює рамки, потім друкує текст вікна. Команди йдуть через `do script … in window id`,
  фокус не потрібен.
- Знімок за замовчуванням фоновий: `screencapture -x -l <id>`. Перед ним скидається колір
  фону вкладки, бо неактивне вікно перемальовується частково й лишає «привидів» курсора
  (риски під першим символом рядка). `"capture": "shottr"` у `.termshot.json` повертає
  старий режим через Shottr; після зміни режиму потрібен `calibrate`.
- У нового вікна має бути видно панель вкладок (View → Show Tab Bar), інакше картинка
  на 56 px нижча, ніж у решти скрінів.
- `-b`/`-a` приймають regex по тексту вікна. Виділяється перша група або весь збіг.
  Префікс `N:` бере N-й збіг.
- Промпт `mininet>` теж розпізнається, `clear` у ньому йде як `sh clear`. `--timeout`
  у `step` для довгих команд (`apt-get`, `pingall`).
- `--no-wait-last`: остання команда не повертає промпт (`tcpdump`, `vim`).
  Наступний крок має завершити її сам (`C-c` тут не надіслати, тому краще
  `timeout 5 tcpdump …` або `ping -c 3`).
- Id вікна й калібрування лежать у `tools/.termshot.json` (не в гіті). Якщо вікно
  закрили або змінили шрифт, треба `open` і `calibrate` заново.
- У `/root/.bashrc` машини `sum` PS1 ставить заголовок вікна (`root@sum: ~/lab3`), а
  `LC_CTYPE=C.UTF-8` прибирає `?` замість `→` у `tshark`: Terminal передає з macOS
  некоректне `LC_CTYPE=UTF-8`.

## Скріни браузера: `tools/browsershot.py`

```
uv run tools/browsershot.py open URL      # окремий Chrome (профіль tools/.chrome-profile), CDP :9333
uv run tools/browsershot.py shot OUT.png [--url URL] [--py CODE] [--js CODE] [-b SELECTOR …]
uv run tools/browsershot.py js CODE       # виконати JS на сторінці, надрукувати результат
```

- Окремий профіль без закладок і акаунтів. Знімок фоновий: `screencapture -o -l`.
  Перед кожним знімком вікно повертається до 1280×800 через CDP, бо його можуть
  розгорнути руками.
- `--py` виконує код Playwright зі змінною `page` (кліки, `page.fill`, `page.check`).
  `-b` малює червону рамку навколо елемента за селектором Playwright.
- Chrome не резолвить `*.orb.local`: брати IP машини `sum` (192.168.139.71).

## Структура

```
docs/labs/LR01.pdf … LR07-08.pdf   методички, READ-ONLY
labs/NN-slug/img/                  скріни лаби (NN-name.png по порядку кроків)
labs/NN-slug/report/               звіт (kpi-lab-report)
tools/termshot.py                  автоматизація терміналу й скрінів
```

## Лаба 1: `labs/01-debian-network-config` (зроблено)

Скріни `img/01…22`, звіт `report/report.md` → `report/Соколов_Олександр_ІП-33_1.docx`
(`just report <ім'я>` з теки лаби). Залишений стан машини: `interfaces.d/eth1` (dummy,
10.1.1.125/8, `metric 2000`), `interfaces.d/eth2` (dummy через `pre-up`, 172.16.10.5/24),
скрипти `if-pre-up.d/eth1`, `if-post-down.d/eth1`. Опції `/proc/sys/net/ipv4` повернуті
до типових.

Нюанси: Terminal віддає текст без переносів, `termshot` сам ділить рядки по 112 для рамок.
Довгий рядок, який переноситься посеред виділення, обводиться двома рамками (`…$` і `^…`).
Перший `service networking restart` не підняв `allow-hotplug eth1`, другий підняв.

## Лаба 2: `labs/02-linux-network-tools` (зроблено)

Скріни `img/01…33`, звіт `report/report.md` → `report/Соколов_Олександр_ІП-33_2.docx`.
Docker стоїть усередині `sum` (`docker.io` + `docker-compose` 1.29 з Debian), не на
macOS: так промпт `root@sum` і заголовок вікна ті самі. Dockerfile і compose лежать у
`labs/02-…/lab2/` (ім'я теки = ім'я compose-проєкту `lab2`), у `sum` на них веде
симлінк `~/lab2`. `eth1` з ЛР1 вимкнено (`ifdown`), бо `10.1.1.125/8` перекривав
10.10/10.11. Контейнери перемикати у вікні через `exit` + `docker exec -it hostN bash`.

Нюанси: `termshot` розгортає табуляції перед пошуком рамок (`brctl show`). Після
перебудови мосту на іншому хості кілька секунд висить `FAILED` у ARP-кеші, перший пінг
може не пройти. `ifdown -a` у контейнері кладе `lo` і `eth0` (порти бріджу), не
використовувати. Клієнт `nc` без `-w 1` не виходить сам.

## Лаба 3: `labs/03-ssh-over-sctp` (зроблено)

Скріни `img/01…26`, файли в `labs/03-…/lab3/` (симлінк `~/lab3` у `sum`): Dockerfile
(додано `systemd`, `gcc`, `python3-dev`, `libsctp-dev` – без них не збирається pysctp і
нема `/usr/sbin/init`), compose з бріджем `br-lab3`, `server.py`/`client.py`, утиліта
`sctpcp.py` (3.4), дампи `*.pcap`. Модуль `sctp` ядра OrbStack вантажиться сам при першому
SCTP-сокеті. Wireshark замінює `tcpdump -w` на бріджі + `tshark -r` у `sum`
(`2>/dev/null` ховає попередження про root). Сценарій зйомки 01–22 – одним скриптом,
бо 04 (`compose up`) не повториш без перестворення контейнерів.

Нюанси: `server.py` скорочено на два порожні рядки, щоб влазив у 20 рядків. Перший
SSH-вхід (ключ хоста + юридична довідка Ubuntu) не влазить у вікно, тому знімається
другий. `nc localhost` іде на `::1`, а socat слухає тільки IPv4: брати `127.0.0.1`.
socat без `reuseaddr` не перезапускається на тому ж порту, поки той у TIME_WAIT.
`pysctp` віддає великі повідомлення частинами, межу визначає `MSG_EOR`; номер потоку
видно лише після `events.data_io = True`.

## Лаба 4: `labs/04-snmp` (зроблено)

Скріни `img/01…19`, звіт `report/report.md` → `report/Соколов_Олександр_ІП-33_4.docx`.
Файли в `labs/04-snmp/lab4/` (симлінк `~/lab4` у `sum`): Dockerfile, compose з бріджем
`br-lab4` (та сама підмережа 10.10.0.0/24, що в ЛР3, тому контейнери ЛР3 знято
`docker-compose down`), `monitor.sh` (4.4), `SOKOLOV-LAB4-MIB.txt` + `lab4mib.py` (4.5,
`pass` у `snmpd.conf` host1). У контейнери файли кладуться `docker cp` повз вікно.
SNMPv3-користувач `sokolov`, паролі `123456789`, рівень `authNoPriv`.

Нюанси: типовий `snmpd` у контейнері падає на `agentaddress … [::1]` (нема IPv6), крок
з `udp:161` це лікує. Перед `net-snmp-config --create-snmpv3-user` зупиняти `snmpd`.
`snmp-mibs-downloader` стоїть лише на host2. `snmpd` кешує `ifTable` кілька секунд, тому
моніторинг з інтервалом 1 с дає нулі й сплески – брати 5 с. Рамка `termshot` – тільки
в межах одного рядка; у `snmpset`/`snmpget` зі збігом у відповіді set і get брати `2:`.

## Лаба 5: `labs/05-ansible` (зроблено)

Скріни `img/01…39`, звіт `report/report.md` → `report/Соколов_Олександр_ІП-33_5.docx`.
Файли в `labs/05-ansible/lab5/` (симлінк `~/lab5` у `sum`): Dockerfile, compose з бріджем
`br-lab5` (контейнери ЛР4 знято `docker-compose down`), `playbook.yml` (4.3),
`configure_eth1.yml` (4.4), `monitor.sh` (3.4), `firewall.yml` (3.5, теги `firewall` і
`bandwidth`). На host1 вони лежать у `/root`, кладуться `docker cp`. Ansible 5.10 з PPA
(є індекс arm64), інвентар `server1 ansible_host=10.10.0.3`, SSH root за ключем.
Залишений стан host2: eth1 10.11.0.2/24, `icmp_echo_ignore_all=1`, iptables INPUT DROP,
`tbf 2mbit` на eth0, `iperf3 -s -D`.

Нюанси: `allow-hotplug` у контейнері не піднімається після `systemctl restart networking`
(нема udev), тому `auto eth1`. `gateway` на eth1 без `metric` ламає `ifup` (`File exists`).
Вивід плейбука має влазити в 20 рядків: `gather_facts: false`, задачі об'єднано, частини
запускаються через `--tags`. Зупинка `ssh` на host2 не робить його UNREACHABLE, поки живе
ControlPersist-сесія: треба `pkill sshd` і очистити `~/.ansible/cp`.

## Лаба 6: `labs/06-netmiko` (зроблено)

Скріни `img/01…26`, звіт `report/report.md` → `report/Соколов_Олександр_ІП-33_6.docx`.
Файли в `labs/06-netmiko/lab6/` (симлінк `~/lab6` у `sum`): Dockerfile (Netmiko 3.4.0 +
`cryptography==3.4.8`, `PermitRootLogin yes`), compose з бріджем `br-lab6` (контейнери ЛР5
знято), `mgmt.py` (4.2), `configure_eth1.py` (4.3), `ipparse.py` + `ifaces.py` +
`configure_eth1_v2.py` (3.4), `monitor.py` (3.5). Керуючий вузол – host2, скрипти в
`/root` (кладуться `docker cp`), керований – host1, root/`12345`. Залишений стан host1
після рестарту в 3.5: eth1 нема, ICMP увімкнено.

Нюанси: новіша `cryptography` на Python 3.8 друкує `CryptographyDeprecationWarning` на
кожен запуск. ENTRYPOINT `init`, тому разову перевірку образу робити через
`docker run --entrypoint python3`. `send_command` триває ~1 с. Монітор з падінням host1
довше за таймаут `termshot step`: дочекатися промпту і зняти `shot`. Оригінальний
`configure_eth1.py` лишає eth1 у стані DOWN, це й показує парсер.

## Лаба 7–8: `labs/07-sdn-openflow` (зроблено)

Одна методичка `LR07-08.pdf` і один звіт: скріни `img/01…35`, `report/report.md` →
`report/Соколов_Олександр_ІП-33_7-8.docx`. compose у `lab7/` (симлінк `~/lab7`): host1
ubuntu:20.04 (Mininet 2.2.2 + OVS 2.13.8 ставляться в контейнері), host2
`latarc/floodlight` (лише amd64, `platform: linux/amd64`, іде через Rosetta), порт
8080 опубліковано. Веб-інтерфейс: `http://192.168.139.71:8080/ui/pages/index.html`.
Друге вікно Terminal (підключення до host1/`sum`) – окремий `.termshot.json`: копію
стану перемикати руками.

Нюанси: модуль `openvswitch` вантажиться в `sum` (`apt install kmod; modprobe
openvswitch`), контейнер його не завантажить. `mn` зависає на «Adding hosts»: `mnexec`
закриває 2^30 дескрипторів, перед `mn` потрібен `ulimit -n 65536`. Firewall Floodlight –
білий список (увімкнений без правил ріже все, і ARP теж); правила перевіряються за
зростанням Priority (менше число – раніше). Форма firewall завжди шле `dl-type` і
протокол (без вибору – ICMP), тому ARP-правило додано через REST. ACL ставить у
комутатор постійний потік `priority=30000 … actions=drop`. Потоки Forwarding мають
`idle_timeout=5`. `ps` через пайп не обрізає рядки до 80 – додавати `cut`. Вивід `curl`
без `\n` ламає розпізнавання промпту – `; echo`.
