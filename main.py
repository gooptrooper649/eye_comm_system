import cv2
import mediapipe as mp
import tkinter as tk
from tkinter import Canvas
from PIL import Image, ImageTk
import pyttsx3
import threading
import time
from collections import deque
import numpy as np

print("🚀 EYE TRACKING COMMUNICATION SYSTEM - SENTENCE MODE ENHANCED")
print("=" * 60)

# ---------------- CAMERA INITIALIZATION ----------------
print("📹 Initializing camera...")
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("❌ Cannot open camera 0, trying camera 1...")
    cap = cv2.VideoCapture(1)
    if not cap.isOpened():
        print("❌ No cameras available")
        exit(1)

print("✅ Camera initialized")

# ---------------- MEDIAPIPE INITIALIZATION ----------------
print("🧠 Initializing MediaPipe...")
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Eye tracking landmarks
LEFT_EYE = [33, 133, 159, 145]
RIGHT_EYE = [362, 263, 386, 374]
LEFT_IRIS_POINTS = [474, 475, 476, 477]
RIGHT_IRIS_POINTS = [469, 470, 471, 472]

print("✅ MediaPipe initialized")

# ---------------- TTS SYSTEM ----------------
def speak(text):
    """Non-blocking TTS function"""
    def run():
        try:
            engine = pyttsx3.init()
            engine.setProperty('rate', 150)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"TTS Error: {e}")
    
    threading.Thread(target=run, daemon=True).start()

print("✅ TTS system initialized")

# ---------------- SENTENCE MODE DATA STRUCTURE ----------------
sentence_tree = {
    "root": ["I want", "I need", "I have", "I feel", "I want to talk"],
    
    "I want": ["water", "food", "help", "to sleep", "to sit", "to turn over"],
    
    "I need": ["doctor", "nurse", "medicine", "help", "to talk"],
    
    "I have": ["pain"],
    
    "pain": ["in chest", "in head", "in back", "in shoulder", "in legs"],
    
    "I feel": ["happy", "sad", "anxious", "tired", "scared"],
    
    "I want to talk": ["wife", "husband", "mother", "father", "nurse", "doctor"]
}

