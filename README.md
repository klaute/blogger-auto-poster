# Blogger Auto Poster

Automatischer Uploader für vorbereitete Markdown-Posts nach Blogger.

## Ablauf

- Aktive Markdown-Dateien liegen direkt in `posts/queue`.
- Geparkte Entwürfe liegen in `posts/queue/backlog` und werden nicht automatisch gepostet.
- Jede Datei enthält Frontmatter mit `title` und `labels`.
- Das Script veröffentlicht im konfigurierten Intervall genau den nächsten fälligen Post.
- Jede Markdown-Datei direkt in `posts/queue` darf verarbeitet werden.
- `posts/order.txt` bestimmt die Reihenfolge der vorbereiteten Blogposts.
- Erfolgreiche Dateien werden nach `posts/done` verschoben.
- Fehlgeschlagene Dateien bleiben standardmäßig in der Queue; bei nicht lesbaren Dateien werden sie nach `posts/failed` verschoben.

## Architektur

Die Software ist fachlich in kleine Module getrennt:

- `src/config.py`: YAML-Config laden.
- `src/markdown_posts.py`: Markdown-Dateien, Frontmatter, Labels, HTML-Rendering und Tracking-Marker.
- `src/state.py`: lokale Posting-State-Datei lesen, schreiben und aktualisieren.
- `src/scheduling.py`: Intervall-, Wochenplan- und Blogger-Zeitlogik.
- `src/notifications.py`: Pushover-Proxy und Benachrichtigungen.
- `src/blogger_api.py`: Google OAuth und Blogger-API-Aufrufe.
- `src/posting_runtime.py`: automatischer Posting-Zyklus, Queue-Verarbeitung und Dateiverschiebung.
- `src/post_management.py`: manuelle Management-Aktionen auf lokalen Posts und Blogger-Posts.
- `scripts/manage-posts.py`: interaktive Benutzereingabe, keine fachliche Kernlogik.
- `src/blogger_auto_poster.py`: CLI-Einstieg für den Docker-Container und Kompatibilitäts-Exports für alte Imports.

Die Trennung ist bewusst einfach: Benutzeroberfläche fragt nur Eingaben ab, Markdown-Logik kennt Blogger nicht, Blogger-API kennt keine interaktive Bedienung, und der Runtime-Loop orchestriert die einzelnen Bausteine.

## Projektstruktur

```text
.
├── config/
│   └── config.example.yml
├── posts/
│   ├── queue/
│   │   ├── backlog/
│   │   └── ignore/
│   ├── done/
│   ├── failed/
│   └── order.txt
├── scripts/
├── src/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

- `config/config.example.yml`: versionierte Beispielkonfiguration.
- `config/config.yml`: lokale echte Konfiguration, wird nicht committed.
- `credentials.json`: lokale Google-OAuth-Client-Datei, wird nicht committed.
- `posts/queue/`: aktive Markdown-Dateien, die vom Poster betrachtet werden.
- `posts/queue/backlog/`: geparkte Markdown-Dateien, die vom Poster und Management-Script nicht betrachtet werden.
- `posts/queue/ignore/`: Markdown-Dateien, die bewusst nicht gepostet werden.
- `posts/done/`: erfolgreich verarbeitete Markdown-Dateien.
- `posts/failed/`: nicht lesbare oder fehlerhafte Markdown-Dateien.
- `posts/order.txt`: gewünschte Reihenfolge für die Queue.
- `posts/state.json`: lokaler Upload-/Tracking-Status, wird nicht committed.
- `posts/last-*-test-result.json`: letzte Testberichte, werden nicht committed.

## Einrichtung

```sh
cp config/config.example.yml config/config.yml
```

Danach in `config/config.yml` die Blogger-Blog-ID setzen:

- `blogger.blog_id`

`client_id`, `client_secret` und `refresh_token` können aus `credentials.json` erzeugt beziehungsweise in die Config geschrieben werden.

Für lokale Python-Scripte gibt es ein venv-Setup:

```sh
scripts/update-venv.sh
```

Das Script baut `.venv` neu auf, installiert `requirements.txt` und prüft die wichtigsten Python-Einstiegspunkte. Am Ende zeigt es den Aktivierungsbefehl:

```sh
. .venv/bin/activate
```

Alternativ:

```sh
. scripts/load-venv.sh
```

Ein normal ausgeführtes Script kann die aufrufende Shell nicht dauerhaft selbst aktivieren; darum muss der `activate`- oder `load-venv.sh`-Befehl nach dem Neuaufbau einmal in der aktuellen Shell mit führendem Punkt ausgeführt werden. Ohne Aktivierung können lokale Tools direkt mit `.venv/bin/python ...` gestartet werden.

Der Blogger-OAuth-Scope ist:

```text
https://www.googleapis.com/auth/blogger
```

## Blogger Login / OAuth

Das Script loggt sich nicht mit Benutzername und Passwort ein. Blogger wird über Google OAuth 2.0 angesprochen. Die OAuth-Client-Datei heißt `credentials.json` und liegt lokal im Projektroot. Sie wird nicht committed.

Der Ablauf ist:

1. In Google Cloud ein Projekt anlegen oder ein vorhandenes nutzen.
2. Die Blogger API für dieses Projekt aktivieren.
3. Einen OAuth Client vom Typ `Desktop app` anlegen.
4. Die heruntergeladene Datei als `credentials.json` im Projektroot ablegen.
5. Einmalig lokal einen Refresh Token erzeugen.
6. `config/config.yml` automatisch mit `client_id`, `client_secret` und `refresh_token` aktualisieren.

Den Refresh Token erzeugt der Helper:

```sh
scripts/get_blogger_token.py
```

Das Script liest `credentials.json`, zeigt eine Google-Login-URL an und wartet lokal auf `http://127.0.0.1:8765/callback`. Nach der Freigabe schreibt es `client_id`, `client_secret` und `refresh_token` in:

