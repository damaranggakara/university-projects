# Image Compression and Channel Coding

DCT-based image compression in the style of JPEG, followed by transmission over a
simulated noisy channel protected by a Hamming(7,4) error-correcting code. Coursework for
Teori Pengkodean dan Informasi (Coding and Information Theory), Semester 4.

## Pipeline

1. Load image, resize to 256x256, convert to RGB
2. Per channel: split into 8x8 blocks, 2-D DCT, quantise against the standard JPEG
   luminance matrix, store as `uint8`
3. Inverse DCT to reconstruct, and measure **PSNR** against the original
4. Serialise the quantised coefficients to a bitstream
5. Encode with **Hamming(7,4)**: 4 data bits to 7 transmitted bits
6. Inject random bit errors at p = 0.005 to simulate a noisy channel
7. Detect and correct at the receiver, decompress, measure PSNR again

## Results

| Stage | PSNR |
|---|---|
| After DCT compression | **31.89 dB** |
| After noisy channel + correction (as submitted) | 6.92 dB |
| After noisy channel + correction (**decoder fixed**) | **17.93 dB** |

## The bug, and the fix

The original decoder computed its three syndrome bits correctly but assembled them in the
wrong order before converting to an error position:

```python
syndrome = s1 + s2 + s3        # s1 treated as the most significant bit
pos = int(syndrome, 2) - 1
```

In Hamming(7,4) with parity at positions 1, 2 and 4, the check covering position 1 is the
**least** significant syndrome bit, so the order must be `s3 s2 s1`. Reversed, the decoder
flips an innocent bit, converting a recoverable 1-bit error into an unrecoverable 2-bit
one. The fix is one token:

```python
syndrome = s3 + s2 + s1
```

`test_hamming.py` verifies this exhaustively over all 16 data words and all 7 single-bit
error positions, and keeps the buggy ordering alongside for comparison:

```
single-bit error cases : 112  (16 data words x 7 positions)
current implementation : 112/112 recovered (100.0%)
original bit ordering  :  80/112 recovered  (71.4%)

the original ordering failed at bit positions:
   position 3: 16/16 data words
   position 6: 16/16 data words
```

Positions 3 and 6 are the data bits `d1` and `d3`, so roughly 29% of single-bit errors were
mis-corrected, each one doubling the corruption instead of removing it.

## Why 17.93 dB and not 31.89 dB

The fix takes single-bit correction from 71% to 100%, but the recovered image is still well
short of the compression baseline. That residue is **not** a second bug; it is
Hamming(7,4) meeting its design limit. `experiment_error_rate.py` sweeps the channel error
rate to show it:

| p | errors injected | blocks with >=2 errors | residual data bits | PSNR |
|---|---|---|---|---|
| 0.005 | 1900 | 25 | 38 | 21.22 dB |
| 0.001 | 423 | **0** | **0** | 33.90 dB |
| 0.0002 | 83 | 0 | 0 | 33.90 dB |
| 0 | 0 | 0 | 0 | 33.90 dB |

(Run on a 96x96 crop, so its lossless baseline is 33.85 dB rather than 31.89 dB.)

At p = 0.001 and below the channel is **perfectly lossless**, zero residual bit errors,
PSNR identical to the baseline. That is the proof the codec is correct.

At p = 0.005, 25 of the 7-bit blocks receive two or more errors. A Hamming(7,4) code
corrects exactly one error per block, so those are unfixable by construction, and the
decoder's attempt makes each slightly worse. They leave 38 wrong data bits out of 221,184
**0.017% of the payload**, and that is enough to cost 12.6 dB.

The amplification is the interesting part: the corrupted bytes are *quantised DCT
coefficients*, not pixels. One bad coefficient is multiplied by its quantisation step and
spread by the inverse DCT across an entire 8x8 block, so a single bit flip damages 64
pixels. Error in the coefficient domain is far more destructive than the same error in the
pixel domain.

To hold 31.89 dB at p = 0.005 the design needs more than a bit-order fix: bit interleaving
so burst errors spread across blocks, a stronger code (BCH or Reed-Solomon), or
disproportionate protection for the DC coefficient of each block.

## Running it

```bash
pip install -r requirements.txt
python test_hamming.py              # decoder correctness, 112 cases
python experiment_error_rate.py     # error-rate sweep table above
jupyter notebook notebooks/
```

## Notes

Both notebooks carry the corrected decoder and have been re-executed end to end. The
original buggy ordering is preserved in `test_hamming.py` as a comparison case rather than
discarded, so the regression it caused stays visible.

`photo_compression.ipynb` originally read `kucing tengil.jpg`, which exists nowhere on any
available drive. It now uses `data/sample_image.jpeg`, the image from the companion
notebook. The pipeline is image-independent, though exact PSNR figures are specific to
this image.
