# GitHub Setup

Repository name: `loxberry-plugin-velux-active-connect`

```bash
git init
git branch -M main
git add .
git commit -m "Initial release v0.5.5"
git remote add origin https://github.com/fuul1984/loxberry-plugin-velux-active-connect.git
git push -u origin main

git tag v0.5.5
git push origin v0.5.5
```

Der Tag startet `.github/workflows/release.yml`. Danach prüfen, ob das Release-Asset `VELUX_Active_Connect_v0.5.5.zip` vorhanden ist. Erst dann funktioniert der in `release.cfg` eingetragene AutoUpdate-Link.

Die Datei `wiki/velux_active_connect.dokuwiki.txt` kann direkt in die LoxBerry Wiki-Seite kopiert werden.
