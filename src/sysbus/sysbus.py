#! /usr/bin/env python3
# -*- encoding: utf-8 -*-
# vim:set ts=4 sw=4 et:

# René D. février 2016

import sys
import os
import shutil
import re
import argparse
import pickle
import json
import pprint
from collections import *
import functools
import tempfile
import configparser
import datetime
import html
import subprocess


##
# @brief python 3 est requis
if sys.version_info.major < 3:
    raise "Must be using Python 3"

##
# @brief règle un problème de sortie vers un fichier
if sys.stdout.encoding is None:
    reload(sys)
    sys.setdefaultencoding('utf-8')


##
# @brief fonction lambda pour afficher sur stderr
error = functools.partial(print, file=sys.stderr)


##
# @brief requests n'est pas dans la distrib standard de Python3, d'où le traitement spécifique
#        pour l'import de cette librairie
try:
    import requests
    import requests.utils
except ImportError as e:
    error("erreur:", e)
    error("Installez http://www.python-requests.org/ :")
    print("   pip3 install requests")
    print("ou bien (selon la version de tar) :")
    print("   curl -sL https://api.github.com/repos/kennethreitz/requests/tarball/master | tar -xzf - --strip-components 1 '*/requests'")
    print("   curl -sL https://api.github.com/repos/kennethreitz/requests/tarball/master | tar -xzf - --strip-components=1 --wildcards '*/requests'")
    sys.exit(2)


try:
    from .manuf import MacParser
    mac_parser = MacParser()
except ImportError:
    mac_parser = None


##
# @brief informations de connexion à la Livebox
URL_LIVEBOX = 'http://livebox.home/'
USER_LIVEBOX = 'admin'
PASSWORD_LIVEBOX = 'admin'
MINECRAFT_PORT = 54520
VERSION_LIVEBOX = 'lb4'

##
# @brief niveau de détail, -v pour l'augmenter
verbosity = 0


##
# @brief session requests et entêtes d'authentification
session = None
sah_headers = None


##
# @brief affiche un message de mise au point
#
# @param level niveau de détail
# @param args
#
# @return
def debug(level, *args):
    if verbosity >= level:

        RED = '\033[91m'
        GREEN = '\033[92m'
        YELLOW = '\033[93m'
        LIGHT_PURPLE = '\033[94m'
        PURPLE = '\033[95m'
        END = '\033[0m'

        #print(*args, file=sys.stderr)

        if level <= 1: sys.stderr.write(YELLOW)
        elif level == 2: sys.stderr.write(PURPLE)
        else: sys.stderr.write(RED)

        sys.stderr.write(' '.join(args))
        sys.stderr.write(END)
        sys.stderr.write('\n')


##
# @brief lit l'ip et l'adresse MAC de la livebox à partir du nom dns 'livebox.home'
#
# @return ip, mac
def get_livebox_ip_mac():
    p = subprocess.check_output(['arp', '-n', 'livebox.home'], universal_newlines=True)

    # cherche xxx.yyy.zzz.ttt
    ip = re.search('(\d{1,3}(\.\d{1,3}){3})', p)
    if ip is None:
        return

    # cherche XX:XX:XX:XX:XX:XX (ou xx-xx-...)
    eth = re.search('([\dA-Fa-f]{1,2}(?:[-:][\dA-Fa-f]{1,2}){5})', p)
    if eth is None:
        return ip.group(0), None

    return ip.group(0), eth.group(0)


##
# @brief compare deux adresses MAC. Si une est mal formatée, retourne False
#
# @param a
# @param b
#
# @return
def compare_mac(a, b):
    m = re.findall('([a-fA-F\d]{1,2})[:-]?', a)
    if len(m) != 6: return False
    a = [ int(x, 16) for x in m ]

    m = re.findall('([a-fA-F\d]{1,2})[:-]?', b)
    if len(m) != 6: return False
    b = [ int(x, 16) for x in m ]

    return a == b


##
# @brief écrit le fichier de configuration
#        TODO à réécrire pour tenir compte du flag "auto"
#
# @return
def write_conf(args):
    config = configparser.ConfigParser()
    config['main'] = {}
    config['main']['URL_LIVEBOX'] = URL_LIVEBOX
    config['main']['USER_LIVEBOX'] = USER_LIVEBOX
    config['main']['PASSWORD_LIVEBOX'] = PASSWORD_LIVEBOX
    config['main']['VERSION_LIVEBOX'] = VERSION_LIVEBOX
    config['minecraft'] = {}
    config['minecraft']['port'] = str(MINECRAFT_PORT)

    rc = os.path.expanduser("~") + "/" + ".sysbusrc"
    with open(rc, "w") as f:
        config.write(f)

    print("configuration écrite dans %s" % rc)
    print("     url = %s" % (URL_LIVEBOX))
    print("    user = %s" % (USER_LIVEBOX))
    print("password = %s" % (PASSWORD_LIVEBOX))
    print("   model = %s" % (VERSION_LIVEBOX))


##
# @brief lit le fichier de configuration
#
# @return
def load_conf():
    global USER_LIVEBOX, PASSWORD_LIVEBOX, URL_LIVEBOX, VERSION_LIVEBOX, MINECRAFT_PORT

    rc = os.path.expanduser("~") + "/" + ".sysbusrc"
    debug(3, 'rc file', rc)
    config = configparser.ConfigParser()
    try:
        config.read(rc)

        URL_LIVEBOX = config['main']['URL_LIVEBOX']
        USER_LIVEBOX = config['main']['USER_LIVEBOX']
        PASSWORD_LIVEBOX = config['main']['PASSWORD_LIVEBOX']
        VERSION_LIVEBOX = config['main']['VERSION_LIVEBOX']

        MINECRAFT_PORT = config['minecraft']['port']

        if config['main']['auto'].lower() in ['true', 'yes', '1']:
            ip, eth = get_livebox_ip_mac()
            if ip and eth:
                for i in config.sections():
                    if compare_mac(i, eth):
                        if 'URL_LIVEBOX' in config[i]:
                            URL_LIVEBOX = config[i]['URL_LIVEBOX']
                        else:
                            URL_LIVEBOX = "http://{}/".format(ip)
                        if 'USER_LIVEBOX' in config[i]:
                            USER_LIVEBOX = config[i]['USER_LIVEBOX']
                        if 'PASSWORD_LIVEBOX' in config[i]:
                            PASSWORD_LIVEBOX = config[i]['PASSWORD_LIVEBOX']
                        if 'VERSION_LIVEBOX' in config[i]:
                            VERSION_LIVEBOX = config[i]['VERSION_LIVEBOX']

                        debug(1, "using auto detect for MAC %s (%s)" % (eth, config.get(i, 'location', fallback='unknown')))

                        break

    except:
        return False

    debug(2, "%s %s %s %s" % (USER_LIVEBOX, PASSWORD_LIVEBOX, URL_LIVEBOX, VERSION_LIVEBOX))
    return True


##
# @brief charge la conf et sort s'il y a une erreur
#
# @return
def check_conf():
    print("Le fichier ~/.sysbusrc n'a pas été trouvé. Il est nécessaire pour le fonctionnement du programme.")
    print("Utilisez l'option -config (avec éventuellement -url -user -password) pour le créer.")
    print("Exemple:")
    print("   sysbus.py -config -password=1234ABCD")
    sys.exit(2)


##
# @brief retourne le chemin du fichier de sauvegarde du cookie et contextID
#
# @return
def state_file():
    return tempfile.gettempdir() + "/" + "sysbus_state"


