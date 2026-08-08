#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InfiniteDefaultRevisionDict sort items in the order of latest updates and allows arbitrary chaining of keys.

For example,

>>> d=InfiniteDefaultRevisionDict()
>>> dct[person_name][gender] = 'M'
>>> dct[company_name][employees] = [...]
"""

import os, json
from time import time
from collections import defaultdict

class Dict(defaultdict):
	def __init__(self, *args, **kwargs):
		super().__init__(Dict, *args, **kwargs)

	def __setitem__(self, key, value):
		super().__setitem__(key, value)
		if not str(key).endswith(' _tms'):
			super().__setitem__(str(key)+" _tms", time())

	def __delitem__(self, key):
		try:
			super().__delitem__(key)
		except:
			pass
		try:
			super().__delitem__(str(key)+" _tms")
		except:
			pass

	def to_json(self, fp=None, **kwargs):
		return json.dumps(self, default=lambda t: dict(t), **kwargs) if fp==None else json.dump(self, fp, default=lambda t: dict(t), **kwargs)

	def from_json(self, fp_or_data):
		hook = lambda t: Dict(t) if type(t) == dict else t
		self.update(json.loads(fp_or_data, object_hook=hook) if type(fp_or_data) == str
				else json.load(fp_or_data, object_hook=hook))
		return self

	def prune(self, max_items=None, max_age=None):
		"""Prune items in the dict based on the maximum number of items and/or maximum age (in seconds)"""
		if max_items is not None:
			data_keys = [k for k in self.keys() if not str(k).endswith(' _tms')]
			while len(data_keys) > max_items:
				oldest_key = min(data_keys, key=lambda k: self.get(str(k)+' _tms', 0))
				del self[oldest_key]
				data_keys.remove(oldest_key)
		if max_age is not None:
			now = time()
			for k in list(self.keys()):
				if not str(k).endswith(' _tms') and (str(k)+' _tms') in self:
					if now - self[str(k)+' _tms'] > max_age:
						del self[k]
					elif type(self[k]) == Dict:
						self[k].prune(max_items, max_age)


InfiniteDefaultRevisionDict = Dict

# dd=SDict()
# dd['a']['b'][2] = [1,'2',3.5]

# d=LastUpdatedOrderedDict({'a':1, 'b':2})
