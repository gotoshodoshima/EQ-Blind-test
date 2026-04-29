# EQ Shootout

This is a professional-grade Equalizer Blind Test application built with Electron. It allows users to compare different EQ profiles blindly and rank them using the advanced Glicko-2 rating system, powered by next-generation machine learning loudness normalization.

## 🚀 Key Features

*   **Neuro-LUFS Normalization (Machine Learning):** Uses a pre-trained neural network model (`model_weights.json`) to analyze Power Spectral Density (PSD) and EQ frequency response, instantly predicting and matching loudness in O(1) time. This perfectly eliminates volume bias during A/B testing.
*   **Glicko-2 Rating System:** An accurate, competitive ranking system that evaluates EQ profiles based on rating, RD (Rating Deviation), and Volatility. Features rating progression graphs and league tables.
*   **State Persistence:** Your uploaded playlists, EQ profiles, and match history are automatically saved and restored across sessions.
*   **Advanced Playback Controls:** Set custom playback start positions to skip intros and maintain focus during A/B switching.
*   **Visual EQ Editor:** Import Equalizer APO text or adjust frequency bands using an intuitive UI visual editor.
*   **Modern UI/UX:** Features a sleek dark/light mode toggle, custom auto-hiding titlebar, dynamic audio visualizer, and an elegant layout.

## ⚠️ System Requirements (For Neuro-LUFS)

To use the flagship **Neuro-LUFS** normalization feature, the application requires Python to analyze the frequency response of imported audio files.

1.  Ensure **Python** is installed on your system and added to your PATH.
2.  Install the required Python libraries by running:
    ```bash
    pip install numpy scipy soundfile pyloudnorm
    ```

*Note: If Python is not installed, you can still use the app by going to the Setup tab and changing the Normalization Method to **"Legacy RMS (Offline Render)"**.*

## 🎧 How to Use

1.  **Setup:** Import your EQ profiles (Equalizer APO format) or create new ones using the visual editor. Ensure at least two profiles are active.
2.  **Upload:** Load your reference audio files. You can manage your playlist and set custom playback start points.
3.  **Test:** Click "Play A" and "Play B" to compare the hidden EQ profiles, then vote for your preference (or Tie).
4.  **Results:** Check the Ranking, Match History, and League Table to see which EQ performs the best. Export results as JSON, CSV, or PNG images.

## 💻 For Developers

To run this application locally from the source code:

1.  Clone the repository.
2.  Ensure you have the required libraries in the `/libs` folder (React, Tailwind, Lucide, Babel).
3.  Run `npm install` to install Electron dependencies.
4.  Run `npm start` to launch the application.

### Building an Executable

To build a standalone Windows executable (`.exe`):
```bash
npm run dist
```
The installer will be generated in the `dist/` directory.

### Training the Neuro-LUFS Model
If you wish to retrain the neural network model, use the provided `trainer.py` script. The resulting `model_weights.json` will be automatically loaded by the application.