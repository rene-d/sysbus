#!/usr/bin/env bash
# rejoue les requêtes sysbus de livebox.log

password=$1
livebox_url=${2:-http://livebox.home}

mkdir -p ws

# Connexion et récupération du cookies
contextID=$(curl -s -X POST -c "myCookies" -H 'Content-Type: application/x-sah-ws-4-call+json' -H 'Authorization: X-Sah-Login' -d '{"service":"sah.Device.Information","method":"createContext","parameters":{"applicationName":"so_sdkut","username":"admin","password":"'$password'"}}' http://livebox.home/ws|jq --raw-output '.data.contextID')

grep '^POST' livebox.log | grep -v ' {"events":' | while read col1 col2 col3
do
    i=$[i + 1]

    method=$(echo "$col3" | jq -rc '.method')

    if [[ $method =~ list || $method =~ get || $method =~ has || $method =~ retrieve || $method =~ logEvents  ]]; then

        out=ws/$(echo "$col3" | jq -rc '"\(.service).\(.method)"')_$i.json

        curl -s -b myCookies -X POST \
           -H 'Content-Type: application/x-sah-ws-4-call+json; charset=UTF-8' \
           -H 'Accept: text/javascript' \
           -H 'X-Context: '"$contextID"'' \
           -H 'X-Prototype-Version: 1.7' \
           -d "$col3" ${livebox_url}/ws | jq . > $out

    else
        service=$(echo "$col3" | jq -rc '"\(.service):\(.method)"')
        echo "skipping $service"
    fi
done

#Déconnexion et suppression des fichiers temporaires
curl -m1 -s -b myCookies -X POST http://livebox.home/logout
rm myCookies