```yaml
blogger:
  client_id: "..."
  client_secret: "..."
  refresh_token: "GOOGLE_OAUTH_REFRESH_TOKEN"
```

Der Refresh Token, `client_secret` und `credentials.json` sind Secrets und dürfen nicht committed werden. Darum sind `config/config.yml` und `credentials.json` in `.gitignore`; versioniert wird nur `config/config.example.yml`.

Wenn Google keinen Refresh Token ausgibt, wurde die App vermutlich schon einmal autorisiert. Dann entweder die bestehende App-Freigabe im Google-Konto entfernen oder den Helper erneut mit frischem Consent ausführen.

Wichtig: Der `code=...` Wert aus der Browser-Callback-URL ist nur ein temporärer Authorization Code. Er beginnt oft mit `4/...` und gehört nicht direkt in `config/config.yml`. In die Config gehört der Refresh Token, den `scripts/get_blogger_token.py` oder `scripts/extract-refresh-key.py` nach dem Token-Exchange schreibt.

Wenn du die Callback-URL vom Mac manuell kopierst, nutze:

```sh
scripts/extract-refresh-key.py
```

Das Tool fragt nach der Callback-URL oder dem `code=...` Wert, tauscht den Code gegen einen echten Refresh Token und aktualisiert `config/config.yml`. Es gibt nicht einfach den `4/...` Code aus.

Alternativ kann der Python-Helper direkt genutzt werden:

```sh
python -m src.oauth_setup --credentials-file credentials.json --update-config config/config.yml
```

Wenn der Container bereits läuft und `config/config.yml` geändert wurde, den Dauerprozess danach neu starten:

```sh
docker-compose restart blogger-auto-poster
```

Wenn das Script auf einem Server läuft und kein SSH-Tunnel genutzt werden soll:

```sh
scripts/extract-refresh-key.py
```

Dann die angezeigte URL auf dem Mac im Browser öffnen. Die Weiterleitung zu `http://127.0.0.1:8765/callback?...` darf im Browser fehlschlagen. Die komplette Callback-URL kopieren und im Server-Terminal einfügen. Das Script tauscht den `code=4/...` Wert gegen einen echten Refresh Token und schreibt ihn in `config/config.yml`.

## Config

Wichtige Felder in `config/config.yml`:

