import cv2
import torch
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from ultralytics import YOLO
import requests
from math import radians, sin, cos, sqrt, atan2
from flask import Flask, request
import os
from PIL import Image
import io
import psutil
import random
import threading
from datetime import datetime

app = Flask(__name__)

def select_yolo_model():
    total_memory = psutil.virtual_memory().total

    if total_memory < 4 * 1024 * 1024 * 1024:
        print("Low memory detected. Selecting YOLOv11n model.")
        return YOLO('yolo11n.pt')
    elif total_memory < 8 * 1024 * 1024 * 1024:
        print("Moderate memory detected. Selecting YOLOv11s model.")
        return YOLO('yolo11s.pt')
    else:
        print("High memory detected. Selecting YOLOv11m model.")
        return YOLO('yolo11m.pt')

model = select_yolo_model()

SCALE_FACTOR = 0.01
SPEED_THRESHOLD = 5.0
PROLONGED_COLLISION_FRAMES = 40
MIN_COLLISION_DISTANCE = 50
COLLISION_THRESHOLD = 120
ACCIDENT_LOCATION = (19.070, 72.877)

SENDER_EMAIL = "pranavreddy772003@gmail.com"
RECEIVER_EMAIL = "772003pranav@gmail.com"
PASSWORD = "lmip lcuw hmmc soeu"

WEATHER_API_KEY = "7e33ee11182cc2ad20643f007c8b4834"
WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"

def get_vehicle_data():
    speed = random.randint(0, 120)
    acceleration = random.uniform(0, 5)
    braking = random.choice([True, False])
    return speed, acceleration, braking

def detect_vehicle_events(speed, acceleration, braking):
    events = []
    if speed > 100:
        events.append("Overspeeding")
    if acceleration > 3:
        events.append("Heavy acceleration")
    if braking:
        events.append("Hard braking")
    return events

def resize_image(image_path, max_size=(800, 600)):
    with Image.open(image_path) as img:
        img.thumbnail(max_size)
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG')
        return img_byte_arr.getvalue()

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

def calculate_iou(box1, box2):
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    inter_area = max(0, x2 - x1) * max(0, y2 - y1)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box1[1])

    union_area = box1_area + box2_area - inter_area
    return inter_area / union_area if union_area > 0 else 0

def calculate_speed(box1, box2, time_interval):
    x1, y1 = (box1[0] + box1[2]) / 2, (box1[1] + box1[3]) / 2
    x2, y2 = (box2[0] + box2[2]) / 2, (box2[1] + box2[3]) / 2
    distance = sqrt((x2 - x1)**2 + (y2 - y1)**2)
    return distance / time_interval

def alert_nearest_services(location):
    lat, lon = location
    overpass_url = "http://overpass-api.de/api/interpreter"
    overpass_query = f"""
    [out:json];
    (
      node["amenity"="police"](around:5000,{lat},{lon});
      node["amenity"="hospital"](around:5000,{lat},{lon});
    );
    out body;
    """
    response = requests.get(overpass_url, params={'data': overpass_query})
    data = response.json()

    police_stations = []
    hospitals = []

    for element in data['elements']:
        if 'tags' in element:
            name = element['tags'].get('name', 'Unnamed')
            lat_osm, lon_osm = element['lat'], element['lon']
            if element['tags'].get('amenity') == 'police':
                police_stations.append({'name': name, 'lat': lat_osm, 'lon': lon_osm})
            elif element['tags'].get('amenity') == 'hospital':
                hospitals.append({'name': name, 'lat': lat_osm, 'lon': lon_osm})

    nearest_police_station = min(police_stations, key=lambda p: haversine(lat, lon, p['lat'], p['lon']), default=None)
    nearest_hospital = min(hospitals, key=lambda h: haversine(lat, lon, h['lat'], h['lon']), default=None)

    return nearest_police_station, nearest_hospital

def generate_accident_report(collision_count, max_speed, weather_condition, temperature, vehicle_events, 
                             nearest_police_station, nearest_hospital):
    report = f"""
Accident Detection System - Detailed Report
============================================

Incident Details:
-----------------
Date and Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Location: Latitude {ACCIDENT_LOCATION[0]}, Longitude {ACCIDENT_LOCATION[1]}

Collision Metrics:
-----------------
Total Collision Count: {collision_count}
Maximum Detected Speed: {max_speed:.2f} px/s

Weather Conditions:
------------------
Description: {weather_condition}
Temperature: {temperature:.1f}°C

Vehicle Events:
--------------
Detected Events: {', '.join(vehicle_events) if vehicle_events else 'No significant events'}

Nearest Emergency Services:
--------------------------
Police Station: {nearest_police_station['name'] if nearest_police_station else 'Not available'}
Police Station Distance: {haversine(ACCIDENT_LOCATION[0], ACCIDENT_LOCATION[1], 
                                     nearest_police_station['lat'], nearest_police_station['lon']) if nearest_police_station else 'N/A'} km
Hospital: {nearest_hospital['name'] if nearest_hospital else 'Not available'}
Hospital Distance: {haversine(ACCIDENT_LOCATION[0], ACCIDENT_LOCATION[1], 
                               nearest_hospital['lat'], nearest_hospital['lon']) if nearest_hospital else 'N/A'} km

Severity Assessment:
-------------------
{estimate_severity(collision_count, max_speed, weather_condition)}

Emergency Response Recommendation:
----------------------------------
Immediate medical and law enforcement assistance is strongly recommended. 
Please verify the exact location and proceed with caution.

Note: This is an automated system-generated report. Always confirm details with on-site assessment.
"""
    return report

