#!/bin/bash

wget -nc -nv -x -B http://livebox.home/ -i <(
    cat livebox.log | awk '/^GET /{ i=index($2,"?sah"); if (i!=0) print substr($2,1,i-1); else print $2; }' | sort -u
)

if [ "$1" = "indent" ]; then
    find livebox.home -name '*.js' | xargs js-beautify -r -q
    find livebox.home -name '*.json' -execdir sh -c 'jq . {} > .tmpfile && mv .tmpfile {}' \;
fi
