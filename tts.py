import pyttsx3
import threading

def speak(text):
    """
    Convert text to speech using pyttsx3
    """
    def speak_in_thread():
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")
    
    # Run TTS in a separate thread to avoid blocking
    thread = threading.Thread(target=speak_in_thread)
    thread.daemon = True
    thread.start()