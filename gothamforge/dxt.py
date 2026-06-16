import numpy as np
from PIL import Image


def _to_565(c):
    c = np.asarray(c)
    r = (c[..., 0].astype(np.uint16) >> 3) & 0x1F
    g = (c[..., 1].astype(np.uint16) >> 2) & 0x3F
    b = (c[..., 2].astype(np.uint16) >> 3) & 0x1F
    return (r << 11) | (g << 5) | b


def _from_565(c):
    c = c.astype(np.uint16)
    r = (c >> 11) & 0x1F
    g = (c >> 5) & 0x3F
    b = c & 0x1F
    R = (r << 3) | (r >> 2)
    G = (g << 2) | (g >> 4)
    B = (b << 3) | (b >> 2)
    return np.stack([R, G, B], axis=-1).astype(np.float32)


def _to_blocks(img):
    h, w, _ = img.shape
    H = (h + 3) // 4 * 4
    W = (w + 3) // 4 * 4
    if (H, W) != (h, w):
        pad = np.zeros((H, W, 4), np.uint8)
        pad[:h, :w] = img
        if h < H:
            pad[h:H, :w] = img[h - 1:h, :w]
        if w < W:
            pad[:, w:W] = pad[:, w - 1:w]
        img = pad
        h, w = H, W
    bh, bw = h // 4, w // 4
    b = img.reshape(bh, 4, bw, 4, 4).transpose(0, 2, 1, 3, 4)
    return b.reshape(bh * bw, 16, 4)


def _color_block(blocks):
    rgb = blocks[..., :3].astype(np.float32)
    cmax = rgb.max(axis=1)
    cmin = rgb.min(axis=1)
    c0 = _to_565(np.round(cmax)).astype(np.int32)
    c1 = _to_565(np.round(cmin)).astype(np.int32)
    lo = np.minimum(c0, c1)
    hi = np.maximum(c0, c1)
    c0, c1 = hi, lo
    eq = c0 == c1
    c1 = np.where(eq & (c1 > 0), c1 - 1, c1)
    c0 = np.where(eq & (c0 == c1), np.minimum(c0 + 1, 0xFFFF), c0)
    C0 = _from_565(c0.astype(np.uint16))
    C1 = _from_565(c1.astype(np.uint16))
    C2 = (2 * C0 + C1) / 3.0
    C3 = (C0 + 2 * C1) / 3.0
    pal = np.stack([C0, C1, C2, C3], axis=1)            
    diff = rgb[:, :, None, :] - pal[:, None, :, :]      
    idx = (diff * diff).sum(-1).argmin(-1).astype(np.uint32)  
    shifts = (2 * np.arange(16)).astype(np.uint32)
    packed = (idx << shifts).sum(1).astype(np.uint32)
    out = np.empty((blocks.shape[0], 8), np.uint8)
    out[:, 0] = c0 & 0xFF
    out[:, 1] = (c0 >> 8) & 0xFF
    out[:, 2] = c1 & 0xFF
    out[:, 3] = (c1 >> 8) & 0xFF
    out[:, 4] = packed & 0xFF
    out[:, 5] = (packed >> 8) & 0xFF
    out[:, 6] = (packed >> 16) & 0xFF
    out[:, 7] = (packed >> 24) & 0xFF
    return out


def encode_dxt1(img):
    return _color_block(_to_blocks(img)).tobytes()


def encode_dxt5(img):
    blocks = _to_blocks(img)
    nb = blocks.shape[0]
    a = blocks[..., 3].astype(np.float32)
    a0 = np.round(a.max(1)).astype(np.int32)
    a1 = np.round(a.min(1)).astype(np.int32)
    eq = a0 == a1
    a1 = np.where(eq & (a1 > 0), a1 - 1, a1)
    a0 = np.where(eq & (a0 == a1), np.minimum(a0 + 1, 255), a0)
    pal = [a0, a1]
    for k in range(1, 7):  
        pal.append(((7 - k) * a0 + k * a1) // 7)
    apal = np.stack(pal, axis=1).astype(np.float32)     
    aidx = np.abs(a[:, :, None] - apal[:, None, :]).argmin(-1).astype(np.uint64)
    ashift = (3 * np.arange(16)).astype(np.uint64)
    apacked = (aidx << ashift).sum(1).astype(np.uint64) 
    color = _color_block(blocks)
    out = np.empty((nb, 16), np.uint8)
    out[:, 0] = a0 & 0xFF
    out[:, 1] = a1 & 0xFF
    for k in range(6):
        out[:, 2 + k] = (apacked >> np.uint64(8 * k)) & np.uint64(0xFF)
    out[:, 8:16] = color
    return out.tobytes()


def build_mips(pil_rgba):
    mips = [pil_rgba]
    w, h = pil_rgba.size
    while w > 1 or h > 1:
        w = max(1, w // 2)
        h = max(1, h // 2)
        mips.append(pil_rgba.resize((w, h), Image.LANCZOS))
    return mips


def encode(pil_rgba, fmt, gen_mips=True):
    enc = encode_dxt1 if fmt == "DXT1" else encode_dxt5
    mips = build_mips(pil_rgba) if gen_mips else [pil_rgba]
    chunks = [enc(np.asarray(m.convert("RGBA"))) for m in mips]
    return b"".join(chunks), len(mips)
