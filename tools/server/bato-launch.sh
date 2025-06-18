#!/bin/bash

if [ $# == 0 ]; then
	echo "Usage: $0 <batocera-image.img>"
	echo "Usage: $0 stop"
	exit
fi

if [ `whoami` != root ]; then
	sudo $0 "$@"
	exit
fi

# get default display manager
IMG="$1"
DM=`basename $(cat /etc/X11/default-display-manager)`
PORT=54321

mount_if_not () {
	if [ $# -lt 2 ]; then
		echo "Usage: mount_if_not source target [options]"
		exit 1
	fi
	if ! mountpoint -q "$2"; then
		mkdir -p "$2"
		mount ${@:3} "$1" "$2"
	fi
}

unmount_safe () {
	if mountpoint -q "$1"; then
		umount $1
	fi
	if mountpoint -q "$1"; then
		umount -fl $1
	fi
}

if [ $1 != stop ]; then
	# Mount Batocera image
	LOOP_DEV=`losetup --show -Pf $IMG`
	mkdir -p /batocera/boot /batocera/rootfs /batocera/rootfs.upper /batocera/rootfs.lower /batocera/rootfs.work
	mount_if_not $LOOP_DEV"p1" /batocera/boot
	mount_if_not /batocera/boot/boot/batocera /batocera/rootfs.lower
	## Mount Batocera root file-system as overlay so that we can write
	mount -t overlay overlay \
		-o lowerdir=/batocera/rootfs.lower,upperdir=/batocera/rootfs.upper,workdir=/batocera/rootfs.work \
		/batocera/rootfs
	mount_if_not /batocera/boot /batocera/rootfs/boot --bind
	for d in dev dev/pts proc sys run var/run lib/firmware; do
		mount_if_not /$d /batocera/rootfs/$d --bind
	done

	if [ "$2" == mount ]; then exit; fi

	# Copy over DNS configuration so that chroot can access Internet
	rm -f /batocera/rootfs/etc/resolv.conf /batocera/rootfs/etc/machine-id
	cp /etc/resolv.conf /etc/machine-id /batocera/rootfs/etc/

	# Re-purpose shutdown, reboot, and poweroff
	if [ ! -e /batocera/rootfs/root/reboot ]; then
		cd /batocera/rootfs/sbin/
		mv -f shutdown reboot poweroff ../root/ 2>/dev/null
		mkfifo ../signal.fifo
		echo -e '#!/bin/bash\nif [[ "$*" =~ -r ]]; then /etc/init.d/S31emulationstation restart\n else echo exit>/signal.fifo\nfi' >shutdown
		chmod +x shutdown
		cd -
	fi

	# Copy over initial emulationstation configuration files to /userdata
	if [ ! -e /batocera/rootfs/userdata/system ]; then
		cp -rf /batocera/rootfs/usr/share/batocera/datainit/* /batocera/rootfs/userdata/
	fi
	mkdir -p /batocera/rootfs/var/log

	# Determine active GPU device
	GPU=
	for gpu in /dev/dri/card*; do
		if [ "`kmsprint --device=$gpu`" ]; then
			GPU=$gpu
		fi
	done

	# Exit display manager
	systemctl stop bluetooth
	systemctl stop $DM

	if [ "$2" == prepare ]; then exit; fi

	# Enter Batocera
	#chroot /batocera/rootfs /etc/init.d/S01dbus start
	#chroot /batocera/rootfs /etc/init.d/S05udev start
	chroot /batocera/rootfs /etc/init.d/S03seatd start
	chroot /batocera/rootfs /etc/init.d/S06audio start
	chroot /batocera/rootfs bash -c "WLR_BACKENDS=drm WLR_DRM_DEVICES=$GPU /etc/init.d/S31emulationstation start"
	chroot /batocera/rootfs /etc/init.d/S32bluetooth start
	chroot /batocera/rootfs /etc/init.d/S50triggerhappy start
	chroot /batocera/rootfs /etc/init.d/S90hotkeygen start

	read </batocera/rootfs/signal.fifo
fi

sync

# Exit Batocera
chroot /batocera/rootfs /etc/init.d/S90hotkeygen stop
chroot /batocera/rootfs /etc/init.d/S50triggerhappy stop
chroot /batocera/rootfs /etc/init.d/S32bluetooth stop
chroot /batocera/rootfs /etc/init.d/S31emulationstation stop
sleep 0.5
killall -9 emulationstation
chroot /batocera/rootfs start-stop-daemon -K --exec `which bluetoothd`
chroot /batocera/rootfs /etc/init.d/S06audio stop
chroot /batocera/rootfs /etc/init.d/S03seatd stop
#chroot /batocera/rootfs /etc/init.d/S05udev stop
#chroot /batocera/rootfs /etc/init.d/S01dbus stop

# Start display manager
systemctl restart $DM
systemctl restart bluetooth

for d in lib/firmware var/run run sys proc dev/pts dev; do
	unmount_safe /batocera/rootfs/$d
done
unmount_safe /batocera/rootfs/boot
unmount_safe /batocera/rootfs
unmount_safe /batocera/rootfs.lower
unmount_safe /batocera/boot
losetup -l | grep batocera | awk '{print $1}' | while read line; do
	losetup -d $line
done

killall `basename $0`
