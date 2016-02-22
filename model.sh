#! /bin/bash

name=${1:-sysbus}

if [ $name == -intf ]; then
  for i in dump/mibs/*.mib; do
    $0 NeMo.Intf.$(basename -s .mib $i)
  done
  exit
fi

rm -f model.json model.svg model.plantuml

./sysbus.py -model raw $name $2
./model.py

if [ -f model.svg ]; then
  mv model.svg $name.svg
  open $name.svg
elif [ -d models ]; then
  open models
else
  echo pas de fichier créé. erreur ?...
fi