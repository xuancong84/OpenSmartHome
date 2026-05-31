#!/usr/bin/env python3
import argparse
import os
import re
import select
import subprocess
import sys
import termios
import threading
import time
import tty
from pathlib import Path


DEFAULT_DEV = "/dev/rfcomm0"
DEFAULT_CHANNEL = 2

LIGHT_TOGGLE = bytes.fromhex("41 54 07 69 01 03 fc")
STANDBY = bytes.fromhex("41 54 00 0a 01 00 ff")
SESSION_START = bytes.fromhex("41 54 00 15 00 00")

# Selects the custom color palette / custom color mode before sending RGB.
# Seen in the LG XBOOM capture before arbitrary RGB packets.
CUSTOM_PALETTE_SELECT = bytes.fromhex("41 54 07 6d 03 01 04 03 f5")


class RfcommSession:
	def __init__(self, dev: str):
		self.dev = dev
		self.fd: int | None = None
		self.seen = bytearray()
		self.stop_reader = False
		self.reader_thread: threading.Thread | None = None
		self.old_termios = None

	def open(self) -> None:
		self.fd = os.open(self.dev, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)

		# Critical for binary LG packets:
		# /dev/rfcomm0 is a TTY. Without raw mode, Linux can translate 0d -> 0a.
		self.old_termios = termios.tcgetattr(self.fd)
		tty.setraw(self.fd, termios.TCSANOW)

		self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
		self.reader_thread.start()

	def close(self) -> None:
		self.stop_reader = True
		time.sleep(0.2)

		if self.fd is not None:
			try:
				if self.old_termios is not None:
					termios.tcsetattr(self.fd, termios.TCSANOW, self.old_termios)
			except Exception:
				pass

			try:
				os.close(self.fd)
			except OSError:
				pass

			self.fd = None

	def _reader_loop(self) -> None:
		assert self.fd is not None

		while not self.stop_reader:
			readable, _, _ = select.select([self.fd], [], [], 0.05)
			if not readable:
				continue

			try:
				data = os.read(self.fd, 4096)
			except BlockingIOError:
				continue
			except OSError as e:
				print(f"RX error: {e!r}")
				self.stop_reader = True
				return

			if not data:
				print("RX: RFCOMM closed by speaker")
				self.stop_reader = True
				return

			self.seen.extend(data)
			print("RX:", data.hex(" "))

	def write_all(self, data: bytes, timeout: float = 5.0) -> None:
		assert self.fd is not None

		pos = 0
		deadline = time.time() + timeout

		while pos < len(data):
			if time.time() > deadline:
				raise TimeoutError(f"timed out writing {len(data)} bytes to {self.dev}")

			_, writable, _ = select.select([], [self.fd], [], 0.5)
			if not writable:
				continue

			try:
				n = os.write(self.fd, data[pos:])
			except BlockingIOError:
				time.sleep(0.02)
				continue

			if n <= 0:
				raise RuntimeError("zero-byte write to RFCOMM")

			pos += n

	def tx(self, data: bytes, label: str = "") -> None:
		if label:
			print(f"TX {label}:", data.hex(" "))
		else:
			print("TX:", data.hex(" "))
		self.write_all(data)

	def wait_for_bytes(self, target: bytes, timeout: float, label: str = "") -> bool:
		end = time.time() + timeout

		while time.time() < end:
			if target in self.seen:
				if label:
					print(f"Seen {label}: {target.hex(' ')}")
				return True

			if self.stop_reader:
				return False

			time.sleep(0.05)

		return False

	def wait_for_identity_reply_any_mac(self, timeout: float = 3.0) -> bytes | None:
		"""
		Match:
		41 54 00 14 06 xx xx xx xx xx xx cc
		where the 6 middle bytes can be any MAC.
		"""
		prefix = bytes.fromhex("41 54 00 14 06")
		end = time.time() + timeout

		while time.time() < end:
			buf = bytes(self.seen)
			idx = buf.find(prefix)

			if idx >= 0 and len(buf) >= idx + 12:
				pkt = buf[idx:idx + 12]
				mac = pkt[5:11]
				checksum = pkt[11]
				print("Seen identity reply:", pkt.hex(" "))
				print("Identity reply MAC:", ":".join(f"{b:02x}" for b in mac))
				print("Identity reply checksum:", f"{checksum:02x}")
				return pkt

			if self.stop_reader:
				return None

			time.sleep(0.05)

		return None


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
	return subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def normalize_mac(mac: str) -> str:
	mac = mac.strip().lower()
	if not re.fullmatch(r"[0-9a-f]{2}(:[0-9a-f]{2}){5}", mac):
		raise ValueError(f"invalid MAC address: {mac}")
	return mac


