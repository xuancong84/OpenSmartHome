#!/usr/bin/env python3
# This file contains fixed settings that affect the performance behaviour of the smart home system

from lingua import Language

FUZZY_PINYIN = {'ing': 'in'}
FUZZY_GREEK = {'η': 'ι', 'ή': 'ί', 'ὴ': 'ὶ', 'ῆ': 'ῖ', 'ἠ': 'ἰ', 'ἤ': 'ἴ', 'ἢ': 'ἲ', 'ἦ': 'ἶ', 'ἡ': 'ἱ', 'ἥ': 'ἵ', 'ἣ': 'ἳ', 'ἧ': 'ἷ'}
video_file_exts = ['.mp4', '.mkv', '.avi', '.mpg', '.mpeg', '.webm']
audio_file_exts = ['.mp3', '.m4a', '.webm']
media_file_exts = list(set(video_file_exts + audio_file_exts))
punctuation = ',.:;?!，。：；？！'

lang2id = {Language.ENGLISH: 'en', Language.CHINESE: 'zh', Language.HINDI: 'hi', Language.SPANISH: 'es', Language.FRENCH: 'fr',
	Language.ARABIC: 'ar', Language.BENGALI: 'bn', Language.RUSSIAN: 'ru', Language.PORTUGUESE: 'pt', Language.URDU: 'ur',
	Language.INDONESIAN:'id', Language.GERMAN: 'de', Language.JAPANESE: 'ja', Language.TURKISH: 'tr', Language.TAMIL: 'ta',
	Language.VIETNAMESE: 'vi', Language.KOREAN: 'ko', Language.THAI: 'th', Language.GREEK: 'el', Language.HEBREW: 'he', 
	Language.MALAY: 'ms', Language.DUTCH: 'nl', Language.ITALIAN: 'it', Language.POLISH: 'pl'}
