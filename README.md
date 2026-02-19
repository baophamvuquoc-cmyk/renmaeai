# RenmaeAI Studio

**AI-Powered Podcast to Video Production Desktop App**

Transform podcasts into professional videos with AI — auto-generate scripts, find stock footage, create voiceovers, add subtitles, and export ready-to-upload videos.

## ✨ Features

- **AI Script Generation** — Gemini-powered script creation from podcast content
- **Smart Footage Finder** — Auto-search Pexels & Pixabay for matching stock footage
- **Multi-Language TTS** — 100+ neural voices across 50+ languages (Edge TTS)
- **Auto Video Assembly** — Scene-synced visuals, transitions, subtitles
- **SEO Optimization** — AI-generated titles, descriptions, tags, thumbnails
- **Production Hub** — Manage, review, and export all your productions
- **100% Local** — Everything runs on your computer, no cloud processing fees

## 🚀 Quick Start

### Prerequisites

| Tool | Required Version | Download |
|------|-----------------|----------|
| **Python** | 3.10+ | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18+ | [nodejs.org](https://nodejs.org/) |
| **FFmpeg** | Any (optional) | [ffmpeg.org](https://ffmpeg.org/download.html) |

> ⚠️ **Python install:** Check **"Add Python to PATH"** during installation!

### Setup (One-Click)

```bash
# 1. Clone the repository
git clone https://github.com/baophamvuquoc-cmyk/renmaeai.git
cd renmaeai

# 2. Run the installer (creates venv, installs all dependencies)
INSTALL.bat

# 3. Add your API keys to backend\.env (see below)

# 4. Launch the app
START.bat
```

### API Keys (Free)

Edit `backend\.env` with your keys:

```env
GEMINI_API_KEY=your_key_here       # Required for AI features
PEXELS_API_KEY=your_key_here       # For stock footage search
PIXABAY_API_KEY=your_key_here      # For stock footage search
```

**Get free keys:**
- **Gemini**: [makersuite.google.com](https://makersuite.google.com/app/apikey)
- **Pexels**: [pexels.com/api](https://www.pexels.com/api/)
- **Pixabay**: [pixabay.com/api](https://pixabay.com/api/docs/)

## 📖 Usage

### Podcast Remake Workflow

1. **Import** — Paste a YouTube URL or select a local file
2. **Configure** — Choose presets, voice, language, and style
3. **Run Pipeline** — AI processes everything:
   - Script generation → Keyword extraction → Footage search → TTS voiceover → Video assembly
4. **Review** — Check output in Production Hub
5. **Export** — Download the final video with embedded SEO metadata

### Manual Mode

Run backend and frontend separately:

```bash
# Terminal 1: Backend
cd backend
..\.venv\Scripts\activate
python -m uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
npm run dev:web
```

App opens at: [http://localhost:5173](http://localhost:5173)

## 🏗️ Architecture

```
renmaeai/
├── INSTALL.bat              # One-click setup (run first)
├── START.bat                # Launch the app
├── RenmaeAI Studio.exe      # Alternative launcher
├── electron/                # Electron main process
├── src/                     # React + TypeScript frontend
│   ├── components/          # UI components (workflow steps)
│   ├── stores/              # Zustand state management
│   ├── contexts/            # React contexts (i18n, sync)
│   └── lib/                 # API client
├── backend/                 # Python FastAPI backend
│   ├── modules/             # Core logic (NLP, AI, footage, TTS)
│   ├── routes/              # API endpoints
│   └── prompts/             # AI prompt templates
├── scripts/
│   ├── build/               # Build scripts (PyInstaller, Electron)
│   ├── dev/                 # Dev mode scripts
│   └── launcher/            # Launcher source files
├── website/                 # Landing page (GitHub Pages)
└── docs/                    # Documentation
```

## 🛠️ Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | React, TypeScript, Vite, Zustand, TanStack Query, i18next |
| **Backend** | Python, FastAPI, Google Gemini AI, Edge TTS |
| **Video** | MoviePy, FFmpeg |
| **Desktop** | Electron |

## 📝 NPM Scripts

```bash
npm run dev          # Frontend + Electron (desktop)
npm run dev:web      # Frontend + Backend (web browser)
npm run build        # Build for production
npm run backend:dev  # Backend server only
```

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📄 License

MIT License

---

**Made with ❤️ by [RenmaeAI](https://baophamvuquoc-cmyk.github.io/renmaeai/)**
