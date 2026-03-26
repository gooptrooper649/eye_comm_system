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

# ---------------- OpenCV Display Thread ----------------
def opencv_display_thread():
    """Separate thread for OpenCV display to avoid Tkinter blocking"""
    global debug_frame_queue
    
    while True:
        try:
            if len(debug_frame_queue) > 0:
                frame = debug_frame_queue.popleft()
                cv2.imshow("Eye Tracking Debug", frame)
                
            key = cv2.waitKey(1)
            if key & 0xFF == ord('q'):
                cv2.destroyAllWindows()
                break
        except Exception as e:
            print(f"OpenCV display error: {e}")
            break

# ---------------- TTS ----------------
engine = pyttsx3.init()

def speak(text):
    def run():
        engine.say(text)
        engine.runAndWait()
    threading.Thread(target=run).start()

# ---------------- Eye Tracking ----------------
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,  # IMPORTANT
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Eye tracking landmarks
LEFT_EYE = [33, 133, 159, 145]
RIGHT_EYE = [362, 263, 386, 374]

LEFT_IRIS_POINTS = [474, 475, 476, 477]
RIGHT_IRIS_POINTS = [469, 470, 471, 472]

LEFT_IRIS = 474
RIGHT_IRIS = 469

class GazeStabilizer:
    def __init__(self):
        self.ratio_history = deque(maxlen=10)
        self.direction_history = deque(maxlen=5)
        self.last_switch_time = 0

        # Default thresholds (will be calibrated)
        self.left_threshold = 0.30  # More sensitive
        self.right_threshold = 0.70  # More sensitive

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

        # Majority voting
        stable = max(set(self.direction_history), key=self.direction_history.count)

        # Debounce (prevent rapid switching)
        if time.time() - self.last_switch_time < 0.5:
            return None

        if stable != direction:
            return None

        self.last_switch_time = time.time()
        return stable

def get_pupil_center(landmarks, iris_indices):
    x = np.mean([landmarks[i].x for i in iris_indices if len(landmarks) > i])
    y = np.mean([landmarks[i].y for i in iris_indices if len(landmarks) > i])
    return x, y

def get_gaze_ratio(landmarks):
    try:
        # LEFT eye
        left_outer = landmarks[33].x if len(landmarks) > 33 else 0.3
        left_inner = landmarks[133].x if len(landmarks) > 133 else 0.7

        pupil_left_x, _ = get_pupil_center(landmarks, LEFT_IRIS_POINTS)

        left_width = left_inner - left_outer
        if abs(left_width) < 0.001:
            return None

        left_ratio = (pupil_left_x - left_outer) / left_width

        # RIGHT eye
        right_outer = landmarks[362].x if len(landmarks) > 362 else 0.7
        right_inner = landmarks[263].x if len(landmarks) > 263 else 0.3

        pupil_right_x, _ = get_pupil_center(landmarks, RIGHT_IRIS_POINTS)

        right_width = right_inner - right_outer
        if abs(right_width) < 0.001:
            return None

        right_ratio = (pupil_right_x - right_outer) / right_width

        ratio = (left_ratio + right_ratio) / 2

        return max(0.0, min(1.0, ratio))

    except Exception as e:
        print("Ratio error:", e)
        return None

# Initialize stabilizer
stabilizer = GazeStabilizer()
blink_history = deque(maxlen=5)
last_valid_ratio = 0.5  # Fallback for bad frames

# Thread communication
debug_frame_queue = deque(maxlen=1)  # Queue for frames to display

def eye_aspect_ratio(landmarks):
    top = landmarks[159].y if len(landmarks) > 159 else 0.5
    bottom = landmarks[145].y if len(landmarks) > 145 else 0.5
    left = landmarks[33].x if len(landmarks) > 33 else 0.3
    right = landmarks[133].x if len(landmarks) > 133 else 0.7

    vertical = abs(top - bottom)
    horizontal = abs(left - right)

    if horizontal == 0:
        return 1

    return vertical / horizontal

def detect_blink(landmarks):
    ear = eye_aspect_ratio(landmarks)
    blink = ear < 0.18
    blink_history.append(blink)

    # Require 3/5 frames to confirm blink
    return blink_history.count(True) >= 3

