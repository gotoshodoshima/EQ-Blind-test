import os
import glob
import json
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import scipy.signal as signal
import soundfile as sf
import pyloudnorm as pyln

def get_biquad_coeffs(eq_type, f0, fs, Q, gainDB):
    A = 10 ** (gainDB / 40)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * Q)
    
    if eq_type == 'peaking':
        b0 = 1 + alpha * A
        b1 = -2 * np.cos(w0)
        b2 = 1 - alpha * A
        a0 = 1 + alpha / A
        a1 = -2 * np.cos(w0)
        a2 = 1 - alpha / A
    elif eq_type == 'lowshelf':
        b0 = A * ((A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 = 2 * A * ((A - 1) - (A + 1) * np.cos(w0))
        b2 = A * ((A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 = -2 * ((A - 1) + (A + 1) * np.cos(w0))
        a2 = (A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
    elif eq_type == 'highshelf':
        b0 = A * ((A + 1) + (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha)
        b1 = -2 * A * ((A - 1) + (A + 1) * np.cos(w0))
        b2 = A * ((A + 1) + (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha)
        a0 = (A + 1) - (A - 1) * np.cos(w0) + 2 * np.sqrt(A) * alpha
        a1 = 2 * ((A - 1) - (A + 1) * np.cos(w0))
        a2 = (A + 1) - (A - 1) * np.cos(w0) - 2 * np.sqrt(A) * alpha
    else:
        raise ValueError(f"Unknown eq_type: {eq_type}")
        
    return [b0/a0, b1/a0, b2/a0], [1.0, a1/a0, a2/a0]

def calculate_eq_response(bands, fs, num_bins=63):
    # Calculate freq response at 63 log-spaced frequencies from 20Hz to 20kHz
    freqs = np.logspace(np.log10(20), np.log10(20000), num=num_bins)
    w = 2 * np.pi * freqs / fs
    total_response = np.zeros(num_bins)
    
    for band in bands:
        b, a = get_biquad_coeffs(band['type'], band['freq'], fs, band['q'], band['gain'])
        _, h = signal.freqz(b, a, worN=w)
        total_response += 20 * np.log10(np.abs(h) + 1e-10)
        
    return freqs, total_response

def process_file(file_path, meter, fs=44100, num_augmentations=10):
    data, rate = sf.read(file_path)
    if len(data.shape) > 1:
        data = data.mean(axis=1) # mix to mono for analysis simplicity
    
    if rate != fs:
        # Resample logic omitted for brevity; assume 44.1k or 48k is close enough for LUFS estimate
        pass
    
    # Trim to 10 seconds to speed up
    if len(data) > rate * 10:
        start = len(data) // 2 - rate * 5
        data = data[start:start+rate*10]
        
    true_lufs = meter.integrated_loudness(data)
    if np.isinf(true_lufs):
        return []
        
    # Calculate PSD (Welch)
    f, Pxx = signal.welch(data, fs=rate, nperseg=4096)
    target_freqs = np.logspace(np.log10(20), np.log10(20000), num=64)
    # Interpolate PSD to log bins
    psd_interp = np.interp(target_freqs, f, 10 * np.log10(Pxx + 1e-10))
    
    dataset_rows = []
    
    for _ in range(num_augmentations):
        # Generate random EQ
        num_bands = np.random.randint(1, 6)
        bands = []
        for _ in range(num_bands):
            bands.append({
                'type': np.random.choice(['peaking', 'lowshelf', 'highshelf']),
                'freq': np.random.uniform(50, 15000),
                'q': np.random.uniform(0.1, 5.0),
                'gain': np.random.uniform(-15.0, 15.0)
            })
            
        _, eq_resp = calculate_eq_response(bands, rate, num_bins=63)
        
        # Apply EQ
        filtered_data = data.copy()
        for band in bands:
            b, a = get_biquad_coeffs(band['type'], band['freq'], rate, band['q'], band['gain'])
            filtered_data = signal.lfilter(b, a, filtered_data)
            
        eq_lufs = meter.integrated_loudness(filtered_data)
        if np.isinf(eq_lufs):
            continue
            
        delta_lufs = eq_lufs - true_lufs
        
        # X: psd(64) + true_lufs(1) + eq_resp(63)
        X = np.concatenate([psd_interp, [true_lufs], eq_resp])
        Y = np.array([delta_lufs])
        dataset_rows.append((X, Y))
        
    return dataset_rows

class NeuroLUFSMLP(nn.Module):
    def __init__(self):
        super(NeuroLUFSMLP, self).__init__()
        self.net = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
    def forward(self, x):
        return self.net(x)

def main():
    parser = argparse.ArgumentParser(description="Neuro-LUFS Offline Trainer")
    parser.add_argument("--dataset_dir", type=str, required=True, help="Directory containing audio files for training")
    parser.add_argument("--output", type=str, default="model_weights.json", help="Output weights JSON file")
    parser.add_argument("--epochs", type=int, default=50, help="Number of training epochs")
    args = parser.parse_args()

    print(f"Scanning {args.dataset_dir} for audio files...")
    extensions = ('*.wav', '*.flac', '*.mp3', '*.ogg')
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(args.dataset_dir, '**', ext), recursive=True))
        
    if not files:
        print("No audio files found.")
        return

    meter = pyln.Meter(44100) # assume 44.1k for training baseline
    X_all, Y_all = [], []
    
    print(f"Generating dataset from {len(files)} files...")
    for i, file_path in enumerate(files):
        try:
            rows = process_file(file_path, meter)
            for X, Y in rows:
                X_all.append(X)
                Y_all.append(Y)
            if (i+1) % 10 == 0:
                print(f"Processed {i+1}/{len(files)}")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    if not X_all:
        print("Dataset is empty. Aborting.")
        return

    X_tensor = torch.tensor(np.array(X_all), dtype=torch.float32)
    Y_tensor = torch.tensor(np.array(Y_all), dtype=torch.float32)

    # Normalize X
    X_mean = X_tensor.mean(dim=0)
    X_std = X_tensor.std(dim=0)
    X_std[X_std < 1e-5] = 1.0 # prevent division by zero
    X_norm = (X_tensor - X_mean) / X_std

    dataset = TensorDataset(X_norm, Y_tensor)
    loader = DataLoader(dataset, batch_size=32, shuffle=True)

    model = NeuroLUFSMLP()
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001)

    print("Training model...")
    for epoch in range(args.epochs):
        epoch_loss = 0.0
        for batch_X, batch_Y in loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_Y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item()
            
        if (epoch+1) % 10 == 0:
            print(f"Epoch {epoch+1}/{args.epochs}, Loss: {epoch_loss/len(loader):.4f}")

    print("Exporting model weights...")
    weights_export = {
        "mean": X_mean.tolist(),
        "std": X_std.tolist(),
        "layers": []
    }
    
    for layer in model.net:
        if isinstance(layer, nn.Linear):
            weights_export["layers"].append({
                "weight": layer.weight.detach().numpy().tolist(),
                "bias": layer.bias.detach().numpy().tolist(),
                "activation": "relu" if layer != model.net[-1] else "linear"
            })
            
    with open(args.output, 'w') as f:
        json.dump(weights_export, f)
        
    print(f"Weights successfully saved to {args.output}")

if __name__ == "__main__":
    main()
