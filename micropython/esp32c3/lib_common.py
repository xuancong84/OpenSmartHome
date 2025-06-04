import os, sys, time, ntptime, network, gc, select, machine
from machine import Timer, ADC, Pin, PWM, UART
from time import sleep, sleep_ms, ticks_ms
from neopixel import NeoPixel

Timers = {}	# {'timer-name': [last-stamp-sec, period-in-sec, True (is periodic or oneshot), callback_func]}
A0, A1, A2, A3, A4 = [ADC(i) for i in range(5)]

# Global savable parameters, any variable MUST NOT be None, setting it to None will delete the variable
P = {
	'DEBUG': False,
	'SMART_CTRL': True,
	'SAVELOG': False,
	'use_BLE': False,
	'timezone': 8,
	'RL_MAX_DELAY': 10,
	'LOGFILE': 'static/log.txt',
	'DEBUG_dpin_num': '',	# only GPIO 2 or None: for debug blinking
	'PIN_RF_IN': '',		# GPIO5 tested working
	'PIN_RF_OUT': '',		# GPIO4 tested working
	'PIN_IR_IN': '',		# GPIO14 tested working
	'PIN_IR_OUT': '',		# GPIO12 tested working
	'PIN_ASR': '',			# ESP32 can use any GPIO
	'PIN_MSENSOR': '',		# ESP32 can use any GPIO
	'CLS_MSENSOR': '',		# e.g., LD1115H or LD2402, will be passed to `import lib_{CLS_MSENSOR}` and eval(CLS_MSENSOR)
	}

url_string = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_.~/?'
is_valid_pin = lambda pin, P=P: (type(P.get(pin, '')) in [int, tuple]) or P.get(pin, '')
read_py_obj = lambda f: Try(lambda: eval(open(f).read()), '')
execRC = dft_eval = flashLED = lambda **kw:None

def Try(*args):
	exc = ''
	for arg in args:
		try:
			return arg() if callable(arg) else arg
		except Exception as e:
			exc = e
	return str(exc)


class PIN:
	""" Either pass in:
	 A) a machine.Pin object for direct control, or
	 B) an Integer with a pin_name '_*pin_num' to create the pin
	where * can be:
		d: output digital pin
		i: input digital pin
		p: PWM pin
		a: ADC pin
		neo: NeoPixel pin (invert: do not init color (NeoPixel keeps previous color upon reboot but not color buffer))
	or
	 C) a string: to be evaluated to an lambda function to execute, or
	 D) a tuple: a virtual Pin having multiple states, each corresponding to a execRC string item, or
	 E) a list: where multiple Pins are bundled and controlled together
	"""
	def __init__(self, pin, pin_name='', invert=None):
		self.pin_name = f'PIN({pin})'
		self.invert = invert or False
		self.type = None
		if type(pin)==int:
			self.pin = abs(pin)
			self.invert = pin<0 if invert is None else invert
			if pin_name.endswith('pin_num'):
				self.pin_name = pin_name[:-4]
				self.type = pin_name[:-7].split('_')[-1]
				if self.type=='d':
					self.pin = Try(lambda:Pin(self.pin, Pin.OUT), '')
				elif self.type=='p':
					self.pin = Try(lambda:PWM(self.pin, freq=1000, duty=0),'')
				elif self.type=='i':
					self.pin = Try(lambda:Pin(self.pin, Pin.IN), '')
				elif self.type=='a':
					self.pin = Try(lambda:ADC(self.pin), '')
				elif self.type=='neo':
					self.pin = Try(lambda:NeoPixel(Pin(self.pin), 1), '')
					if not self.invert:
						self.pin.write()
					self.invert = False
		elif type(pin) is str:
			self.pin = dft_eval(pin)
		elif type(pin) is tuple:
			self.pin = pin
			self.state = int(invert)
		elif type(pin) is list:
			self.pin = [PIN(p1, pin_name=pin_name, invert=invert) for p1 in pin]
		else:
			self.pin = pin

	def __call__(self, *args):
		try:
			if args:
				prt(self.pin_name, ':', args)
			if self.invert:
				if self.type == 'p':
					return self.pin.duty_u16(round((1-args[0])*65535)) if args else 1-self.pin.duty_u16()/65535
				elif self.type in ['d', 'i']:
					return self.pin(1-args[0]) if args else 1-self.pin()
				elif self.type == 'a':
					return 1.0-self.pin.read_u16()/65535
				elif self.type == '':
					return Pin(self.pin)(1-args[0]) if args else 1-Pin(self.pin)()
			else:
				if self.type == 'p':
					return self.pin.duty_u16(round(args[0]*65535)) if args else self.pin.duty_u16()/65535
				elif self.type in ['d', 'i']:
					return self.pin(*args)
				elif self.type == 'a':
					return self.pin.read_u16()/65535
				elif self.type == '':
					return Pin(self.pin)(*args)
				elif self.type == 'neo':
					if not args:
						return self.pin[0]
					else:
						self.pin[0] = args[0] if type(args[0]) in [tuple, list] else args
						self.pin.write()
						return args[0]

				if type(self.pin) is tuple:
					if not args:
						return self.state
					self.state = args[0]
					return execRC(self.pin[self.state]) if self.state != args[0] else None
				
				if type(self.pin) is list:
					return [p1(*args) for p1 in self.pin]
	
				return self.pin(*args) if callable(self.pin) else None
		except Exception as e:
			return f'Pin({args}) : {e}'


_auto_pins = set()
def auto_makepins(ns, dct):
	for k, v in dct.items():
		if k.endswith('pin_num'):
			setattr(ns, k[:-4], PIN(v, k))
			_auto_pins.add(k[:-4])

