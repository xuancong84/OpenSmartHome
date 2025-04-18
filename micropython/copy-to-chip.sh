#!/usr/bin/env bash

set -e


if [ -e /dev/ttyUSB* ]; then
	export dev=`echo /dev/ttyUSB*`
elif [ -e /dev/tty.wchusbs* ]; then
	export dev=`echo /dev/tty.wchusbs*`
elif [ -e /dev/tty.usbserial-* ]; then
	export dev=`echo /dev/tty.usbserial*`
elif [ -e /dev/tty.usbm* ]; then
	export dev=`echo /dev/tty.usbm*`
elif [ -e /dev/ttyACM* ]; then
	export dev=`echo /dev/ttyACM*`
elif [ -e /dev/ttyACM* ]; then
	export dev=`echo /dev/ttyACM*`
else
	echo 'Error: no device found in /dev/ttyUSB* or /dev/ttyACM*'
	exit 1
fi

pyboard() {
	~/anaconda3/bin/python ~/bin/pyboard.py --device $dev -b 115200 "$@"
}

copy_if() {
	for f in "$@"; do
		if [ -s "$f" ]; then
			pyboard -f cp "$f" :"$f"
		fi
	done
}

if [ $# -gt 0 ]; then
	for f in "$@"; do
		mpy-cross $f
		fmpy=${f::-3}.mpy
		pyboard -f cp $fmpy :firmware/
		pyboard -c "import esp;print('$fmpy', esp.add_frozen('firmware/$fmpy','$fmpy'))"
	done
	exit
fi


set +e
pyboard -f mkdir firmware
set -e

for f in main.py rescue.py lib*.py; do 
	mpy-cross $f
	fmpy=${f::-3}.mpy
	echo "Copying $fmpy ..."
	pyboard -f cp $fmpy :firmware/
	pyboard -c "import esp;print('$fmpy', esp.add_frozen('firmware/$fmpy','$fmpy'))"
done

copy_if rc-codes.txt

set +e
pyboard -f mkdir  static
set -e

copy_if static/*
copy_if *.tcp
copy_if webrepl_cfg.py
copy_if secret.py
copy_if boot.py