##
# @brief authentification
#  - essaie avec les données mémorisées (.cookie / .contextID)
#  - envoie la requête d'authentification
#
# @return True/False
def auth(new_session=False):
    global session, sah_headers

    debug(3, 'state file', state_file())

    for i in range(2):

        if not new_session and os.path.exists(state_file()):
            debug(1, 'loading saved cookies')

            with open(state_file(), 'rb') as f:
                cookies = requests.utils.cookiejar_from_dict(pickle.load(f))

                session = requests.Session()
                session.cookies = cookies

                contextID = pickle.load(f)

        else:
            debug(1, "new session")
            session = requests.Session()

            debug(2, "auth for", VERSION_LIVEBOX)
            if VERSION_LIVEBOX != 'lb4':
                auth = { 'username':USER_LIVEBOX, 'password':PASSWORD_LIVEBOX }
                debug(2, "auth with", str(auth))
                r = session.post(URL_LIVEBOX + 'authenticate', params=auth)
                debug(2, "auth return", r.text)
            else:
                # la mise à jour 2.19.2 de janvier 2017 a introduit un nouveau mécanisme d'authentification
                # de plus, la donnée n'est certainement pas parsée en tant que JSON mais comme chaine de caractères
                # car si le formalisme change un peu l'authentification échoue
                auth = '{"service":"sah.Device.Information","method":"createContext","parameters":{"applicationName":"so_sdkut","username":"%s","password":"%s"}}' % (USER_LIVEBOX, PASSWORD_LIVEBOX)
                sah_headers = { 'Content-Type':'application/x-sah-ws-1-call+json', 'Authorization':'X-Sah-Login' }
                debug(2, "auth with", str(auth))
                r = session.post(URL_LIVEBOX + 'ws', data=auth, headers=sah_headers)
                debug(2, "auth return", r.text)

            if not 'contextID' in r.json()['data']:
                error("auth error", str(r.text))
                break

            contextID = r.json()['data']['contextID']

            # sauve le cookie et le contextID
            debug(1, 'setting cookies')
            with open(state_file(), 'wb') as f:
                data = requests.utils.dict_from_cookiejar(session.cookies)
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
                data = contextID
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)

        sah_headers = { 'X-Context':contextID,
                    'X-Prototype-Version':'1.7',
                    'Content-Type':'application/x-sah-ws-1-call+json; charset=UTF-8',
                    'Accept':'text/javascript' }

        # vérification de l'authentification
        r = session.post(URL_LIVEBOX + 'sysbus/Time:getTime', headers=sah_headers, data='{"parameters":{}}')
        if r.json()['result']['status'] == True:
            return True
        else:
            os.remove(state_file())

    error("authentification impossible")
    return False


##
# @brief requêtes sans authentification: crée la session et des headers par défaut
#
# @return
def noauth():
    global session, sah_headers
    session = requests.Session()
    sah_headers = { 'X-Prototype-Version':'1.7',
                    'Content-Type':'application/x-sah-ws-1-call+json; charset=UTF-8',
                    'Accept':'text/javascript' }




##
# @brief envoie une requête sysbus à la Livebox
#
# @param chemin
# @param args
# @param get
#
# @return
def requete(chemin, args=None, get=False, raw=False, silent=False):

    # nettoie le chemin de la requête
    c = str.replace(chemin or "sysbus", ".", "/")
    if c[0] == "/":
        c = c[1:]

    if c[0:7] != "sysbus/":
        c = "sysbus/" + c

    if get:
        if args is None:
            c += "?_restDepth=-1"
        else:
            c += "?_restDepth="  + str(args)

        debug(1, "requête: %s" % (c))
        ts = datetime.datetime.now()
        t = session.get(URL_LIVEBOX + c, headers=sah_headers)
        debug(2, "durée requête: %s" % (datetime.datetime.now() - ts))
        t = t.content
        #t = b'[' + t.replace(b'}{', b'},{')+b']'

    else:
        # complète les paramètres de la requête
        parameters = { }
        if not args is None:
            for i in args:
                parameters[i] = args[i]

        data = { }
        data['parameters'] = parameters

        # l'ihm des livebox 4 utilise une autre API, qui fonctionne aussi sur les lb2 et lb3
        sep = c.rfind(':')
        data['service'] = c[0:sep].replace('/', '.')
        if data['service'][0:7] == "sysbus.":
            data['service'] = data['service'][7:]
        data['method'] = c[sep+1:]
        c = 'ws'

        # envoie la requête avec les entêtes qui vont bien
        debug(1, "requête: %s with %s" % (c, str(data)))
        ts = datetime.datetime.now()
        t = session.post(URL_LIVEBOX + c, headers=sah_headers, data=json.dumps(data))
        debug(2, "durée requête: %s" % (datetime.datetime.now() - ts))
        t = t.content

    # il y a un truc bien moisi dans le nom netbios de la Time Capsule
    # probable reliquat d'un bug dans le firmware de la TC ou de la Livebox
    t = t.replace(b'\xf0\x44\x6e\x22', b'aaaa')

    if raw == True:
        return t

    t = t.decode('utf-8', errors='replace')
    if get and t.find("}{"):
        debug(2, "listes json multiples")
        t = "[" + t.replace("}{", "},{") + "]"

    try:
        r = json.loads(t)
    except:
        if not silent:
            error("erreur:", sys.exc_info()[0])
            error("mauvais json:", t)
        return

    apercu = str(r)
    if len(apercu) > 50:
        apercu = apercu[:50] + "..."
    debug(1, "réponse:", apercu)

    if not get and 'result' in r:
        if not 'errors' in r['result']:
            debug(1, "-------------------------")
            return r['result']
        else:
            if not silent:
                error("erreur:", t)
            return None

    else:
        debug(1, "-------------------------")
        return r


##
# @brief envoie une requête sysbus et affiche le résultat
#
# @param chemin chemin de la requête
# @param args paramètres supplementaires
#
# @return
def requete_print(chemin, args=None, get=False):
    #print(chemin, args)
    #return
    result = requete(chemin, args, get)
    if result:
        pprint.pprint(result)
    return result



##
# @brief affiche le modèle
#
# @param node
# @param level
#
# @return
def model(node, level=0, file=None):

    def print_functions(node, indent=''):
        for f in node["functions"]:
            aa = ""
            for a in f['arguments']:
                flag = ""
                if 'attributes' in a and 'mandatory' in a['attributes'] and a['attributes']['mandatory']:
                    pass
                else:
                    flag = "opt "
                if 'attributes' in a and 'out' in a['attributes'] and a['attributes']['out']:
                    flag = "out "
                aa += ", " + flag + a['name']
            print(indent + "function:", f['name'], "(" + aa[2:] + ")", file=file)

    def print_parameters(node, indent=''):
        if 'parameters' in node:
            for p in node['parameters']:
                print(indent + "parameter:  %-20s : %-10s = '%s'" % (p['name'], p['type'], p['value']), file=file)


    # si ce n'est pas un datamodel, on sort
    if not 'objectInfo' in node:
        pprint.pprint(node)
        return

    o = node['objectInfo']

    print("", file=file)
    print("=========================================== level", level, file=file)
    print("OBJECT NAME: '%s.%s'  (name: %s)" % (o['keyPath'], o['key'], o['name'] ), file=file)

    print_functions(node)
    print_parameters(node)

    for i in node:
        if i == "children":
            #print("has children...", len(node[i]), file=file)
            pass
        elif i == "objectInfo":
             pass
        elif i == "functions":
            pass
        elif i == "parameters":
            pass

        elif i == "--templateInfo":
            print("templateInfo:")
            pprint.pprint(node[i])
            sys.exit()

        elif i == "errors":
            for e in node["errors"]:
                print(e["error"],  e["info"], e["description"], file=file)
        elif i == "instances":
            print("-->", i, len(node[i]), file=file)
            if i == "instances" and len(node[i])>0:
                k = 0
                for j in node[i]:
                    k += 1

                    #assert(len(j['children']) == 0)
                    #assert(len(j['instances']) == 0)
                    #print(j)
                    #model(j, 99)

                    print("instance %d: '%s.%s' (name: %s)" % (k, j['objectInfo']['keyPath'], j['objectInfo']['key'], j['objectInfo']['name']), file=file)
                    #print("j=",j)
                    #print("oi=", j['objectInfo'])
                    print_functions(j, indent="    ")
                    print_parameters(j, indent="    ")
                    pass
        else:
            print("-->", i, len(node[i]), file=file)

    if 'children' in node:
        for c in node['children']:
            model(c, level + 1, file=file)




##
# @brief analyse le fichier scripts.js à la recherche de requêtes sysbus
#
# @return
def scan_sysbus(args):

    if len(args) > 0:
        # lecture des fichiers passés en ligne de commandes
        s = ""
        for i in args:
            if os.path.exists(i):
                s += open(i).read()
                debug(1, "lecture de %s" % i)

    else:
        if os.path.exists("scripts.js"):
            # lecture scripts.js local
            s = open("scripts.js").read()
            debug(1, "lecture de %s" % "scripts.js")
        else:
            # lecture scripts.js sur la Livebox
            session = requests.Session()
            rep = session.get(URL_LIVEBOX + "scripts.js")
            s = rep.text
            session.close()
            debug(1, "lecture de %s" % (URL_LIVEBOX + "scripts.js"))

    e = re.findall(r'"/?(sysbus[./].*)"', s)
    objects = dict()
    for s in e:
        #print(s)
        i = s.find(':')
        if i >= 0:
            o = s[0:i]
            m = s[i+1:]
        else:
            o = s
            m = ""

        if m.find('"') >= 0:
            m = m[0:m.find('"')]

        o = re.sub('"(.*)"', r'<o>', o)
        o = re.sub(r'\/', r'.', o)

        if not o in objects:
            objects[o] = set()
        objects[o].add(m)

    for i in sorted(objects):
        print(i, list( objects[i]))


##
# @brief crée l'arborescence des scripts javascript de la Livebox à partir de scripts.js
#
# @return
def extract_files(args):

    if os.path.exists("scripts.js"):
        with open("scripts.js") as f:
            js = f.read()
            f.close()
    else:
        session = requests.Session()
        rep = session.get(URL_LIVEBOX + "scripts.js")
        js = rep.text
        session.close()

    t = []
    for i in re.finditer(r'\/\*jsdep.*\*\/', js):
        t.insert(0, i.start())

    print("extracting %d files" % len(t))

    trailing = ""
    j = None
    for i in t:
        s = js[i:j]
        name = re.search(r"(web/js.*) ", s).group(1)
        j = i
        if not os.path.isdir(os.path.dirname(name)):
            os.makedirs(os.path.dirname(name))
        with open(name, "w") as f:
            f.write(s)
            f.close()
        js = js[0:i]
        #trailing += "/* " + name + " */\n"

    # crée un fichier avec ce qu'il reste
    with open("web/js/MAIN.js", "w") as f:
        f.write(js)
        if trailing != "":
            f.write(trailing)
        f.close()


##
# @brief demande le module de gestion de graphviz.
# il y en a plusieurs, j'en ai choisi récent et qui fonctionne avec python3
#
# documentation:
#   http://www.graphviz.org/
#   http://graphviz.readthedocs.org/
#
# @return
def load_graphviz():
    try:
        from graphviz import Digraph as dg
    except ImportError as e:
        error("erreur:", e)
        error("Installez https://github.com/xflr6/graphviz : pip3 install graphviz")
        sys.exit(2)
    return dg



##
# @brief dumpe dans un fichier le datamodel, à partir d'un noeud ou depuis la racine
#
# @param chemin
# @param prof
# @param out
#
# @return
def model_raw_cmd(chemin, prof=None, out=None):

    r = requete(chemin, prof, get=True, raw=True)

    if not r is None:
        with open(out or "model.json", "wb") as f:
            f.write(r)
            f.close()
        debug(1, "modèle écrit dans", out or "model.json")
    else:
        error("modèle non accessible")



##
# @brief crée un diagramme de classe UML avec plantuml
#
class uml_model:

    def __init__(self, model, filename):

        self.uml = open(filename, "w")
        self.uml.write("@startuml\n")

        self._build_node(model)

        self.uml.write("@enduml\n")
        self.uml.close()


    def _build_node(self, node, level=0):

        name = node['objectInfo']['key']
        if name == "": name = "sysbus"

        path = node['objectInfo']['keyPath'] + "." + name
        if path[0] == ".": path = path[1:]

        self.uml.write('class "%s" as %s {\n' % (name, path))

        # analyse les paramètres du noeud
        if 'parameters' in node:
            for i in node['parameters']:

                access = ""
                if 'attributes' in i:
                    for j in i['attributes']:
                        if i['attributes'] == False: continue
                        if j == "read_only": access = "#"
                        elif j == "persistent": pass
                        elif j == "volatile": pass
                        else:
                            print("attribut inconnu:", j, i)
                            sys.exit(2)

                self.uml.write('  %s%s %s\n' % (access, i['type'], i['name']))

        # analyse les fonctions du noeud
        if 'functions' in node:
            for i in node['functions']:

                access = ""
                if 'attributes' in i:
                    for j in i['attributes']:
                        if i['attributes'] == False: continue
                        if j == "message": access = "~"
                        elif j == "variadic": pass
                        else:
                            print("attribut inconnu:", j, i)
                            sys.exit(2)

                arguments = []
                if 'arguments' in i:
                    for j in i['arguments']:
                        name = j['name']
                        if 'attributes' in j:
                            mandatory = False
                            out = False
                            for k, v in j['attributes'].items():
                                if k == 'out': out = v
                                elif k == 'mandatory': mandatory = v
                                elif k == 'in': pass
                                else:
                                    print("attribut inconnu:", k, j)
                                    sys.exit(2)
                            if not mandatory and not out: name = "opt " + name
                            if out: name = "out " + name
                        arguments.append(name)

                self.uml.write('  %s%s %s(%s)\n' % (access, i['type'], i['name'], ','.join(arguments)))

        self.uml.write('}\n')

        #print("%s%s" % ("    " * level, name))

        parent_path = path
        parent_name = name

        # analyse les children du noeud courant
        for child in node['children']:
            o = child['objectInfo']
            #assert(o['indexPath'] == o['keyPath'])
            assert(o['state'] == "ready")

            name = o['key']
            path = o['keyPath'] + "." + name

            # crée le noeud child
            self._build_node(child, level + 1)

            # lie le child au noeud courant
            self.uml.write('"%s" <-- "%s"\n' % (parent_path, path))

        # cas particulier des children non autorisés
        if 'errors' in node:
            for error in node['errors']:
                if error['error'] == 13:
                    name = error['info']
                    if name == "": name = "EMPTY"
                    path = node['objectInfo']['keyPath'] + "." + name

                    #print("%s%s *" % ("    " * (level + 1), name))

                    self.uml.write('class "%s" as %s {\n' % (name, path))
                    self.uml.write('}\n')
                    self.uml.write('"%s" <-- "%s"\n' % (parent_path, path))


##
# @brief
#
# @param filename
#
# @return
def open_file_in_os(filename):
    if sys.platform.startswith('darwin'):
        subprocess.call(['open', filename])
    elif os.name == 'nt':
        os.startfile(filename)
    elif os.name == 'posix':
        subprocess.call(['xdg-open', filename])


