import sys
import json
import numpy as np
import scipy.signal as signal
import soundfile as sf
import pyloudnorm as pyln

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No file path provided."}))
        sys.exit(1)
        
    file_path = sys.argv[1]
    
    try:
        data, rate = sf.read(file_path)
        if len(data.shape) > 1:
            data = data.mean(axis=1) # mix to mono
            
        meter = pyln.Meter(rate)
        true_lufs = meter.integrated_loudness(data)
        
        # Trim to 10 seconds for faster PSD computation if needed
        # but let's do the whole file if it's not too long, or limit to 30s.
        if len(data) > rate * 30:
            start = len(data) // 2 - rate * 15
            data = data[start:start+rate*30]
            
        f, Pxx = signal.welch(data, fs=rate, nperseg=4096)
        target_freqs = np.logspace(np.log10(20), np.log10(20000), num=64)
        psd_interp = np.interp(target_freqs, f, 10 * np.log10(Pxx + 1e-10))
        
        result = {
            "true_lufs": float(true_lufs),
            "psd": psd_interp.tolist()
        }
        
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

if __name__ == "__main__":
    main()
