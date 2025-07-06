#!/usr/bin/env python3
# This file contains non-UI-adjustable settings that configures your entire home setup

import os, sys
from collections import defaultdict

# all fields must be set, if absent put ''
KTV_SPEAKER='10:3C:88:17:20:78'
KTV_SPEAKER_ON={'protocol':'BLE', 'data': '0201011bffff00ee1bc878f64a4491542fb40e6e1b2120a5443c1ea5e2a6dd'}
KTV_SPEAKER_OFF={'protocol':'BLE', 'data': '0201011bffff00ee1bc878f64a4491562fb40e6ecaf0f38b95edcf743364c4'}
KTV_SCREEN='livingTV:HDMI_2'
KTV_EXEC='~/projects/pikaraoke/run-cloud.sh'
MP3_SPEAKER='54:B7:E5:9E:F4:14'
MP3_DFTLIST='Desktop/musics.m3u'
MP4_SPEAKER=['hdmi', 'audio.stereo']
MP4_DFTLIST='KTV'
BLE_DEVICES=[{'name':'living room ceiling light player', 'MAC':'99:52:A0:B7:E8:8F'}]
MIC_RECORDER='usb'
TMP_DIR='/dev/shm'
DEFAULT_S2T_SND_FILE=f'{TMP_DIR}/speech.webm'
DEFAULT_T2S_SND_FILE=f'{TMP_DIR}/speak.mp3'
SPEECH_SAMPLING_RATE=16000
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
	'asr_fail': ('a5040a', 2.5),
	'asr_error': ('a5050a', 1),

	'speak_drama': ('a5650a', 3.5),
	'speak_movie': ('a5650a', 3.5),
	'speak_file': ('a5650a', 3.5),
	'speak_song': ('a5640a', 3),
	'asr_not_found_song': ('a5020a', 3),
	'asr_not_found_movie': ('a5200a', 3),
	'asr_not_found_drama': ('a52a0a', 3),
	'asr_not_found_file': ('a5160a', 3),
	'asr_found_song': ('a5000a', 3),
	'asr_found_drama': ('a5280a', 3),
	'asr_found_movie': ('a51e0a', 3),
	'asr_found_file': ('a5140a', 3),

	'set_timer_speak': ('a5660a', 4),
	'set_timer_okay': ('a50a0a', 3),
	'set_timer_fail': ('a50b0a', 3),
	'set_timer_unknown': ('a50b0a', 3),
	'set_timer_cancel': ('a50c0a', 3),
	
	'fan1': ('a55b0a', 0),
	'fan2': ('a55c0a', 0),
	'fan3': ('a55d0a', 0),
	'fan4': ('a55e0a', 0),
	'fan5': ('a55f0a', 0),
	'fan6': ('a5600a', 0),
	'fanL': ('a5510a', 0),
	'fanM': ('a5520a', 0),
	'fanH': ('a5530a', 0),
	'ceilfan0': ('a55a0a', 0),
	'floorfan0': ('a5500a', 0),
	'anyfan0': ('a5460a', 0),
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

# For AutoFan control
# For auto-learning fan levels, this is the duration within it will OverWrite-Last value
AUTO_LEARN_OWL_SEC = 300
# - 'OFF' button is compulsory for every fan
# - Fans with 'ON' button must be powered on first before setting speed level
# - 'S_' means for speech reporting
FAN_DATA = {
	'dinningFan': {
		'type': '433',
		'OFF': f'{ASRchip_voice_IP}/rc_run?DFS',
		'S_OFF': 'ceilfan0',
		'LEVELS': [
			f'{ASRchip_voice_IP}/rc_run?DFL',
			f'{ASRchip_voice_IP}/rc_run?DFM',
			f'{ASRchip_voice_IP}/rc_run?DFH'],
		'S_LEVELS': ['fanL', 'fanM', 'fanH']
	},
	'sofaFan': {
		'type': '433',
		'OFF': f'{ASRchip_voice_IP}/rc_run?SFS',
		'S_OFF': 'ceilfan0',
		'LEVELS': [
			f'{ASRchip_voice_IP}/rc_run?SF1',
			f'{ASRchip_voice_IP}/rc_run?SF2',
			f'{ASRchip_voice_IP}/rc_run?SF3',
			f'{ASRchip_voice_IP}/rc_run?SF4',
			f'{ASRchip_voice_IP}/rc_run?SF5',
			f'{ASRchip_voice_IP}/rc_run?SF6'],
		'S_LEVELS': ['fan1', 'fan2', 'fan3', 'fan4', 'fan5', 'fan6']
	},
	'roomFloorFan': {
		'type': 'dyson',
		'sn': 'E1G-SG-NGA0425A',
		'IP': '192.168.50.12',
		'PORT': 1883,
		'GET_SPEED': (lambda: os.dysonFanGetSpeed('roomFloorFan')),
		'OFF': f'{ASRchip_voice_IP}/rc_run?RFF',
		'S_OFF': 'floorfan0',
		'ON': f'{ASRchip_voice_IP}/rc_run?RFN',
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
		'type': 'dyson',
		'sn': 'E1G-SG-NGA0301A',
		'IP': '192.168.50.11',
		'PORT': 1883,
		'GET_SPEED': (lambda: os.dysonFanGetSpeed('livingFloorFan')),
		'OFF': f'{ASRchip_voice_IP}/rc_run?LFF',
		'S_OFF': 'floorfan0',
		'ON': f'{ASRchip_voice_IP}/rc_run?LFN',
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
			{'protocol': 'TCP', 'IP': '192.168.50.11', 'PORT': 1883, 'data': b'2\xbc\x01\x00\x1b438/E1G-SG-NGA0301A/command\x00\x04{\n  "data": {\n    "fnsp": "0010"\n  },\n  "h": "438/E1G-SG-NGA0301A/command",\n  "mode-reason": "LAPP",\n  "msg": "STATE-SET",\n  "time": "2023-12-20T10:26:49Z"\n}'}
		]
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
