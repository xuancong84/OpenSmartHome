function runLenDecode(bytes) {
	let pixels = [];
	let line = [];
	let incr = 0;
	let color = 0;
	let len = 0;
	let i = 0;
	while (i < bytes.length) {
		if (bytes[i]) {
			incr = 1;
			color = bytes[i];
			len = 1;
		}
		else {
			const check = bytes[i + 1];
			if (check === 0) {
				incr = 2;
				color = 0;
				len = 0;
				pixels.push(line);
				line = [];
			}
			else if (check < 64) {
				incr = 2;
				color = 0;
				len = check;
			}
			else if (check < 128) {
				incr = 3;
				color = 0;
				len = ((check - 64) << 8) + bytes[i + 2];
			}
			else if (check < 192) {
				incr = 3;
				color = bytes[i + 2];
				len = check - 128;
			}
			else {
				incr = 4;
				color = bytes[i + 3];
				len = ((check - 192) << 8) + bytes[i + 2];
			}
		}
		let temp = [];
		for (let j = 0; j < len; j++) {
			temp.push(color);
		}
		line = line.concat(temp);
		i += incr;
	}
	if (line.length !== 0) {
		pixels.push(line);
	}
	return pixels;
}
function ycbcr2rgb(rgb) {
	let transposed = [
		[1, 1, 1],
		[0, -0.34414, 1.772],
		[1.402, -0.71414, 0],
	];
	for (let h = 0; h < rgb.length; h++) {
		rgb[h][1] = rgb[h][1] - 128;
		rgb[h][2] = rgb[h][2] - 128;
	}
	rgb = mmultiply(rgb, transposed);
	for (let i = 0; i < rgb.length; i++) {
		for (let j = 0; j < rgb[i].length; j++) {
			if (rgb[i][j] > 255) {
				rgb[i][j] = 255;
			}
			else if (rgb[i][j] < 0) {
				rgb[i][j] = 0;
			}
		}
	}
	return rgb;
}
function getPxAlpha(imgData, palette) {
	const px = runLenDecode(imgData);
	let a = [];
	for (let h = 0; h < palette.length; h++) {
		const entry = palette[h];
		a.push(entry.Alpha);
	}
	let alpha = [];
	for (let i = 0; i < px.length; i++) {
		let temp = [];
		for (let j = 0; j < px[i].length; j++) {
			temp.push(a[px[i][j]]);
		}
		alpha.push(temp);
	}
	return [px, alpha];
}
function getRgb(palette) {
	let ycbcr = [];
	for (let i = 0; i < palette.length; i++) {
		const entry = palette[i];
		ycbcr.push([entry.Y, entry.Cr, entry.Cb]);
	}
	const rgb = ycbcr2rgb(ycbcr);
	return rgb;
}
const mmultiply = (a, b) => a.map((x, i) => transpose(b).map(y => dotproduct(x, y)));
const dotproduct = (a, b) => a.map((x, i) => a[i] * b[i]).reduce((m, n) => m + n);
const transpose = (a) => a[0].map((x, i) => a.map(y => y[i]));