def calibrate():
    print("Look CENTER...")
    time.sleep(2)
    center = np.mean(stabilizer.ratio_history)

    print("Look LEFT...")
    time.sleep(2)
    left = np.mean(stabilizer.ratio_history)

    print("Look RIGHT...")
    time.sleep(2)
    right = np.mean(stabilizer.ratio_history)

    stabilizer.left_threshold = (left + center) / 2
    stabilizer.right_threshold = (right + center) / 2

    print("Calibration done!")

def draw_eye_debug(frame, landmarks, w, h):
    try:
        # LEFT eye landmarks
        left_outer = landmarks[33].x if len(landmarks) > 33 else 0.3
        left_inner = landmarks[133].x if len(landmarks) > 133 else 0.7
        left_y = int(landmarks[145].y * h) if len(landmarks) > 145 else int(h/2)
        
        # Get true pupil centers
        pupil_left_x, pupil_left_y = get_pupil_center(landmarks, LEFT_IRIS_POINTS)
        
        # RIGHT eye landmarks (if available, otherwise mirrored)
        if len(landmarks) > 469:
            right_outer = landmarks[362].x
            right_inner = landmarks[263].x
            right_y = int(landmarks[374].y * h) if len(landmarks) > 374 else left_y
            pupil_right_x, pupil_right_y = get_pupil_center(landmarks, RIGHT_IRIS_POINTS)
        else:
            # Fallback: use mirrored left eye
            right_outer = 1.0 - left_outer
            right_inner = 1.0 - left_inner
            right_y = left_y
            pupil_right_x = 1.0 - pupil_left_x
            pupil_right_y = pupil_left_y
        
        # Convert normalized → pixel for LEFT eye
        left_outer_px = int(left_outer * w)
        left_inner_px = int(left_inner * w)
        pupil_left_px = int(pupil_left_x * w)
        pupil_left_py = int(pupil_left_y * h)
        
        # Convert normalized → pixel for RIGHT eye
        right_outer_px = int(right_outer * w)
        right_inner_px = int(right_inner * w)
        pupil_right_px = int(pupil_right_x * w)
        pupil_right_py = int(pupil_right_y * h)
        
        # Draw LEFT eye boundary
        cv2.line(frame, (left_outer_px, left_y), (left_inner_px, left_y), (255, 0, 0), 2)
        
        # Draw LEFT true pupil center with enhanced visualization
        cv2.circle(frame, (pupil_left_px, pupil_left_py), 6, (255, 255, 0), -1)
        cv2.circle(frame, (pupil_left_px, pupil_left_py), 8, (0, 255, 255), 2)  # Outer ring
        
        # Draw LEFT eye corners
        cv2.circle(frame, (left_outer_px, left_y), 5, (0, 0, 255), -1)
        cv2.circle(frame, (left_inner_px, left_y), 5, (0, 0, 255), -1)
        
        # Draw RIGHT eye boundary
        cv2.line(frame, (right_outer_px, right_y), (right_inner_px, right_y), (255, 0, 0), 2)
        
        # Draw RIGHT true pupil center with enhanced visualization
        cv2.circle(frame, (pupil_right_px, pupil_right_py), 6, (255, 255, 0), -1)
        cv2.circle(frame, (pupil_right_px, pupil_right_py), 8, (0, 255, 255), 2)  # Outer ring
        
        # Draw RIGHT eye corners
        cv2.circle(frame, (right_outer_px, right_y), 5, (0, 0, 255), -1)
        cv2.circle(frame, (right_inner_px, right_y), 5, (0, 0, 255), -1)
        
        # Add eye labels
        cv2.putText(frame, "L", (left_outer_px - 15, left_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(frame, "R", (right_outer_px - 15, right_y), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                   
    except Exception as e:
        print(f"Debug draw error: {e}")
        import traceback
        traceback.print_exc()

def draw_ratio_bar(frame, ratio):
    bar_x = 50
    bar_y = 400
    bar_width = 300
    bar_height = 20

    # Background
    cv2.rectangle(frame, (bar_x, bar_y),
                  (bar_x + bar_width, bar_y + bar_height),
                  (200, 200, 200), -1)

    # Fill based on ratio
    fill = int(bar_width * ratio)
    cv2.rectangle(frame, (bar_x, bar_y),
                  (bar_x + fill, bar_y + bar_height),
                  (0, 255, 0), -1)

    # Threshold lines
    cv2.line(frame, (bar_x + int(bar_width * 0.35), bar_y),
             (bar_x + int(bar_width * 0.35), bar_y + bar_height),
             (0, 0, 255), 2)

    cv2.line(frame, (bar_x + int(bar_width * 0.65), bar_y),
             (bar_x + int(bar_width * 0.65), bar_y + bar_height),
             (0, 0, 255), 2)

    # Text
    cv2.putText(frame, f"Ratio: {round(ratio, 2)}",
                (bar_x, bar_y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), 2)

def draw_gaze_arrow(frame, direction, w, h):
    center_x = w // 2
    center_y = h // 2

    if direction == "LEFT":
        cv2.arrowedLine(frame, (center_x, center_y),
                        (center_x - 100, center_y),
                        (0, 255, 0), 3)

    elif direction == "RIGHT":
        cv2.arrowedLine(frame, (center_x, center_y),
                        (center_x + 100, center_y),
                        (0, 255, 0), 3)

    else:
        cv2.circle(frame, (center_x, center_y), 10, (255,255,0), -1)

def get_gaze_and_blink(frame):
    global last_valid_ratio
    
    # Create a copy for drawing to avoid modifying original
    debug_frame = frame.copy()
    
    # Reduce noise
    debug_frame = cv2.GaussianBlur(debug_frame, (5, 5), 0)
    
    rgb = cv2.cvtColor(debug_frame, cv2.COLOR_BGR2RGB)
    result = face_mesh.process(rgb)

    gaze = "CENTER"
    blink = False
    ratio = last_valid_ratio  # Default to last valid
    direction = "CENTER"

    h, w, _ = debug_frame.shape

    # Confidence filtering - skip if no face detected
    if not result.multi_face_landmarks:
        print("❌ NO FACE LANDMARKS DETECTED")
        return gaze, blink, debug_frame
    
    print(f"✅ FACES DETECTED: {len(result.multi_face_landmarks)}")
    
    if len(result.multi_face_landmarks) == 0:
        print("❌ EMPTY FACE LANDMARKS")
        return gaze, blink, debug_frame

    for face_landmarks in result.multi_face_landmarks:
        landmarks = face_landmarks.landmark
        
        # Check if we have enough landmarks
        print(f"📍 LANDMARKS COUNT: {len(landmarks)}")
        if len(landmarks) >= 468:  # Works for both 468 and 478 landmarks
            print("✅ LANDMARKS VALID - PROCEEDING WITH DRAWING")
            # Get eye ratio for more accurate gaze detection
            current_ratio = get_gaze_ratio(landmarks)
            
            # Tracking stability check - only accept if valid
            if current_ratio is not None:
                last_valid_ratio = current_ratio  # Update fallback
                ratio = current_ratio
                direction = stabilizer.get_stable_direction(ratio)
                
                if direction:
                    gaze = direction

            # DRAW EVERYTHING 
            print("Drawing overlay...")  # Debug logging
            draw_eye_debug(debug_frame, landmarks, w, h)
            draw_ratio_bar(debug_frame, ratio)
            draw_gaze_arrow(debug_frame, direction, w, h)

            # Blink detection using normalized EAR
            blink = detect_blink(landmarks)

    return gaze, blink, debug_frame

# ---------------- GUI ----------------
root = tk.Tk()
root.title("Assistive Communication System")
root.geometry("1200x700")

# Main container
main_frame = tk.Frame(root)
main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

# Left side - Camera feed
left_frame = tk.Frame(main_frame)
left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

tk.Label(left_frame, text="Camera Feed", font=("Arial", 14, "bold")).pack()
camera_canvas = Canvas(left_frame, width=640, height=480, bg="black")
camera_canvas.pack(pady=10)

# Eye movement signals
signals_frame = tk.Frame(left_frame)
signals_frame.pack(pady=10)

gaze_label = tk.Label(signals_frame, text="Gaze: CENTER", font=("Arial", 12), fg="blue")
gaze_label.pack(side=tk.LEFT, padx=10)

blink_label = tk.Label(signals_frame, text="Blink: NO", font=("Arial", 12), fg="red")
blink_label.pack(side=tk.LEFT, padx=10)

# Right side - Communication buttons
right_frame = tk.Frame(main_frame)
right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=20)

tk.Label(right_frame, text="Communication Options", font=("Arial", 14, "bold")).pack(pady=10)

# Create a container frame for buttons to use grid
button_container = tk.Frame(right_frame)
button_container.pack(pady=10)

buttons_text = ["Water", "Food", "Washroom", "Help"]
buttons = []
selected_index = 0
last_blink_time = 0

def highlight():
    for i, btn in enumerate(buttons):
        if i == selected_index:
            btn.config(bg="red", fg="white")
        else:
            btn.config(bg="lightgray", fg="black")

def select():
    text = buttons_text[selected_index]
    print("Selected:", text)
    speak(text)

# Create buttons in grid inside the container
for i, text in enumerate(buttons_text):
    btn = tk.Button(button_container, text=text, font=("Arial", 16), width=12, height=3)
    btn.grid(row=i//2, column=i%2, padx=10, pady=10)
    buttons.append(btn)

highlight()

# ---------------- Camera Loop ----------------
cap = cv2.VideoCapture(0)

def update():
    global selected_index, last_blink_time

    ret, frame = cap.read()
    if not ret:
        print("❌ FRAME CAPTURE FAILED")
        root.after(100, update)
        return
    
    print("✅ FRAME CAPTURED")
    print(f"Frame shape: {frame.shape}")

    # Get eye tracking data with debug frame
    gaze, blink, debug_frame = get_gaze_and_blink(frame)
    
    if debug_frame is None:
        print("❌ DEBUG_FRAME IS NONE")
        root.after(100, update)
        return
        
    print("✅ EYE TRACKING COMPLETED")

    # Queue frame for OpenCV thread instead of direct display
    if len(debug_frame_queue) >= 1:
        debug_frame_queue.popleft()  # Remove oldest if full
    debug_frame_queue.append(debug_frame)
    
    print("📺 FRAME QUEUED FOR OPENCV DISPLAY")

    # Update eye movement signals
    gaze_label.config(text=f"Gaze: {gaze}")
    blink_label.config(text=f"Blink: {'YES' if blink else 'NO'}")
    
    # Update colors based on signals
    if gaze == "LEFT":
        gaze_label.config(fg="green")
    elif gaze == "RIGHT":
        gaze_label.config(fg="orange")
    else:
        gaze_label.config(fg="blue")
    
    blink_label.config(fg="red" if blink else "gray")

    # Move selection based on gaze
    if gaze == "LEFT":
        selected_index = max(0, selected_index - 1)
    elif gaze == "RIGHT":
        selected_index = min(len(buttons) - 1, selected_index + 1)

    # Blink = select
    if blink and time.time() - last_blink_time > 1.5:
        select()
        last_blink_time = time.time()

    # Update button highlighting
    highlight()

    try:
        frame_rgb = cv2.cvtColor(debug_frame, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb, (640, 480))
        img = Image.fromarray(frame_resized)
        imgtk = ImageTk.PhotoImage(image=img)
        
        camera_canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        camera_canvas.image = imgtk  # Keep a reference
        print("✅ TKINTER DISPLAY UPDATED")
    except Exception as e:
        print(f"❌ TKINTER DISPLAY ERROR: {e}")

    # Schedule next update
    root.after(100, update)
    print("=== CAMERA LOOP END ===\n")

# Add calibration button
calib_button = tk.Button(right_frame, text="Calibrate", command=calibrate, font=("Arial", 12))
calib_button.pack(pady=10)

# Start OpenCV display thread BEFORE Tkinter mainloop
print("🚀 STARTING OPENCV DISPLAY THREAD")
opencv_thread = threading.Thread(target=opencv_display_thread, daemon=True)
opencv_thread.start()

update()
root.mainloop()