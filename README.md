# 🎵 MikaBox: The AI-Powered "Safety First" Smart Speaker for Kids
**A "Gemma 4 Good" Hackathon Submission**

![MikaBox Thumbnail](/Users/I743656/.gemini/antigravity/brain/8beb943b-8246-4eea-8504-b058d0e232a9/mikabox_thumbnail_v2_1778789821933.png)

MikaBox is a 100% open-source, privacy-first, edge-AI powered smart speaker and storytelling companion for children. Built as a smarter, safer alternative to commercial speakers (like the Toniebox or Amazon Echo), it uses **Gemma 4** to ensure your child's data never leaves the house while actively monitoring their digital and physical wellbeing.

---

## 🏆 Why "Gemma 4 Good"?

MikaBox goes far beyond playing music. It leverages the power of Gemma 4 to solve critical problems in pediatric digital wellbeing:

1. **🛡️ The "Safety Shield" (Intent Detection)**: Mika dynamically analyzes children's conversational intent. If a child suggests doing something dangerous (e.g. playing with fire, leaving the house, drinking chemicals), Gemma 4 instantly interrupts, firmly warns the child, and fires a real-time WebSocket alert to the parents' dashboard.
2. **🧠 Persistent RAG Memory**: Mika isn't a forgetful chatbot. She uses a **Retrieval-Augmented Generation (RAG)** pipeline to learn and recall personal facts about the child over months. By embedding knowledge locally with `sentence-transformers` and using lightning-fast cosine similarity, she provides a deeply personalized companion experience without hitting token limits.
3. **🎭 Active "Choose-Your-Own-Adventure" Learning**: Passive screen-time is detrimental to early brain development. Mika combats this by telling interactive, branching audio stories where the child must make decisions to move the plot forward.
4. **🌍 Zero-Shot Multilingualism**: Demonstrating Gemma 4's incredible native language capabilities, Mika automatically detects if a child speaks in English, German, or other languages. She instantly understands the context and seamlessly switches her spoken response to match the child's native tongue—perfect for bilingual households!
5. **🔒 Uncompromising Privacy**: Commercial smart speakers upload your child's voice to corporate clouds. MikaBox runs inference locally on your home server. Your child's voice, their data, and their memories never touch the public internet.

---

## ⚙️ Architecture Overview

```text
┌──────────────────────────┐     WiFi      ┌──────────────────────────────┐
│  MikaBox Device (Pi 4/5) │◄────────────►│  Home Server (Desktop/NAS)   │
│                          │               │                              │
│  • USB microphone        │  Voice audio  │  • Gemma 4 E2B (LiteRT-LM)  │
│  • Bluetooth speaker     │──────────────►│  • Speech-to-Text (Whisper)  │
│                          │  Commands     │  • Text-to-Speech (Piper)    │
│                          │◄──────────────│  • RAG Embeddings (MiniLM)   │
│                          │               │  • FastAPI Backend + SQLite  │
└──────────────────────────┘               └──────────────┬───────────────┘
                                                          │ WebSocket/HTTP
                                              ┌───────────▼───────────┐
                                              │  Companion Web App    │
                                              │  (React + Vite)       │
                                              │  • Safety Alerts      │
                                              │  • Mika's Memory Mgr  │
                                              │  • Content Library    │
                                              └───────────────────────┘
```

---

## 🚀 Key Technical Features

### 1. Lightweight RAG Memory at the Edge
Mika extracts facts from the child's speech and saves them. When the child speaks, Mika embeds the audio transcript into a 384-dimensional vector, searches the SQLite vector database using numpy cosine similarity, and injects the top 2 most relevant facts directly into Gemma 4's hidden context. 

### 2. Parent Dashboard Control
The React web app acts as a remote control and monitoring station. Parents can manage child profiles, control playback, set "Wind Down" bedtime hours, and review/delete facts from Mika's Memory.

---

## 🛠️ Quick Start

### 1. The Home Server (Backend & AI Inference)
*Runs on a PC, Mac, or home NAS.*
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Start the server and AI models
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 2. The Companion App (Frontend)
```bash
cd frontend
npm install
npm run dev
# Dashboard available at http://localhost:5173
```

### 3. The Physical Device (Raspberry Pi)
```bash
cd device
pip install -r requirements.txt

# Run the device firmware, pointing it to your Home Server
python -m mikabox --server-host <YOUR_SERVER_IP> --server-port 8000
```

---

## 🧰 Hardware BOM (Prototype Build)
| Component | Purpose | ~Cost |
|---|---|---|
| Raspberry Pi 4/5 (2GB+) | Main device computer | $45 |
| USB microphone | Voice input | $10 |
| Bluetooth Speaker | Sound output | $15 |

**Total Build Cost:** ~$70

---

## 🔮 Future Hardware Roadmap

While the current MVP focuses on establishing the AI intelligence and backend infrastructure, our physical roadmap includes upgrading the speaker chassis to support:
- **NFC Sticker Reader (PN532):** Allowing children to tap physical cards or toys to instantly trigger specific audio content or stories.
- **LED Ring (WS2812B):** Providing visual feedback for Mika's states (Listening, Thinking, Speaking, Error).

---

## 📜 License
MIT License. Built with ❤️ for the Gemma 4 Good Hackathon.