```yaml
blogger:
  blog_id: "BLOGGER_BLOG_ID"
  client_id: "GOOGLE_OAUTH_CLIENT_ID"
  client_secret: "GOOGLE_OAUTH_CLIENT_SECRET"
  refresh_token: "GOOGLE_OAUTH_REFRESH_TOKEN"

posting:
  input_dir: "/data/queue"
  done_dir: "/data/done"
  failed_dir: "/data/failed"
  state_file: "/data/state.json"
  order_file: "/data/order.txt"
  due_mode: "interval"
  interval_seconds: 604800
  check_interval_seconds: 3600
  dry_run: true
  dry_run_move_done: false
  publish_mode: "draft"
  schedule:
    weekday: "friday"
    time: "09:00"
    timezone: "Europe/Berlin"
  ignore_dirs:
    - "ignore"
    - "backlog"

tracking:
  marker_prefix: "blogger-auto-poster-source-id"
  remote_check_enabled: true
  update_existing_on_change: true
  remote_statuses:
    - "draft"
    - "live"
    - "scheduled"
  remote_max_pages_per_status: 10

notifications:
  pushover:
    enabled: false
    host: "pushover-app-server"
    port: 8090
    mode: "get"
    token: "PUSHOVER_APP_TOKEN"
    app_name: "Blogger Auto Poster"
    dedupe_prefix: "blogger-auto-poster"
    timeout_seconds: 10
```

- `blogger.blog_id`: numerische Blogger-Blog-ID.
- `blogger.client_id`: Google OAuth Client ID.
- `blogger.client_secret`: Google OAuth Client Secret.
- `blogger.refresh_token`: dauerhafter Token, mit dem das Script neue Access Tokens holen kann.
- `posting.input_dir`: Queue mit Markdown-Dateien.
- `posting.done_dir`: Zielordner für erfolgreich gepostete Dateien.
- `posting.failed_dir`: Zielordner für nicht lesbare Dateien.
- `posting.state_file`: merkt sich den letzten erfolgreichen Post-Zeitpunkt.
- `posting.order_file`: feste Reihenfolge für die Queue.
- `posting.due_mode`: `interval` nutzt `interval_seconds`; `weekly_schedule` lädt nur am konfigurierten Wochentag zur konfigurierten Uhrzeit hoch.
- `posting.interval_seconds`: Abstand zwischen zwei Posts, `604800` ist eine Woche.
- `posting.check_interval_seconds`: wie oft der laufende Container prüft, ob der nächste Post fällig ist.
- `posting.dry_run`: wenn `true`, wird nichts zu Blogger hochgeladen.
- `posting.dry_run_move_done`: verschiebt im Dry-Run trotzdem nach `done`; normalerweise `false` lassen.
- `posting.publish_mode`: `draft` erzeugt Blogger-Entwürfe, `live` veröffentlicht direkt, `scheduled` erzeugt geplante Blogger-Posts.
- `posting.schedule.weekday`: Wochentag für `publish_mode: "scheduled"`, z.B. `friday` oder `freitag`.
- `posting.schedule.time`: Uhrzeit für geplante Posts im Format `HH:MM`.
- `posting.schedule.timezone`: Zeitzone für die Planung, z.B. `Europe/Berlin`.
- `posting.ignore_dirs`: Unterordner von `posting.input_dir`, die nicht gescannt werden; `ignore` und `backlog` bleiben dadurch aus dem Posting-Lauf heraus.
- `tracking.marker_prefix`: Prefix für den unsichtbaren HTML-Kommentar im Blogger-Post.
- `tracking.remote_check_enabled`: prüft vor dem Upload per Blogger API, ob die Quelle bereits existiert.
- `tracking.update_existing_on_change`: aktualisiert einen vorhandenen Blogger-Post/Draft, wenn dieselbe Quelldatei erneut in der Queue liegt und sich der Inhalt geändert hat.
- `tracking.remote_statuses`: Blogger-Statuswerte, die beim Remote-Check durchsucht werden.
- `tracking.remote_max_pages_per_status`: maximale API-Seiten pro Status beim Remote-Check.
- `notifications.pushover.enabled`: schaltet Pushover-Benachrichtigungen vor echten Blogger-Uploadversuchen ein.
- `notifications.pushover.host`: Hostname oder IP des internen Pushover-Proxys.
- `notifications.pushover.port`: HTTP-Port des Pushover-Proxys; im Pushover-Projekt ist `8090` der Standard.
- `notifications.pushover.mode`: `get` oder `post`, analog zum `MODE` im Pushover-Testscript.
- `notifications.pushover.token`: API-Token für den Pushover-Proxydienst.
- `notifications.pushover.app_name`: Titel der Pushover-Nachricht.
- `notifications.pushover.dedupe_prefix`: Prefix für stabile Dedupe-Keys gegen doppelte Benachrichtigungen.
- `notifications.pushover.timeout_seconds`: Timeout für den internen Pushover-Aufruf.