##
# @brief
#
# @param chemin
# @param prof
# @param out
#
# @return
def model_uml_cmd(chemin, prof=None, out=None):

    model = requete(chemin, prof, get=True, raw=True)
    if not model:
        return

    model = model.decode('utf-8', errors='replace')
    model = json.loads(model)

    plants = []

    fmt = os.path.splitext(out)[1][1:] if out else "svg"
    file_to_open = None
    debug(2, "format de sortie: %s" % fmt)

    # est-on à la racine du modèle ?
    if model['objectInfo']['keyPath'] == "" and model['objectInfo']['key'] == "":

        if not os.path.isdir("models"):
            debug(2, "créatoin répertoire: " % "models")
            os.makedirs("models")

        # on crée des diagrammes par top-level objects, sinon c'est trop gros
        for node in model['children']:
            name = node['objectInfo']['key']
            plant = "models/%s.plantuml" % name

            debug(1, "génération diagramme %s" % name)
            uml_model(node, plant)
            plants.append(plant)

        for error in model['errors']:
            if error['error'] == 13:
                name = error['info']
                debug(1, "accès interdit: %s" % name)

    else:
        s = os.path.splitext(out or "model")[0] + ".plantuml"

        debug(1, "génération diagramme %s" % s)
        uml_model(model, s)
        plants.append(s)

        file_to_open = out or "model." + fmt

    if shutil.which("plantuml"):
        debug(1, "lancement plantuml")
        subprocess.call('plantuml -t' + fmt + ' ' + ' '.join(plants), shell=True)

        if file_to_open:
            open_file_in_os(file_to_open)

    else:
        print("plantuml est nécessaire, vous pouvez le télécharger ici:")
        print("  OSX: brew install plantuml")
        print("  Debian/Ubuntu: sudo apt-get install plantuml")
        print("  autres: http://sourceforge.net/projects/plantuml/files/plantuml.jar/download")
        print("Nota: Graphviz est également nécessaire")


##
# @brief crée un tableau croisé MIBs/Interfaces
#
# @param output_html
#
# @return
def MIBs_table_cmd(output_html=False):
    intf = set()
    mibs = set()

    r = requete("NeMo.Intf.lo:getMIBs", { "traverse": "all" })
    if r is None or not 'status' in r: return

    r = r['status']

    for m in r:
        mibs.add(m)
        for i in r[m]:
            intf.add(i)

    mibs = sorted(mibs)
    intf = sorted(intf)

    #print("MIBs (%d): %s" % (len(mibs), str(mibs)))
    #print("Intf (%d): %s" % (len(intf), str(intf)))

    if output_html:
        # affichage dans une page HTML

        print(
'''<!DOCTYPE html>
<html>
<head>

<style>
table {
    width:100%;
}
table, th, td {
    border: 1px solid black;
    border-collapse: collapse;
}
th, td {
    padding: 5px;
    text-align: center;
    white-space: nowrap;
}
table#t01 tr:nth-child(even) {
    background-color: #eee;
}
table#t01 tr:nth-child(odd) {
   background-color:#fff;
}
table#t01 th	{
    background-color: black;
    color: white;
}
table#t01 td:nth-child(1)	{
    text-color: blue;
    color: blue;
    text-align: left;
}
.details {
    white-space: pre;
    font-family: monospace;
    text-align: left;

    border-color: darkblue;
    border-width: 1px;
    border-style: solid;
    position: absolute;
    color: darkblue;
    background-color: white;
    z-index: 1;
    display: none;
}
</style>

<script>
var last = null;
function fenetre(nom) {
    fenetre_close();
    document.getElementById(nom).style.display="inline-block";
    last = nom;
}
function fenetre_close() {
    if (last) {
        document.getElementById(last).style.display="none";
        last = null;
    }
}
</script>

</head>
<body>

''')

        print('<table id="t01">')

        # la ligne d'entête
        print('  <tr>')
        print('    <th>%s</th>' % 'Intf')
        for m in mibs:
            print('    <th>%s</th>' % m)
        print('  </tr>')

        for i in intf:
            print('  <tr>')

            # la première colonne: le nom de l'interface
            rr = requete("NeMo.Intf.%s:get" % i, silent=True)
            action = 'fenetre_close()'
            if not rr or 'status' not in rr:
                x = '<div style="color:red;">' + i + '</div>'
            else:
                # cellule cliquable pour afficher les détails
                details = html.escape(pprint.pformat(rr['status']))
                x = '\n<div id="%s" class="details" onclick="fenetre_close()">' % (i)
                x += details
                x += '</div>\n'
                x += '<div style="color:darkblue;">' + i + '</div>'
                action = 'fenetre(\'%s\')' % (i)
            print('    <td onclick="%s">%s</td>' % (action, x))

            # les autres colonnes: les MIBs
            for m in mibs:
                action = 'fenetre_close()'
                if i in r[m]:
                    if len(r[m][i]) == 0:
                        # MIB déclarée pour l'interface mais vide
                        x = "0"
                    else:
                        # il y a des valeurs pour la MIB
                        # cellule cliquable pour afficher les détails
                        x = '<div id="%s#%s" class="details" onclick="fenetre_close()">' % (i, m)
                        x += html.escape(pprint.pformat(r[m][i]))
                        x += '</div>'
                        x += '<div style="color:darkblue;">X</div>'
                        action = 'fenetre(\'%s#%s\')' % (i, m)
                else:
                    # MIB absente pour l'interface
                    x = ""
                print('    <td onclick="%s">%s</td>' % (action, x))

            print('  </tr>')
        print('  </table>')

        print('</body>')
        print('</html>')

    else:
        # affichage en markdown/texte

        len_intf = 0
        for i in intf:
            if len_intf < len(i): len_intf = len(i)

        s = "|{:{len}}|".format("Intf", len=len_intf)
        for m in mibs:
            len_m = len(m)
            if len_m < 3: len_m = 3
            s += '{:^{len}}|'.format(m, len=len_m)
        print(s)

        s = "|:%s|" % ("-" * (len_intf - 1))
        for m in mibs:
            len_m = len(m)
            if len_m < 3: len_m = 3
            s += ":%s:|" % ("-" * (len_m - 2))
        print(s)

        for i in intf:
            s = "|{:{len}}|".format(i, len=len_intf)
            for m in mibs:
                len_m = len(m)
                if len_m < 3: len_m = 3
                if i in r[m]:
                    if len(r[m][i]) == 0:
                        # MIB déclarée pour l'interface mais vide
                        x = "0"
                    else:
                        # il y a des valeurs pour la MIB
                        x = "X"
                else:
                    # MIB absente pour l'interface
                    x = ""
                s += "{:^{len}}|".format(x, len=len_m)
            print(s)

        pass


##
# @brief dumpe toutes les MIBs dans un sous-répertoire mibs au format pretty print Python et décodé
#
# @return
def MIBs_save_cmd():
    # liste toutes les interfaces
    intf = set()
    r = requete("NeMo.Intf.lo:getIntfs", { "traverse": "all" })
    if not r is None:
        for i in r['status']:
            intf.add(i)

    if not os.path.isdir("mibs"):
        os.makedirs("mibs")

    # dump les datamodels de chaque interface
    for i in intf:
        r = requete('NeMo.Intf.' + i, get=True)
        if r is None: continue

        # le modèle en json
        with open("mibs/" + i + ".dict", "w") as f:
            pprint.pprint(r, stream=f)
            #json.dump(r, f, indent=4, separators=(',', ': '))
            f.close()

        # le modèle décodé
        with open("mibs/" + i + ".model", "w") as f:
            for j in r:
                print("---------------------------------------------------------", file=f)
                model(j, file=f)
            f.close()

    # dump le contenu des MIBs par interface
    for i in intf:
        r = requete('NeMo.Intf.' + i + ':getMIBs', { "traverse": "this" })
        if r is None: continue
        with open("mibs/" + i + ".mib", "w") as f:
            pprint.pprint(r, stream=f)
            f.close()


