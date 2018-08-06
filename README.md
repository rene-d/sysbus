# sysbus.py
`sysbus.py` est un script écrit Python 3 qui permet de contrôler une Livebox par programme et d'en explorer les possibilités de contrôle et autres informations masquées. C'est un outil « expérimental ».

Il n'y a - malheureusement - aucune information cachée croustillante à découvrir, ou alors je n'ai rien trouvé. La Livebox est suffisamment bien fermée.

## Installation

Le script est écrit en [Python 3](https://www.python.org/downloads/). Il requiert également [requests](http://docs.python-requests.org/) qui simplifie grandement les requêtes HTTP. Il utilise éventuellement [Graphviz](http://www.graphviz.org) et un de ses modules d'interface Python [graphviz](https://pypi.python.org/pypi/graphviz) pour dessiner des graphes.

    $  pip3 install requests graphviz

Il faudra également installer le moteur Graphviz. Sur OSX on peut utiliser [brew](http://brew.sh). Sur Linux, `sudo apt-get install graphviz` ou équivalent selon la distribution.

Cela devrait fonctionner également avec Windows. Se référer aux sites des différents logiciels pour les procédures d'installation.

## Configuration

La plupart des requêtes requiert une authentification. C'est l'utilisateur `admin` et le mot de passe d'administration (par défaut les 8 premiers caractères de la clé Wi-Fi).

Le script mémorise le mot de passe (ainsi que l'adresse de la Livebox et sa version si l'on n'utilise pas les valeurs par défaut) dans le fichier `~/.sysbusrc`.  

La version de la livebox vaut par défaut `lb4` (Livebox 4) mais peut être remplacée (`lb3` par exemple) après l'argument `-lversion`.  

Pour configurer, taper la commande suivante (en admettant que le mot de passe soit SECRET):

    $ ./sysbus.py -config -password SECRET [ -url http://192.168.1.1/ ] [ -lversion lb4 ]

Dorénavant, le script utilisera ces informations de connexion à chaque fois. On peut tester en demandant l'heure de l'équipement:

    $ ./sysbus.py
    Livebox time:  Sun, 14 Feb 2016 22:08:32 GMT+0100

## Utilisation

Un certain nombre de requêtes sont intégrées au script (comme la demande de l'heure, ou des clés Wi-Fi, des périphériques présents, etc.) avec plus ou moins de formatage du résultat.

Le script est aussi capable d'envoyer presque n'importe quelle requête, pourvu qu'on la spécifie entièrement sur la ligne de commande.

    $ ./sysbus.py Time:getTime
    Livebox time:  Sun, 14 Feb 2016 22:13:30 GMT+0100

L'option `-h` ou `--help` affiche l'ensemble de la syntaxe possible.

## L'interface sysbus

En parcourant les sources mises à disposition par Orange [ici](http://opensource.orange.com/), on peut établir que les Livebox depuis la version 2 utilisent un middleware développé par [SoftAtHome](http://www.softathome.com) et un moteur de datamodel maison nommé "pcb".

Malheureusement je n'ai trouvé aucune référence sur Internet de cette technologie propriétaire, ou bien elle est noyée parmi toutes les [significations](https://fr.wikipedia.org/wiki/PCB) de l'acronyme, dont _Printed Circuit Board_. Orange et son séide SoftAtHome offrent donc un jeu de piste et d'énigmes.

Ce datamodel interne communique avec l'extérieur via une interface HTTP et du JSON nommée "sysbus".

C'est cette interface qu'exploite l'interface d'administration [http://livebox.home] ou les apps [iOS](https://itunes.apple.com/fr/app/ma-livebox/id445573616?mt=8) et [Android](https://play.google.com/store/apps/details?id=com.orange.mylivebox.fr&hl=fr).

Le principe est d'envoyer des requêtes POST avec une liste de paramètres dans un objet JSON, le retour sera un objet JSON contenant le résultat de la requête.

Il est raisonnable de penser que c'est également par cette voie qu'Orange administre les Livebox (activation du Wi-Fi partagé, mises à jour) et peut-être diagnostics du réseau et/ou du matériel.

### Exemple avec curl

API utilisée par les Livebox 4 (firmware SG40_sip-fr-2.14.8.1_7.21.3.1), qui fonctionne avec les Livebox 3 (avec le firmware SG30_sip-fr-5.17.3.1 au moins):

    $ curl -s -X POST -H "Content-Type: application/x-sah-ws-1-call+json" -d '{"service":"NMC","method":"getWANStatus","parameters":{}}' http://192.168.1.1/ws

API utilisée par les précédents Livebox ainsi que les applications mobiles:

    $ curl -s -X POST -H "Content-Type: application/json" -d '{"parameters":{}}' http://192.168.1.1/sysbus/NMC:getWANStatus | jq .

Résultat :

    {
      "result": {
        "status": true,
        "data": {
          "LinkType": "ethernet",
          "LinkState": "up",
          "MACAddress": "3C:81:D8:xx:yy:zz",
          "Protocol": "dhcp",
          "ConnectionState": "Bound",
          "LastConnectionError": "None",
          "IPAddress": "aa.bb.cc.dd",
          "RemoteGateway": "aa.bb.cc.dd",
          "DNSServers": "80.10.246.136,81.253.149.6",
          "IPv6Address": "2a01:cb00:xyzt:abcd:1:2:3:4",
          "IPv6DelegatedPrefix": "2a01:cb00:xyzt:abcd::/56"
        }
      }
    }

[jq](https://stedolan.github.io/jq/) est un outil qui permet entre autres de
reformater le JSON.

Nota: cette requête ne requiert pas d'authentification, contrairement à la demande d'heure.

### Exemples avec le script

    # requête similaire à l'exemple curl ci-dessus
    $ ./sysbus.py sysbus.NMC:getWANStatus

    # en passant des paramètres
    $ ./sysbus.py sysbus.NMC.Wifi:set Enable=True Status=True

### Où trouver les requêtes ?

Le script a une option `-scan` qui liste plus ou moins les appels de méthode qui sont utilisées par l'interface web d'administration. Il utilise pour cela l'agglomérat de scripts javascript de la Livebox. Il faudra en revanche fouiller pour savoir les paramètres éventuels.

Les débogueurs des navigateurs modernes sont aussi capables d'afficher les requêtes envoyées et leurs résultats.

Un autre moyen est d'utiliser [wireshark](https://www.wireshark.org) ou [tcpflow](https://github.com/simsong/tcpflow) et réaliser les actions que le souhaiter scripter, soit via l'interface web, soit via l'app mobile si on sait capturer le Wi-Fi du smartphone ou de la tablette.

Enfin, la dernière source d'information est le datamodel.

## Le datamodel

L'interface sysbus a une fonctionnalité intéressante : celle de pouvoir découvrir le datamodel.

Pour cela, la requête HTTP à faire est un GET sur le nom de l'objet. Le JSON retourné décrit le modèle.

`sysbus.py` est capable de rendre plus lisible le retour en détectant les fonctions, les paramètres et les instances d'objet. Le décodage, basé uniquement sur l'observation, est peut-être incomplet.

    # interroge le datamodel de l'objet NMC.Wifi
    $ ./sysbus.py NMC.Wifi -model

    =========================================== level 0
    OBJECT NAME: 'NMC.Wifi'  (name: Wifi)
    function: startPairing (opt clientPIN)
    function: stopPairing ()
    function: startAutoChannelSelection ()
    function: getStats (out RxBytes, out TxBytes)
    function: get ()
    function: set (opt parameters)
    parameter:  Enable               : bool       = 'True'
    parameter:  Status               : bool       = 'True'
    parameter:  ConfigurationMode    : bool       = 'True'

Lancé sans nom d'objet, le programme affiche le datamodel entier, aux restrictions d'accès près. Cependant des sous-objets peuvent être accessibles, comme NeMo.Intf.data alors que ni NeMo ni NeMo.Intf ne sont accessibles. Il y a également les objets NeMo.MIB.*nom* (NeMo.MIB.alias par exemple), mais accès interdit.

L'option `-modeluml` va créer les diagrammes de classes avec [plantuml](http://plantuml.com) (voir exemple ci-dessous).

Le datamodel reprend certains éléments de différents TR du Broadband Forum (cf. [TR-181](https://www.broadband-forum.org/cwmp/tr-181-2-10-0.html) par exemple). Par exemple, l'objet Device.Hosts est très similaire à celui qu'on trouve dans la Livebox, plus des extensions spécifiques à Orange (X_ORANGE-COM_xxx).

Par ailleurs, la présence d'un utilisateur 'cwmpd' (cf. l'objet UserManagement) au mot de passe inconnu tend à prouver que la Livebox communique en utilisant _CWMP_ (ou [TR-069](https://fr.wikipedia.org/wiki/TR-069)) avec sa gateway de management côté Orange.

![diagramme de classe Hosts](docs/Hosts.png)

### Nouveautés Livebox 4

L'interface web de la LB4 est beaucoup plus évoluée. Le datamodel est sensiblement le même, avec des objets en plus.

On y trouve aussi une description des méthodes via des requêtes Json :

    curl -s http://livebox.home/sdkut/apis/pcb/Time/getTime.json | jq .


## Le graphe NeMo.Intf

Les interfaces et pseudo-interfaces sont organisées en interne en graphe via des connexions _upper_ et _lower_.

L'option `-graph` de `sysbus.py` utilise Graphviz pour afficher le graphe entier des interfaces.

    $ ./sysbus.py -graph

![graphe fonctionnel](docs/nemo_intf.png)

En grisé, les blocs qui sont inaccessibles (ils sont découverts uniquement grâce aux liaisons _upper_ et _lower_). Et en ellipse, les blocs désactivés.

Le graphe s'affiche en SVG, ce qui est permet de zoomer sans perte. C'est modifiable uniquement dans le source du script (changer 'svg' en 'png' par exemple).

Chaque interface gère une ou plusieurs MIBs. La liste peut être extraite avec la commande :

    $ ./sysbus.py -MIBs show

Les MIB (_Management Information Base_) sont apparemment proches des MIB SNMP, sans toutefois en être - ou alors ce sont des MIB propriétaires et inaccessibles en SNMP. C'est la MIB nommée `base` qui est exploitée pour construire le graphe.

    $ ./sysbus.py NeMo.Intf.wl1:getMIBs mibs=base traverse=this
    {'status': {'base': {'wl1': {'Enable': True,
                                 'Flags': 'wlanvap penable netdev enabled '
                                          'wlanvap-bound wlansta netdev-bound '
                                          'inbridge netdev-up up',
                                 'LLIntf': {'wifi1_ath': {'Name': 'wifi1_ath'}},
                                 'Name': 'wl1',
                                 'Status': True,
                                 'ULIntf': {'bridge': {'Name': 'bridge'}}}}}}

L'interprétation du résultat de cette requête est :

- l'objet `wl1` possède la MIB `base`
- les propriétés de la MIB `base` sont : `Name` `LLIntf` `ULIntf` `Status` `Enable` `Flags`
- cette MIB décrit le graphe, `wl1` étant connecté par un lien _upper_ à l'interface `bridge` et par un lien _lower_ à `wifi1_ath`
- l'interface est activée (`Status`)

La commande est également capable d'établir un tableau croisé entre MIBs et interface pour en trouver l'usage. Cf. ce [résultat](docs/MIBs.md) où X=utilisée, 0=référencée mais vide.

    $ ./sysbus.py -MIBs table [html]

**Remarques :**

- Le graphe est peut-être incomplet puisqu'on ne connait les liaisons que des blocs accessibles : on ne peut pas connaître les liaisons entre deux blocs inaccessibles.
- Par ailleurs, les deux blocs commençant par `data` et `lan` semblent séparés, tout deux étant au sommet de deux graphes distincts (au moins si le Wi-Fi partagé n'est pas activé). Pourtant le flux de données passe nécessairement d'un graphe à l'autre. `data` est relié à `eth1` qui la connexion extérieure, vers le boîtier fibre, `lan` est relié au Wi-Fi et à `eth0` qui représente le switch 4 ports du réseau local.
- Il reste certainement à découvrir d'autres informations disséminées dans ces MIB.

## La topologie du réseau

La Livebox est plus ou moins capable d'afficher la [topologie du réseau](http://livebox.home/supportMapper.html) depuis sa page d'administration. Ces informations sont stockées dans le datamodel, et il a plus de détails que l'interface web veut bien en afficher.

Notamment, les périphériques connectés en Wi-Fi 2.4GHz (interface wl0) et ceux connectés en 5GHz (interface wl1).

`sysbus.py` doit être lancé avec l'option `-topo` pour obtenir ce graphe. En fonction du nombre de périphériques, le graphe est très gros. En rajoutant `simple` le programme n'affiche que le nom des périphériques.

On y voit également les ports USB et l'UPnP.

    $ ./sysbus.py -topo simple

![topologie réseau](docs/devices.png)