# ---------------- GAZE TRACKING ----------------
class GazeTracker:
    def __init__(self):
        self.ratio_history = deque(maxlen=20)
        self.direction_history = deque(maxlen=10)
        self.last_switch_time = 0
        self.left_threshold = 0.25
        self.right_threshold = 0.75
        self.current_stable_direction = "CENTER"
        self.blink_history = deque(maxlen=5)
        self.cursor_history = deque(maxlen=5)
        self.last_valid_ratio = 0.5

    def smooth_ratio(self, ratio):
        self.ratio_history.append(ratio)
        return np.mean(self.ratio_history)

    def get_direction(self, ratio):
        if ratio < self.left_threshold:
            return "LEFT"
        elif ratio > self.right_threshold:
            return "RIGHT"
        else:
            return "CENTER"

    def get_stable_direction(self, ratio):
        smooth = self.smooth_ratio(ratio)
        direction = self.get_direction(smooth)
        self.direction_history.append(direction)

        if len(self.direction_history) >= 8:
            direction_count = self.direction_history.count(direction)
            confidence = direction_count / len(self.direction_history)
            
            if confidence >= 0.7 and time.time() - self.last_switch_time > 1.0:
                if direction != self.current_stable_direction:
                    self.current_stable_direction = direction
                    self.last_switch_time = time.time()
                    return direction

        return self.current_stable_direction if self.current_stable_direction != "CENTER" else None

    def eye_aspect_ratio(self, landmarks):
        top = landmarks[159].y if len(landmarks) > 159 else 0.5
        bottom = landmarks[145].y if len(landmarks) > 145 else 0.5
        left = landmarks[33].x if len(landmarks) > 33 else 0.3
        right = landmarks[133].x if len(landmarks) > 133 else 0.7

        vertical = abs(top - bottom)
        horizontal = abs(left - right)

        if horizontal == 0:
            return 1
        return vertical / horizontal

    def detect_blink(self, landmarks):
        ear = self.eye_aspect_ratio(landmarks)
        blink = ear < 0.18
        self.blink_history.append(blink)
        return self.blink_history.count(True) >= 3

    def get_pupil_center(self, landmarks, iris_indices):
        x = np.mean([landmarks[i].x for i in iris_indices if len(landmarks) > i])
        y = np.mean([landmarks[i].y for i in iris_indices if len(landmarks) > i])
        return x, y

    def get_gaze_ratio(self, landmarks):
        try:
            # LEFT eye
            left_outer = landmarks[33].x if len(landmarks) > 33 else 0.3
            left_inner = landmarks[133].x if len(landmarks) > 133 else 0.7
            pupil_left_x, _ = self.get_pupil_center(landmarks, LEFT_IRIS_POINTS)
            left_width = left_inner - left_outer
            if abs(left_width) < 0.001:
                return None
            left_ratio = (pupil_left_x - left_outer) / left_width

            # RIGHT eye
            right_outer = landmarks[362].x if len(landmarks) > 362 else 0.7
            right_inner = landmarks[263].x if len(landmarks) > 263 else 0.3
            pupil_right_x, _ = self.get_pupil_center(landmarks, RIGHT_IRIS_POINTS)
            right_width = right_inner - right_outer
            if abs(right_width) < 0.001:
                return None
            right_ratio = (pupil_right_x - right_outer) / right_width

            ratio = (left_ratio + right_ratio) / 2
            return max(0.0, min(1.0, ratio))

        except Exception as e:
            return None

    def process_frame(self, frame):
        """Process frame and return gaze data with visualizations"""
        h, w, _ = frame.shape
        
        # Create debug frame
        debug_frame = frame.copy()
        debug_frame = cv2.GaussianBlur(debug_frame, (5, 5), 0)
        
        # Convert to RGB for MediaPipe
        rgb = cv2.cvtColor(debug_frame, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        gaze = "CENTER"
        blink = False
        ratio = self.last_valid_ratio
        direction = "CENTER"

        if result.multi_face_landmarks:
            for face_landmarks in result.multi_face_landmarks:
                landmarks = face_landmarks.landmark
                
                if len(landmarks) >= 468:
                    # Calculate gaze ratio
                    current_ratio = self.get_gaze_ratio(landmarks)
                    if current_ratio is not None:
                        self.last_valid_ratio = current_ratio
                        ratio = current_ratio
                        direction = self.get_stable_direction(ratio)
                        if direction:
                            gaze = direction

                    # Detect blink
                    blink = self.detect_blink(landmarks)

                    # Draw visualizations
                    self.draw_visualizations(debug_frame, landmarks, w, h, ratio, direction, gaze, blink)

        return gaze, blink, debug_frame

    def draw_visualizations(self, frame, landmarks, w, h, ratio, direction, gaze, blink):
        """Draw eye tracking visualizations on frame"""
        try:
            # Draw eye boundaries and pupils
            left_outer = landmarks[33].x if len(landmarks) > 33 else 0.3
            left_inner = landmarks[133].x if len(landmarks) > 133 else 0.7
            left_y = int(landmarks[145].y * h) if len(landmarks) > 145 else int(h/2)
            
            pupil_left_x, pupil_left_y = self.get_pupil_center(landmarks, LEFT_IRIS_POINTS)
            
            if len(landmarks) > 469:
                right_outer = landmarks[362].x
                right_inner = landmarks[263].x
                right_y = int(landmarks[374].y * h) if len(landmarks) > 374 else left_y
                pupil_right_x, pupil_right_y = self.get_pupil_center(landmarks, RIGHT_IRIS_POINTS)
            else:
                right_outer = 1.0 - left_outer
                right_inner = 1.0 - left_inner
                right_y = left_y
                pupil_right_x = 1.0 - pupil_left_x
                pupil_right_y = pupil_left_y
            
            # Convert to pixel coordinates
            left_outer_px = int(left_outer * w)
            left_inner_px = int(left_inner * w)
            pupil_left_px = int(pupil_left_x * w)
            pupil_left_py = int(pupil_left_y * h)
            
            right_outer_px = int(right_outer * w)
            right_inner_px = int(right_inner * w)
            pupil_right_px = int(pupil_right_x * w)
            pupil_right_py = int(pupil_right_y * h)
            
            # Draw LEFT eye
            cv2.line(frame, (left_outer_px, left_y), (left_inner_px, left_y), (255, 0, 0), 2)
            cv2.circle(frame, (pupil_left_px, pupil_left_py), 6, (255, 255, 0), -1)
            cv2.circle(frame, (pupil_left_px, pupil_left_py), 8, (0, 255, 255), 2)
            
            # Draw RIGHT eye
            cv2.line(frame, (right_outer_px, right_y), (right_inner_px, right_y), (255, 0, 0), 2)
            cv2.circle(frame, (pupil_right_px, pupil_right_py), 6, (255, 255, 0), -1)
            cv2.circle(frame, (pupil_right_px, pupil_right_py), 8, (0, 255, 255), 2)
            
            # Draw gaze cursor
            if ratio is not None:
                self.cursor_history.append(ratio)
                smooth_ratio = sum(self.cursor_history) / len(self.cursor_history)
                cursor_x = int(smooth_ratio * w)
                cursor_y = h // 2
                
                cv2.circle(frame, (cursor_x, cursor_y), 15, (0, 255, 255), 2)
                cv2.circle(frame, (cursor_x, cursor_y), 10, (255, 255, 255), -1)
                cv2.circle(frame, (cursor_x, cursor_y), 3, (0, 0, 255), -1)
            
            # Draw gaze direction arrow
            center_x = w // 2
            center_y = h // 2
            if direction == "LEFT":
                cv2.arrowedLine(frame, (center_x, center_y), (center_x - 100, center_y), (0, 255, 0), 3)
            elif direction == "RIGHT":
                cv2.arrowedLine(frame, (center_x, center_y), (center_x + 100, center_y), (0, 255, 0), 3)
            else:
                cv2.circle(frame, (center_x, center_y), 10, (255,255,0), -1)
            
            # Draw ratio bar
            bar_x = 50
            bar_y = 400
            bar_width = 300
            bar_height = 20
            
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (200, 200, 200), -1)
            fill = int(bar_width * ratio) if ratio is not None else 0
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill, bar_y + bar_height), (0, 255, 0), -1)
            cv2.line(frame, (bar_x + int(bar_width * 0.35), bar_y), (bar_x + int(bar_width * 0.35), bar_y + bar_height), (0, 0, 255), 2)
            cv2.line(frame, (bar_x + int(bar_width * 0.65), bar_y), (bar_x + int(bar_width * 0.65), bar_y + bar_height), (0, 0, 255), 2)
            
            # Add text information
            cv2.putText(frame, f"Gaze: {gaze}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, f"Blink: {'YES' if blink else 'NO'}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, f"Ratio: {ratio:.2f}" if ratio is not None else "Ratio: --", (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            
        except Exception as e:
            pass  # Silently handle visualization errors

# Initialize gaze tracker
gaze_tracker = GazeTracker()
print("✅ Gaze tracking engine initialized")

# ---------------- MODE MANAGEMENT ----------------
class ModeManager:
    def __init__(self):
        self.current_mode = "quick"  # "quick" or "sentence"
        self.sentence_state = "root"
        self.sentence_words = []
        self.numbered_options = {}
        
    def reset_sentence_mode(self):
        self.sentence_state = "root"
        self.sentence_words = []
        self.numbered_options = {}

# Button selection delay system
class ButtonDelayManager:
    def __init__(self):
        self.selection_delay = 3.0  # seconds to stay on button before selection
        self.selection_start_time = {}
        self.current_button_index = None
        
    def start_selection_timer(self, button_index):
        """Start timer for button selection"""
        current_time = time.time()
        self.current_button_index = button_index
        self.selection_start_time[button_index] = current_time
        return current_time
    
    def should_select(self, button_index):
        """Check if button should be selected (delay passed)"""
        if button_index not in self.selection_start_time:
            return False
        
        current_time = time.time()
        elapsed = current_time - self.selection_start_time[button_index]
        return elapsed >= self.selection_delay
    
    def get_remaining_time(self, button_index):
        """Get remaining time before selection"""
        if button_index not in self.selection_start_time:
            return self.selection_delay
        
        current_time = time.time()
        elapsed = current_time - self.selection_start_time[button_index]
        remaining = self.selection_delay - elapsed
        return max(0, remaining)
    
    def reset_timer(self, button_index=None):
        """Reset selection timer"""
        if button_index is None:
            self.selection_start_time.clear()
            self.current_button_index = None
        elif button_index in self.selection_start_time:
            del self.selection_start_time[button_index]

# Initialize managers
mode_manager = ModeManager()
delay_manager = ButtonDelayManager()
print("✅ Mode manager initialized")
print("✅ Button delay manager initialized")

# ---------------- GUI INITIALIZATION ----------------
print("🖥️ Initializing GUI...")
root = tk.Tk()
root.title("Eye Tracking Communication System - Sentence Mode Enhanced")
root.geometry("1200x700")
root.configure(bg="#f0f0f0")

# Main container
main_frame = tk.Frame(root, bg="#f0f0f0")
main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

# Left side - Camera feed
left_frame = tk.Frame(main_frame, bg="#f0f0f0")
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

tk.Label(left_frame, text="Camera Feed", font=("Arial", 16, "bold"), bg="#f0f0f0").pack(pady=10)
camera_canvas = Canvas(left_frame, width=640, height=480, bg="black", highlightthickness=2, highlightbackground="blue")
camera_canvas.pack(pady=10)

# Eye movement signals
signals_frame = tk.Frame(left_frame, bg="#f0f0f0")
signals_frame.pack(pady=10)

gaze_label = tk.Label(signals_frame, text="Gaze: CENTER", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="blue")
gaze_label.pack(side=tk.LEFT, padx=10)

blink_label = tk.Label(signals_frame, text="Blink: NO", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="red")
blink_label.pack(side=tk.LEFT, padx=10)

# Mode indicator
mode_label = tk.Label(left_frame, text="Mode: QUICK", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="green")
mode_label.pack(pady=5)

# Right side - Communication buttons
right_frame = tk.Frame(main_frame, bg="#f0f0f0")
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# Title label
title_label = tk.Label(right_frame, text="Communication Options", font=("Arial", 16, "bold"), bg="#f0f0f0")
title_label.pack(pady=10)

# Sentence display (initially hidden)
sentence_frame = tk.Frame(right_frame, bg="#f0f0f0")
sentence_label = tk.Label(sentence_frame, text="Sentence: ", font=("Arial", 14, "bold"), bg="#f0f0f0", fg="darkblue", wraplength=400)
sentence_label.pack(pady=10)

# Button grid
button_container = tk.Frame(right_frame, bg="#f0f0f0")
button_container.pack(expand=True, fill=tk.BOTH)

# Quick mode buttons
quick_buttons_text = [
    "Food", "Water", "Help",
    "Yes", "No", "Washroom", 
    "Pain", "Sentence Mode"
]

# Keyboard button mapping for quick mode
quick_button_map = {
    "1": "Food",
    "2": "Water", 
    "3": "Help",
    "4": "Yes",
    "5": "No",
    "6": "Washroom",
    "7": "Pain",
    "8": "Sentence Mode"
}

buttons = []
selected_row = 0
selected_col = 0
last_blink_time = 0
last_gaze_move_time = 0

def highlight_buttons():
    """Highlight selected button with delay progress"""
    global selected_row, selected_col
    
    for i, btn in enumerate(buttons):
        current_index = (selected_row * 3) + selected_col
        
        if i == current_index:
            # Check if delay is active
            remaining_time = delay_manager.get_remaining_time(i)
            
            if remaining_time > 0:
                # Show progress with color intensity
                progress = 1.0 - (remaining_time / delay_manager.selection_delay)
                red_intensity = int(255 * progress)
                bg_color = f"#{red_intensity:02x}0000"
                btn.config(bg=bg_color, fg="white", font=("Arial", 16, "bold"))
                
                # Update button text to show countdown
                original_text = btn.cget("text")
                if '\n' in original_text:
                    base_text = original_text.split('\n', 1)[1]
                else:
                    base_text = original_text
                
                if remaining_time < 1.0:
                    countdown_text = f"{i+1}\n{base_text}\n{remaining_time:.1f}s"
                else:
                    countdown_text = f"{i+1}\n{base_text}"
                
                btn.config(text=countdown_text)
            else:
                # Fully selected - ready to activate
                btn.config(bg="red", fg="white", font=("Arial", 16, "bold"))
                
                # Restore original text
                original_text = btn.cget("text")
                if '\n' in original_text:
                    base_text = original_text.split('\n', 1)[1]
                    if '\n' in base_text:
                        base_text = base_text.split('\n', 1)[0]
                else:
                    base_text = original_text
                
                if '\n' not in base_text and i+1 <= 9:
                    display_text = f"{i+1}\n{base_text}"
                else:
                    display_text = base_text
                
                btn.config(text=display_text)
        else:
            # Restore normal appearance
            original_text = btn.cget("text")
            if '\n' in original_text:
                base_text = original_text.split('\n', 1)[1]
                if '\n' in base_text:
                    base_text = base_text.split('\n', 1)[0]
            else:
                base_text = original_text
            
            # Restore proper format
            if mode_manager.current_mode == "sentence":
                # Check if this is a control button
                options = sentence_tree.get(mode_manager.sentence_state, []) + ["Speak", "Back", "Clear", "Exit"]
                if i < len(options) and options[i] in ["Speak", "Back", "Clear", "Exit"]:
                    if '\n' not in base_text and i+1 <= 9:
                        display_text = f"{i+1}\n{base_text}"
                    else:
                        display_text = base_text
                    btn.config(bg="orange", fg="white", font=("Arial", 12, "bold"))
                else:
                    if '\n' not in base_text and i+1 <= 9:
                        display_text = f"{i+1}\n{base_text}"
                    else:
                        display_text = base_text
                    btn.config(bg="lightgreen", fg="black", font=("Arial", 12, "bold"))
            else:
                # Quick mode
                if '\n' not in base_text and i+1 <= 8:
                    display_text = f"{i+1}\n{base_text}"
                else:
                    display_text = base_text
                btn.config(bg="lightblue", fg="black", font=("Arial", 14, "bold"))
            
            btn.config(text=display_text)

def select_quick_button():
    """Handle quick mode button selection"""
    current_index = selected_row * 3 + selected_col
    if current_index < len(quick_buttons_text):
        text = quick_buttons_text[current_index]
        print(f"Selected: {text}")
        
        if text == "Sentence Mode":
            switch_to_sentence_mode()
        else:
            speak(text)
            print(f"🗣️ Spoken: '{text}'")

def handle_sentence_selection(choice):
    """Handle sentence mode selection"""
    global selected_row, selected_col
    
    print(f"Sentence selection: {choice}")
    
    if choice == "Speak":
        if mode_manager.sentence_words:
            sentence = " ".join(mode_manager.sentence_words)
            speak(sentence)
            print(f"🗣️ Spoken sentence: '{sentence}'")
        return
    
    elif choice == "Back":
        if mode_manager.sentence_words:
            mode_manager.sentence_words.pop()
            # Simple state reset
            if len(mode_manager.sentence_words) == 0:
                mode_manager.sentence_state = "root"
            else:
                # Try to find appropriate state based on last word
                last_word = mode_manager.sentence_words[-1]
                if last_word in sentence_tree:
                    mode_manager.sentence_state = last_word
                else:
                    mode_manager.sentence_state = "root"
        update_sentence_display()
        render_sentence_options()
        return
    
    elif choice == "Clear":
        mode_manager.reset_sentence_mode()
        update_sentence_display()
        render_sentence_options()
        return
    
    elif choice == "Exit":
        switch_to_quick_mode()
        return
    
    # NORMAL WORD SELECTION
    mode_manager.sentence_words.append(choice)
    
    # MOVE STATE
    if choice in sentence_tree:
        mode_manager.sentence_state = choice
    elif choice == "pain":
        mode_manager.sentence_state = "pain"
    else:
        mode_manager.sentence_state = "root"
    
    update_sentence_display()
    render_sentence_options()

def render_sentence_options():
    """Render sentence mode buttons"""
    global buttons, selected_row, selected_col
    
    # Clear existing buttons
    for btn in buttons:
        btn.destroy()
    buttons.clear()
    
    # Get options for current state
    options = sentence_tree.get(mode_manager.sentence_state, [])
    
    # Add control buttons (always at the end)
    options += ["Speak", "Back", "Clear", "Exit"]
    
    # Limit to 9 buttons max
    options = options[:9]
    
    # Create numbered options mapping
    mode_manager.numbered_options.clear()
    for i, option in enumerate(options):
        key = str(i + 1)
        mode_manager.numbered_options[key] = option
    
    # Create buttons
    for i, option in enumerate(options):
        row = i // 3
        col = i % 3
        
        # Add number prefix
        display_text = f"{i+1}\n{option}"
        
        # Different styling for control buttons
        if option in ["Speak", "Back", "Clear", "Exit"]:
            btn = tk.Button(button_container, text=display_text, font=("Arial", 12, "bold"), 
                          width=12, height=3, bg="orange", fg="white",
                          relief=tk.RAISED, bd=2)
        else:
            btn = tk.Button(button_container, text=display_text, font=("Arial", 12, "bold"), 
                          width=12, height=3, bg="lightgreen", fg="black",
                          relief=tk.RAISED, bd=2)
        
        btn.grid(row=row, column=col, padx=15, pady=15)
        buttons.append(btn)
    
    # Reset selection
    selected_row = 0
    selected_col = 0
    highlight_buttons()

def render_quick_options():
    """Render quick mode buttons"""
    global buttons, selected_row, selected_col
    
    # Clear existing buttons
    for btn in buttons:
        btn.destroy()
    buttons.clear()
    
    # Create quick mode buttons
    for i, text in enumerate(quick_buttons_text):
        row = i // 3
        col = i % 3
        
        # Add number prefix
        button_number = i + 1
        if button_number <= 8:
            display_text = f"{button_number}\n{text}"
        else:
            display_text = text
        
        btn = tk.Button(button_container, text=display_text, font=("Arial", 14, "bold"), 
                      width=12, height=4, bg="lightblue", fg="black",
                      relief=tk.RAISED, bd=2)
        btn.grid(row=row, column=col, padx=15, pady=15)
        buttons.append(btn)
    
    # Reset selection
    selected_row = 0
    selected_col = 0
    highlight_buttons()

def switch_to_sentence_mode():
    """Switch to sentence mode"""
    mode_manager.current_mode = "sentence"
    mode_manager.reset_sentence_mode()
    
    # Update UI
    title_label.config(text="Sentence Mode")
    mode_label.config(text="Mode: SENTENCE", fg="blue")
    sentence_frame.pack(pady=5, before=button_container)
    
    update_sentence_display()
    render_sentence_options()
    
    print("🔄 Switched to SENTENCE MODE")

def switch_to_quick_mode():
    """Switch to quick mode"""
    mode_manager.current_mode = "quick"
    
    # Update UI
    title_label.config(text="Communication Options")
    mode_label.config(text="Mode: QUICK", fg="green")
    sentence_frame.pack_forget()
    
    render_quick_options()
    
    print("🔄 Switched to QUICK MODE")

def update_sentence_display():
    """Update sentence display label"""
    sentence = " ".join(mode_manager.sentence_words)
    sentence_label.config(text=f"Sentence: {sentence}")

def on_key_press(event):
    """Handle keyboard number input"""
    key = event.char
    
    if mode_manager.current_mode == "quick":
        if key in quick_button_map:
            selected_text = quick_button_map[key]
            print(f"🔑 Keyboard input: {key} -> {selected_text}")
            
            # Find button index for visual feedback
            button_index = None
            for i, text in enumerate(quick_buttons_text):
                if text == selected_text:
                    button_index = i
                    break
            
            if button_index is not None:
                # Visual feedback
                original_bg = buttons[button_index].cget("bg")
                original_fg = buttons[button_index].cget("fg")
                original_font = buttons[button_index].cget("font")
                
                buttons[button_index].config(bg="yellow", fg="red", font=("Arial", 16, "bold"))
                root.update()
                
                # Handle selection
                if selected_text == "Sentence Mode":
                    switch_to_sentence_mode()
                else:
                    speak(selected_text)
                    print(f"🗣️ Spoken: '{selected_text}'")
                
                # Restore appearance
                root.after(200, lambda: buttons[button_index].config(
                    bg=original_bg, fg=original_fg, font=original_font
                ))
    
    elif mode_manager.current_mode == "sentence":
        if key in mode_manager.numbered_options:
            choice = mode_manager.numbered_options[key]
            print(f"🔑 Keyboard input: {key} -> {choice}")
            
            # Find button index for visual feedback
            button_index = None
            options = sentence_tree.get(mode_manager.sentence_state, []) + ["Speak", "Back", "Clear", "Exit"]
            for i, option in enumerate(options[:9]):
                if option == choice:
                    button_index = i
                    break
            
            if button_index is not None and button_index < len(buttons):
                # Visual feedback
                original_bg = buttons[button_index].cget("bg")
                original_fg = buttons[button_index].cget("fg")
                original_font = buttons[button_index].cget("font")
                
                buttons[button_index].config(bg="yellow", fg="red", font=("Arial", 14, "bold"))
                root.update()
                
                # Handle selection
                handle_sentence_selection(choice)
                
                # Restore appearance
                root.after(200, lambda: buttons[button_index].config(
                    bg=original_bg, fg=original_fg, font=original_font
                ))

# Initialize quick mode
render_quick_options()
print("✅ GUI initialized")

# Bind keyboard events
root.bind("<Key>", on_key_press)
print("✅ Keyboard input handler bound")

# ---------------- MAIN UPDATE FUNCTION ----------------
def update():
    """Main update loop"""
    global selected_row, selected_col, last_blink_time, last_gaze_move_time
    
    try:
        # Read from camera
        ret, frame = cap.read()
        if ret:
            # Process frame for eye tracking
            gaze, blink, debug_frame = gaze_tracker.process_frame(frame)
            
            # Update signal labels
            gaze_label.config(text=f"Gaze: {gaze}")
            blink_label.config(text=f"Blink: {'YES' if blink else 'NO'}")
            
            # Update colors
            if gaze == "LEFT":
                gaze_label.config(fg="green")
            elif gaze == "RIGHT":
                gaze_label.config(fg="orange")
            else:
                gaze_label.config(fg="blue")
            
            blink_label.config(fg="red" if blink else "gray")
            
            # Handle navigation with improved maneuverability
            current_time = time.time()
            current_index = (selected_row * 3) + selected_col
            
            # Reset delay timer when moving to new button
            if delay_manager.current_button_index != current_index:
                delay_manager.reset_timer()
                delay_manager.start_selection_timer(current_index)
            
            if gaze == "LEFT" and current_time - last_gaze_move_time > 1.5:
                if selected_col > 0:
                    selected_col = selected_col - 1
                else:
                    # Smart navigation: go up one row if possible
                    if selected_row > 0:
                        selected_row = selected_row - 1
                        selected_col = 2  # Rightmost column
                    else:
                        # At top-left, go to bottom-right
                        max_row = (len(buttons) - 1) // 3
                        selected_row = max_row
                        selected_col = 2 if len(buttons) > (max_row * 3 + 2) else (len(buttons) - 1) % 3
                
                last_gaze_move_time = current_time
                print(f"👈 Moved LEFT to row {selected_row}, col {selected_col}")
                
            elif gaze == "RIGHT" and current_time - last_gaze_move_time > 1.5:
                if selected_col < 2:
                    # Check if there's a button in the next column
                    next_index = (selected_row * 3) + selected_col + 1
                    if next_index < len(buttons):
                        selected_col = selected_col + 1
                    else:
                        # No button in next column, go to next row
                        max_row = (len(buttons) - 1) // 3
                        if selected_row < max_row:
                            selected_row = selected_row + 1
                            selected_col = 0
                        else:
                            # At bottom-right, wrap to top-left
                            selected_row = 0
                            selected_col = 0
                else:
                    # At rightmost column, go to next row
                    max_row = (len(buttons) - 1) // 3
                    if selected_row < max_row:
                        selected_row = selected_row + 1
                        selected_col = 0
                    else:
                        # Wrap to top-left
                        selected_row = 0
                        selected_col = 0
                
                last_gaze_move_time = current_time
                print(f"👉 Moved RIGHT to row {selected_row}, col {selected_col}")
            
            # Handle selection with delay system
            if blink and current_time - last_blink_time > 1.5:
                current_index = (selected_row * 3) + selected_col
                if current_index < len(buttons) and delay_manager.should_select(current_index):
                    if mode_manager.current_mode == "quick":
                        select_quick_button()
                    else:
                        # Get current button text
                        btn_text = buttons[current_index].cget("text")
                        if '\n' in btn_text:
                            choice = btn_text.split('\n', 1)[1]
                            if '\n' in choice:
                                choice = choice.split('\n', 1)[0]
                        else:
                            choice = btn_text
                        
                        handle_sentence_selection(choice)
                    
                    last_blink_time = current_time
                    delay_manager.reset_timer()
            
            # Update button highlighting
            highlight_buttons()
            
            # Update camera canvas
            try:
                frame_rgb = cv2.cvtColor(debug_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                imgtk = ImageTk.PhotoImage(image=img)
                
                camera_canvas.delete("all")
                camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
                camera_canvas.image = imgtk  # Keep reference
                
            except Exception as e:
                print(f"Canvas update error: {e}")
            
            # Show debug frame in OpenCV window
            cv2.imshow("Eye Tracking Debug", debug_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                root.quit()
                
        else:
            print("⚠️ Camera read failed")
        
    except Exception as e:
        print(f"Update error: {e}")
    
    # Schedule next update
    root.after(33, update)  # ~30 FPS

# Start updates
print("🖥️ Starting main update loop...")
update()

# ---------------- MAIN LOOP ----------------
print("🚀 SYSTEM READY - SENTENCE MODE ENHANCED")
print("=" * 60)
print("Instructions:")
print("• Look LEFT/RIGHT to navigate buttons")
print("• Blink to select highlighted button")
print("• Press number keys 1-9 for quick selection")
print("• Press 'q' in debug window to close")
print("• Close main window to exit")
print("=" * 60)
print("Quick Mode Button Mapping:")
for key, text in quick_button_map.items():
    print(f"  {key}: {text}")
print("=" * 60)
print("Sentence Mode Structure:")
for state, options in sentence_tree.items():
    print(f"  {state}: {options}")
print("=" * 60)

try:
    root.mainloop()
except KeyboardInterrupt:
    print("\n🛑 Keyboard interrupt")
except Exception as e:
    print(f"❌ Main loop error: {e}")
finally:
    print("🧹 Cleaning up...")
    cap.release()
    cv2.destroyAllWindows()
    print("✅ System shutdown complete")
