#!/usr/bin/env bash

find livebox.home -name '*.js' | xargs js-beautify -r -q
find livebox.home -name '*.json' -execdir sh -c 'jq . {} > .tmpfile && mv .tmpfile {}' \;
