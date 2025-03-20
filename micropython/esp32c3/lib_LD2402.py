import os, sys, gc, select, math
from machine import Pin, PWM
from time import sleep, sleep_ms, ticks_ms
from array import array
from microWebSrv import MicroWebSrv as MWS
from lib_common import *
import lib_common as g

gc.collect()

# For 24GHz microwave micro-motion sensor HLK-LD2402
class MSENSOR:
	TYPE = 'HLK-LD2402'
	CMD_ENTER = b'\xfd\xfc\xfb\xfa\x04\x00\xff\x00\x01\x00\x04\x03\x02\x01'
	CMD_LEAVE = b'\xfd\xfc\xfb\xfa\x02\x00\xfe\x00\x04\x03\x02\x01'
	CMD_MODE_ENG = b'\xfd\xfc\xfb\xfa\x08\x00\x12\x00\x00\x00\x04\x00\x00\x00\x04\x03\x02\x01'
	# CMD_MODE_TXT = b'\xfd\xfc\xfb\xfa\x08\x00\x12\x00\x00\x00\x64\x00\x00\x00\x04\x03\x02\x01'

	def send_cmd(self, cmd, wait=True):
		self.uart.write(cmd)
		if wait:
			sleep(0.1)
			while self.uart.any():
				self.uart.read()

	def read_energy(self):
		try:
			data = self.uart.read()
			if data.endswith(b'\r\n'):
				self.init_eng_mode()
				return None
			while b'\xf4\xf3\xf2\xf1' in data:
				p1 = data.find(b'\xf4\xf3\xf2\xf1')
				if data[p1+137:p1+141] == b'\xf8\xf7\xf6\xf5':
					data = data[p1+9:p1+137]
					return array('i', (int.from_bytes(data[i:i+4], 'little') for i in range(0, len(data), 4)))
				data = data[p1+4:]
		except:
			return None


	P = {
		'Calibration_page': '/LD2402.html',
		'UPDATE_ENV_INTV_MS': 2000, # interval for updating environment (ambient light, temperature, etc.)
		'DARK_TH_LOW': 700,		# the darkness level below which sensor will be turned off
		'DARK_TH_HIGH': 800,	# the darkness level above which light will be turned on if motion
		'DELAY_ON_MOV': 30000,
		'DELAY_ON_OCC': 20000,
		'TH_TRIGGER': [5000]*32,
		'TH_SUSTAIN': [4000]*32,
		'GATE_ENABLED': list(range(32)),
		'LED_BEGIN': 300,
		'LED_END': 400,
		'GLIDE_TIME': 1200,
		'N_CONSEC_TRIG': 1,
		'sensor_pwr_dpin_num': '',
		'ctrl_output_dpin_num': '',
		'led_master_dpin_num': '',
		'led_level_ppin_num': '',
		'led_discharge_dpin_num': '',
		'F_read_lux': '',
		'F_read_thermal': '',
		'night_start': '18:00',
		'night_stop': '07:00',
		'midnight_starts': ["23:00", "23:00", "23:00", "23:00", "00:00", "00:00", "23:00"],
		'midnight_stops': ["07:00", "07:00", "07:00", "07:00", "07:00", "07:00", "07:00"],
		'smartctl_starts': ["00:00"]*7,
		'smartctl_stops': ["23:59"]*7,
	}

	def init_eng_mode(self):
		self.send_cmd(self.CMD_ENTER)
		self.send_cmd(self.CMD_MODE_ENG)
		self.send_cmd(self.CMD_LEAVE, False)

	def __init__(self, uart, mws:MWS):  # Typically ~15 frames
		# init status
		# uart.init(115200, timeout_char=10, rxbuf=256)
		self.tm_last_ambient = round(time.time()*1000)
		self.elapse = 0
		self.uart = uart

		# status
		self.is_smartlight_on = False
		self.is_dark_mode = False
		self.logging = False
		self.lux_level = None
		self.thermal_level = None
		self.sensor_log = ''
		self.n_consec_trig = 0
		self.is_calib_mode = False

		# load default params if necessary and create pins
		self.P.update(P.get('LD2402', {}))
		P['LD2402'] = self.P
		auto_makepins(self, self.P)

		# must turn on motion sensor first then turn it off, otherwise it will keeps outputing null
		self.sensor_pwr_dpin(True)

		# keep PWM capacitor discharged before LED smooth on
		self.led_discharge_dpin(False)

		# add webserver handlers
		mws.add_route('/LD2402_calib_begin', 'GET', self.calib_begin)
		mws.add_route('/LD2402_calib_end', 'GET', self.calib_end)
		mws.add_route('/LD2402_calib_get', 'GET', self.calib_get)


	def status(self):
		return {
			'is_smartlight_on': self.is_smartlight_on,
			'is_dark_mode': self.is_dark_mode,
			'lux_level': self.lux_level,
			'thermal_level': self.thermal_level,
			'logging': self.logging,
			'sensor_log': self.sensor_log if self.logging else None,
			'LED_smooth_switch_dpin': self.LED_smooth_switch_dpin(),
			'smartlight_dpin': self.smartlight_dpin()
			}

	def is_midnight(self):
		tm = getDateTime()
		return isTimeInBetween(getTimeString(tm)[:5], self.P['midnight_starts'][tm[6]], self.P['midnight_stops'][tm[6]])
	
	def is_smartctl(self):
		tm = getDateTime()
		return isTimeInBetween(getTimeString(tm)[:5], self.P['smartctl_starts'][tm[6]], self.P['smartctl_stops'][tm[6]])

	def is_night(self):
		return isTimeInBetween(getTimeString()[:5], self.P['night_start'], self.P['night_stop'])

	def LED_smooth_switch_dpin(self, state=None):
		if state is None:
			return self.led_master_dpin()
			
		if not is_valid_pin('led_master_dpin_num', self.P) or self.led_master_dpin()==state:
			return

		prt("glide LED on" if state else "glide LED off")
		GLIDE_TIME = abs(self.P['GLIDE_TIME'])
		LED_END = self.P['LED_END']
		LED_BEGIN = self.P['LED_BEGIN']
		tm0 = ticks_ms()
		spd = abs(LED_END - LED_BEGIN)/max(GLIDE_TIME, 1)
		if state:
			Try(lambda: Pin(self.P['led_discharge_dpin_num'], Pin.IN))
			self.led_level_ppin(LED_BEGIN)
			self.led_master_dpin(1)
			tm_dif = ticks_ms()-tm0
			while tm_dif<GLIDE_TIME and tm_dif>=0:
				self.led_level_ppin(round(LED_BEGIN+spd*tm_dif))
				tm_dif = ticks_ms()-tm0
			self.led_level_ppin(LED_END)
		else:
			# self.led_level_ppin(LED_END)
			# tm_dif = ticks_ms()-tm0
			# while tm_dif<GLIDE_TIME and tm_dif>=0:
			# 	self.led_level_ppin(round(LED_END-spd*tm_dif))
			# 	tm_dif = ticks_ms()-tm0
			self.led_level_ppin(LED_BEGIN)
			sleep_ms(GLIDE_TIME)
			Try(lambda: Pin(self.P['led_discharge_dpin_num'], Pin.OUT)(0))
			self.led_master_dpin(0)
			self.led_level_ppin(0)

	def smartlight_dpin(self, state=None):
		if state is None:
			return self.is_smartlight_on

		if state:
			if self.is_smartctl():
				self.LED_smooth_switch_dpin(True) if self.is_midnight() else self.ctrl_output_dpin(True)
				self.is_smartlight_on = True
				prt("smartlight on")
		else:
			self.ctrl_output_dpin(False)
			self.LED_smooth_switch_dpin(False)
			self.is_smartlight_on = False
			prt("smartlight off")

	def calib_begin(self, *args):
		self.ev32_cnt = 0
		self.ev32_mean = array('f', [0]*32)
		self.ev32_max = array('f', [0]*32)
		self.ev32_min = array('f', [100]*32)
		self.is_calib_mode = True
		gc.collect()
		return 'OK'

	def calib_run1(self, ev32):
		self.ev32_cnt += 1
		for i in range(32):
			self.ev32_mean[i] += ev32[i]
			self.ev32_max[i] = max(self.ev32_max[i], ev32[i])
			self.ev32_min[i] = min(self.ev32_min[i], ev32[i])

	def calib_end(self, *args):
		self.is_calib_mode = False
		mul = 1/max(1, self.ev32_cnt)
		for i in range(32):
			self.ev32_mean[i] *= mul
		return self.calib_get(*args)
	
	def calib_get(self, clie, resp):
		if not self.ev32_cnt:
			return '{}'
		mul = 1/self.ev32_cnt
		obj = {
			'max': ['%.1f'%v for v in self.ev32_max],
			'min': ['%.1f'%v for v in self.ev32_min],
			'mean': ['%.1f'%(v*mul) for v in self.ev32_mean] if self.is_calib_mode else ['%.1f'%v for v in self.ev32_mean]
		}
		return resp.WriteResponseJSONOk(obj)
	
	def compare(self, ev32, th):
		for i in self.P['GATE_ENABLED']:
			if ev32[i]>th[i]:
				return (i, ev32[i])
		return None

	def handleUART(self):
		# read energy values from LD2402
		ev32 = self.read_energy()
		if not ev32:
			return
		
		# handle calibration mode
		if self.is_calib_mode:
			self.last_reading = array('f', (math.log(v+1,10)*10 for v in ev32))
			self.calib_run1(self.last_reading)
			# print(('%.1f '*32) % tuple(self.last_reading))

		# determine activation
		acti = 0
		res = self.compare(ev32, self.P['TH_SUSTAIN'])
		if res:
			acti = 1
			res1 = self.compare(ev32, self.P['TH_TRIGGER'])
			if res1:
				acti = 2
				res = res1
				self.n_consec_trig += 1
				if self.n_consec_trig >= self.P['N_CONSEC_TRIG']:
					acti = 3
			else:
				self.n_consec_trig = 0
		else:
			self.n_consec_trig = 0

		# append to sensor log if enabled
		if self.logging:
			self.sensor_log += f'{"NSTT"[acti]}{(" %d %d"%res) if res else ""}\n'
			while len(self.sensor_log)>120:
				p = self.sensor_log.find('\n')
				self.sensor_log = self.sensor_log[p+1:] if p>=0 else ''
				gc.collect()

		# run ets for PWM
		sleep_ms(0)

		if acti:
			self.run1(acti)


	def run1(self, acti=0):
		millis = round(time.time()*1000)

		# Update ambient level
		if millis-self.tm_last_ambient >= self.P['UPDATE_ENV_INTV_MS']:
			self.lux_level = dft_eval(self.P['F_read_lux'], 9999999)
			self.thermal_level = dft_eval(self.P['F_read_thermal'], '')
			self.tm_last_ambient = millis

		if self.is_dark_mode: # in night
			if self.smartlight_dpin(): # when light/led is on
				if acti >= 2:
					self.elapse = max(self.elapse, millis + self.P['DELAY_ON_MOV'])
				elif acti >= 1:
					self.elapse = max(self.elapse, millis + self.P['DELAY_ON_OCC'])
				if millis > self.elapse:
					self.smartlight_dpin(False)
					sleep_ms(400) # wait for light sensor to stablize and refresh lux value
					self.lux_level = dft_eval(self.P['F_read_lux'], 9999999)
			else:  # when light/led is off
				if (acti>=3) and self.lux_level>=self.P['DARK_TH_HIGH']:
					self.smartlight_dpin(True)
					self.elapse = millis+self.P['DELAY_ON_MOV']
				elif (type(self.lux_level)==int and self.lux_level<self.P['DARK_TH_LOW']): # return to day mode
					if not self.is_night():
						self.sensor_pwr_dpin(False)
					self.is_dark_mode = False
		else: # in day
			if (type(self.lux_level)==int and self.lux_level>(self.P['DARK_TH_HIGH']+self.P['DARK_TH_LOW'])/2):
				self.sensor_pwr_dpin(True)
				self.is_dark_mode = True
