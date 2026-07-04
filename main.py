from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import random
from datetime import datetime
from datetime import timedelta
import uvicorn

app = FastAPI(title="The Boss's Big Idea - Backend API")

# Enable CORS - Fixed to be more explicit
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
)

# 1. Initialize In-Memory Data Store
ROOMS = ["Drawing Room", "Work Room 1", "Work Room 2"]
devices_db = []
device_id_counter = 1

for room in ROOMS:
    # 2 Fans per room
    for i in range(1, 3):
        devices_db.append({
            "id": device_id_counter,
            "name": f"Fan {i}",
            "type": "fan",
            "room": room,
            "status": "off",
            "power_draw_watts": 60,
            "last_changed": datetime.now().isoformat()
        })
        device_id_counter += 1
        
    # 3 Lights per room
    for i in range(1, 4):
        devices_db.append({
            "id": device_id_counter,
            "name": f"Light {i}",
            "type": "light",
            "room": room,
            "status": "off",
            "power_draw_watts": 15,
            "last_changed": datetime.now().isoformat()
        })
        device_id_counter += 1

# 2. Background Task: Simulate Live Office Activity
async def simulate_device_activity():
    """Randomly toggles a device's status every 5 to 15 seconds to simulate activity."""
    while True:
        await asyncio.sleep(random.randint(5, 15))
        device = random.choice(devices_db)
        device["status"] = "on" if device["status"] == "off" else "off"
        device["last_changed"] = datetime.now().isoformat()
        print(f"[SIMULATOR] Toggled {device['room']} - {device['name']} to {device['status']}")

@app.on_event("startup")
async def startup_event():
    # Comment/uncomment below line to enable/disable simulator
    asyncio.create_task(simulate_device_activity())
    print("✅ Backend API started successfully!")
    print("✅ Simulator is RUNNING - devices will toggle automatically")
    print("📡 API available at: http://127.0.0.1:8000")
    print("📖 API docs available at: http://127.0.0.1:8000/docs")

# 3. API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "message": "The Boss's Big Idea API is running!",
        "endpoints": ["/api/devices", "/api/power", "/api/alerts"]
    }

@app.get("/api/devices")
async def get_all_devices():
    """Returns the live status of all 15 devices."""
    return {"devices": devices_db}

@app.get("/api/power")
async def get_power_usage():
    """Calculates total and per-room power consumption in real-time."""
    total_power = 0
    room_power = {room: 0 for room in ROOMS}
    
    for device in devices_db:
        if device["status"] == "on":
            total_power += device["power_draw_watts"]
            room_power[device["room"]] += device["power_draw_watts"]
            
    return {
        "total_power_watts": total_power,
        "room_breakdown": room_power,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/alerts")
async def get_alerts():
    """Generates alerts based on exact problem statement requirements."""
    alerts = []
    now = datetime.now()
    
    # Check if current time is outside 9 AM - 5 PM (17:00)
    is_after_hours = now.hour >= 17 or now.hour < 9

    for room in ROOMS:
        room_devices = [d for d in devices_db if d["room"] == room]
        
        # 1. AFTER HOURS ALERT
        if is_after_hours:
            devices_left_on = [d["name"] for d in room_devices if d["status"] == "on"]
            if devices_left_on:
                alerts.append({
                    "timestamp": now.isoformat(),
                    "message": f"🌙 After Hours Alert: {len(devices_left_on)} devices still ON in {room}.",
                    "level": "warning",
                    "room": room,
                    "devices": devices_left_on
                })

        # 2. CONTINUOUS USAGE ALERT (> 2 hours)
        all_on = all(d["status"] == "on" for d in room_devices)
        if all_on:
            times_on = [(now - datetime.fromisoformat(d["last_changed"])) for d in room_devices]
            if all(t > timedelta(hours=2) for t in times_on):
                alerts.append({
                    "timestamp": now.isoformat(),
                    "message": f"🚨 CRITICAL: All devices in {room} have been running continuously for over 2 hours!",
                    "level": "critical",
                    "room": room
                })
                
    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "timestamp": now.isoformat()
    }

# Manual device control endpoint (bonus feature)
@app.post("/api/devices/{device_id}/toggle")
async def toggle_device(device_id: int):
    """Manually toggle a specific device on or off."""
    for device in devices_db:
        if device["id"] == device_id:
            device["status"] = "on" if device["status"] == "off" else "off"
            device["last_changed"] = datetime.now().isoformat()
            return {
                "success": True,
                "device": device,
                "message": f"{device['name']} in {device['room']} is now {device['status']}"
            }
    return {"success": False, "message": f"Device {device_id} not found"}

# Run the server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )