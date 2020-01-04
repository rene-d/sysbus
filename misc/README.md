# reverse proxy pour analyser les requêtes livebox de l'interface web

## Lancement
Soit avec Docker (requiert [Docker](https://www.docker.com)):
```bash
docker-compose up --build
```

Soit directement (requiert [Go](https://golang.org)):
```bash
go run proxy.go
```

Ouvrir la [page d'administration](http://localhost:8000/) sur le reverse proxy.

## Extraction des fichiers
```bash
./getfiles.sh
```

Le script également met en forme les JSON avec [jq](https://stedolan.github.io/jq/) et Javascript avec [js-beautify](https://github.com/beautify-web/js-beautify).

## Exploitation des requêtes `POST /ws`

```bash
# dans livebox.log:
POST /ws {"service":"DeviceInfo","method":"get","parameters":{}}
POST /ws {"service":"NetMaster","method":"getInterfaceConfig","parameters":{"name":"Ethernet_DHCP"}}

# commandes sysbus équivalentes:
sysbus DeviceInfo:get
sysbus NetMaster:getInterfaceConfig name=Ethernet_DHCP
```
