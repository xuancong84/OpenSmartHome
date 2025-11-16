import os, sys
import numpy as np
import sounddevice as sd
import soundfile as sf
from silero_vad import load_silero_vad, VADIterator
from lib.NLP import *
from lib.prompts import *

vad_model = load_silero_vad()
vad_iterator = VADIterator(vad_model, threshold=VAD_THRESHOLD, sampling_rate=SPEECH_SAMPLING_RATE)
def record_voice_until_sil(
		timeout_wait = 5,						# max wait time for speech to start
		timeout_max = 30,						# max duration for the speech
		timeout_sil = 2,						# max silence for stopping recording
		output_file = DEFAULT_S2T_SND_FILE,		# default output file
		SAMPLING_RATE = SPEECH_SAMPLING_RATE,	# 16 kHz for Silero VAD
		CHUNK_SIZE    = 512,					# samples per chunk (~32 ms)
	):
	print("⏳ Listening… please speak into your microphone.")
	audio_buffer = []
	speech_started = is_speech = False
	silence_accum = total_time = 0.0

	with sd.InputStream(
		samplerate=SAMPLING_RATE,
		blocksize=CHUNK_SIZE,
		dtype="int16",
		channels=1,
	) as stream:
		chunk_dur = CHUNK_SIZE / SAMPLING_RATE
		while total_time < timeout_max:
			data, overflowed = stream.read(CHUNK_SIZE)
			if overflowed:
				print("⚠️  Warning: input buffer overflow")

			# Convert int16 PCM → float32 in [-1, 1]
			chunk = data.flatten().astype(np.float32) / 32768.0

			# Run VAD: returns non-empty dict when speech is detected
			vad_status = vad_iterator(chunk)
			if vad_status:
				if 'start' in vad_status:
					is_speech = True
				elif 'end' in vad_status:
					is_speech = False
			
			total_time += chunk_dur
			audio_buffer.append(chunk)
			if is_speech:
				silence_accum = 0.0
				if not speech_started:
					print("🗣️  Speech detected, recording…")
					audio_buffer = audio_buffer[-4:]	# extract 3x32ms sil before speech start
					speech_started = True
			else:
				silence_accum += chunk_dur
				if silence_accum >= (timeout_sil if speech_started else timeout_wait):
					print(f"🔇 {silence_accum}s of silence – stopping.")
					break

			print('sil:%.3f/%d, total:%.3f/%d'%(silence_accum, timeout_sil, total_time, timeout_max), end='\r', file=sys.stderr)

	# Reset model state for next use
	vad_iterator.reset_states()

	# Concatenate and save WAV
	waveform = np.concatenate(audio_buffer)
	sf.write(output_file+'.wav', waveform, SAMPLING_RATE)
	print(f"✅ Saved recording to {output_file}.wav")
	runsys(f'ffmpeg -y -i {output_file}.wav -c:a libopus -b:a 128k {output_file}')

@tool
def listen(	max_wait_sec = 30,
			max_dur_sec = 60,
			timeout_sil_sec = 3):
	"""Listen to the speaker

	Args:
		max_wait_sec (int = 30): max time to wait for the speaker
		max_dur_sec (int = 60): max duration of the speech
		timeout_sil_sec (int = 3): the silence duration that indicates end-of-speech 

	Returns:
		str: the transcribed text of the speech, it can be empty if there is an error or the user wants to end the conversation
	"""
	record_voice_until_sil(timeout_wait=max_wait_sec, timeout_max = max_dur_sec, timeout_sil = timeout_sil_sec)
	asr_out = os.recog_and_do('', '', '', (lambda t, *args, **kwargs: t), **args)
	return Try(lambda: asr_out["text"], '')

@tool
def speak(text, lang=None, blocking=True):
	"""Speak text to the user.

	Args:
		text (str): the text to speak
		lang (str = None): the ISO language ID, specify None to auto determine, e.g., 'en', 'zh'
		blocking (bool = True): whether to wait for the operation to complete
	"""
	thread = os.speaker('on', 'MP3_SPEAKER', return_obj=True)
	lang, txt = os.prepare_TTS(text, lang_id=lang, fn=DEFAULT_GPT_SND_FILE)
	thread.join()
	os.play_audio(DEFAULT_GPT_SND_FILE, blocking, None)
	run_thread(os._off_speaker_delayed)

@tool
def show_HTML(html, tv_name):
	"""Present information to the user on the TV (will be auto turned on if it is off) in the form of a dynamic HTML webpage, it can contain Javascript to allow animation to help the user understand visually.

	Args:
		html (str): the HTML string
		tv_name (str): TV name or the IP/IP:port of the open browser window with a connected websocket
	"""
	os.tv_on_if_off(tv_name, wait_ready=True)
	full_path = SHARED_PATH + GPT_TMP_RDIR
	Try(lambda: os.makedirs(full_path))
	fn = pd.Timestamp.now().strftime('%Y%m%d-%H%M%S') + '.html'
	with open(full_path+'/'+fn, 'wt') as fp:
		fp.write(html)
	os.tv(tv_name, f'openBrowserAt "{os.url_root}/files/{GPT_TMP_RDIR}/{fn}"')

@tool
def run_python_script(code: str, **kwargs):
	"""Run the standalone python script using the current python interpreter

	Args:
		code (str): the complete code of the Python script
		**kwargs: options to be passed to subprocess.run()

	Returns:
		The subprocess.CompletedProcess object
	"""
	full_path = SHARED_PATH + GPT_TMP_RDIR
	Try(lambda: os.makedirs(full_path))
	fn = full_path + '/' + pd.Timestamp.now().strftime('%Y%m%d-%H%M%S') + '.py'
	with open(fn, 'wt') as fp:
		fp.write(code)
	p = subprocess.run([sys.executable, fn], **kwargs)
	return p

def load_GPT_model():
	model = None
	if hasattr(secret, 'OPENAI_API_KEY') and hasattr(secret, 'OPENAI_GPT_MODEL'):
		from strands.models.openai import OpenAIModel
		model = OpenAIModel(
			client_args = {"api_key": secret.OPENAI_API_KEY},
			model_id = secret.OPENAI_GPT_MODEL,
			reasoning={"effort": "high"},
		)
	return model

def get_sys_prompt():
	ret = SYSTEM_PROMPT_PREFIX
	for name, url in HUBS.items():
		ret += f"\nHub name: {name}\n"
		cmd_tbl = parseRC(os.get_http(url+'/rc_load')[0])
		ret += '\n'.join([f'{its[0]}\t{its[1]}' for its in cmd_tbl if (its[0] and not its[0].isdigit())]) + '\n'
	return ret
