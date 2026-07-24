# Test full encode/decode of lens response with real image
import struct, zlib, random, urllib.request, io

def _varint(n):
    out=bytearray()
    while True:
        b=n&0x7f; n>>=7
        out.append(b | (0x80 if n else 0))
        if not n: break
    return bytes(out)

def _key(fn, wt): return _varint((fn<<3)|wt)
def _bytes(fn, b): return _key(fn,2)+_varint(len(b))+b
def _str(fn,s): return _bytes(fn,s.encode())
def _u64(fn,n): return _key(fn,0)+_varint(n)
def _i32(fn,n): return _key(fn,0)+_varint(n)
def _msg(fn,m): return _bytes(fn,m)

def make_text_png():
    # simple white PNG with no real text - use qr if exists
    from pathlib import Path
    p = Path(r"C:\Users\MetafyLabs\qr_code.png")
    if p.exists():
        return p.read_bytes()
    # solid
    w=h=100
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag+data) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes([255,255,255]*w) for _ in range(h))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

png = make_text_png()
print('png bytes', len(png))
# get dims with cv2 or simple
try:
    import cv2, numpy as np
    arr = np.frombuffer(png, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    h,w = img.shape[:2]
except Exception as e:
    print('cv2 fail', e); w=h=400

req_id = _u64(1, random.randint(1, 2**63-1)) + _i32(2,1) + _i32(3,1)
locale = _str(1,'en')+_str(2,'US')+_str(3,'America/New_York')
client = _i32(1,3)+_i32(2,4)+_msg(4,locale)
req_ctx = _msg(3,req_id)+_msg(4,client)
payload = _bytes(1,png)
meta = _i32(1,w)+_i32(2,h)
img = _msg(1,payload)+_msg(3,meta)
obj = _msg(1,req_ctx)+_msg(3,img)
body = _msg(1,obj)

req = urllib.request.Request(
  'https://lensfrontend-pa.googleapis.com/v1/crupload',
  data=body,
  headers={
    'content-type':'application/x-protobuf',
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'x-goog-api-key':'AIzaSyDr2UxVnv_U85AbhhY8XSHSIavUW0DC-sY',
    'origin':'https://lens.google.com',
    'referer':'https://lens.google.com/',
  },
  method='POST'
)
with urllib.request.urlopen(req, timeout=30) as r:
    data=r.read()
    print('status', r.status, 'len', len(data))
    # dump printable strings
    import re
    strings = re.findall(rb'[\x20-\x7e]{3,}', data)
    print('strings:', [s.decode() for s in strings[:40]])
