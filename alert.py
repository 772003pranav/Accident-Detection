import cv2
import torch
import time
from ultralytics import YOLO  # Importing YOLOv8
import requests
from math import radians, sin, cos, sqrt, atan2

# Load the YOLOv8 model
model = YOLO('yolov8n.pt')

# Constants
SCALE_FACTOR = 0.01
SPEED_THRESHOLD = 5.0
PROLONGED_COLLISION_FRAMES = 30
MIN_COLLISION_DISTANCE = 50
COLLISION_THRESHOLD = 120
ACCIDENT_LOCATION = (19.070, 72.877)  # Replace with actual accident location

# Haversine formula
def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1, lon1, lat2, lon2 = radians(lat1), radians(lon1), radians(lat2), radians(lon2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance

# Function to alert nearest services
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

    if nearest_police_station:
        print(f"Nearest police station: {nearest_police_station['name']} at {nearest_police_station['lat']}, {nearest_police_station['lon']}")
    else:
        print("No police station found nearby.")

    if nearest_hospital:
        print(f"Nearest hospital: {nearest_hospital['name']} at {nearest_hospital['lat']}, {nearest_hospital['lon']}")
    else:
        print("No hospital found nearby.")

    return nearest_police_station, nearest_hospital

# Function to calculate Intersection over Union (IoU)
def calculate_iou(box1, box2):
    x1_inter = max(box1[0], box2[0])
    y1_inter = max(box1[1], box2[1])
    x2_inter = min(box1[2], box2[2])
    y2_inter = min(box1[3], box2[3])
    
    inter_area = max(0, x2_inter - x1_inter) * max(0, y2_inter - y1_inter)
    box1_area = (box1[2] - box1[0]) * (box1[3] - box1[1])
    box2_area = (box2[2] - box2[0]) * (box2[3] - box2[1])
    
    union_area = box1_area + box2_area - inter_area
    iou = inter_area / union_area if union_area > 0 else 0
    return iou

# Function to detect accidents from a video
def detect_accident(video_path):
    cap = cv2.VideoCapture(video_path)
    accident_detected = False
    frame_counter = 0
    prolonged_collision_count = 0  # Track prolonged collision

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)  # Perform detection on the frame
        boxes = results[0].boxes.xyxy.cpu().numpy()  # Get bounding boxes in xyxy format

        # Draw detections on the frame
        for i, box in enumerate(boxes):
            x1, y1, x2, y2 = box[:4]
            conf = box[4] if len(box) > 4 else None
            cls = int(box[5]) if len(box) > 5 else None

            color = (0, 255, 0)  # Normal detection color
            if accident_detected:
                color = (0, 0, 255)  # Red for accident detected

            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)

        collision_detected = False

        for i in range(len(boxes)):
            for j in range(i + 1, len(boxes)):
                box1 = boxes[i][:4]
                box2 = boxes[j][:4]
                
                iou = calculate_iou(box1, box2)
                if iou > 0.2:
                    collision_detected = True
                    prolonged_collision_count += 1
                    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Collision detected between object {i} and object {j}!")

                    if prolonged_collision_count >= PROLONGED_COLLISION_FRAMES:
                        accident_detected = True
                        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Accident Detected due to prolonged collision!")

        # If accident detected, alert nearest services
        if accident_detected:
            nearest_police_station, nearest_hospital = alert_nearest_services(ACCIDENT_LOCATION)
            print("Accident Detected! Alerting the nearest services...")

        # Draw "Accident Detected" text on the frame
        if accident_detected:
            cv2.putText(frame, "Accident Detected!", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Display the frame
        cv2.imshow('Accident Detection', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

# Usage
detect_accident("accident.mp4")
