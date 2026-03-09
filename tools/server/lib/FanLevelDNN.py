import math
import os
from collections import defaultdict
from copy import deepcopy
from typing import Dict, List, Optional, Tuple

import torch
import torch.nn as nn
import torch.nn.functional as F


class FanLevelDNN(nn.Module):
	"""
	Predict fan level in [0, N_levels] from:
	- temperature
	- humidity
	- real-feel temperature (computed internally)

	Checkpoint stores:
	- model weights
	- training data points
	- normalization statistics
	- config
	"""

	class _MLP(nn.Module):
		def __init__(self, in_dim: int, out_dim: int, hidden: Tuple[int, ...] = (32, 16)):
			super().__init__()
			layers = []
			prev = in_dim
			for h in hidden:
				layers += [nn.Linear(prev, h), nn.ReLU()]
				prev = h
			layers.append(nn.Linear(prev, out_dim))
			self.net = nn.Sequential(*layers)

		def forward(self, x: torch.Tensor) -> torch.Tensor:
			return self.net(x)

	def __init__(
		self,
		checkpoint_path: str,
		N_levels: int,
		hidden: Tuple[int, ...] = (32, 16),
		lr: float = 1e-3,
		device: Optional[str] = None,
	):
		super().__init__()
		self.checkpoint_path = checkpoint_path
		self.N_levels = int(N_levels)
		self.hidden = tuple(hidden)
		self.lr = lr
		self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))

		self.model = self._MLP(in_dim=3, out_dim=self.N_levels + 1, hidden=self.hidden).to(self.device)
		self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)

		# data[level] = list of {"temp": ..., "humidity": ..., "fan_level": ...}
		self.data: Dict[int, List[dict]] = defaultdict(list)

		# track last added point as (fan_level, index_within_that_level_list)
		self._last_added: Optional[Tuple[int, int]] = None

		# normalization stats
		self.x_mean = torch.zeros(3, dtype=torch.float32, device=self.device)
		self.x_std = torch.ones(3, dtype=torch.float32, device=self.device)

		if os.path.exists(self.checkpoint_path):
			self._load(self.checkpoint_path)

	# ---------- public API ----------

	def add_data(self, temperature_c: float, humidity_pct: float, fan_level: int) -> None:
		"""Add one point. Keeps max 16 points per fan level, dropping the earliest of that level."""
		self._validate_input(temperature_c, humidity_pct, fan_level)

		bucket = self.data[fan_level]
		bucket.append({
			"temp": float(temperature_c),
			"humidity": float(humidity_pct),
			"fan_level": int(fan_level),
		})

		if len(bucket) > 16:
			bucket.pop(0)

		self._last_added = (fan_level, len(bucket) - 1)

	def replace_data(self, temperature_c: float, humidity_pct: float, fan_level: int) -> None:
		"""
		Replace the last added point.
		If fan_level changes, the point is moved to the new fan-level bucket.
		"""
		self._validate_input(temperature_c, humidity_pct, fan_level)

		if self._last_added is None:
			raise ValueError("No previously added data point to replace.")

		old_level, old_idx = self._last_added
		if old_level not in self.data or old_idx >= len(self.data[old_level]):
			raise RuntimeError("Last-added data reference is no longer valid.")

		# Remove old point
		self.data[old_level].pop(old_idx)

		# Clean up empty bucket
		if not self.data[old_level]:
			del self.data[old_level]

		# Add replacement as the newest point of the new level
		self.add_data(temperature_c, humidity_pct, fan_level)

	def train(self, epochs: int = 10, batch_size: int = 16, verbose: bool = False) -> float:
		"""
		Train on all stored points.
		Returns final loss.
		"""
		X, y = self._build_dataset()
		if len(y) == 0:
			raise ValueError("No training data available.")

		self._fit_normalizer(X)
		X = self._normalize(X)

		dataset = torch.utils.data.TensorDataset(X, y)
		loader = torch.utils.data.DataLoader(dataset, batch_size=min(batch_size, len(dataset)), shuffle=True)

		self.model.train()
		final_loss = 0.0

		for epoch in range(epochs):
			running = 0.0
			for xb, yb in loader:
				xb = xb.to(self.device)
				yb = yb.to(self.device)

				self.optimizer.zero_grad()
				logits = self.model(xb)
				loss = F.cross_entropy(logits, yb)
				loss.backward()
				self.optimizer.step()
				running += loss.item()

			final_loss = running / max(1, len(loader))
			if verbose and ((epoch + 1) % 50 == 0 or epoch == 0 or epoch + 1 == epochs):
				print(f"Epoch {epoch+1}/{epochs} - loss={final_loss:.4f}")

		return self

	@torch.no_grad()
	def predict(self, temperature_c: float, humidity_pct: float) -> Tuple[int, torch.Tensor]:
		"""
		Returns:
			predicted_level, probabilities
		"""
		if not self.data:
			return math.ceil(self.N_levels/2)
		self._validate_input(temperature_c, humidity_pct, 0, check_level=False)
		self.model.eval()
		real_feel = self._compute_real_feel_c(temperature_c, humidity_pct)
		x = torch.tensor([[temperature_c, humidity_pct, real_feel]], dtype=torch.float32, device=self.device)
		x = self._normalize(x)
		probs = F.softmax(self.model(x), dim=-1).squeeze(0).cpu()
		pred = int(torch.argmax(probs).item())
		return pred

	def save(self, path: Optional[str] = None) -> None:
		"""Save model + training data + config to checkpoint."""
		path = path or self.checkpoint_path
		payload = {
			"model_state": self.model.state_dict(),
			"data": {int(k): deepcopy(v) for k, v in self.data.items()},
			"N_levels": self.N_levels,
			"hidden": self.hidden,
			"lr": self.lr,
			"x_mean": self.x_mean.detach().cpu(),
			"x_std": self.x_std.detach().cpu(),
			"last_added": self._last_added,
		}
		if not os.path.isdir(os.path.dirname(path)):
			os.makedirs(os.path.dirname(path), exist_ok=True)
		torch.save(payload, path)

	# ---------- internal helpers ----------

	def _load(self, path: str) -> None:
		ckpt = torch.load(path, map_location=self.device)

		saved_levels = int(ckpt["N_levels"])
		if saved_levels != self.N_levels:
			raise ValueError(f"Checkpoint N_levels={saved_levels}, but constructor received N_levels={self.N_levels}")

		saved_hidden = tuple(ckpt.get("hidden", self.hidden))
		if saved_hidden != self.hidden:
			self.hidden = saved_hidden
			self.model = self._MLP(in_dim=3, out_dim=self.N_levels + 1, hidden=self.hidden).to(self.device)
			self.optimizer = torch.optim.Adam(self.model.parameters(), lr=self.lr)

		self.model.load_state_dict(ckpt["model_state"])
		self.data = defaultdict(list, {int(k): list(v) for k, v in ckpt.get("data", {}).items()})
		self.x_mean = ckpt.get("x_mean", torch.zeros(3)).to(self.device)
		self.x_std = ckpt.get("x_std", torch.ones(3)).to(self.device)
		self._last_added = ckpt.get("last_added", None)

	def _build_dataset(self) -> Tuple[torch.Tensor, torch.Tensor]:
		features = []
		labels = []

		for level in range(self.N_levels + 1):
			for item in self.data.get(level, []):
				t = float(item["temp"])
				h = float(item["humidity"])
				rf = self._compute_real_feel_c(t, h)
				features.append([t, h, rf])
				labels.append(level)

		if not features:
			return (
				torch.empty((0, 3), dtype=torch.float32, device=self.device),
				torch.empty((0,), dtype=torch.long, device=self.device),
			)

		X = torch.tensor(features, dtype=torch.float32, device=self.device)
		y = torch.tensor(labels, dtype=torch.long, device=self.device)
		return X, y

	def _fit_normalizer(self, X: torch.Tensor) -> None:
		self.x_mean = X.mean(dim=0)
		self.x_std = X.std(dim=0)
		self.x_std = torch.where(self.x_std < 1e-6, torch.ones_like(self.x_std), self.x_std)

	def _normalize(self, X: torch.Tensor) -> torch.Tensor:
		return (X - self.x_mean) / self.x_std

	def _validate_input(
		self,
		temperature_c: float,
		humidity_pct: float,
		fan_level: int,
		check_level: bool = True,
	) -> None:
		if not isinstance(temperature_c, (int, float)):
			raise TypeError("temperature_c must be numeric.")
		if not isinstance(humidity_pct, (int, float)):
			raise TypeError("humidity_pct must be numeric.")
		if not (0.0 <= float(humidity_pct) <= 100.0):
			raise ValueError("humidity_pct must be in [0, 100].")
		if check_level:
			if not isinstance(fan_level, int):
				raise TypeError("fan_level must be int.")
			if not (0 <= fan_level <= self.N_levels):
				raise ValueError(f"fan_level must be in [0, {self.N_levels}].")

	@staticmethod
	def _compute_real_feel_c(temperature_c: float, humidity_pct: float) -> float:
		"""
		Computes a standard heat-index style 'real-feel' using NOAA heat index.

		Uses ambient temperature directly when conditions are outside the normal
		heat-index range, which is common practice.
		"""
		t_c = float(temperature_c)
		rh = float(humidity_pct)

		# Heat index is defined mainly for warm/humid conditions.
		if t_c < 27.0 or rh < 40.0:
			return t_c

		t_f = t_c * 9.0 / 5.0 + 32.0

		hi_f = (
			-42.379
			+ 2.04901523 * t_f
			+ 10.14333127 * rh
			- 0.22475541 * t_f * rh
			- 0.00683783 * t_f * t_f
			- 0.05481717 * rh * rh
			+ 0.00122874 * t_f * t_f * rh
			+ 0.00085282 * t_f * rh * rh
			- 0.00000199 * t_f * t_f * rh * rh
		)

		# NOAA adjustments
		if 80.0 <= t_f <= 112.0 and rh < 13.0:
			hi_f -= ((13.0 - rh) / 4.0) * math.sqrt((17.0 - abs(t_f - 95.0)) / 17.0)
		elif 80.0 <= t_f <= 87.0 and rh > 85.0:
			hi_f += ((rh - 85.0) / 10.0) * ((87.0 - t_f) / 5.0)

		return (hi_f - 32.0) * 5.0 / 9.0

if __name__ == '__main__':
	print(FanLevelDNN._compute_real_feel_c(30, 85))
	aa=5