Optional kann statt `host`/`port` weiterhin `notifications.pushover.url` gesetzt werden. Dann muss sie direkt auf den `/send` Endpoint zeigen, z.B. `http://pushover-app-server:8090/send`. Wenn `host` gesetzt ist, haben `host` und `port` Vorrang vor einer eventuell noch vorhandenen alten `url`. Alte Pushover-Proxy-URLs mit Port `5000` werden intern auf den Projektstandard `8090` korrigiert.

Wenn Pushover aktiviert ist, sendet das Script vor jedem echten Blogger-Schreibzugriff eine Nachricht. Das gilt für normale Posts mit `publish_mode: "draft"`, `publish_mode: "live"` oder `publish_mode: "scheduled"` und auch für den temporären Draft im Blogger-Verifikationstest. Zusätzlich sendet das Script Pushover-Fehlerhinweise, wenn ein Posting-Zyklus scheitert, ein Verifikations-Draft fehlschlägt oder eine Markdown-Datei nicht lesbar ist und nach `failed` verschoben wurde. Die Fehlernachricht enthält eine kurze Ursache und den nächsten Diagnosepunkt. Dry-Runs senden keine Upload-Start-Nachricht, weil dabei kein Uploadversuch gestartet wird. Ein fehlgeschlagener Pushover-Aufruf blockiert den Blogger-Upload nicht; der Fehler wird nur geloggt.

## Markdown-Struktur

Jeder Blogpost ist eine einzelne Markdown-Datei mit YAML-Frontmatter:

```markdown
---
title: "PowerMgr"
labels:
  - Smart Home
  - Energie
  - PV
---

# PowerMgr

## Zweck

...
```

Pflichtfelder:

- `title`: Blogger-Titel.
- `labels`: Blogger-Labels.
  Vor echten Blogger-Schreibzugriffen gleicht das Tool die Schreibweise mit bereits vorhandenen Blogger-Labels ab. Beispiel: Wenn auf dem Blog `Smart Home` existiert und lokal `smart home` steht, wird beim Upload `Smart Home` verwendet. Neue Labels sind erlaubt; sie werden nur getrimmt, whitespace-normalisiert und im Log als neu ausgewiesen.

Die lokale Freigabe erfolgt ausschließlich über Ordner:

- `posts/queue/`: aktive Posts; der Server darf diese Dateien verarbeiten.
- `posts/queue/backlog/`: geparkte Posts; der Server und das Management-Script sehen diese Dateien nicht.
- `posts/queue/ignore/`: bewusst ignorierte Posts oder Rohmaterial.
- `posts/done/`: lokal bereits verarbeitete Dateien. Diese Dateien können mit einem Blogger-Post verknüpft sein, müssen es aber nicht mehr, wenn der Remote-Post gelöscht wurde.

Labels werden bewusst im Markdown-Frontmatter gepflegt. Die Runtime-Config enthält keine Label-Regeln und ergänzt keine Labels automatisch. Bestehende Blogger-Labels dienen als Referenz für einheitliche Schreibweisen; die konkrete Entscheidung pro Artikel bleibt in der jeweiligen Markdown-Datei. Das Management-Script kann die aktuell auf Blogger vorhandenen Labels anzeigen.

Markdown-Dateien dürfen normale Markdown-Überschriften und Absätze enthalten. Der sichtbare Inhalt wird nach HTML gerendert; zusätzlich fügt das Tool einen unsichtbaren Tracking-Kommentar ein, damit ein vorhandener Blogger-Post später wiedergefunden und aktualisiert werden kann.

## Duplicate Tracking

Das Script trackt gepostete Quellen mit einer stabilen `source_id`, die aus dem Markdown-Dateinamen gebildet wird.

