# reverse proxy pour analyser les requêtes livebox de l'interface web

C'est la méthode la plus simple pour reconstruire l'arborescence des fichiers du serveur web de la Livebox. L'analyse de `loader.js` ou `mhsLoader.js` est Extrêmement compliquée.

Elle s'effectue en deux phases:
* consignation par le reverse proxy des requêtes http en naviguant sur l'interface d'administration
* analyse des fichiers à la recherche de fichiers supplémentaires

## Lancement
Soit avec Docker (requiert [Docker](https://www.docker.com)):
```bash
docker-compose up --build
```

Soit directement (requiert [Go](https://golang.org)):
```bash
go run proxy.go
```

Ouvrir la [page d'administration](http://localhost:8000/) sur le reverse proxy et faire des actions.

Les requêtes sont consignées dans le fichier `livebox.log`.

## Extraction des fichiers
```bash
./getfiles.sh
./sdkut.py
```

Le script peut également mettre en forme les JSON avec [jq](https://stedolan.github.io/jq/) et Javascript avec [js-beautify](https://github.com/beautify-web/js-beautify).

```bash
./getfiles.sh indent
```

## L'interface d'administration

Il y a principalement 3 types de fichiers:
* fichiers « web » (.html, .png, librairies Javascript, etc.)
* description d'un service SoftAtHome : `sdkut/semantic/sah/x/y/z.js`
* description d'un service pcb (ou sysbus) : `sdkut/apis/pcb/<Object>/<method>.json`


## Exploitation des requêtes `POST /ws`

```bash
# dans livebox.log:
POST /ws {"service":"DeviceInfo","method":"get","parameters":{}}
POST /ws {"service":"NetMaster","method":"getInterfaceConfig","parameters":{"name":"Ethernet_DHCP"}}

# commandes sysbus équivalentes:
sysbus DeviceInfo:get
sysbus NetMaster:getInterfaceConfig name=Ethernet_DHCP
```