def requete_object(path):

    def get_parameters(node):
        o = dict()
        if 'parameters' in node:
            for p in node['parameters']:
                if p['type'] == 'string':
                    o[p['name']] = p['value']
                elif p['type'] == 'uint32':
                    o[p['name']] = int(p['value'])
                elif p['type'] == 'date_time':
                    o[p['name']] = p['value']
                elif p['type'] == 'bool':
                    o[p['name']] = (p['value'].lower() == "true")
                else:
                    print("unkwown type: ", str(p))
                    sys.exit()
        return o

    def obj(node):
        # si ce n'est pas un noeud du datamodel, on sort
        if not 'objectInfo' in node:
            return
        #o = node['objectInfo']
        #pprint.pprint(o)
        o = get_parameters(node)
        return o

    r = requete(path, 0, get=True)
    o = []
    for node in r:
        o.append(obj(node))

    return o



def livebox_info():
    result = requete("DeviceInfo:get", silent=True)
    if result is None:
        # l'objet DeviceInfo n'a pas de méthode dans la MIB de la Livebox 2
        o = requete_object("DeviceInfo")
        o = o[0]
        print("%20s : %s" % ("SoftwareVersion", o['SoftwareVersion']))
        print("%20s : %s" % ("UpTime", str(datetime.timedelta(seconds=int(o['UpTime'])))))
        print("%20s : %s" % ("ExternalIPAddress", o['ExternalIPAddress']))
    else:
        o = result['status']
        print("%20s : %s" % ("SoftwareVersion", o['SoftwareVersion']))
        print("%20s : %s  (NumberOfReboots: %s)" % ("UpTime", str(datetime.timedelta(seconds=int(o['UpTime']))), o['NumberOfReboots']))
        print("%20s : %s" % ("ExternalIPAddress", o['ExternalIPAddress']))

        # pas d'objet Devices dans la Livebox 2
        result = requete("Devices.Device.lan:getFirstParameter", { "parameter": "IPAddress" }, silent=True)
        if 'status' in result:
            print("%20s : %s" % ("IPv4Address", result['status']))

        # ni d'adresse IPv6
        result = requete("NMC.IPv6:get")
        print("%20s : %s" % ("IPv6Address", result['data']['IPv6Address']))

        result = requete("NMC:getWANStatus")
        if 'data' in result:
            print("%20s : %s" % ("IPv6DelegatedPrefix", result['data']['IPv6DelegatedPrefix'] if 'IPv6DelegatedPrefix' in result['data'] else 'n/a'))
            print("%20s : %s" % ("IPv6Address", result['data']['IPv6Address']))

    result = requete("VoiceService.VoiceApplication:listTrunks")
    if 'status' in result:
        for i in result['status']:
            for j in i['trunk_lines']:
                if j['enable'] == "Enabled":
                    print("%20s : %s" % ("directoryNumber", j['directoryNumber']))

    #result = requete("Time:getTime")
    #print("%20s : %s" % ("Time", result['data']['time']))


##
# @brief inspiré de http://forum.eedomus.com/viewtopic.php?f=50&t=2914
#
# @param parser
#
# @return
def add_singles(parser):

    cmds = [
        [ "wifistate", "", "NMC.Wifi:get" ],
#        [ "lanstate", "", "NeMo.Intf.lan:getMIBs" ],
#        [ "dslstate", "", "NeMo.Intf.dsl0:getDSLStats" ],
#        [ "iplan", "", "NeMo.Intf.lan:luckyAddrAddress" ],
#        [ "ipwan", "", "NeMo.Intf.data:luckyAddrAddress" ],
        [ "phonestate", "", "VoiceService.VoiceApplication:listTrunks" ],
        [ "tvstate", "", "NMC.OrangeTV:getIPTVStatus" ],
        [ "wifion", "", [ "NMC.Wifi:set", { "Enable":True, "Status":True } ] ],
        [ "wifioff", "", [ "NMC.Wifi:set", { "Enable":False, "Status":False } ] ],
#        [ "macon", "", [ "NeMo.Intf.wl0:setWLANConfig", {"mibs":{"wlanvap":{"wl0":{"MACFiltering":{"Mode":"WhiteList"}}}}} ] ],
#        [ "macoff", "", [ "NeMo.Intf.wl0:setWLANConfig", {"mibs":{"wlanvap":{"wl0":{"MACFiltering":{"Mode":"Off"}}}}} ] ],
        [ "devices", "", "Devices:get" ],
        [ "guestwifion", "Active le Wifi invité uniquement", [ "NMC.Guest:set", { "Enable":True } ] ],
        [ "guestwifioff", "Désactive le Wifi invité uniquement", [ "NMC.Guest:set", { "Enable":False } ] ],
        [ "privatewifioff", "Désactive le Wifi privé uniquement", [ "NeMo.Intf.lan:setWLANConfig", {"mibs":{"penable":{"wl0":{"Enable":False,"PersistentEnable":False,"Status":False},"eth6":{"Enable":False,"PersistentEnable":False,"Status":False}},"wlanvap":{"wl0":{},"eth6":{}}}} ] ],
        [ "privatewifion", "Active le Wifi privé uniquement", [ "NeMo.Intf.lan:setWLANConfig", {"mibs":{"penable":{"wl0":{"Enable":True,"PersistentEnable":True,"Status":True},"eth6":{"Enable":True,"PersistentEnable":True,"Status":True}},"wlanvap":{"wl0":{},"eth6":{}}}} ] ],
    ]

    for i in cmds:
        parser.add_argument('-' + i[0], help=i[1], dest='req_auth', action='store_const', const=i[2])


