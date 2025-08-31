from fastapi import FastAPI, Body, Query
from typing import Optional, Dict, Any, List
import math, random, datetime

app = FastAPI(title="Pre-Survey Mock API — Plus")

SAMPLE = {
  "addresses":[
    {
      "id":"cust_1",
      "label":"10 Downing Street, London SW1A 2AA",
      "lat":51.5033635, "lng":-0.1276248,
      "image_url":"https://placehold.co/640x360?text=Street+View+Mock",
      "satellite_url":"https://placehold.co/320x180?text=Satellite+Mock",
      "type_guess":"terraced_house",
      "access":{
        "driveway": False, "stairs_visible": True, "double_yellow": True, "red_route": False,
        "narrow_road": True, "parking_zone":"CPZ A (mock)",
        "notes":[
          "No on-site parking; kerbside restrictions likely.",
          "Stairs at entrance; consider extra handling time."
        ],
        "crew_recommendation":"2-person crew",
        "equipment":["trolley","ramps","blankets"]
      }
    },
    {
      "id":"cust_2",
      "label":"221B Baker Street, London NW1 6XE",
      "lat":51.523767, "lng":-0.1585557,
      "image_url":"https://placehold.co/640x360?text=Street+View+Mock",
      "satellite_url":"https://placehold.co/320x180?text=Satellite+Mock",
      "type_guess":"flat_above_shop",
      "access":{
        "driveway": False, "stairs_visible": True, "double_yellow": False, "red_route": False,
        "narrow_road": False, "parking_zone":"CPZ B (mock)",
        "notes":[
          "Likely shared entrance; check lift availability.",
          "On-street pay & display nearby."
        ],
        "crew_recommendation":"3-person crew (stairs)",
        "equipment":["trolley","straps"]
      }
    },
    {
      "id":"cust_3",
      "label":"1 Canada Square, Canary Wharf, London E14 5AB",
      "lat":51.505455, "lng":-0.0235,
      "image_url":"https://placehold.co/640x360?text=Street+View+Mock",
      "satellite_url":"https://placehold.co/320x180?text=Satellite+Mock",
      "type_guess":"apartment_tower",
      "access":{
        "driveway": True, "stairs_visible": False, "double_yellow": False, "red_route": False,
        "narrow_road": False, "parking_zone":"Private access (mock)",
        "notes":[
          "Service bay available; book lift with building mgmt.",
          "Loading dock clearance ok for Luton vans."
        ],
        "crew_recommendation":"3-person crew",
        "equipment":["dollies","blankets","straps"]
      }
    }
  ],
  "depots":[
    {"id":"depot_1","label":"Depot: Battersea, SW11","lat":51.465,"lng":-0.151},
    {"id":"depot_2","label":"Depot: Stratford, E15","lat":51.54,"lng":0.001}
  ]
}

ADDR_BY_ID = {a["id"]:a for a in SAMPLE["addresses"]}
DEPOT_BY_ID = {d["id"]:d for d in SAMPLE["depots"]}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

@app.get("/api/sample_addresses")
def sample_addresses():
    return {"customers":[{"id":a["id"],"label":a["label"]} for a in SAMPLE["addresses"]],
            "depots":[{"id":d["id"],"label":d["label"]} for d in SAMPLE["depots"]]}

@app.post("/api/intake")
def intake(payload: Dict[str, Any] = Body(...)):
    cust_id = payload.get("customer_address_id")
    depot_id = payload.get("depot_id")
    if cust_id not in ADDR_BY_ID: return {"error":"unknown customer address"}
    if depot_id not in DEPOT_BY_ID: return {"error":"unknown depot"}
    return {"origin": DEPOT_BY_ID[depot_id], "dest": ADDR_BY_ID[cust_id]}

