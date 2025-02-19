import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random

# Haversine formula to calculate the distance between two points
def haversine(lon1, lat1, lon2, lat2):
    lon1, lat1, lon2, lat2 = map(np.radians, [lon1, lat1, lon2, lat2])  # Correct unpacking
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = np.sin(dlat / 2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    r = 6371  # Radius of the Earth in kilometers
    return c * r

# Number of hospitals and police stations
num_hospitals = 9
num_police_stations = 9

# Random accident location
accident_location = (random.randint(100, 900), random.randint(100, 700))

# Generate random locations for hospitals and police stations
hospital_locations = [(random.randint(100, 900), random.randint(100, 700)) for _ in range(num_hospitals)]
police_station_locations = [(random.randint(100, 900), random.randint(100, 700)) for _ in range(num_police_stations)]

# Set up the plot
fig, ax = plt.subplots(figsize=(10, 7))
ax.set_xlim(0, 1024)
ax.set_ylim(0, 768)
ax.set_title("Haversine Formula Demonstration with Accident Alert System", fontsize=14)

# Plot the accident point
ax.plot(accident_location[0], accident_location[1], 'bo', label="Accident Location", markersize=8)

# List to store distance information for animation
distances = []

# Combine hospitals and police stations into one list
all_sources = [(f"Hospital {i+1}", loc) for i, loc in enumerate(hospital_locations)] + \
              [(f"Police Station {i+1}", loc) for i, loc in enumerate(police_station_locations)]

# Shuffle the sources so that they are mixed
random.shuffle(all_sources)

# Calculate distances between the accident and all sources
for name, (lon, lat) in all_sources:
    dist = haversine(accident_location[0], accident_location[1], lon, lat)
    distances.append((name, dist, lon, lat))

# Sort distances by the closest first
distances.sort(key=lambda x: x[1])

# Separate the distances into hospitals and police stations
hospital_distances = [d for d in distances if "Hospital" in d[0]]
police_station_distances = [d for d in distances if "Police Station" in d[0]]

# Get the nearest hospital and police station
nearest_hospital = hospital_distances[0]
nearest_police_station = police_station_distances[0]

# Define the animation update function
def update(frame):
    # Do not clear axes here, so the legend stays intact
    ax.set_xlim(0, 1024)
    ax.set_ylim(0, 768)

    # Plot the accident point (only once)
    ax.plot(accident_location[0], accident_location[1], 'bo', markersize=8)

    # Plot all sources (hospitals and police stations)
    for name, (x, y) in all_sources:
        if "Hospital" in name:
            ax.plot(x, y, 'ro', label=f"{name} (Hospital)" if name == all_sources[0][0] else "")
        else:
            ax.plot(x, y, 'go', label=f"{name} (Police Station)" if name == all_sources[0][0] else "")

    # Highlight the current source (the one currently being visited)
    current_source = distances[frame][0]
    current_x, current_y = distances[frame][2], distances[frame][3]
    
    # Only draw the axis from accident to source once visited
    if frame >= 0:
        ax.plot([accident_location[0], current_x], [accident_location[1], current_y], 'k--', linewidth=2)
    
    # Display distance text in kilometers with dynamic spacing
    distance_text = f"Distance to {current_source}: {distances[frame][1]:.2f} km"
    
    # Adjust the vertical position of the text to avoid overlap with other elements
    text_y_pos = 700 - (frame * 25)  # More space between lines
    ax.text(20, text_y_pos, distance_text, fontsize=12, color='black')

    # After all frames are shown, display the nearest hospital and police station for 10 seconds
    if frame == len(distances) - 1:
        # Create a text box for nearest hospital and police station
        textstr = f"Nearest Hospital:\n{nearest_hospital[0]}: {nearest_hospital[1]:.2f} km\n\n" \
                  f"Nearest Police Station:\n{nearest_police_station[0]}: {nearest_police_station[1]:.2f} km"

        # Place the box outside the plot area, but lower than the distance text
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.5)
        ax.text(1050, 500, textstr, fontsize=14, bbox=props, ha='left')  # Adjust the y-position to 500

        # Stop the animation after showing the nearest sources
        ani.event_source.stop()

    return ax,

# Add the legend once, before the animation starts (only add labels once)
ax.legend(loc="upper left", bbox_to_anchor=(1, 1), fontsize=10)

# Adjust layout to ensure the legend fits within the plot area
plt.tight_layout()

# Create the animation
ani = animation.FuncAnimation(fig, update, frames=len(distances), interval=600, blit=False)

# Show the plot with the animation
plt.show()