##
# @brief mes commandes
#
# @param parser
#
# @return
def add_commands(parser):

    cmds = [
        [ "wpson", "active le (WPS) Wi-Fi Protected Setup",
                    [ "NeMo.Intf.wl0:setWLANConfig",
                      {"mibs":{"wlanvap":{"wl0":{"WPS":{"Enable":True}},"wl1":{"WPS":{"Enable":True}}}}} ] ],
        [ "wpsoff", "désactive le (WPS) Wi-Fi Protected Setup",
                    [ "NeMo.Intf.wl0:setWLANConfig",
                      {"mibs":{"wlanvap":{"wl0":{"WPS":{"Enable":False}},"wl1":{"WPS":{"Enable":False}}}}} ] ],
        [ "version", "affiche la version et détails de la Livebox",
                    [ "DeviceInfo:get" ] ],
    ]

    for i in cmds:
        parser.add_argument('-' + i[0], help=i[1], dest='req_auth', action='store_const', const=i[2])


    def info_cmd(args):
        """ affiche des infos de la Livebox (adresses IP)"""
        livebox_info()


    def time_cmd(args):
        """ affiche l'heure de la Livebox """
        result = requete("Time:getTime")
        if result:
            t = result['data']['time']
            result = requete("Time:getLocalTimeZoneName")
            tz = result['data']['timezone']
            print("Livebox time: {} ({})".format(t, tz))


    def dslrate_cmd(args):
        """ DSL datarate """
        result = requete("NeMo.Intf.data:getMIBs", { "traverse":"down", "mibs":"dsl" })
        if 'status' in result and 'dsl' in result['status'] and 'dsl0' in result['status']['dsl']:
            m = result['status']['dsl']['dsl0']
            print("Downstream: {:6.2f} Mbit".format(m['DownstreamCurrRate'] / 1024.))
            print("Upstream:   {:6.2f} Mbit".format(m['UpstreamCurrRate'] / 1024.))
            d = datetime.timedelta(seconds=int(m['LastChange']))
            print("LastChange: {}".format((datetime.datetime.now() - d).ctime()))
        else:
            print("DSL rate non disponible")


    def wifi_cmd(args):
        """ affiche les passphrases des réseaux Wi-Fi """
        r = requete('NeMo.Intf.data:getMIBs', { "traverse": "all" })
        for wl, c in r['status']['wlanvap'].items():
            if 'BSSID' in c:
                print(wl, c['BSSID'], c['SSID'], c['Security']['KeyPassPhrase'], c['Security']['ModeEnabled'])


    def qrcode_cmd(args):
        """ affiche les passphrases Wi-Fi en qrcode """
        try:
            import qrcode
        except ImportError:
            print("Module qrcode non trouvé: pip3 install qrcode")
            exit(2)
        qr = qrcode.QRCode(version=1,
                           error_correction=qrcode.constants.ERROR_CORRECT_L,
                           box_size=10,
                           border=4)

        last_passphrase = None
        r = requete("NeMo.Intf.lan:getMIBs")
        for wl in r['status']['wlanvap']:
            c = r['status']['wlanvap'][wl]
            passphrase =  c['Security']['KeyPassPhrase']
            print(wl, c['BSSID'], c['SSID'], passphrase, c['Security']['ModeEnabled'])
            if last_passphrase != passphrase:
                last_passphrase = passphrase
                qr.clear()
                qr.add_data(passphrase)
                qr.make(fit=True)
                qr.print_ascii(tty=True)

    #
    def setname_cmd(args):
        if len(args) < 2:
            error("Usage: -setname MAC name [source [source ...]]")
            return
        mac = str.upper(args[0])
        name = args[1]
        print("set name", mac, name)
        if len(args) == 2:
            requete_print('Devices.Device.' + mac + ':setName', {"name":name })
        else:
            for i in range(2, len(args)):
                requete_print('Devices.Device.' + mac + ':setName', {"name":name, "source":args[i]})

    #
    def getdev_cmd(args):
        if len(args) == 1:
            mac = str.upper(args[0])
            requete_print('Devices.Device.' + mac + ':get')
        else:
            error("Usage: %s -getdev MACAddress" % sys.argv[0])

    #
    def dhcp_cmd(args):
        """ affiche la table des DHCP statiques """
        if VERSION_LIVEBOX == 'lb28':
            dhcpv4_object = 'NMC'
        else:
            dhcpv4_object = 'DHCPv4.Server.Pool.default'
        requete_print(dhcpv4_object + ":getStaticLeases")

    #
    def adddhcp_cmd(args):
        """ ajoute une entrée DHCP statique """

        if VERSION_LIVEBOX == 'lb28':
            dhcpv4_object = 'NMC'
        else:
            dhcpv4_object = 'DHCPv4.Server.Pool.default'

        if len(args) == 2:
            mac = str.upper(args[0])
            name = args[1]
            print("set dhcp", mac, name)

            requete_print(dhcpv4_object + ':addStaticLease', {"MACAddress": mac ,"IPAddress":  name })
        else:
            error("Usage: %s -adddchp MACAddress IPAddress" % sys.argv[0])

    #
    def deldhcp_cmd(args):
        """ supprime une entrée DHCP statique """

        if VERSION_LIVEBOX == 'lb28':
            dhcpv4_object = 'NMC'
        else:
            dhcpv4_object = 'DHCPv4.Server.Pool.default'

        if len(args) >= 1:
            leases = requete(dhcpv4_object + ':getStaticLeases')
            if args[0] == "all":
                for lease in leases['status']:
                    mac = lease['MACAddress']
                    requete_print(dhcpv4_object + ':deleteStaticLease', {"MACAddress": mac})

            else:
                for i in args:
                    for lease in leases['status']:
                        mac = lease['MACAddress']
                        if str.upper(mac) == str.upper(i):
                            print("del dhcp", mac)
                            requete_print(dhcpv4_object + ':deleteStaticLease', {"MACAddress": mac})
        else:
            error("Usage: %s -deldchp MACAddress..." % sys.argv[0])

    #
    def hosts_cmd(args):
        """ affiche la liste des hosts """
        r = requete("Hosts.Host:get")
        if not r:
            return
        if len(args) > 0:
            for i in range(0, len(args)):
                for _, host in r['status'].items():
                    if host['MACAddress'].lower() == args[i].lower():
                        pprint.pprint(host)
                    elif host['HostName'].lower() == args[i].lower():
                        pprint.pprint(host)
                    elif host['IPAddress'] == args[i]:
                        pprint.pprint(host)
        else:
            #pprint.pprint(r['status'])
            for _, host in r['status'].items():
                actif = " " if host['Active'] else "*"
                if mac_parser is None:
                    s = "%-18s %-15s %c %-35s %s" % (host['MACAddress'], host['InterfaceType'], actif, host['HostName'], host['IPAddress'])
                else:
                    s = "%-18s %-12s %-15s %c %-35s %s" % (host['MACAddress'], mac_parser.get_manuf(host['MACAddress']), host['InterfaceType'], actif, host['HostName'], host['IPAddress'])
                print(s)

    #
    def ipv6_cmd(args):
        """ liste les hosts avec une adresse IPv6 """
        r = requete("Devices:get")
        for i in r['status']:
            a = "-"
            if 'IPv6Address' in i:
                for j in i['IPv6Address']:
                    if j['Scope'] != 'link':
                        a = j['Address']
            b = "-"
            if 'IPAddress' in i: b = i['IPAddress']
            if a == "-": continue
            print("%4s %-32s %-5s %-16s %s" % (i['Index'], i['Name'], i['Active'], b, a))



    #
    def model_cmd(args):
        """ interroge le datamodel de la Livebox: -model [ path [ depth ] ] """

        chemin = 'sysbus'
        prof = None
        if len(args)  >= 1:
            if args[0].startswith("sysbus"):
                chemin = args[0]
            else:
                chemin += '.' + args[0]

        if len(args) >= 2:
            prof = args[1]

        r = requete(chemin, prof, get=True)

        #pprint.pprint(r)
        #print(json.dumps(r))
        #print(type(r))
        if not r is None:
            for i in r:
                model(i)


    def object_cmd(args):
        """ affiche l'objet sans descendre dans le datamodel """
        if len(args) >= 1:
            a = [ args[0], 0 ]
            model_cmd(a)
        else:
            error("Usage...")


    #
    def MIBs_cmd(args):
        """ interroge les MIBs de NeMo.Intf: -MIBs [ nom [ mib ] | show | dump ] """

        '''  trouvé dans opensource.orange.com
- A <b>flag set</b> is a space separated list of flag names. Example: "enabled up".
- A <b>flag expression</b> is a string in which flag names are combined with the logical operators &&, || and !.
  Subexpressions may be grouped with parentheses.
  The empty string is also a valid flag expression and it evaluates to true by definition. Example: "enabled && up".
- Starting at a given Intf, the network stack dependency graph can be traversed in different ways. There are six predefined
  <b>traverse modes</b>:
  - <b>this</b> consider only the starting Intf.
  - <b>down</b> consider the entire closure formed by recursively following the LLIntf references.
  - <b>up</b> consider the entire closure formed by recursively following the ULIntf referenes.
  - <b>down exclusive</b> the same as down, but exclude the starting Intf.
  - <b>up exclusive</b> the same as up, but exclude the starting Intf.
  - <b>one level down</b> consider only direct LLIntfs.
  - <b>one level up</b> consider only direct ULIntfs.
  - <b>all</b> consider all Intfs.
  .
  The resulting structured set of Intfs is called the <b>traverse tree</b>.
  Example: if you apply the traverse mode "down" on Intf eth1 which has LLIntfs swport1, swport2 and swport3,
  the traverse tree will consist of eth1, swport1, swport2 and swport3.
- Some data model functions accept a parameter and/or a function name as input argument. By extension, they may also accept a
  <b>parameter spec</b> and/or <b>function spec</b> as input argument. A parameter/function spec is the concatentation of
  the dot-separated key path relative to a NeMo Intf instance and the parameter/function name, separated by an extra dot.
  Example: the parameter spec "ReqOption.3.Value" refers to the parameter Value held by the object NeMo.Intf.{i}.ReqOption.3.
        '''

        if len(args) == 0:

            # récupère toutes les MIBs de toutes les interfaces
            r = requete('NeMo.Intf.data:getMIBs', { "traverse": "all" })
            if r is None: return
            # pprint.pprint(r)
            print(json.dumps(r, indent=4))

        else:

            if args[0] == "show":
                intf = set()
                r = requete("NeMo.Intf.lo:getIntfs", { "traverse": "all" })
                if not r is None:
                    for i in r['status']:
                        intf.add(i)

                mibs = set()
                r = requete('NeMo.Intf.lo:getMIBs', { "traverse": "this" })
                if not r is None:
                    for i in r['status']:
                        mibs.add(i)

                print()
                print("MIBs (%d): %s" % (len(mibs), str(sorted(mibs))))
                print()
                print("Intf (%d): %s" % (len(intf), str(sorted(intf))))

            elif args[0] == "table":
                html = (len(args) >= 2 and args[1] == "html")
                MIBs_table_cmd(html)

            elif args[0] == "dump":
                MIBs_save_cmd()


