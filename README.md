# 🎬 LocalTube

A fast, modern, and lightweight local video streaming platform and browser that gives your offline video collection a familiar YouTube-like interface.

---

## ⚡ Quick Start (No Setup Required!)

LocalTube is packaged as a **standalone, zero-install portable application**. No Python, Node.js, or FFmpeg installation is needed on your computer.

### 📥 1-Click Download

Go to the [**Releases Page**](https://github.com/) and download the package for your OS:

- **Windows:** Download `LocalTube-Windows-x64.zip`
  - Unzip the folder and double-click `LocalTube.exe`.
  - Your default browser will automatically open to `http://localhost:8080`.
- **Linux:** Download `LocalTube-Linux-x64.tar.gz`
  - Extract and run `./LocalTube`.
- **macOS:** Download `LocalTube-macOS-x64.zip`
  - Extract and double-click `LocalTube`.

---

## 🐳 Docker / Homelab / NAS (1-Command Setup)

If you run a home server, Unraid, TrueNAS, CasaOS, or prefer Docker, LocalTube is completely containerized with FFmpeg pre-installed:

### Using Docker Compose (Recommended)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  localtube:
    image: ghcr.io/yourusername/localtube:latest
    container_name: localtube
    restart: unless-stopped
    ports:
      - "8080:8080"
    volumes:
      # Application data & cache
      - ./data:/app/backend/data
      # Mount your local video library folder (read-only):
      - /path/to/your/videos:/videos:ro
```

Run:
```bash
docker-compose up -d
```
Then visit `http://localhost:8080`.

---

## 🚀 Running from Source / Repository

If you cloned or downloaded this repository, you can launch LocalTube with a single script:

### Windows:
Simply double-click **`run.bat`**.
> *On first run, it will automatically detect Python, install dependencies, build the frontend, and open the app in your browser.*

### Linux / macOS:
```bash
./run.sh
```
> *On first run, it will set up the virtual environment, install requirements, and launch LocalTube.*

---

## ✨ Features

- **YouTube-Style Interface:** Familiar grid layout, responsive video cards, search, and theater mode.
- **Auto-Generated Thumbnails & Video Previews:** Hover previews generated efficiently using FFmpeg concat demuxing.
- **Fast Local Streaming:** Supports HTTP range requests for instant seeking in large media files.
- **Multi-Folder Library Scanning:** Scan multiple directories with real-time background task tracking.
- **Zero Configuration:** Works out of the box with zero external database setup (powered by SQLite).

---

## 🛠️ Development

If you want to contribute or modify LocalTube:

### 1. Backend Setup
```bash
cd backend
python -m venv venv

# On Windows:
venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --port 8080 --reload
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

## 📄 License

AGPL-3.0 license
