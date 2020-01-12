#!/usr/bin/env bash

password=$1
livebox_url=${2:-http://livebox.home}

if [ -z "$password" ]; then
    wget -nc -nv -x -B ${livebox_url} -i <(cat livebox.log | sed -n -E 's/^GET ([^? ]*).*$/\1/p' | sort -u)
else
    # Connexion et récupération du cookies
    contextID=$(curl -s -X POST -c "myCookies" -H 'Content-Type: application/x-sah-ws-4-call+json' -H 'Authorization: X-Sah-Login' -d '{"service":"sah.Device.Information","method":"createContext","parameters":{"applicationName":"so_sdkut","username":"admin","password":"'$password'"}}' http://livebox.home/ws|jq --raw-output '.data.contextID')

    cat livebox.log | sed -n -E 's/^GET ([^? ]*).*$/\1/p' | sort -u | while read uri
    do
        resource=livebox.home$uri
        # echo $resource
        if [ ! -f $resource ]; then
            mkdir -p $(dirname $resource)
            curl -s -b myCookies -X GET \
                -H 'X-Context: '"$contextID"'' \
                --fail \
                -o $resource \
                ${livebox_url}${uri}
        fi
    done

    # Déconnexion et suppression des fichiers temporaires
    curl -m1 -s -b myCookies -X POST http://livebox.home/logout
    rm myCookies
fi
