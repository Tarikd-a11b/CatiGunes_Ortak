# -*- coding: utf-8 -*-
"""Evka-5 icin MobileSAM (ONNX) + ayak izi kutu-yonlendirmesi."""
import json, math, numpy as np, onnxruntime as ort
from PIL import Image

REF = json.load(open('cache/evka5_mozaik_ref.json'))
Z, X0, Y0, TS = REF['zoom'], REF['x0'], REF['y0'], REF['tile']
MPP = REF['m_per_px']

def lonlat2px(lon, lat):
    n = (1 << Z) * TS
    gx = (lon + 180.0) / 360.0 * n
    gy = (1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n
    return gx - X0 * TS, gy - Y0 * TS

def px2lonlat(px, py):
    n = (1 << Z) * TS
    gx, gy = px + X0 * TS, py + Y0 * TS
    lon = gx / n * 360.0 - 180.0
    lat = math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * gy / n))))
    return lon, lat

MEAN = np.array([123.675, 116.28, 103.53], np.float32)
STD  = np.array([58.395, 57.12, 57.375], np.float32)

class MobileSAM:
    def __init__(self, enc='models/mobile_sam_image_encoder.onnx',
                       dec='models/sam_mask_decoder_single.onnx'):
        o = ort.SessionOptions(); o.intra_op_num_threads = 0
        self.enc = ort.InferenceSession(enc, o, providers=['CPUExecutionProvider'])
        self.dec = ort.InferenceSession(dec, o, providers=['CPUExecutionProvider'])
        self.enc_in = self.enc.get_inputs()[0].name

    def embed(self, img_rgb, normalize=True):
        """img_rgb: HxWx3 uint8, kare ve 1024x1024 olmali."""
        x = img_rgb.astype(np.float32)
        if normalize:
            x = (x - MEAN) / STD
        return self.enc.run(None, {self.enc_in: x})[0]

    def box(self, emb, box_xyxy, orig_hw):
        """SAM kutu-yonlendirmesi: iki nokta, etiket 2 (sol-ust) ve 3 (sag-alt)."""
        x0, y0, x1, y1 = box_xyxy
        pc = np.array([[[x0, y0], [x1, y1]]], np.float32)
        pl = np.array([[2.0, 3.0]], np.float32)
        out = self.dec.run(None, {
            'image_embeddings': emb,
            'point_coords': pc, 'point_labels': pl,
            'mask_input': np.zeros((1, 1, 256, 256), np.float32),
            'has_mask_input': np.zeros(1, np.float32),
            'orig_im_size': np.array(orig_hw, np.float32)})
        masks, iou = out[0], out[1]
        return masks[0, 0] > 0.0, float(np.ravel(iou)[0])
