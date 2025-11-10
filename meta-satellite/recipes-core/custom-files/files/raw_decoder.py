
import numpy as np

def demosaic_bilinear(raw, pattern='rggb'):
    """
    Simple bilinear demosaic using pure numpy (no scipy).
    pattern: one of ['rggb', 'bggr', 'grbg', 'gbrg']
    """
    h, w = raw.shape
    rgb = np.zeros((h, w, 3), dtype=np.float32)

    # mask positions for each color in Bayer
    if pattern == 'rggb':
        r_mask = np.tile([[1,0],[0,0]], (h//2, w//2))
        g_mask = np.tile([[0,1],[1,0]], (h//2, w//2))
        b_mask = np.tile([[0,0],[0,1]], (h//2, w//2))
    elif pattern == 'bggr':
        b_mask = np.tile([[1,0],[0,0]], (h//2, w//2))
        g_mask = np.tile([[0,1],[1,0]], (h//2, w//2))
        r_mask = np.tile([[0,0],[0,1]], (h//2, w//2))
    elif pattern == 'grbg':
        g_mask = np.tile([[1,0],[0,1]], (h//2, w//2))
        r_mask = np.tile([[0,1],[0,0]], (h//2, w//2))
        b_mask = np.tile([[0,0],[1,0]], (h//2, w//2))
    elif pattern == 'gbrg':
        g_mask = np.tile([[0,1],[1,0]], (h//2, w//2))
        b_mask = np.tile([[1,0],[0,0]], (h//2, w//2))
        r_mask = np.tile([[0,0],[0,1]], (h//2, w//2))
    else:
        raise ValueError("Unsupported Bayer pattern")

    # extract each channel
    R = raw * r_mask
    G = raw * g_mask
    B = raw * b_mask

    # Manual 2D convolution using numpy (bilinear kernel)
    def convolve2d_bilinear(img):
        # Pad image with edge values
        padded = np.pad(img, 1, mode='edge')
        
        # Apply 3x3 bilinear kernel manually
        result = (
            1 * padded[0:-2, 0:-2] + 2 * padded[0:-2, 1:-1] + 1 * padded[0:-2, 2:] +
            2 * padded[1:-1, 0:-2] + 4 * padded[1:-1, 1:-1] + 2 * padded[1:-1, 2:] +
            1 * padded[2:, 0:-2]   + 2 * padded[2:, 1:-1]   + 1 * padded[2:, 2:]
        ) / 16.0
        
        return result

    # interpolate missing pixels
    R = convolve2d_bilinear(R)
    G = convolve2d_bilinear(G)
    B = convolve2d_bilinear(B)

    rgb[...,0] = R
    rgb[...,1] = G
    rgb[...,2] = B
    np.clip(rgb, 0, 1, out=rgb)
    return rgb

def rawfAwb(rawf, rgain, bgain, bayer='rggb'):
    hrb_map = {'rggb': np.array([[rgain, 1.0],[1.0, bgain]]),
               'bggr': np.array([[bgain, 1.0],[1.0, rgain]]),
               'grbg': np.array([[1.0, rgain],[bgain, 1.0]]),
               'gbrg': np.array([[1.0, bgain],[rgain, 1.0]])}

    h_rb = hrb_map[bayer]
    b_width = rawf.shape[1]
    rawf = np.hsplit(rawf, b_width/2)
    rawf = np.vstack(rawf)
    b_shape = rawf.shape
    rawf = rawf.reshape(-1,2,2)

    rawf = rawf * h_rb

    rawf = rawf.reshape(b_shape)
    rawf = np.hstack(np.vsplit(rawf, b_width/2))
    return rawf

def raw10torawf(raw, h):
    raw10 = raw.reshape(h, -1, 5).astype(np.uint16)
    a,b,c,d,e = [raw10[...,x] for x in range(5)]
    x1 = a + ((b & 0x03) << 8)
    x2 = (b >> 2) + ((c & 0x0f) << 6)
    x3 = (c >> 4) + ((d & 0x3f) << 4)
    x4 = (d >> 6) + (e << 2)
    x1 = x1.reshape(h, -1, 1)
    x2 = x2.reshape(h, -1, 1)
    x3 = x3.reshape(h, -1, 1)
    x4 = x4.reshape(h, -1, 1)
    x = np.dstack((x1, x2, x3, x4))
    x = x.reshape(h, -1)
    return x / np.float64(2**10)

def raw10ptorawf(raw, h):
    raw16 = raw.view(np.dtype('<u2'))  # '>u2' = big-endian uint16
    # Mask to keep only lower 10 bits (0x3FF = 0b1111111111)
    raw10 = raw16 & 0x3FF
    # Reshape to image dimensions
    raw10 = raw10.reshape(h, -1)
    # Normalize to [0.0, 1.0]
    return raw10.astype(np.float64) / np.float64(2**10)

def mipirawtorawf(raw, h):
    raw10 = raw.reshape(h, -1, 5).astype(np.uint16)
    a,b,c,d,e = [raw10[...,x] for x in range(5)]
    x1 = (a << 2) + ((e >> 0) & 0x03)
    x2 = (b << 2) + ((e >> 2) & 0x03)
    x3 = (c << 2) + ((e >> 4) & 0x03)
    x4 = (d << 2) + ((e >> 6) & 0x03)
    x1 = x1.reshape(h, -1, 1)
    x2 = x2.reshape(h, -1, 1)
    x3 = x3.reshape(h, -1, 1)
    x4 = x4.reshape(h, -1, 1)
    x = np.dstack((x1, x2, x3, x4))
    x = x.reshape(h, -1)
    return x / np.float64(2**10)


def raw8torawf(raw, h):
    return raw.reshape((h, -1))/np.float(2**8)

def raw16torawf(raw, h):
    return raw.reshape((h, -1))/np.float(2**16)

def yuv420torgb(yuv, h, isYvu=False):
    yuv = yuv.astype(np.int32)

    w = int(yuv.size / (h * 1.5))
    y = yuv[0:w*h]
    # u,v size is  h/2 * w/2
    if isYvu:
        v = yuv[w*h::2]
        u = yuv[w*h+1::2]
    else:
        u = yuv[w*h::2]
        v = yuv[w*h+1::2]

    # u,v size is  h/2 * w
    u = np.stack((u,u), axis=1).flatten()
    v = np.stack((v,v), axis=1).flatten()

    # u,v size is h * w
    u.resize(int(h/2), w)
    u = np.stack((u,u), axis=1).flatten()
    v.resize(int(h/2), w)
    v = np.stack((v,v), axis=1).flatten()

    b = 1.164 * (y-16) + 2.018 * (u - 128)
    g = 1.164 * (y-16) - 0.813 * (v - 128) - 0.391 * (u - 128)
    r = 1.164 * (y-16) + 1.596 * (v - 128)

    rgb = np.stack((r,g,b), axis=1)
    np.clip(rgb, 0, 256, out=rgb)
    rgb = rgb/256.0
    return rgb.reshape(h, w, 3)

class RawImageBase(object):
    def __init__(self, path, width, height, usize=None, offset=0, dtype=np.uint8):
        self.path = path
        self.width = width
        self.height = height
        self.usize = usize
        self.offset = offset
        self.dtype = dtype
        self.raw = None
        self.rgb = None
        pass

    def load(self):
        # 1. open file
        with open(self.path, 'rb') as infile:
            # 2. skip offset
            infile.read(self.offset)
            # 3. load date from file
            self.raw = np.fromfile(infile, self.dtype)

        # 4. force resize
        if self.width is not None and self.usize is not None:
            self.raw.resize((int(self.width * self.usize * self.height)))

        pass

    def getRGB(self):
        return self.rgb

class RawBayerImage(RawImageBase):
    def __init__(self, path, width, height, usize, offset, dtype, bayer='rggb', rawtorawf=None):
        RawImageBase.__init__(self, path=path, width=width,
                              height=height, usize=usize,
                              offset=offset, dtype=dtype)
        self.bayer = bayer
        self.rawtorawf = rawtorawf


    def load(self):
        RawImageBase.load(self)
        rawf = self.rawtorawf(self.raw, self.height)
        rawf = rawfAwb(rawf, 4.0, 2.7, self.bayer)  # Bước 4
        self.rgb = demosaic_bilinear(rawf, self.bayer)
        
        # THÊM ĐOẠN NÀY:
        # Color correction matrix
        self.rgb = self.rgb * 1.2
        # self.rgb = np.clip(self.rgb, 0.0, 1.0)


class Raw10Image(RawBayerImage):
    def __init__(self, path, width, height, offset=0, bayer='rggb'):
        RawBayerImage.__init__(self, path=path, width=width,
                              height=height, usize=1.25,
                              offset=offset, bayer=bayer,
                              dtype=np.uint8, rawtorawf=raw10torawf)


class MipiRawImage(RawBayerImage):
    def __init__(self, path, width, height, offset=0, bayer='rggb'):
        RawBayerImage.__init__(self, path=path, width=width,
                              height=height, usize=1.25,
                              offset=offset, bayer=bayer,
                              dtype=np.uint8, rawtorawf=mipirawtorawf)
        
class Raw10PaddedImage(RawBayerImage):
    def __init__(self, path, width, height, offset=0, bayer='rggb'):
        RawBayerImage.__init__(self, path=path, width=width,
                              height=height, usize=2.0,
                              offset=offset, bayer=bayer,
                              dtype=np.uint8, rawtorawf=raw10ptorawf)

class Raw8Image(RawBayerImage):
    def __init__(self, path, width, height, offset=0, bayer='rggb'):
        RawBayerImage.__init__(self, path=path, width=width,
                              height=height, usize=1.0,
                              offset=offset, bayer=bayer,
                              dtype=np.uint8, rawtorawf=raw8torawf)

class Raw16Image(RawBayerImage):
    def __init__(self, path, width, height, offset=0, bayer='rggb'):
        RawBayerImage.__init__(self, path=path, width=width,
                              height=height, usize=2.0,
                              offset=offset, bayer=bayer,
                              dtype=np.uint16, rawtorawf=raw16torawf)


class GrayImage(RawImageBase):
    def __init__(self, path, width, height, offset=0):
        RawImageBase.__init__(self, path=path, width=width,
                              height=height, usize=1.0,
                              offset=offset, dtype=np.uint8);

    def load(self):
        RawImageBase.load(self)
        raw = self.raw / np.float(2**8)
        self.rgb = raw.reshape(self.height, -1)


class YuvImage(RawImageBase):
    def __init__(self, path, width, height, offset=0, isYvu=False):
        RawImageBase.__init__(self, path=path, width=width,
                              height=height, usize=1.5,
                              offset=offset, dtype=np.uint8)
        self.isYvu = isYvu

    def load(self):
        RawImageBase.load(self)
        self.rgb = yuv420torgb(self.raw, self.height, self.isYvu)

class YvuImage(YuvImage):
    def __init__(self, path, width, height, offset=0):
        YuvImage.__init__(self, path=path, width=width,
                          height=height, offset=offset, isYvu=True)