def mac_to_bytes(mac: str) -> bytes:
	return bytes(int(x, 16) for x in normalize_mac(mac).split(":"))


def checksum(length: int, payload: bytes) -> int:
	return (-((length + sum(payload)) & 0xFF)) & 0xFF


def make_packet(group: int, command: int, payload: bytes = b"") -> bytes:
	if len(payload) == 0:
		return bytes([0x41, 0x54, group, command, 0x00, 0x00])

	length = len(payload)
	return bytes([0x41, 0x54, group, command, length]) + payload + bytes([checksum(length, payload)])


def make_registration_packet(local_mac: str) -> bytes:
	payload = bytes([0x01, 0x00]) + mac_to_bytes(local_mac)
	return make_packet(0x00, 0x14, payload)



def parse_rgb(value: str) -> tuple[int, int, int]:
	"""
	Accepts RGB as rrggbb, #rrggbb, or 0xrrggbb.
	Returns (r, g, b), each 0..255.
	"""
	raw = value.strip().lower()
	if raw.startswith("#"):
		raw = raw[1:]
	if raw.startswith("0x"):
		raw = raw[2:]

	if not re.fullmatch(r"[0-9a-f]{6}", raw):
		raise ValueError(f"invalid RGB color '{value}'. Use rrggbb, #rrggbb, or 0xrrggbb")

	return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)


def make_rgb_packet(r: int, g: int, b: int) -> bytes:
	"""
	LG arbitrary RGB command observed from the custom palette:
	41 54 07 6d 07 01 01 03 00 RR GG BB CC
	"""
	for name, value in (("r", r), ("g", g), ("b", b)):
		if not 0 <= value <= 255:
			raise ValueError(f"{name} must be in range 0..255, got {value}")

	payload = bytes([0x01, 0x01, 0x03, 0x00, r, g, b])
	return make_packet(0x07, 0x6D, payload)


def detect_local_bluetooth_mac() -> str:
	cp = run(["bluetoothctl", "show"], check=True)
	m = re.search(r"Controller\s*([0-9A-Fa-f:]{17})", cp.stdout)

	if not m:
		raise RuntimeError("could not detect local Bluetooth MAC from `bluetoothctl show`")

	return normalize_mac(m.group(1))


def rfcomm_release(dev: str) -> None:
	run(["rfcomm", "release", dev], check=False)


def rfcomm_bind(dev: str, speaker_mac: str, channel: int) -> None:
	rfcomm_release(dev)

	cp = run(["rfcomm", "bind", dev, speaker_mac, str(channel)], check=False)
	if cp.returncode != 0:
		raise RuntimeError(
			"rfcomm bind failed\n"
			f"stdout:\n{cp.stdout}\n"
			f"stderr:\n{cp.stderr}\n"
		)

	deadline = time.time() + 5
	while time.time() < deadline:
		if Path(dev).exists():
			return
		time.sleep(0.1)

	raise RuntimeError(f"{dev} was not created after rfcomm bind")


def cmd_toggle_light(session: RfcommSession) -> int:
	session.tx(LIGHT_TOGGLE, "toggle_light")

	# Expected:
	#   41 54 07 69 02 03 01 fa = now ON
	#   41 54 07 69 02 03 00 fb = now OFF
	got = session.wait_for_bytes(bytes.fromhex("41 54 07 69 02 03"), 5, "light response")

	if not got:
		print("WARNING: did not see light toggle response")
		return 2

	return 0




def cmd_set_rgb(session: RfcommSession, rgb: str, select_palette: bool = True) -> int:
	r, g, b = parse_rgb(rgb)
	packet = make_rgb_packet(r, g, b)

	print(f"RGB color: #{r:02x}{g:02x}{b:02x}")

	if select_palette:
		session.tx(CUSTOM_PALETTE_SELECT, "select_custom_palette")
		# The speaker may echo/reply to this, but RGB can still work if no reply is seen.
		time.sleep(0.2)

	session.tx(packet, f"set_rgb #{r:02x}{g:02x}{b:02x}")

	# Expected response should start with the same command family. Keep this loose because
	# different firmware versions may return different state/detail payloads.
	got = session.wait_for_bytes(bytes.fromhex("41 54 07 6d"), 3, "RGB/color response")
	if not got:
		print("WARNING: did not see RGB/color response")
		return 2

	return 0