def auto_status(ns, dct):
	for name in _auto_pins:
		if hasattr(ns, name) and name not in dct:
			dct[name] = getattr(ns, name)()
	for k, v in dct.items():
		if type(v)==dict and hasattr(ns, k):
			auto_status(getattr(ns, k), v)
	return dct


getDateTime = lambda: time.localtime(time.time()+3600*P['timezone'])

def getTimeString(tm=None):
	tm = tm or getDateTime()
	return '%02d:%02d:%02d'%(tm[3],tm[4],tm[5])

def getDateString(tm=None, showDay=True):
	tm = tm or getDateTime()
	ds = "%04d-%02d-%02d"%(tm[0],tm[1],tm[2])
	return ds if showDay else ds[:-3]

weekDays=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
def getWeekdayNum(tm=None):
	tm = tm or getDateTime()
	return tm[6]

def getWeekdayString(tm):
	return weekDays[tm[6]]

def getFullDateTime():
	tm = getDateTime()
	return getDateString(tm)+" ("+getWeekdayString(tm)+") "+getTimeString(tm)

def syncNTP():
	t = time.time()
	for i in range(3):
		try:
			ntptime.settime()
			break
		except:
			time.sleep(1)
			gc.collect()
	t = time.time()-t
	for k, v in Timers.items():
		v[0] += t

# Compare time string, whether dt is in between dt1 and dt2
# If dt1==dt2 => range=0, always false
# If dt1='00:00*' && dt2='24:00*' => range=24hrs, always true
def isTimeInBetween(dt, dt1, dt2):
	if not dt1 or not dt2 or dt1==dt2:
		return False
	return (dt>=dt1 and dt<=dt2) if dt2 > dt1 else (dt>=dt1 or dt<=dt2)

# On ESP8266, virtual timers with large periods (> a few seconds) will cause system crash upon receiving HTTP request
def FastTimer(period, F, keep=False):
	assert period<2000
	tmr = Timer(-1)
	tmr.init(period=period, mode=Timer.PERIODIC, callback=F)
	if keep:
		return tmr
	else:
		del tmr

def SetTimer(name, period, repeat, F):
	Timers[name] = [time.time(), period, repeat, F]

def DelTimer(name):
	Timers.pop(name, None)

def prt(*args, **kwarg):
	if P['DEBUG']:
		print(getFullDateTime(), end=' ')
		print(*args, **kwarg)
	if P['SAVELOG']:
		LOGFILE = P['LOGFILE']
		try:
			if os.stat(LOGFILE)[6]>500000:
				os.rename(LOGFILE, LOGFILE+'.old')
		except:
			pass
		with open(LOGFILE, 'a') as fp:
			print(getFullDateTime(), end=' ', file=fp)
			print(*args, **kwarg, file=fp)

def parse_data(s):
	if type(s)==int:
		h = hex(s)[2:]
		return bytes.fromhex(('0'+h) if len(h)&1 else h)
	if type(s)==str:
		return Try(lambda: bytes.fromhex(s), s.encode())
	return s

def url_encode(s):
	try:
		p = s.find('/', s.find('//')+2)
		return s[:p] + ''.join([(c if c in url_string else f'%{ord(c):x}') for c in s[p:]])
	except:
		return s

def load_params(ns):
	ret = Try(lambda: [P.update(eval(open('params.conf').read())), 'OK'][1], 'Load default OK')
	auto_makepins(ns, P)
	return ret

def save_params():
	try:
		with open('params.conf', 'w') as fp:
			fp.write(str(P))
		return 'OK'
	except Exception as e:
		return str(e)


class UART_buf:
	def __init__(self, obj):
		self.uart = obj
		for attr in dir(obj):
			if not hasattr(self, attr):
				setattr(self, attr, getattr(obj, attr))

	def any(self):
		return bool(select.select([self.uart], [], [], 0)[0])
	
	def read(self):
		buf = bytearray(256)
		n = 0
		while select.select([self.uart], [], [], 0.001)[0] and n<256:
			buf[n] = ord(self.uart.read(1))
			n += 1
		return bytes(buf[:n])

def set_uart(p):
	try:
		p = eval(p) if type(p) is str else p
		if type(p) is int:
			if p in [20, 21]:
				import micropython
				micropython.kbd_intr(-1)
				return UART_buf(sys.stdin.buffer)	# the same as sys.stdout.buffer (bound to RX0/TX0)
			return UART(1, 115200, rx=p, tx=21, timeout_char=1)
		elif type(p) is tuple:
			if p[0] in [20,21] or p[1] in [20,21]:
				import micropython
				micropython.kbd_intr(-1)
				return UART_buf(sys.stdin.buffer)	# the same as sys.stdout.buffer (bound to RX0/TX0)
			return UART(1, 115200, rx=p[0], tx=p[1], timeout_char=1)
	except:
		pass
	return None


class Critical():
	def __init__(self, disable_irq=True, max_freq=True):
		self.disable_irq = disable_irq
		self.max_freq = max_freq

	def __enter__(self):
		if self.max_freq:
			self.freq = machine.freq()
			if self.freq < 160000000:
				machine.freq(160000000)
				sleep_ms(10)
		if self.disable_irq:
			self.irqs = machine.disable_irq()
		return self
	
	def __exit__(self, exception_type, exception_value, exception_traceback):
		if self.disable_irq:
			machine.enable_irq(self.irqs)
		if self.max_freq and self.freq < 160000000:
			machine.freq(self.freq)
			sleep_ms(10)
