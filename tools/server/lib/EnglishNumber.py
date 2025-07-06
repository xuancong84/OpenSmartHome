import re
from typing import Optional, Tuple

# Mapping for units (1–9), teens (10–19) and tens (20,30,…,90)
_UNITS = {
	"one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
	"six": 6, "seven": 7, "eight": 8, "nine": 9
}
_TEENS = {
	"ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
	"fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19
}
_TENS = {
	"twenty": 20, "thirty": 30, "forty": 40,
	"fifty": 50, "sixty": 60, "seventy": 70,
	"eighty": 80, "ninety": 90
}

def _word_to_num(phrase: str) -> Optional[int]:
	"""
	Convert a 1– or 2‐word English number (with optional hyphens)
	into its integer value, or return None if out of range or invalid.
	"""
	# normalize hyphens/spaces and split
	parts = phrase.lower().replace('-', ' ').split()
	if len(parts) == 1:
		w = parts[0]
		if w in _UNITS:
			return _UNITS[w]
		if w in _TEENS:
			return _TEENS[w]
		if w in _TENS:
			return _TENS[w]
		return None
	if len(parts) == 2:
		tens, unit = parts
		if tens in _TENS and unit in _UNITS:
			return _TENS[tens] + _UNITS[unit]
	return None

def detect_trailing_number(sentence: str):
	"""
	If `sentence` ends with a number (1–99, either digits or words),
	returns (sentence_without_that_number, numeric_value).
	Otherwise returns (original_sentence, None).
	"""
	original = sentence
	# 1) Strip trailing whitespace and simple punctuation
	s = sentence.rstrip()
	s = re.sub(r"[\.!\?;:]+$", "", s)  # remove trailing . ! ? ; :
	
	tokens = s.split()
	if not tokens:
		return original, None

	# 2) Try a two‐word word‐number first (e.g. "twenty three")
	if len(tokens) >= 2:
		last2 = " ".join(tokens[-2:])
		val = _word_to_num(last2)
		if val is not None:
			head = " ".join(tokens[:-2])
			return head, val

	# 3) Try pure digits
	last = tokens[-1]
	if last.isdigit():
		num = int(last)
		if 1 <= num <= 99:
			head = " ".join(tokens[:-1])
			return head, num

	# 4) Try a one‐word number (e.g. "seven" or "ninety")
	val = _word_to_num(last)
	if val is not None:
		head = " ".join(tokens[:-1])
		return head, val

	# 5) No trailing number found
	return original, None


if __name__=='__main__':
	# Example usage and test cases
	test_sentences = [
		"I have twenty three",
		"No number here.",
		"This ends with ninety-nine!",
		"He ran thirty two miles.",
		"They scored 96!",
		"Finished fifty."
	]

	for s in test_sentences:
		print(f"'{s}' -> {detect_trailing_number(s)}")