Beim erfolgreichen Posten wird die `source_id` in `posts/state.json` unter `posted_posts` gespeichert. Zusätzlich schreibt das Script einen unsichtbaren HTML-Kommentar in den Blogger-Post:

```html
<!-- blogger-auto-poster-source-id: example-post.md:... -->
```

Vor einem echten Upload prüft das Script:

1. Gibt es die `source_id` bereits lokal in `posts/state.json`?
2. Falls nicht: findet die Blogger API in `draft`, `live` oder `scheduled` bereits einen Post mit diesem Marker?
3. Wenn ein bestehender Post gefunden wird und `tracking.update_existing_on_change: true` gesetzt ist, wird der bestehende Blogger-Post aktualisiert.
4. Nur wenn kein bestehender Post gefunden wird, wird ein neuer Post erzeugt.

Wenn ein existierender Post erkannt oder aktualisiert wird, wird die Markdown-Datei nach `posts/done/` verschoben und der Fund in `posts/state.json` nachgetragen. Dadurch wird derselbe Quell-Post nicht doppelt erzeugt.

Einen Reupload für eine korrigierte Datei triggert man bewusst über das Management-Tool:

```sh
scripts/manage-posts.py --config config/config.yml
```

Dort die Update-Aktion wählen. Das Tool aktualisiert den vorhandenen Blogger-Post mit demselben Marker. Die lokale Datei bleibt dort, wo sie liegt; bei normalen Serverläufen wird sie nach erfolgreichem Upload nach `posts/done/` verschoben.

Wenn ein Blogger-Post extern oder über die Delete-Aktion gelöscht wurde, gibt es keine Blogger-Post-ID mehr. Dann kann der lokale `done` Artikel nicht mehr offline gestellt, veröffentlicht oder aktualisiert werden. Das Management-Script zeigt ihn als `not linked`. Für einen neuen Upload muss die Markdown-Datei bewusst wieder nach `posts/queue/` gelegt und dann über Aktion 1 neu hochgeladen werden.

## Post Management

Für manuelle Arbeit an der Queue gibt es ein interaktives Script:

```sh
scripts/manage-posts.py --config config/config.yml
```

Das Script zeigt die verfügbaren Markdown-Dateien direkt aus `posts/queue` und `posts/done` mit Titel und Labels an. Dateien in `posts/queue/backlog` und `posts/queue/ignore` werden nicht angezeigt. `done` Einträge werden zusätzlich als `linked` oder `not linked` markiert. `linked` bedeutet: lokal ist eine Blogger-Post-ID bekannt. `not linked` bedeutet: Die Datei liegt zwar lokal in `done`, aber es gibt keinen aktuell bekannten Blogger-Post dazu.

Danach können diese Aktionen gewählt werden:

1. Einzelnen Post mit dem konfigurierten `publish_mode` hochladen oder aktualisieren.
2. Einen Blogger-Post offline nehmen, also zurück auf Draft setzen, ohne ihn zu löschen.
3. Einen Blogger-Draft direkt veröffentlichen.
4. Einen bestehenden Blogger-Post jetzt aktualisieren.
5. Blogger-Status und eindeutige Verknüpfung `lokale Datei -> Blogger post id` anzeigen.
6. Die aktuell auf Blogger vorhandenen Labels anzeigen.
7. Danger-Aktion: einen bereits erkannten Blogger-Post endgültig löschen.

Die Aktionen 2 bis 5 und 7 brauchen eine bestehende Blogger-Verknüpfung. Bei `not linked` Einträgen bricht das Script kontrolliert ab und erklärt, dass zuerst ein neuer Upload nötig ist. Das verhindert, dass ein lokaler Markdown-Artikel mit einem Blogger-Post verwechselt wird, der remote bereits gelöscht wurde oder nicht mehr auffindbar ist.

Beim lokalen Aufruf mappt das Management-Tool die Docker-Pfade aus der Config automatisch auf das Repository: `/data/queue` wird zu `posts/queue`, `/data/done` zu `posts/done` und `/data/state.json` zu `posts/state.json`. Dadurch funktioniert dieselbe `config/config.yml` im Container und auf dem Host. Mit `--use-config-paths` kann dieses Mapping abgeschaltet werden, falls wirklich die Pfade aus der Config direkt verwendet werden sollen.