#            # sauve toutes les MIBs de toutes les interfaces dans un fichier
#            elif args[0] == "save":
#                r = requete('NeMo.Intf.data:getMIBs', { "traverse": "all" })
#                if r is None: return
#                with open("MIBs_all", "w") as f:
#                    pprint.pprint(r, stream=f)
#                    f.close()
#                print("MIBs écrites dans MIBs_all")

            else:
                if len(args) > 1:
                    r = requete('NeMo.Intf.' + args[0] + ':getMIBs', { "traverse": "this", "mibs":args[1] })
                else:
                    r = requete('NeMo.Intf.' + args[0] + ':getMIBs', { "traverse": "this" })
                if r is None: return
                pprint.pprint(r)


    # ajout la règle pour vpn sur le NAS, l'interface web de la Livebox empêche d'en mettre sur le port 1701
    def add1701_cmd(args):
        """ règle spéciale pour rajouter la règle de forwarding pour L2TP """
        if len(args) != 1:
            error("Usage: ...")
        else:
            print("ajout règle udp1701 pour l'adresse interne %s" % args[0])
            requete_print('Firewall:setPortForwarding',
                            {"description":"udp1701",
                            "persistent":True,
                            "enable":True,
                            "protocol":"17",
                            "destinationIPAddress":args[0],
                            "internalPort":"1701",
                            "externalPort":"1701",
                            "origin":"webui",
                            "sourceInterface":"data",
                            "sourcePrefix":"",
                            "id":"udp1701"})

    # crée une règle de firewall IPv4 sur un port fixe externe et variable interne
    # pratique pour jouer à Minecraft entre amis sans configurer de VPN
    # (d'où le nom de la commande)
    def minecraft_cmd(args):
        """ règle spéciale pour minecraft (forwarding port externe fixe vers un port interne variable) """
        if len(args) != 1:
            error("Usage: -minecraft PORT_INTERNE ou ? ou 0 pour supprimer")

        elif args[0] == '?':

            r = requete('Firewall:getPortForwarding',
                        {"id":"minecraft", "origin":"webui"}, silent=True)
            if r is None:
                print("pas de règle minecraft active")
            else:
                r = r['status']['webui_minecraft']

                ip = requete("DeviceInfo:get")
                ip = ip['status']['ExternalIPAddress']

                print("règle: %s:%s (externe) <-> %s:%s (interne)" % (ip, r['ExternalPort'], r['DestinationIPAddress'], r['InternalPort']))

        else:
            import socket

            port = int(args[0])
            ip = socket.gethostbyname(socket.getfqdn())

            r = requete('Firewall:getPortForwarding',
                        {"id":"minecraft", "origin":"webui"}, silent=True)
            if not r is None:
                r = requete('Firewall:deletePortForwarding',
                            {"id":"minecraft",
                            "origin":"webui",
                            "destinationIPAddress":r['status']['webui_minecraft']['DestinationIPAddress'] })

            if port >= 1024 and port < 65536:
                print("ajout règle minecraft pour le port interne %s et l'adresse %s" % (port, ip))
                r = requete('Firewall:setPortForwarding',
                                {"description":"minecraft",
                                "persistent":True,
                                "enable":True,
                                "protocol":"6",
                                "destinationIPAddress":ip,
                                "internalPort":port,
                                "externalPort":str(MINECRAFT_PORT),
                                "origin":"webui",
                                "sourceInterface":"data",
                                "sourcePrefix":"",
                                "id":"minecraft"}, silent=True)
                if not r is None and r['status'] == 'webui_minecraft':
                    print("Succès")

                    r = requete("DeviceInfo:get")
                    ip = r['status']['ExternalIPAddress']

                    r = requete('Firewall:getPortForwarding', {"id":"minecraft", "origin":"webui"}, silent=True)
                    r = r['status']['webui_minecraft']

                    print("règle: %s:%s (externe) <-> %s:%s (interne)" % (ip, r['ExternalPort'], r['DestinationIPAddress'], r['InternalPort']))

                else:
                    print("Erreur...")
                    print(r)

            else:
                r = requete('Firewall:getPortForwarding', {"id":"minecraft", "origin":"webui"}, silent=True)
                if r is None:
                    print("règle supprimée")
                else:
                    print("Erreur...")
                    print(r)

    def graph_cmd(args):
        """ affiche le graphe fonctionnel des interfaces """

        # charge graphviz
        Digraph = load_graphviz()

        view = True
        for i in args:
            if i == "noview":
                view = False
                args.remove(i)
                break

        if len(args) > 0:
            if len(args) >= 2:
                r = requete('NeMo.Intf.%s:getMIBs' % args[0], { "traverse":args[1], "mibs":"base" })
            else:
                r = requete('NeMo.Intf.%s:getMIBs' % args[0], { "mibs":"base" })
        else:
            r = requete('NeMo.Intf.lo:getMIBs', { "traverse":"all", "mibs":"base" })
        if r is None: return
        if not 'status' in r or not 'base' in r['status']: return
        r = r['status']['base']

        dot = Digraph(name='NeMo.Intf', format='svg', engine='dot')

        dot.attr('node', fontname='Helvetica')
        #dot.attr('node', fontname='Times-Roman')

        for i, node in r.items():
            #dot.attr('node', tooltip=v['Flags'] if 'Flags' in v else '')
            if 'Enable' in node:
                if node['Enable'] == True:
                    dot.node(i, shape='box')
                else:
                    dot.node(i, shape='ellipse', color='lightgrey')
            else:
                dot.node(i, shape='box', color='lightgrey')

        for i, v in r.items():
            for j in v['LLIntf']:
                dot.edge(i, j)

        dot.render(filename="nemo_intf.gv", view=view)


    ##
    # @brief affiche la topologie du réseau tel qu'il est vu par la Livebox
    #
    # @param args 'simple' pour ne pas afficher les détails
    #
    # @return
    def topo_cmd(args):

        # charge graphviz
        Digraph = load_graphviz()

        view = True
        for i in args:
            if i == "noview":
                view = False
                args.remove(i)
                break

        r = requete("Devices.Device.HGW:topology")
        if r is None or not 'status' in r: return
        r = r['status']

        simpleTopo = args[0] == "simple" if len(args) > 0 else False

        dot = Digraph(name='Devices', format='svg', engine='dot')

        # oriente le graphe de gauche à droite
        # plutôt que de haut en bas
        dot.attr('graph', rankdir="LR")

        ##
        # @brief fonction récursive de création du graphe de topologie
        #
        # @param node
        #
        # @return
        def traverse(node):
            key = node['Key'].replace(':', '_')

            dot.attr('node', shape="box")

            # éléments communs à tous les devices:
            communs = set([ 'Tags', 'DiscoverySource', 'Key', 'Alternative', 'Active', 'Index', 'LastConnection',
                            'Name', 'LastChanged', 'Names', 'DeviceType', 'Master', 'DeviceTypes' ])

            if simpleTopo:
                label = node['Name']
            else:

                label = ""
                for nom in ['Name', 'Index', 'DeviceType', 'LastConnection']:
                    if nom in node:
                        s = str(node[nom])
                        if s != "":
                            label += r"%s: %s\n" % (nom, s)
                label += r"\n"

                ignores = set(['ClientID', 'Ageing', 'IPAddressSource', 'VendorClassID' ])
                for i, v in node.items():
                    if i in communs: continue
                    if i in ignores: continue
                    if type(v) is list or str(v) == "":
                        continue
                    label += r"%s: %s\n" % (i, str(v))

            dot.node(key, label=label, color="black" if node['Active'] else "lightgrey")

            if 'Children' in node:
                for j in node['Children']:
                    dot.edge(key, j['Key'].replace(':', '_'))
                    traverse(j)

        for i in r:
            traverse(i)

        if simpleTopo:
            dot.render(filename="devices-simple.gv", view=view)
        else:
            dot.render(filename="devices.gv", view=view)


    ##
    # @brief
    #
    # @param args
    #
    # @return
    def calls_cmd(args):
        """ affiche la liste des appels """
        r = requete("VoiceService.VoiceApplication:getCallList")
        if r is None or not 'status' in r:
            return

        r = r['status']
        if len(args) == 1 and args[0] == '?':
            return print(r[0].keys())

        for i in r:
            if len(args) > 0:
                print(i[args[0]])
            else:
                d = datetime.datetime.strptime(i['startTime'], "%Y-%m-%dT%H:%M:%SZ")

                if i['callOrigin'] == 'local':
                    arrow = '<=='
                else:
                    arrow = '==>'
                print("{:>3} {} {:16}  {}  {}  {:10}".format(
                    i['callId'],
                    arrow,
                    i['remoteNumber'] if i['remoteNumber'] != '' else '**********',
                    d,
                    str(datetime.timedelta(seconds=int(i['duration']))),
                    i['callType']
                    ))


    ################################################################################


    # utilise la réflexivité de Python pour ajouter automatiquement les commandes "xxx_cmd"
    #
    for cmd, func in locals().items():
        if cmd.endswith("_cmd") and callable(func):
            parser.add_argument('-' + cmd[:-4], help=str.strip(func.__doc__ or ""), dest='run_auth', action='store_const', const=func)


