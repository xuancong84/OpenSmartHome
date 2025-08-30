import os, sys, esp, machine, time, network
from machine import Pin

reserved_pins = []

def rescue():
	dummy = lambda *arg:(lambda *arg1:None)
	P12 = dummy if 12 in reserved_pins else Pin
	P13 = dummy if 13 in reserved_pins else Pin
	sta_if = network.WLAN(network.STA_IF)
	sta_if.active(True)
	if b'RESCUE-ESP' in [i[0] for i in sta_if.scan()]:
		sta_if.connect('RESCUE-ESP', 'rescue-esp')
		x = 0
		while not sta_if.isconnected():
			x += 1
			P12(12, Pin.OUT)(x&1)
			P13(13, Pin.OUT)(not x&1)
			time.sleep(0.25)
		P12(12, Pin.IN)
		P13(13, Pin.IN)
		os.dupterm(None, 1)
		import webrepl
		webrepl.start()
		sys.exit()
	else:
		P12(12, Pin.IN)
		P13(13, Pin.IN)
		sta_if.active(False)
		