class BaseSegment {
	constructor(bytes) {
		this.SEGMENT = {
			'14': 'PDS',
			'15': 'ODS',
			'16': 'PCS',
			'17': 'WDS',
			'80': 'END',
		};
		if (80 !== bytes[0] && 71 !== bytes[1]) {
			throw new Error('InvalidSegmentError');
		}
		this.pts = a2h2i(bytes, 2, 6) / 90;
		this.dts = a2h2i(bytes, 6, 10) / 90;
		this.type = this.SEGMENT[intToHex(bytes[10])];
		this.size = a2h2i(bytes, 11, 13);
		this.data = bytes.slice(13);
	}
}
class PresentationCompositionSegment {
	constructor(base) {
		this.STATE = {
			'00': 'Normal',
			'40': 'Acquisition Point',
			'80': 'Epoch Start',
		};
		this.base = base;
		this.width = a2h2i(base.data, 0, 2);
		this.height = a2h2i(base.data, 2, 4);
		this.frameRate = base.data[4];
		this.num = a2h2i(base.data, 5, 7);
		this.state = this.STATE[intToHex(base.data[7])];
		this.paletteUpdate = Boolean(base.data[8]);
		this.paletteId = base.data[9];
		this.numComps = base.data[10];
		this.windowObjects = [];
		let b = this.base.data.slice(11);
		while (b.length) {
			const len = 8 * (1 + b[3] ? 1 : 0);
			this.windowObjects.push(new CompositionObject(b.slice(0, len)));
			b = b.slice(len);
		}
		this.base.data = new Uint8Array(0);
	}
	getObjectById(id) {
		for (let i = 0; i < this.windowObjects.length; i++) {
			if (this.windowObjects[i].objectId === id) {
				return this.windowObjects[i];
			}
		}
		return null;
	}
	getObjectByWindowId(id) {
		for (let i = 0; i < this.windowObjects.length; i++) {
			if (this.windowObjects[i].windowId === id) {
				return this.windowObjects[i];
			}
		}
		return null;
	}
}
class WindowDefinitionSegment {
	constructor(base) {
		this.base = base;
		this.numWindows = base.data[0];
		this.windows = [];
		for (let i = 0; i < this.numWindows; i++) {
			let o = 9 * i;
			const wdw = {
				windowId: base.data[o + 1],
				xOffset: a2h2i(base.data, o + 2, o + 4),
				yOffset: a2h2i(base.data, o + 4, o + 6),
				width: a2h2i(base.data, o + 6, o + 8),
				height: a2h2i(base.data, o + 8, o + 10),
			};
			this.windows.push(wdw);
		}
		this.base.data = new Uint8Array(0);
	}
}
class PaletteDefinitionSegment {
	constructor(base) {
		this.base = base;
		this.paletteId = base.data[0];
		this.version = base.data[1];
		this.palette = [];
		for (let i = 0; i < 256; i++) {
			this.palette.push(new Palette(0, 0, 0, 0));
		}
		const a = base.data.slice(2).length / 5;
		for (var i = 0; i < a; i++) {
			const j = 2 + i * 5;
			this.palette[base.data[j]] = new Palette(base.data[j + 1], base.data[j + 2], base.data[j + 3], base.data[j + 4]);
		}
		this.base.data = new Uint8Array(0);
	}
}
class ObjectDefinitionSegment {
	constructor(base) {
		this.SEQUENCE = {
			' 40': 'Last',
			' 80': 'First',
			' c0': 'First and last',
		};
		this.base = base;
		this.id = a2h2i(base.data, 0, 2);
		this.version = base.data[2];
		this.type = this.SEQUENCE[' ' + intToHex(base.data[3])];
		this.len = a2h2i(base.data, 4, 7);
		this.width = a2h2i(base.data, 7, 9);
		this.height = a2h2i(base.data, 9, 11);
		this.imgData = base.data.slice(11);
		if (this.type === 'Last') {
			this.imgData = base.data.slice(4);
		}
		this.base.data = new Uint8Array(0);
	}
}
class EndSegment {
	constructor(base) {
		this.base = base;
		this.end = true;
		this.base.data = new Uint8Array(0);
	}
}
class CompositionObject {
	constructor(data) {
		this.objectId = a2h2i(data, 0, 2);
		this.windowId = data[2];
		this.cropped = Boolean(data[3]);
		this.xOffset = a2h2i(data, 4, 6);
		this.yOffset = a2h2i(data, 6, 8);
		this.xOffsetCrop = this.cropped ? a2h2i(data, 8, 10) : -1;
		this.yOffsetCrop = this.cropped ? a2h2i(data, 10, 12) : -1;
		this.widthCrop = this.cropped ? a2h2i(data, 12, 14) : -1;
		this.heightCrop = this.cropped ? a2h2i(data, 14, 16) : -1;
	}
}
class Palette {
	constructor(Y, Cr, Cb, Alpha) {
		this.Y = Y;
		this.Cr = Cr;
		this.Cb = Cb;
		this.Alpha = Alpha;
	}
}
function a2h2i(array, from, to) {
	// array to hex to int
	let hex = '';
	for (let i = from; i < to; i++) {
		hex += intToHex(array[i]);
	}
	return parseInt(hex, 16);
}
function intToHex(x) {
	return ('00' + x.toString(16)).slice(-2);
}