@app.get("/api/property-image")
def property_image(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {"error":"unknown address"}
    return {"image_url": a["image_url"], "satellite_url": a["satellite_url"], "type_guess": a["type_guess"]}

@app.get("/api/access-insights")
def access_insights(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {"error":"unknown address"}
    return a["access"]

@app.get("/api/route")
def route(origin_id: str = Query(...), dest_id: str = Query(...), depart_at: Optional[str] = None):
    o = DEPOT_BY_ID.get(origin_id)
    d = ADDR_BY_ID.get(dest_id)
    if not o or not d: return {"error":"unknown origin/dest"}
    km = haversine(o["lat"], o["lng"], d["lat"], d["lng"])
    base_speed = 25.0
    congestion = random.uniform(0.85, 1.35)
    eta_minutes = max(5, int((km / base_speed) * 60 * congestion))
    incidents = []
    if congestion > 1.25:
        incidents.append("Heavy congestion near major junction (mock).")
    elif congestion > 1.1:
        incidents.append("Moderate traffic on arterial road (mock).")
    leave_by = "Leave now" if eta_minutes < 90 else "Leave within 15 min"
    poly = {"type":"LineString","coordinates":[[o["lng"],o["lat"]],[d["lng"],d["lat"]]]}
    return {"distance_km": round(km,1), "eta_minutes": eta_minutes, "incidents": incidents, "leave_by": leave_by, "polyline": poly}

@app.get("/api/parking")
def parking(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {"error":"unknown address"}
    rules = {
        "cust_1": {"cpz":"Westminster CPZ A (mock)","restrictions":["No loading 7–10am","Residents only 8:30–18:30"],"red_route":False,"bus_lane":True,"bay_types":["Pay & Display","Residents Permit"],"waiver_required":True},
        "cust_2": {"cpz":"City of Westminster CPZ B (mock)","restrictions":["Pay & Display 8–18:30"],"red_route":False,"bus_lane":False,"bay_types":["Pay & Display"],"waiver_required":False},
        "cust_3": {"cpz":"Private estate (mock)","restrictions":["Loading dock managed access"],"red_route":False,"bus_lane":False,"bay_types":["Loading Bay"],"waiver_required":False}
    }
    return rules.get(address_id, {"cpz":"Unknown","restrictions":[],"red_route":False,"bus_lane":False,"bay_types":[],"waiver_required":False})

@app.get("/api/building")
def building(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {"error":"unknown address"}
    meta = {
        "cust_1": {"floors": 3, "lift": False, "door_width_cm": 85, "stair_width_cm": 90, "rear_access": False},
        "cust_2": {"floors": 4, "lift": False, "door_width_cm": 80, "stair_width_cm": 85, "rear_access": False},
        "cust_3": {"floors": 50, "lift": True, "door_width_cm": 90, "stair_width_cm": 110, "rear_access": True}
    }
    return meta.get(address_id, {"floors": None, "lift": None, "door_width_cm": None, "stair_width_cm": None, "rear_access": None})

@app.get("/api/safety")
def safety(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {"error":"unknown address"}
    hazards = {
        "cust_1": {"width_restriction": "2.0m (mock)", "low_bridge": None, "one_way": True, "steep_gradient": False, "crime_risk": "Medium"},
        "cust_2": {"width_restriction": None, "low_bridge": None, "one_way": False, "steep_gradient": False, "crime_risk": "Low"},
        "cust_3": {"width_restriction": "2.4m (estate gate) (mock)", "low_bridge": None, "one_way": True, "steep_gradient": False, "crime_risk": "Low"}
    }
    return hazards.get(address_id, {"width_restriction": None, "low_bridge": None, "one_way": None, "steep_gradient": None, "crime_risk": None})

@app.get("/api/weather")
def weather(lat: float = Query(...), lng: float = Query(...), date: Optional[str] = None):
    conditions = ["Clear", "Partly Cloudy", "Cloudy", "Light Rain", "Heavy Rain", "Windy"]
    temp = round(random.uniform(8, 24), 1)
    wind = round(random.uniform(5, 28), 1)
    cond = random.choice(conditions)
    precip = 70 if "Rain" in cond else (20 if cond=="Cloudy" else 5)
    impact = []
    if "Rain" in cond: impact.append("Protect fabrics; allow extra loading time.")
    if wind > 20: impact.append("High wind: secure items; use extra straps.")
    return {"date": date or str(datetime.date.today()), "condition": cond, "temp_c": temp, "wind_kmh": wind,
            "precip_chance_pct": precip, "impact": impact}

@app.get("/api/compliance")
def compliance(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {"error":"unknown address"}
    base_url = "https://council.example/parking-waiver"
    waiver_link = f"{base_url}?address={a['label'].replace(' ','+')}&date=tbd&vehicle=Luton+van"
    checklist = [
        {"item":"Dynamic risk assessment completed","status":"pending"},
        {"item":"Parking/waiver checked","status":"pending"},
        {"item":"Lift booked (if applicable)","status":"pending"},
        {"item":"Customer confirmed access notes","status":"pending"}
    ]
    return {"waiver_required": True if address_id=='cust_1' else False, "waiver_link": waiver_link, "risk_checklist": checklist}