Die interaktive Bedienung steckt nur in `scripts/manage-posts.py`. Die Queue- und Blogger-Aktionen liegen zentral in `src/post_management.py` und nutzen `src/blogger_api.py`, `src/markdown_posts.py`, `src/state.py` und `src/posting_runtime.py`. Dadurch verwenden Docker-Prozess, Testscript und Management-Tool dieselben Kernpfade.

Der Server plant nicht eine separate Liste im Menü. Wenn `posting.publish_mode: "scheduled"` gesetzt ist, erzeugt der normale Posting-Lauf einen geplanten Blogger-Post. Die Reihenfolge kommt aus `posts/order.txt`; Dateien, die dort nicht stehen, kommen danach alphabetisch nach Dateiname.

Bei Blogger sind geplante Posts keine normalen Entwürfe mit Status `DRAFT`, sondern Posts mit zukünftigem `published` Datum. Bis zu diesem Zeitpunkt erscheinen sie nicht öffentlich.

## Betrieb

```sh
docker-compose up --build
```

Ohne `--once` bleibt der Container dauerhaft aktiv. Der Post-Zyklus wird über `posting.interval_seconds` gesteuert. Mit dem Standardwert `604800` wird frühestens einmal pro Woche ein erfolgreicher Post verarbeitet. `posting.check_interval_seconds` steuert nur, wie oft der Container aufwacht und prüft, ob der nächste Post fällig ist.

Initial ist `posting.dry_run: true` gesetzt. Damit wird nichts zu Blogger hochgeladen und nichts verschoben. Für echte Drafts:

```yaml
posting:
  dry_run: false
  publish_mode: "draft"
```

Für direkte Veröffentlichung:

```yaml
posting:
  dry_run: false
  publish_mode: "live"
```

Für geplante Veröffentlichung, z.B. Veröffentlichung jeden Freitag um 09:00 Uhr:

```yaml
posting:
  dry_run: false
  publish_mode: "scheduled"
  schedule:
    weekday: "friday"
    time: "09:00"
    timezone: "Europe/Berlin"
```

Wenn der Container nicht sofort den nächsten Post vorbereiten soll, sondern echte Uploads nur freitags um 09:00 Uhr starten soll:

```yaml
posting:
  dry_run: false
  due_mode: "weekly_schedule"
  schedule:
    weekday: "friday"
    time: "09:00"
    timezone: "Europe/Berlin"
```

## CLI

Der Container startet:

```sh
python -m src.blogger_auto_poster --config /config/config.yml --log-level INFO
```

Nützliche Flags:

- `--config PATH`: Pfad zur YAML-Config.
- `--once`: genau einen Zyklus ausführen und danach beenden.
- `--log-level INFO`: Log-Level setzen, z.B. `DEBUG`.

Lokaler Test ohne Docker:

```sh
python -m src.blogger_auto_poster --config config/config.yml --once
```

Solange `dry_run: true` gesetzt ist, zeigt der Lauf nur, welcher Post als nächstes verarbeitet würde.

## Script-Übersicht

| Script | Zweck | Typischer Aufruf |
| --- | --- | --- |
| `scripts/update-venv.sh` | Lokale `.venv` neu bauen, Requirements installieren, Python-Einstiegspunkte prüfen. | `scripts/update-venv.sh` |
| `scripts/load-venv.sh` | Vorhandene `.venv` in der aktuellen Shell laden. Muss mit führendem Punkt ausgeführt werden. | `. scripts/load-venv.sh` |
| `scripts/get_blogger_token.py` | OAuth-Flow lokal starten und `config/config.yml` mit Client- und Refresh-Token-Werten aktualisieren. | `scripts/get_blogger_token.py` |
| `scripts/extract-refresh-key.py` | Manuell kopierte Google-Callback-URL gegen Refresh Token tauschen, wenn der Browser nicht auf dem Server läuft. | `scripts/extract-refresh-key.py` |
| `scripts/diagnose-oauth-config.py` | OAuth-Konfiguration maskiert prüfen; optional mit echtem Token-Refresh. | `scripts/diagnose-oauth-config.py --config config/config.yml` |
| `scripts/manage-posts.py` | Interaktive Verwaltung lokaler Markdown-Dateien und verknüpfter Blogger-Posts. | `scripts/manage-posts.py --config config/config.yml` |
| `scripts/build-and-verify.sh` | Docker-Image bauen, Container starten und sicheren Dry-Run ausführen. | `scripts/build-and-verify.sh` |
| `scripts/test-blogger-config.sh` | Nach gestarteten Container prüfen: Software, Dry-Run, OAuth, Pushover und optional temporären Blogger-Draft. | `scripts/test-blogger-config.sh --all` |
| `scripts/export-public-repo.sh` | Sanitized Public-Repository mit Tool-Code, Anleitung und Beispielpost erzeugen. | `scripts/export-public-repo.sh --remote git@github.com:klaute/blogger-auto-poster.git` |