def send_email(subject, report, images, video=None):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject

    msg.attach(MIMEText(report, 'plain'))

    for image in images[:min(3, len(images))]:
        img_data = resize_image(image)
        img_name = os.path.basename(image)
        img = MIMEImage(img_data, name=img_name)
        msg.attach(img)

    if video:
        video_name = os.path.basename(video)
        with open(video, 'rb') as f:
            video_data = f.read()
        video_attachment = MIMEText(video_data, 'base64', 'utf-8')
        video_attachment.add_header('Content-Disposition', 'attachment', filename=video_name)
        msg.attach(video_attachment)

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, PASSWORD)
        server.send_message(msg)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def get_weather(lat, lon):
    params = {
        'lat': lat,
        'lon': lon,
        'appid': WEATHER_API_KEY,
        'units': 'metric'
    }
    response = requests.get(WEATHER_URL, params=params)
    weather_data = response.json()

    if response.status_code == 200:
        weather_description = weather_data['weather'][0]['description']
        temperature = weather_data['main']['temp']
        return weather_description, temperature
    else:
        return "Unknown", 0

def estimate_severity(collision_count, max_speed, weather_condition):
    if collision_count > 5 or max_speed > SPEED_THRESHOLD * 1.5 or "rain" in weather_condition or "fog" in weather_condition:
        return "HIGH SEVERITY: Immediate emergency response required"
    elif collision_count > 3 or max_speed > SPEED_THRESHOLD:
        return "MEDIUM SEVERITY: Urgent medical attention recommended"
    else:
        return "LOW SEVERITY: Standard medical check recommended"

def detect_accident(video_path):
    cap = cv2.VideoCapture(video_path)
    accident_detected = False
    frame_counter = 0
    collision_count = 0
    max_speed = 0
    last_boxes = []
    prolonged_collision_count = 0
    images_to_attach = []
    video_clip_start_frame = None
    video_clip_end_frame = None
    email_sent = False
    vehicle_events = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        speed, acceleration, braking = get_vehicle_data()
        current_vehicle_events = detect_vehicle_events(speed, acceleration, braking)
        vehicle_events.extend(current_vehicle_events)

        current_time = time.time()
        results = model(frame)
        boxes = results[0].boxes.xyxy.cpu().numpy()

        for i, box in enumerate(boxes):
            if len(box) >= 4:
                x1, y1, x2, y2 = box[:4]
                conf = box[4] if len(box) > 4 else None
                cls = int(box[5]) if len(box) > 5 else None

                label = f'Class {cls}: {conf:.2f}' if conf is not None else 'Unknown'
                color = (0, 255, 0)
                if accident_detected:
                    color = (0, 0, 255)

                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                cv2.putText(frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

                if len(last_boxes) > i:
                    speed = calculate_speed(last_boxes[i], box[:4], 1)
                    max_speed = max(max_speed, speed)
                    cv2.putText(frame, f'Speed: {speed:.2f} px/s', (int(x1), int(y1) + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

        collision_detected = False

        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                box1 = boxes[i][:4]
                box2 = boxes[j][:4]

                iou = calculate_iou(box1, box2)
                if iou > 0.2:
                    collision_detected = True
                    collision_count += 1

                    if prolonged_collision_count < PROLONGED_COLLISION_FRAMES:
                        prolonged_collision_count += 1
                    if prolonged_collision_count >= PROLONGED_COLLISION_FRAMES:
                        accident_detected = True

        if accident_detected:
            last_boxes = boxes
            for box in boxes:
                x1, y1, x2, y2 = box[:4]
                cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 2)

            cv2.putText(frame, "Accident Detected!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            if video_clip_start_frame is None:
                video_clip_start_frame = frame_counter
            video_clip_end_frame = frame_counter

            weather_condition, temperature = get_weather(ACCIDENT_LOCATION[0], ACCIDENT_LOCATION[1])

            nearest_police_station, nearest_hospital = alert_nearest_services(ACCIDENT_LOCATION)

            frame_filename = f'uploads/frame_{frame_counter}.jpg'
            cv2.imwrite(frame_filename, frame)
            images_to_attach.append(frame_filename)

            if not email_sent and len(images_to_attach) >= 1:
                segment_video_path = crop_accident_video(video_path, video_clip_start_frame, video_clip_end_frame)
                
                # Generate comprehensive report
                accident_report = generate_accident_report(
                    collision_count, 
                    max_speed, 
                    weather_condition, 
                    temperature, 
                    list(set(vehicle_events)), 
                    nearest_police_station, 
                    nearest_hospital
                )

                send_email('Accident Detection System - Critical Report', 
                           accident_report, 
                           images_to_attach, 
                           segment_video_path)
                
                email_sent = True
                break

        last_boxes = boxes
        frame_counter += 1
        cv2.imshow("Accident Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    for image in images_to_attach:
        os.remove(image)

def crop_accident_video(video_path, start_frame, end_frame):
    input_video = cv2.VideoCapture(video_path)
    fps = input_video.get(cv2.CAP_PROP_FPS)
    frame_width = int(input_video.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(input_video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_video_path = 'uploads/accident_segment.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (frame_width, frame_height))

    input_video.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

    for frame_counter in range(start_frame, end_frame + 1):
        ret, frame = input_video.read()
        if not ret:
            break
        out.write(frame)

    input_video.release()
    out.release()
    return output_video_path

@app.route('/detect', methods=['POST'])
def detect_route():
    video_file = request.files['video']
    video_path = f'uploads/{video_file.filename}'
    video_file.save(video_path)
    detect_accident(video_path)
    return "Detection completed."

if __name__ == "__main__":
    app.run(debug=True)