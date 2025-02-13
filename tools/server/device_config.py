#!/usr/bin/env python3
# This file contains non-UI-adjustable settings that configures your entire home setup

import os, sys
from collections import defaultdict

# all fields must be set, if absent put ''
KTV_SPEAKER='10:3C:88:17:20:78'
KTV_SCREEN='livingTV:HDMI_1'
MP3_SPEAKER='54:B7:E5:9E:F4:14'
MP3_DFTLIST='Desktop/musics.m3u'
MP4_SPEAKER=['hdmi', 'audio.stereo']
MP4_DFTLIST='KTV'
BLE_DEVICES=[{'name':'living room ceiling light player', 'MAC':'99:52:A0:B7:E8:8F'}]
MIC_RECORDER='usb'
TMP_DIR='/dev/shm'
DEFAULT_S2T_SND_FILE=f'{TMP_DIR}/speech.webm'
DEFAULT_T2S_SND_FILE=f'{TMP_DIR}/speak.mp3'
PLAYSTATE_FILE='.playstate.json.gz'
DRAMA_DURATION_TH=1200
LG_TV_CONFIG_FILE='~/.lgtv/config.json'
LG_TV_BIN='./miniconda3/bin/lgtv --ssl'
SHARED_PATH='~/Public'
DOWNLOAD_PATH=SHARED_PATH+'/Download'
MAX_WALK_LEVEL=2
ASR_CLOUD_URL='http://localhost:8883/run_asr/base'
ASR_CLOUD_TIMEOUT=8
VOICE_VOL=defaultdict(lambda: None, {None: 60})
STD_VOL_DBFS=-21
DEBUG_LOG = True
CUSTOM_CMDLINES={}
HUBS={}

ASRchip_voice_IP='http://192.168.50.4'
ASRchip_voice_hex = {
	'speak_drama': ('a5650a', 3.5),
	'speak_song': ('a5640a', 3),
	'asr_not_found': ('a5020a', 3),
	'asr_not_found_drama': ('a5020a', 3),
	'asr_not_found_file': ('a5020a', 3),
	'asr_found': ('a5000a', 3),
	'asr_found_drama': ('a5000a', 3),
	'asr_found_file': ('a5000a', 3),
}

VOICE_CMD_FFWD_DCT = {
	'快进到': 'auto',
	'快进': 'auto',
	'电视机快进到': 'livingTV',
	'电视机快进': 'livingTV',
	'客厅电视机快进到': 'livingTV',
	'客厅电视机快进': 'livingTV',
	'播放器快进到': None,
	'播放器快进': None,
	'主人房电视机快进到': 'masterTV',
	'主人房电视机快进': 'masterTV',
	'客人房电视机快进到': 'commonTV',
	'客人房电视机快进': 'commonTV',
	
	'快退到': 'auto',
	'快退': 'auto',
	'电视机快退到': 'livingTV',
	'电视机快退': 'livingTV',
	'客厅电视机快退到': 'livingTV',
	'客厅电视机快退': 'livingTV',
	'播放器快退到': None,
	'播放器快退': None,
	'主人房电视机快退到': 'masterTV',
	'主人房电视机快退': 'masterTV',
	'客人房电视机快退到': 'commonTV',
	'客人房电视机快退': 'commonTV',
}

FAN_CMDS = {
	'dinningFan': {
		'OFF': 'http://192.168.50.4/rc_run?DFS',
		'LEVELS': [
			'http://192.168.50.4/rc_run?DFL',
			'http://192.168.50.4/rc_run?DFM',
			'http://192.168.50.4/rc_run?DFH']
	},
	'sofaFan': {
		'OFF': 'http://192.168.50.4/rc_run?SFS',
		'LEVELS': [
			'http://192.168.50.4/rc_run?SF1',
			'http://192.168.50.4/rc_run?SF2',
			'http://192.168.50.4/rc_run?SF3',
			'http://192.168.50.4/rc_run?SF4',
			'http://192.168.50.4/rc_run?SF5',
			'http://192.168.50.4/rc_run?SF6']
	},
	'roomFloorFan': {
		'OFF': 'http://192.168.50.4/rc_run?RFF',
		'ON': 'http://192.168.50.4/rc_run?RFN',
		'LEVELS': [
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0001"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0002"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0003"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0004"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0005"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0006"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0007"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0008"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0009"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.12', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0425A/command\x00\x04{\n  "data": {\n    "fnsp": "0010"\n  },\n  "h": "438/E1G-SG-NGA0425A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T11:02:20Z"\n}'}]
	},
	'livingFloorFan': {
		'OFF': 'http://192.168.50.4/rc_run?LFF',
		'ON': 'http://192.168.50.4/rc_run?LFN',
		'LEVELS': [
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0001"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0002"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0003"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0004"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0005"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0006"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0007"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0008"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0009"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'},
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0010"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'}]
	}
}

SECRET_VARS = ['ASR_CLOUD_URL', 'CUSTOM_CMDLINES', 'HUBS', 'ACCUWEATHER_API_GET']
if os.path.isfile('secret.py'):
	import secret
else:
	class A: pass
	secret = A()

for var in SECRET_VARS:
	exec(f'{var}=getattr(secret, "{var}", None)', globals(), globals())