Lokale Python-Scripts sollten nach `scripts/update-venv.sh` entweder mit aktivierter venv oder explizit über `.venv/bin/python` ausgeführt werden.

## Public Export / GitHub

Das interne Arbeitsrepository enthält echte Blogpost-Entwürfe und lokale Runtime-Dateien. Für eine öffentliche Veröffentlichung wird deshalb kein normales `git push` dieses Repositories verwendet, sondern ein gezielter Export:

```sh
scripts/export-public-repo.sh \
  --target ../blogger-auto-poster-public \
  --remote git@github.com:klaute/blogger-auto-poster.git
```

Der Export kopiert nur:

- Tool-Code aus `src/`
- die freigegebenen Scripts
- `Dockerfile`, `docker-compose.yml`, `requirements.txt`
- `config/config.example.yml`
- diese `README.md`
- einen neutralen Beispielpost unter `posts/queue/example-post.md`

Nicht kopiert werden:

- echte Blogposts aus `posts/queue/backlog`, `posts/queue/ignore`, `posts/done` oder `posts/failed`
- `config/config.yml`
- `credentials.json`
- OAuth Tokens, Pushover Tokens, State-Dateien und Testberichte

Das Script initialisiert im Zielordner ein neues Git-Repository und erstellt den Initial-Commit. Mit `--push` kann der Export direkt nach GitHub gepusht werden:

```sh
scripts/export-public-repo.sh \
  --target ../blogger-auto-poster-public \
  --remote git@github.com:klaute/blogger-auto-poster.git \
  --push
```

Vor einem öffentlichen Push sollte der Export immer auf private Pfade, echte Tokens und private Blogpost-Inhalte geprüft werden.

## Logging

Der Container schreibt bewusst kurze Statusmeldungen nach stdout, sichtbar mit:

```sh
docker-compose logs -f blogger-auto-poster
```

Im normalen Betrieb erscheinen Meldungen zu:

- Startparameter wie Queue, Intervall, Publish-Modus und Dry-Run.
- jedem Queue-Check.
- nicht fälligen Posts inklusive `seconds_until_due`.
- leerer aktiver Queue.
- Dry-Run, Remote-Duplikaten, erfolgreichen Uploads und verschobenen Dateien.
- Fehlern im Posting-Zyklus inklusive Stacktrace.

## Build und Verifikation

Das Build-Script baut das Image, startet den Container und prüft, ob der Service läuft:

```sh
scripts/build-and-verify.sh
```

Der Standardlauf ist sicher:

- `docker-compose build`
- `docker-compose up -d`
- Containerstatus prüfen
- einen `--once` Dry-Run im Container ausführen

Ein echter Blogger-API-Schreibtest ist optional und muss bewusst aktiviert werden:

```sh
VERIFY_BLOGGER_DRAFT=1 scripts/build-and-verify.sh
```

Dieser Test erzeugt einen temporären Blogger-Entwurf, prüft die API-Antwort und löscht den Entwurf direkt wieder. Er verwendet immer einen Draft, unabhängig von `posting.publish_mode`.

Voraussetzungen für den Draft-Test:

- `config/config.yml` enthält echte Blogger-OAuth-Werte.
- `blogger.blog_id` ist die richtige Blog-ID.
- Der OAuth-Refresh-Token hat den Scope `https://www.googleapis.com/auth/blogger`.

