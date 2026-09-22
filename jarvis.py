"""
J.A.R.V.I.S. - Python Virtual Desktop Voice Assistant
---------------------------------------------------
Features:
1. Speech Recognition (STT via microphone)
2. Text-to-Speech Voice Output (TTS via pyttsx3)
3. Gemini AI integration for intelligent QA (with REST API fallback)
4. Built-in system commands (time, date, open websites, web search, jokes)

Usage:
    python jarvis.py
"""

import os
import sys
import time
import datetime
import webbrowser
import json
import urllib.request
import urllib.parse

def load_env_file():
    """Load GEMINI_API_KEY from .env.local or .env file if present."""
    for env_filename in [".env.local", ".env"]:
        filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), env_filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, val = line.split("=", 1)
                            key = key.strip()
                            val = val.strip().strip('"').strip("'")
                            if key == "GEMINI_API_KEY" and val:
                                os.environ["GEMINI_API_KEY"] = val
                                return val
            except Exception as e:
                pass
    return os.getenv("GEMINI_API_KEY", "")

# Load environment variables on startup
load_env_file()

# Try importing speech_recognition
try:
    import speech_recognition as sr
except ImportError:
    sr = None
    print("[WARN] 'speech_recognition' module not found. Run: pip install SpeechRecognition")

# Try importing pyttsx3 for offline voice output
try:
    import pyttsx3
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    for voice in voices:
        if "david" in voice.name.lower() or "english" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break
    engine.setProperty('rate', 175)
except ImportError:
    engine = None
    print("[WARN] 'pyttsx3' module not found. Run: pip install pyttsx3")

# Try importing google.genai
try:
    from google import genai
    GEMINI_SDK_AVAILABLE = True
except ImportError:
    GEMINI_SDK_AVAILABLE = False


def speak(text: str):
    """Speak text using TTS engine and print to console."""
    print(f"\n[J.A.R.V.I.S.]: {text}")
    if engine:
        try:
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS Error]: {e}")


def listen() -> str:
    """Listen to microphone input and return transcribed text."""
    if not sr:
        return input("\n[You (Terminal Mode)]: ")

    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("\n[Listening... Speak into your microphone]")
        r.adjust_for_ambient_noise(source, duration=0.8)
        try:
            audio = r.listen(source, timeout=6, phrase_time_limit=10)
            print("[Processing audio...]")
            query = r.recognize_google(audio, language="en-US")
            print(f"[You Said]: {query}")
            return query
        except sr.WaitTimeoutError:
            print("[Timeout]: No speech detected.")
            return ""
        except sr.UnknownValueError:
            speak("I didn't quite catch that, Sir. Could you repeat?")
            return ""
        except sr.RequestError as e:
            speak("Speech recognition service is currently unavailable.")
            return ""
        except Exception as e:
            print(f"[Mic Error]: {e}")
            return ""


def ask_gemini_rest(prompt: str, api_key: str) -> str:
    """Fallback to direct Gemini REST API call using built-in urllib."""
    system_prompt = (
        "You are J.A.R.V.I.S., a polite, intelligent, and articulate virtual assistant. "
        "Address the user as Sir. Keep spoken answers concise (2 to 3 sentences maximum)."
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": f"{system_prompt}\nUser Question: {prompt}\nResponse:"}
                ]
            }
        ]
    }
    
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            res_body = json.loads(response.read().decode("utf-8"))
            candidates = res_body.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
    except Exception as e:
        return f"Sir, I encountered an issue querying the Gemini REST API: {e}"
        
    return "At your service, Sir. However, I didn't receive a response from my core."


def ask_gemini(prompt: str) -> str:
    """Send question to Gemini AI API (uses SDK if available, or REST API fallback)."""
    api_key = load_env_file()
    if not api_key:
        return "Sir, I require a valid GEMINI_API_KEY in .env.local to access full AI capabilities."

    if GEMINI_SDK_AVAILABLE:
        try:
            client = genai.Client(api_key=api_key)
            system_prompt = (
                "You are J.A.R.V.I.S., a polite, intelligent, and articulate virtual assistant. "
                "Address the user as Sir. Keep spoken answers concise (2 to 3 sentences maximum)."
            )
            full_query = f"{system_prompt}\nUser Question: {prompt}\nResponse:"
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_query,
            )
            return response.text.strip()
        except Exception as e:
            print(f"[SDK Fallback trigger]: {e}")

    # Fallback to direct REST API
    return ask_gemini_rest(prompt, api_key)


def process_command(command: str) -> bool:
    """Process user command. Returns False if user wants to exit."""
    if not command:
        return True

    cmd = command.lower().strip()

    # Exit Commands
    if any(k in cmd for k in ["exit", "quit", "stop", "goodbye", "bye jarvis"]):
        speak("Goodbye, Sir. System shutting down.")
        return False

    # Time Command
    elif "time" in cmd:
        now = datetime.datetime.now().strftime("%I:%M %p")
        speak(f"The current time is {now}, Sir.")

    # Date Command
    elif "date" in cmd or "today" in cmd:
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        speak(f"Today's date is {today}, Sir.")

    # Open Websites
    elif "open youtube" in cmd:
        speak("Opening YouTube, Sir.")
        webbrowser.open("https://youtube.com")
    elif "open google" in cmd:
        speak("Opening Google, Sir.")
        webbrowser.open("https://google.com")
    elif "open github" in cmd:
        speak("Opening GitHub, Sir.")
        webbrowser.open("https://github.com")

    # Search Web
    elif cmd.startswith("search for ") or cmd.startswith("google "):
        query = cmd.replace("search for ", "").replace("google ", "")
        speak(f"Searching Google for {query}, Sir.")
        webbrowser.open(f"https://www.google.com/search?q={query}")

    # General Question via Gemini AI
    else:
        speak("Processing your request, Sir...")
        answer = ask_gemini(command)
        speak(answer)

    return True


def main():
    speak("J.A.R.V.I.S. Python Assistant initialized. How may I help you today, Sir?")
    
    running = True
    while running:
        try:
            query = listen()
            if query:
                running = process_command(query)
            time.sleep(0.5)
        except KeyboardInterrupt:
            speak("Emergency shutoff initiated. Goodbye, Sir.")
            sys.exit(0)


if __name__ == "__main__":
    main()
