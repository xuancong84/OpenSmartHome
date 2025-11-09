import os, sys, string, json, gzip
from natsort import natsorted
from unidecode import unidecode
import traceback

def Try(*args):
	exc = ''
	for arg in args:
		try:
			return arg() if callable(arg) else arg
		except:
			exc = traceback.format_exc()
	return str(exc)

def Open(fn, mode='r', **kwargs):
	if fn == '-':
		return sys.stdin if mode.startswith('r') else sys.stdout
	fn = expand_path(fn)
	return gzip.open(fn, mode, **kwargs) if fn.lower().endswith('.gz') else open(fn, mode, **kwargs)

TransNatSort = lambda lst: natsorted(lst, key=unidecode)
expand_path = lambda t: os.path.expandvars(os.path.expanduser(t))
isdir = lambda t: os.path.isdir(expand_path(t))
isfile = lambda t: os.path.isfile(expand_path(t))
listdir = lambda t: TransNatSort(Try(lambda: os.listdir(expand_path(t)), []))
showdir = lambda t: [(p+'/' if isdir(os.path.join(t,p)) else p) for p in listdir(t) if not p.startswith('.')]
trimpath = lambda t: t.replace('//', '/').replace('/./','/')
get_alpha = lambda t: ''.join([c for c in t if c in string.ascii_letters])
get_alnum = lambda t: ''.join([c for c in t if c in string.ascii_letters+string.digits])

LOG = lambda *args, **kwargs: print('LOG:', *args, **kwargs) if sys.DEBUG_LOG else None

def list_get_args(lst, N, defaults, cast=None):
	"""Get arguments (with default values) from a variable-length list

	Args:
		lst (list): the input list
		N (int): number of returned arguments
		defaults (list): default argument list, its length must be shorter than `lst`
		cast: cast each output into type, default = None (do not cast)
	"""
	ret = [None]*(N-len(defaults)) + defaults
	ret[:len(lst)] = lst
	if cast != None:
		ret = [cast(i) for i in ret]
	return ret

