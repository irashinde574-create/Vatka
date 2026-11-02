 🎙️ Vakta (वक्ता) — Zero-Typing Voice Super-App for Local Businesses

> **Built for the Sarvam AI Hackathon**  
> *Empowering micro-entrepreneurs, gig workers, and local vendors to run their entire business through natural Indic voice commands.*

---

## 📸 Overview

**Vakta** (meaning *Speaker* or *Voice* in Sanskrit/Hindi) is a voice-first business management tool designed for the millions of Indian micro-entrepreneurs, local service providers, and gig workers who prefer spoken conversation over typing or complex app interfaces. 

By leveraging **Sarvam AI’s cutting-edge Speech-to-Text and Bulbul Text-to-Speech APIs**, Vakta listens to natural, code-mixed conversations (e.g., Hinglish, Marathi + English), parses business intents into structured data, and outputs instant regional audio confirmations alongside digital invoices.

---

## 🌟 Key Features

* **🗣️ Code-Mixed Voice Capture:** Speak naturally in mixed regional languages (Hinglish, Marathi-English, Hindi, etc.). No need to speak rigid English or pause like a robot.
* **🧠 Automated Intent & Entity Extraction:** Automatically parses customer names, order items, delivery times, price amounts, and phone numbers directly into structured records.
* **🔊 Bulbul Regional Voice Output:** Generates natural, human-like voice responses in native Indian accents using Sarvam's Bulbul TTS to confirm orders back to the vendor or customer.
* **📊 Zero-Click Voice Ledger:** Organizes voice logs into an auto-updating dashboard with itemized breakdowns and daily totals.
* **📲 Multi-Channel Ready:** Pre-formats WhatsApp payment links and confirmation messages for 1-click sharing.
* **⚡ High-Friction Resilient:** Includes dynamic fallback handlers to ensure robust live demonstrations even under network latency.

---

## 🏗️ Architecture & Tech Stack

* **Frontend:** Mobile-first, single-page Web UI (HTML5 + Tailwind CSS + Web Audio API).
* **Backend:** Python FastAPI (`main.py`) orchestrating asynchronous workflows.
* **AI & Speech Engine:** 
  * **Sarvam AI STT (`saaras`):** Transcribes code-mixed Indian speech to text.
  * **Sarvam AI TTS (`bulbul`):** Converts structured text updates back into natural Indic speech.
  * **LLM Engine:** Extracts structured JSON payloads (intents, entities, amounts).

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.9+
- A valid **Sarvam AI API Key**

### 2. Installation & Setup

Clone the repository and install dependencies:
```bash
git clone https://github.com/your-username/vakta.git
cd vakta

pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```env
SARVAM_API_KEY=your_sarvam_api_key_here
```

### 4. Running the Application
Start the FastAPI server locally using `uvicorn`:
```bash
uvicorn main:app --reload
```
Open your browser and navigate to `http://localhost:8000`.

---

## 🧪 Demo Test Scenarios

### Scenario A: Code-Mixed Tiffin Order (Hinglish)
> **Input Speech:** *"Bhaiya, kal subah 10 baje ke liye 2 tiffin pack kar dena. Ek Jain meal, ek normal meal. Address 402 Sunshine Apartments, Kothrud hai. Unko bolo 300 rupees Google Pay pe bhej de."*  
> **Output Result:** 
> - **Parsed Entity:** 1x Jain Meal, 1x Normal Meal | Total: ₹300 | Delivery: Tomorrow 10:00 AM
> - **Bulbul TTS:** *"Order confirm ho gaya hai: 2 tiffin kal subah 10 baje Kothrud address par deliver honge..."*

### Scenario B: Auto Repair Shop (Marathi + English)
> **Input Speech:** *"Soham cha phone aala hota. Tyanchi Activa servicing sathi aali ahe. Front brake pad badlaycha ahe ani Monday sandhyakali 6 baje delivery pahije. Total bill 1800 rupaye banva."*  
> **Output Result:** 
> - **Parsed Entity:** Customer: Soham | Service: Activa Servicing + Front Brake Replacement | Total: ₹1800

---

## 📄 License
This project is open-source under the MIT License. Built with ❤️ for the Sarvam AI Hackathon.
