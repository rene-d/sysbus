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
        => assets peut être un des paths défini dans require.config()

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

    logging.info(f"télécharge: {f}")
    r = requests.get("http://" + f.as_posix())

    if fail_ok and r.status_code != 200:
        return False

    assert r.status_code == 200

    f.parent.mkdir(exist_ok=True, parents=True)
    f.write_bytes(r.content)
    return True


def load_first():
    # download("livebox.home/loader.js")
    # download("livebox.home/mhsLoader.js")
    # download("livebox.home/common/loader.js")
    # download("livebox.home/common/commonLoader.js")
    download("livebox.home/config.override/appConfig.json")



def main():
    load_first()

    unseen = set()
    seen = set()

    def parse_file(f):
        nonlocal seen, unseen

        script = f.read_text()
        sah_pcb = set()

        for m in re.findall(r'\.callSahApi\("(.+?)"', script):
            sah_pcb.add(m)
        for m in re.findall(r'\.callSahApi\.bind\(this\.root,"(.+?)"', script):
            sah_pcb.add(m)

        for m in re.findall(r'\.push\("api", ?"(.+?)"', script):
            sah_pcb.add(m)

        # ajoute les éléments répérés qui n'ont pas encore été analysés
        sah_pcb = sah_pcb - seen
        unseen = unseen.union(sah_pcb)

    # analyse initiale avec les fichiers déjà téléchargés
    for f in pathlib.Path("livebox.home").rglob("*.js"):
        parse_file(f)

    # tant qu'il y des éléments nouveaux
    while len(unseen) > 0:
        i = unseen.pop()

        if i.startswith("sah."):
            f = pathlib.Path("livebox.home/sdkut/semantic")
            for p in i.split("."):
                f /= p
            f = f.with_suffix(".js")

        elif i.startswith("pcb."):
            f = pathlib.Path("livebox.home/sdkut/apis")
            for p in i.split("."):
                f /= p
            f = f.with_suffix(".json")

        else:
            # logging.warning(f"préfixe inconnu: {i}")
            continue

        if download(f):
            parse_file(f)


if __name__ == "__main__":
    main()
