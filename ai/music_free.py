import io, math, random, wave, struct
from typing import Literal
Genre = Literal["lofi","ambient","synthwave","piano"]

def _sine(t, f): return math.sin(2*math.pi*f*t)

def generate_wav(seconds: int = 30, genre: Genre = "lofi", sample_rate: int = 22050) -> bytes:
    n = int(seconds*sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        if genre == "ambient":
            base, beat = 110, 0.0
        elif genre == "synthwave":
            base, beat = 140, 0.7
        elif genre == "piano":
            base, beat = 220, 0.2
        else:
            base, beat = 98, 0.35
        prog = [0, 5, 3, 7]
        scale = [0,2,3,5,7,8,10]
        def nf(step): return base * (2**(step/12))
        for i in range(n):
            t = i/sample_rate
            bar = int(t//2.0)
            root = prog[bar%len(prog)]
            chord = [root, root+3, root+7]
            s = 0.0
            for cs in chord:
                f = nf(cs)
                s += 0.18*_sine(t,f)+0.06*_sine(t,f*2)
            mel = root + random.choice(scale)
            s += 0.10*_sine(t,nf(mel))
            if beat>0:
                ph = (t*2.0)%1.0
                if ph<0.02:
                    s += beat*(1.0-ph/0.02)
            s = math.tanh(s) + (random.random()-0.5)*0.01
            env = min(1.0,t/0.5)*min(1.0,(seconds-t)/0.8)
            s *= env
            val = max(-1.0,min(1.0,s))
            wf.writeframes(struct.pack("<h", int(val*32767)))
    return buf.getvalue()