def cmd_enter_standby(session: RfcommSession, local_mac: str) -> int:
	registration = make_registration_packet(local_mac)

	session.tx(SESSION_START, "session_start")

	identity = session.wait_for_identity_reply_any_mac(timeout=3)
	if identity is None:
		print("WARNING: did not see identity reply, continuing anyway")

	session.tx(registration, f"register_local_mac {local_mac}")
	time.sleep(0.5)

	session.tx(STANDBY, "enter_standby")

	if session.wait_for_bytes(STANDBY, 1, "standby echo"):
		print("Standby command echoed. Waiting for speaker-initiated disconnect...")
	else:
		print("WARNING: standby command was not echoed")
		return 3

	# Do not call bluetoothctl disconnect. Let the speaker close the link.
	time.sleep(1)
	return 0


def main() -> int:
	parser = argparse.ArgumentParser(
		description="LG XBOOM XO3Q RFCOMM controller: toggle_light / set_rgb / enter_standby"
	)
	parser.add_argument("--speaker_mac", "-mac", default="54:15:89:25:FB:C3", help="Bluetooth speaker MAC, e.g. 54:15:89:25:FB:C3")
	parser.add_argument(
		"cmd",
		choices=["toggle_light", "set_rgb", "enter_standby"],
		help="Command to run",
	)
	parser.add_argument(
		"color",
		nargs="?",
		help="RGB color for set_rgb, e.g. ff0000, #00ff00, or 0x0000ff",
	)
	parser.add_argument("--dev", default=DEFAULT_DEV, help=f"RFCOMM device, default {DEFAULT_DEV}")
	parser.add_argument("--channel", type=int, default=DEFAULT_CHANNEL, help="RFCOMM channel, default 2")
	parser.add_argument(
		"--local-mac",
		default=None,
		help="Override local Bluetooth MAC. Default: auto-detect using bluetoothctl show",
	)
	parser.add_argument(
		"--skip-palette-select",
		action="store_true",
		help="For set_rgb, skip the custom-palette select packet before sending RGB.",
	)
	parser.add_argument(
		"--no-bind",
		action="store_true",
		help="Do not run rfcomm bind/release. Use an already-created /dev/rfcommX.",
	)
	parser.add_argument(
		"--keep-bound",
		action="store_true",
		help="Do not rfcomm release at exit.",
	)

	args = parser.parse_args()

	speaker_mac = normalize_mac(args.speaker_mac)

	if args.cmd == "set_rgb" and not args.color:
		import datetime_color
		rgb = datetime_color.datetime2color()
		args.color = ''.join([hex(c)[2:] for c in rgb])
	if args.cmd != "set_rgb" and args.color:
		parser.error("color argument is only valid with set_rgb")

	if args.local_mac:
		local_mac = normalize_mac(args.local_mac)
	else:
		local_mac = detect_local_bluetooth_mac()

	print("Speaker MAC:", speaker_mac)
	print("Local Bluetooth MAC:", local_mac)
	print("Command:", args.cmd)
	print("RFCOMM device:", args.dev)
	print("RFCOMM channel:", args.channel)

	bound_by_script = False

	try:
		if not args.no_bind:
			print("Binding RFCOMM...")
			rfcomm_bind(args.dev, speaker_mac, args.channel)
			bound_by_script = True

		session = RfcommSession(args.dev)
		session.open()

		try:
			if args.cmd == "toggle_light":
				return cmd_toggle_light(session)

			if args.cmd == "set_rgb":
				assert args.color is not None
				return cmd_set_rgb(session, args.color, select_palette=not args.skip_palette_select)

			if args.cmd == "enter_standby":
				return cmd_enter_standby(session, local_mac)

			print(f"unsupported command: {args.cmd}")
			return 1

		finally:
			session.close()

	finally:
		if bound_by_script and not args.keep_bound:
			print("Releasing RFCOMM...")
			rfcomm_release(args.dev)


if __name__ == "__main__":
	sys.exit(main())
