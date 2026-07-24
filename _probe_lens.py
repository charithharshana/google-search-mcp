import urllib.request
from pathlib import Path
# Test Lens Chromium endpoint with a tiny PNG
import struct, zlib, random

def make_png(w=64, h=64):
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag+data) & 0xffffffff)
    raw = b''.join(b'\x00' + bytes([255,0,0]*w) for _ in range(h))
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b'')

# manual protobuf encode helpers
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

png = make_png()
# build LensOverlayServerRequest matching yt-screenshot
req_id = _u64(1, random.randint(1, 2**63-1)) + _i32(2,1) + _i32(3,1)
locale = _str(1,'en')+_str(2,'US')+_str(3,'America/New_York')
client = _i32(1,3)+_i32(2,4)+_msg(4,locale)
req_ctx = _msg(3,req_id)+_msg(4,client)
payload = _bytes(1,png)
meta = _i32(1,64)+_i32(2,64)
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
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data=r.read()
        print('status', r.status, 'len', len(data), 'preview', data[:80])
except Exception as e:
    print('ERR', type(e), e)
    if hasattr(e,'read'):
        print(e.read()[:300])
