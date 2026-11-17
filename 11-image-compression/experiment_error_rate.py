"""Isolate the cause of residual image damage after error correction.

Sweeps the channel bit-error probability through the full
compress -> Hamming(7,4) -> noisy channel -> correct -> decompress pipeline and
reports, at each rate, how many 7-bit blocks received more than one error (which
Hamming cannot correct), how many data bits survive wrong, and the resulting PSNR.

Run:  python experiment_error_rate.py
"""
import numpy as np, cv2, sys
from PIL import Image
sys.path.insert(0, ".")
from test_hamming import add_hamming_code, detect_and_correct_hamming, remove_hamming_code

rng = np.random.default_rng(1)
Q = np.array([[16,11,10,16,24,40,51,61],[12,12,14,19,26,58,60,55],
              [14,13,16,24,40,57,69,56],[14,17,22,29,51,87,80,62],
              [18,22,37,56,68,109,103,77],[24,35,55,64,81,104,113,92],
              [49,64,78,87,103,121,120,101],[72,92,95,98,112,100,103,99]], float)

img = np.array(Image.open("data/sample_image.jpeg").convert("RGB").resize((96,96)), float)

def compress(ch):
    out = np.zeros_like(ch); rec = np.zeros_like(ch)
    for i in range(0,ch.shape[0],8):
        for j in range(0,ch.shape[1],8):
            q = np.round(cv2.dct(np.float32(ch[i:i+8,j:j+8]-128))/Q)
            out[i:i+8,j:j+8] = q+128
            rec[i:i+8,j:j+8] = np.clip(cv2.idct(np.float32(q*Q))+128,0,255)
    return out.astype(np.uint8), rec.astype(np.uint8)

def decompress(ch):
    out = np.zeros(ch.shape, np.float32)
    for i in range(0,ch.shape[0],8):
        for j in range(0,ch.shape[1],8):
            q = ch[i:i+8,j:j+8].astype(np.float32)-128
            out[i:i+8,j:j+8] = np.clip(cv2.idct(np.float32(q*Q))+128,0,255)
    return out

comp = np.stack([compress(img[:,:,c])[0] for c in range(3)], 2)
recon= np.stack([compress(img[:,:,c])[1] for c in range(3)], 2)
def psnr(a,b):
    m=np.mean((a.astype(float)-b.astype(float))**2)
    return float('inf') if m==0 else 20*np.log10(255/np.sqrt(m))

print(f"baseline compression PSNR : {psnr(img,recon):.2f} dB\n")
bs  = ''.join(format(b,'08b') for b in comp.tobytes())
enc = add_hamming_code(bs)
nbl = len(enc)//7
print(f"{'p':>8} {'injected':>9} {'>=2-err blk':>12} {'resid bits':>11} {'PSNR':>8}")
print("-"*56)
for p in (0.005, 0.001, 0.0002, 0.0):
    b = np.frombuffer(enc.encode(), dtype=np.uint8).copy()
    flip = rng.random(len(b)) < p
    b[flip] ^= 1  # '0'(48) <-> '1'(49)
    corrupt = b.tobytes().decode()
    inj = int(flip.sum())
    blk = np.add.reduceat(flip[:nbl*7].astype(int), np.arange(0,nbl*7,7))
    fix,_ = detect_and_correct_hamming(corrupt)
    dec   = remove_hamming_code(fix)
    resid = sum(1 for x,y in zip(bs,dec) if x!=y)
    arr = np.frombuffer(bytearray(int(dec[i:i+8],2) for i in range(0,len(dec),8)),
                        dtype=np.uint8)[:comp.size].reshape(comp.shape)
    out = np.stack([decompress(arr[:,:,c]) for c in range(3)], 2)
    print(f"{p:>8} {inj:>9} {int((blk>=2).sum()):>12} {resid:>11} {psnr(img,out):>7.2f} dB")