##
# @brief requête sybus avec paramètres optionnels
#
# @param sysbus
# @param args
#
# @return
def par_defaut(sysbus, args, raw=False):

    # par défaut, affiche l'heure de la Livebox
    if sysbus is None:
        livebox_info()

        #result = requete(Time:getTime")
        #if result:
        #    print("Livebox time: ", result['data']['time'])

    else:
        parameters = OrderedDict()
        for i in args:
            a = i.split("=", 1)
            parameters[a[0]] = a[1]

        # analyse une requête formulée comme les queries sur les NeMo.Intf.xxx :
        # 'NeMo.Intf.wl1.getParameters(name="NetDevIndex", flag="", traverse="down")'
        p = sysbus.find('(')
        if p >= 0 and sysbus[-1] == ')' and sysbus.find('.') > 0:
            i = sysbus.find(':')
            if i == -1 or i > p:
                # sépare le chemin des paramètres entre parenthèses
                t = sysbus[p + 1:-1]
                sysbus = sysbus[:p]

                # remplace le dernier . par : (séparation du chemin du nom de la fonction)
                p = sysbus.rfind('.')
                sysbus = sysbus[0:p] + ':' + sysbus[p+1:]

                # ajoute les arguments passés entre parenthèses
                for i in t.split(','):
                    if i.find('=') > 0:
                        a = i.strip().split('=', 1)
                        parameters[a[0]] = a[1].strip('"')

        # envoie la requête
        if raw:
            r = requete(sysbus, parameters, raw=True)
            r = r.decode('utf-8', errors='replace')
            sys.stdout.write(r)
        else:
            requete_print(sysbus, parameters)


##
# @brief fonction principale
#
# @return
def main():
    global USER_LIVEBOX, PASSWORD_LIVEBOX, URL_LIVEBOX, VERSION_LIVEBOX
    global verbosity

    parser = argparse.ArgumentParser(description='requêtes sysbus pour Livebox')

    parser.add_argument("-v", "--verbose", action="count", default=verbosity)

    # options "commandes"
    parser.add_argument('-scan', help="analyse les requêtes sysbus dans scripts.js",
            dest='run', action='store_const',
            const=scan_sysbus)

    parser.add_argument('-files', help="extrait les scripts",
            dest='run', action='store_const',
            const=extract_files)

    # gestion de l'authentification
    parser.add_argument('-url', help="url de la Livebox")
    parser.add_argument('-user', help="user de la Livebox")
    parser.add_argument('-password', help="password de la Livebox")
    parser.add_argument('-lversion', help="version de la Livebox (lb4, lb3, ...)")

    # mémorise et affiche la conf
    parser.add_argument('-config', help="écrit la configuration dans ~/.sysbusrc",
            dest='run', action='store_const',
            const=write_conf)

    parser.add_argument('-noauth', help="ne s'authentifie pas avant les requêtes", action='store_true', default=False)

    # modifications du comportement des commandes
    parser.add_argument('-raw', help="", action='store_true', default=False)
    parser.add_argument('-out', help="fichier de sortie")

    # les commandes "requêtes"
    add_singles(parser)
    add_commands(parser)
    parser.add_argument('-modelraw', help="", action='store_true', default=False)
    parser.add_argument('-modeluml', help="", action='store_true', default=False)

    # ajout des arguments génériques (chemin de la commande et paramètres)
    parser.add_argument('sysbus', help="requête", nargs='?')
    parser.add_argument('parameters', help="paramètres", nargs='*')

    # analyse la ligne de commandes
    args = parser.parse_args()

    verbosity = args.verbose
    load_conf()

    new_session = False
    if args.url:
        URL_LIVEBOX = args.url
        if URL_LIVEBOX[-1] != "/": URL_LIVEBOX += "/"
    if args.lversion:
        VERSION_LIVEBOX = args.lversion
    if args.user:
        USER_LIVEBOX = args.user
        new_session = True          # ne charge pas le fichier des cookies
    if args.password:
        PASSWORD_LIVEBOX = args.password
        new_session = True          # ne charge pas le fichier des cookies


    if args.run:
        a = args.parameters
        if not args.sysbus is None:
            a.insert(0, args.sysbus)
        args.run(a)

    else:
        if args.noauth:
            noauth()                        # initialise la session requests
        else:
            if not auth(new_session):       # initialise la session requests avec authentification
                sys.exit(1)


        if args.modelraw:
            prof = None if len(args.parameters) == 0 else args.parameters[0]
            model_raw_cmd(args.sysbus, prof, out=args.out)

        elif args.modeluml:
            prof = None if len(args.parameters) == 0 else args.parameters[0]
            model_uml_cmd(args.sysbus, prof, out=args.out)

        else:
            if args.out:
                debug(2, "redirect to", args.out)
                sys.stdout = open(args.out, "w")

            # commande complexe
            if args.run_auth:
                a = args.parameters
                if not args.sysbus is None:
                    a.insert(0, args.sysbus)
                args.run_auth(a)

            # requête simple
            elif args.req_auth:
                if type(args.req_auth) is str:
                    requete_print(args.req_auth)
                elif len(args.req_auth) == 1:
                    requete_print(args.req_auth[0])
                else:
                    requete_print(args.req_auth[0], args.req_auth[1])

            # requête passée sur la ligne de commandes
            else:
                par_defaut(args.sysbus, args.parameters, args.raw)


if __name__ == '__main__':
    main()
