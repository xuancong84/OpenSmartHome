import torch
import numpy as np
import sounddevice as sd
import soundfile as sf
from silero_vad import load_silero_vad, VADIterator
from lib.NLP import *


torch.set_num_threads(1)
model = load_silero_vad()
vad_iterator = VADIterator(model, sampling_rate=SPEECH_SAMPLING_RATE)
def record_voice_until_sil(
		timeout_max = 30,						# max duration
		timeout_sil = 3,						# max silence for stopping recording
		output_file = DEFAULT_S2T_SND_FILE,		# default output file
		SAMPLING_RATE = SPEECH_SAMPLING_RATE,	# 16 kHz for Silero VAD
		CHUNK_SIZE    = 512,					# samples per chunk (~32 ms)
	):
	print("⏳ Listening… please speak into your microphone.")
	audio_buffer = []
	speech_started = False
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
			is_speech = bool(vad_iterator(chunk))
			
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
				if silence_accum >= timeout_sil:
					print(f"🔇 {timeout_sil}s of silence – stopping.")
					break

			print('sil:%.3f/%d, total:%.3f/%d'%(silence_accum, timeout_sil, total_time, timeout_max), end='\r', file=sys.stderr)

	# Reset model state for next use
	vad_iterator.reset_states()

	# Concatenate and save WAV
	waveform = np.concatenate(audio_buffer)
	sf.write(output_file+'.wav', waveform, SAMPLING_RATE)
	print(f"✅ Saved recording to {output_file}.wav")
	runsys(f'ffmpeg -i {output_file}.wav -c:a libopus -b:a 128k {output_file}')


