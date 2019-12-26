#!/usr/bin/env bash

# sysbus_cmd="$(cd $(dirname $0); pwd)/src/sysbus/sysbus.py"
sysbus_cmd=sysbus

sysbus()
{
	#time -p $sysbus_cmd $* 2>/dev/null
	$sysbus_cmd $* 2>/dev/null
}

progress_i=0
progress_max=$(awk '/^progress [[:digit:]]/{ a += $2 } END{ print a }' $0)

progress()
{
	if [ "$1" == "done" ]; then
		printf "\n"
		return
	fi

	progress_i=$(($progress_i + $1))

	# Process data
	let _progress=$progress_i*100/$progress_max
	let _done=(${_progress}*4)/10
	let _left=40-$_done

	# Build progressbar string lengths
	_fill=$(printf "%${_done}s")
	_empty=$(printf "%${_left}s")

	# Build progressbar strings and print the ProgressBar line
	printf "\rProgress : [${_fill// /*}${_empty// /-}] ${_progress}%%"

	shift
	$* &> /dev/null
}

mkdir -p dump
cd dump

# télécharge le fichier scripts.js des livebox, c'est l'agrégation de plusieurs fichiers .js
progress 200   curl -s -O --compressed http://livebox.home/scripts.js
progress 20    curl -s -O --compressed http://livebox.home/version.txt
progress 280   sysbus -version -out status.txt
progress 470   sysbus -info -out info.txt
progress 420   sysbus -hosts -out hosts.txt
progress 8500  sysbus -model -out model.txt
progress 9500  sysbus -modelraw -out model.json
progress 870   sysbus -graph noview
progress 590   sysbus -topo simple noview
progress 590   sysbus -topo noview
progress 1260  sysbus -MIBs -out mibs_all
progress 290   sysbus -MIBs show -out mibs.txt
progress 14003 sysbus -MIBs dump
progress 1750  sysbus -MIBs table -out mibs-table.md
progress 1210  sysbus -MIBs table html -out mibs-table.html

progress done