#!/usr/bin/env python3

"""
analyse les fichiers à la recherche des appels aux API sah et pcb (sysbus)

exemples:
    .callSahApi("sah.Connection.Client.Wan.setIpv6",
    .push("api", "pcb.Time.getTime",

nota:
    la recherche de liens (via des require() ou define()) est bien plus compliquée

    define("json!assets/mhs/settings/settings.json", ...
        => json! précise le type de contenu
        => assets peut être un des paths définis dans require.config()

    malheureusement le lien est parfois dynamique
"""

import pathlib
import re
import requests
import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)


def download(f, fail_ok=False):
    if isinstance(f, str):
        f = pathlib.Path(f)

    if f.is_file():
        return False

    #logging.info(f"télécharge: {f}")
    r = requests.get("http://" + f.as_posix())

    if fail_ok and r.status_code != 200:
        return False

    assert r.status_code == 200

    f.parent.mkdir(exist_ok=True, parents=True)
    f.write_bytes(r.content)
    return True


def get_paths(filename):
    f = pathlib.Path(filename)
    if not f.is_file():
        return

    paths = {}

    m = re.search(r"paths:\s*{(.*?)}", f.read_text(), re.DOTALL)

    script = m.group(1)

    script = re.sub(r'langApp:.*?lang",', "", script)

    for path in script.split(","):

        alias, real = path.strip().split(":")
        alias = alias.strip().strip('"')
        real = real.strip().strip('"')

        if real == ".":
            real = f.parent
        else:
            parts = list(pathlib.Path(real).parts)
            real = f.parent

            while len(parts) > 0 and parts[0] == "..":
                real = real.parent
                del parts[0]

            for part in parts:
                real /= part

        if alias in paths:
            assert path == paths[alias]
        else:
            paths[alias] = real

    return paths


def main():
    paths = get_paths("livebox.home/loader.js")
    paths = get_paths("livebox.home/common/loader.js")

    seen = set()
    files = list()

    def parse_file(f):
        nonlocal seen, files

        if f.as_posix() in seen:
            return
        seen.add(f.as_posix())

        if not f.is_file():
            return

        script = f.read_text()

        for m in re.findall(r'define\("(\w+!)?(.+?)"[,\)\s]', script):
            # print(f, m)
            r = m[1].split("/")
            if r[0] in paths:
                pass
                mm = paths[r[0]] / "/".join(r[1:])

                if pathlib.Path(mm).is_file():
                    continue

                print("\033[31m" + str(m) + "\033[0m", "⇒", mm)
                # if download(mm, True):
                #     files.append(mm)
            else:
                # print(m)
                pass

    for f in pathlib.Path("livebox.home").rglob("*.js"):
        files.append(f)

    # tant qu'il y des éléments nouveaux
    while len(files) > 0:
        i = files.pop()
        parse_file(i)


if __name__ == "__main__":
    main()