class SUPtitles {
	constructor(video, link) {
		this.offset = 0;
		this.timeout = null;
		this.lastPalette = null;
		this.cv = [];
		this.canvasSizeSet = false;
		this.playHandler = () => {
			this.offset = 0;
			this.cv.map(c => c.getContext('2d').clearRect(0, 0, c.width, c.height));
			this.start();
		};
		this.pauseHandler = () => {
			clearTimeout(this.timeout);
		};
		console.info('# SUP Starting');
		this.video = video;
		video.addEventListener('play', this.playHandler);
		video.addEventListener('pause', this.pauseHandler);
		const canvas = document.createElement('canvas');
		canvas.height = 1080;
		canvas.width = 1920;
		canvas.style.width = '100%';
		canvas.style.height = '100%';
		canvas.style.top = '0';
		canvas.style.left = '0';
		canvas.style.position = 'absolute';
		canvas.style.pointerEvents = 'none';
		video.parentNode.appendChild(canvas);
		this.cv.push(canvas);
		fetch(link)
			.then(response => response.arrayBuffer())
			.then(buffer => {
			this.file = new Uint8Array(buffer);
			console.info('# SUP Ready');
			this.start();
		});
	}
	dispose() {
		clearTimeout(this.timeout);
		this.timeout = null;
		this.video.removeEventListener('play', this.playHandler);
		this.video.removeEventListener('pause', this.pauseHandler);
		this.file = null;
		this.offset = null;
		this.lastPalette = null;
		this.video = null;
		this.cv.map(c => (c.outerHTML = ''));
		this.cv = null;
		console.info('# SUP Disposed');
	}
	videoTime() {
		return this.video.currentTime * 1000;
	}
	start() {
		if (this.offset === 0) {
			while (this.offset < this.file.length) {
				const pts = a2h2i(this.file, this.offset + 2, this.offset + 6) / 90;
				const size = 13 + a2h2i(this.file, this.offset + 11, this.offset + 13);
				const type = a2h2i(this.file, this.offset + 10, this.offset + 11);
				if (pts > this.videoTime() && type === 22) {
					break;
				}
				else {
					this.offset += size;
				}
			}
			this.getNextSubtitle();
		}
	}
	getNextSubtitle() {
		if (this.offset < this.file.length) {
			let ended = false;
			let PCS;
			let WDS;
			let PDS;
			let ODS = [];
			while (!ended) {
				const size = 13 + a2h2i(this.file, this.offset + 11, this.offset + 13);
				const bytes = this.file.slice(this.offset, this.offset + size);
				const base = new BaseSegment(bytes);
				switch (base.type) {
					case 'PCS':
						PCS = new PresentationCompositionSegment(base);
						if (!this.canvasSizeSet) {
							this.cv.map(c => {
								c.height = PCS.height;
								c.width = PCS.width;
								return null;
							});
							this.canvasSizeSet = true;
						}
						break;
					case 'WDS':
						WDS = new WindowDefinitionSegment(base);
						break;
					case 'PDS':
						PDS = new PaletteDefinitionSegment(base);
						this.lastPalette = PDS.palette;
						break;
					case 'ODS':
						ODS.push(new ObjectDefinitionSegment(base));
						break;
					case 'END':
						ended = true;
						break;
					default:
						throw new Error('InvalidSegmentError');
				}
				this.offset += size;
			}
			this.timeout = setTimeout(() => {
				PDS || this.lastPalette
					? this.draw(PCS, WDS, PDS, ODS)
					: console.log('# SUP SKIPPING, NO PALETTE');
				this.getNextSubtitle();
			}, PCS.base.pts - this.videoTime());
		}
	}
	draw(PCS, WDS, PDS, ODS) {
		if (ODS.length > 0) {
			// DRAW
			let first = null;
			ODS.map(o => {
				if (o.type === 'First') {
					first = o;
				}
				else {
					let imgData = o.imgData;
					if (first) {
						imgData = Uint8Array.from([
							...[].slice.call(first.imgData),
							...[].slice.call(o.imgData),
						]);
					}
					const width = first ? first.width : o.width;
					const height = first ? first.height : o.height;
					const object = PCS.getObjectById(first ? first.id : o.id);
					const xOffset = object.xOffset;
					const yOffset = object.yOffset;
					const pixels = this.getPixels(imgData, PDS ? PDS.palette : this.lastPalette, width, height);
					this.cv[0] // object.windowId
						.getContext('2d')
						.putImageData(new ImageData(pixels, width, height), xOffset, yOffset);
					first = null;
				}
				return null;
			});
		}
		else {
			// ERASE
			WDS.windows.map((w) => {
				if (PCS.windowObjects.length === 0 ||
					(PCS.windowObjects.length && !PCS.getObjectByWindowId(w.windowId))) {
					this.cv[0] // w.windowId
						.getContext('2d')
						.putImageData(new ImageData(new Uint8ClampedArray(w.width * w.height * 4), w.width, w.height), w.xOffset, w.yOffset);
				}
				return null;
			});
		}
	}
	getPixels(imgData, palette, width, height) {
		const rgb = getRgb(palette);
		let [pxMx1, alphaMx1] = getPxAlpha(imgData, palette);
		const pxls = new Uint8ClampedArray(width * height * 4);
		for (let h = 0; h < pxMx1.length; h++) {
			for (let w = 0; w < pxMx1[h].length; w++) {
				const i = h * pxMx1[h].length + w;
				pxls[i * 4 + 0] = rgb[pxMx1[h][w]][0];
				pxls[i * 4 + 1] = rgb[pxMx1[h][w]][1];
				pxls[i * 4 + 2] = rgb[pxMx1[h][w]][2];
				pxls[i * 4 + 3] = alphaMx1[h][w];
			}
		}
		return pxls;
	}
}