## Blogger-Zugangsdaten testen

Wenn `config/config.yml` echte Blogger-Werte enthält, kann der komplette Zugang mit einem sprechenden Testscript geprüft werden:

```sh
scripts/test-blogger-config.sh
```

Ohne Parameter läuft der komplette Test. Mit Parametern wird nur der ausgewählte fachliche Check ausgeführt:

```sh
scripts/test-blogger-config.sh --software
scripts/test-blogger-config.sh --dry-run
scripts/test-blogger-config.sh --oauth
scripts/test-blogger-config.sh --pushover
scripts/test-blogger-config.sh --blogger-draft
scripts/test-blogger-config.sh --all
```

Auch bei Einzelchecks prüft das Script die dafür nötigen technischen Voraussetzungen, zum Beispiel `docker-compose` und den laufenden Container.

Das Script sagt Schritt für Schritt, was es tut:

- `docker-compose` prüfen
- vorhandenen laufenden Container prüfen
- Software-Selbsttest im Container ausführen
- Queue-/Markdown-Dry-Run ausführen
- Pushover testen, wenn `notifications.pushover.enabled` aktiv ist
- Access Token über den Refresh Token holen
- einen temporären Blogger-Entwurf erzeugen
- prüfen, ob Blogger eine Post-ID liefert
- den Test-Entwurf wieder löschen

Der Software-Selbsttest prüft ohne Blogger-Schreibzugriff:

- Python-Syntax der Module im Container.
- Modulgrenzen und Kompatibilitäts-Exports.
- Management-CLI-Verfügbarkeit.
- Den manuellen Update-Pfad: vorhandenen Blogger-Post aktualisieren und Tracking-State fortschreiben.

Wenn Pushover aktiviert ist, sendet dieser Test eine explizite Pushover-Testnachricht. Der anschließende Blogger-Draft-Test löst zusätzlich die normale Upload-Start-Nachricht aus, weil dabei ein echter Blogger-Schreibversuch gestartet wird.

Wichtig: Der Blogger-Draft-Test liest keine Markdown-Datei aus der Queue und lädt keinen echten Artikel hoch. Er erstellt nur einen temporären Post mit dem Titel `Blogger Auto Poster Verification ...` und löscht genau diesen Post danach wieder. Wenn ein echter Artikel wie `Blogger Auto Poster` als Draft im Blog liegt, kam er aus einem echten Posting-Lauf oder aus dem Management-Tool, nicht aus diesem Credential-Test.

Am Ende steht klar:

- `RESULT: OK`: Zugangsdaten funktionieren, Test-Draft wurde gelöscht.
- `RESULT: FAILED`: Test ist fehlgeschlagen.
- `Manual cleanup required: yes/no`: ob in Blogger manuell ein Test-Draft gelöscht werden muss.
- `Summary`: kompakte PASS/SKIP/FAIL-Übersicht aller gewählten Checks.

Die Detailberichte des letzten Tests liegen in:

```text
posts/last-pushover-test-result.json
posts/last-blogger-test-result.json
```

Das Script baut und startet den Container bewusst nicht. Für Build/Start ist `scripts/build-and-verify.sh` zuständig. Wenn kein Container läuft, bricht der Credential-Test ab.

Wenn Code im Projekt geändert wurde, muss vor dem Test ein neues Image gebaut werden:

```sh
scripts/build-and-verify.sh
scripts/test-blogger-config.sh
```

Wenn der Blogger-Test mit `invalid_grant` oder `invalid_client` fehlschlägt, gibt das Testscript eine lokale OAuth-Diagnose aus. Diese prüft maskiert:

- ob `config/config.yml` vollständig ist
- ob `refresh_token` plausibel aussieht
- ob `client_id` und `client_secret` in `config/config.yml` zu `credentials.json` passen
- welche genaue Google-Antwort beim Token-Refresh kommt

`credentials.json` wird dafür read-only in den Container gemountet und bleibt durch `.gitignore` lokal.

## Markdown vorbereiten

Nach manuellen Änderungen können Frontmatter und einfache Markdown-Abstände erneut normalisiert werden:

```sh
python -m src.prepare_posts --config config/config.example.yml --input-dir posts/queue/backlog
```
