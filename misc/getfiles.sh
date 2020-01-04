#!/bin/bash

wget -nv -x -B http://livebox.home/ -i <(
    cat livebox.log | awk '/^GET /{print substr($2, 1, index($2, "?sah") - 1) }' | sort -u
)


find livebox.home -name '*.js' | xargs js-beautify -r

find livebox.home -name '*.json' -execdir sh -c 'jq . {} > .tmpfile && mv .tmpfile {}' \;
