from fastapi import FastAPI, Body, Query
from typing import Optional, Dict, Any
import os, math, random, datetime, urllib.parse, httpx

app = FastAPI(title='Pre-Survey — Sandbox Mode')

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

SAMPLE = {
  'addresses':[
    {'id':'cust_1','label':'10 Downing Street, London SW1A 2AA','lat':51.5033635,'lng':-0.1276248,
     'image_url':'https://placehold.co/640x360?text=Street+View+Mock','satellite_url':'https://placehold.co/320x180?text=Satellite+Mock',
     'type_guess':'terraced_house',
     'access':{'driveway': False,'stairs_visible': True,'double_yellow': True,'red_route': False,'narrow_road': True,'parking_zone':'CPZ A (mock)',
               'notes':['No on-site parking; kerbside restrictions likely.','Stairs at entrance; consider extra handling time.'],
               'crew_recommendation':'2-person crew','equipment':['trolley','ramps','blankets']}},
    {'id':'cust_2','label':'221B Baker Street, London NW1 6XE','lat':51.523767,'lng':-0.1585557,
     'image_url':'https://placehold.co/640x360?text=Street+View+Mock','satellite_url':'https://placehold.co/320x180?text=Satellite+Mock',
     'type_guess':'flat_above_shop',
     'access':{'driveway': False,'stairs_visible': True,'double_yellow': False,'red_route': False,'narrow_road': False,'parking_zone':'CPZ B (mock)',
               'notes':['Likely shared entrance; check lift availability.','On-street pay & display nearby.'],
               'crew_recommendation':'3-person crew (stairs)','equipment':['trolley','straps']}},
    {'id':'cust_3','label':'1 Canada Square, Canary Wharf, London E14 5AB','lat':51.505455,'lng':-0.0235,
     'image_url':'https://placehold.co/640x360?text=Street+View+Mock','satellite_url':'https://placehold.co/320x180?text=Satellite+Mock',
     'type_guess':'apartment_tower',
     'access':{'driveway': True,'stairs_visible': False,'double_yellow': False,'red_route': False,'narrow_road': False,'parking_zone':'Private access (mock)',
               'notes':['Service bay available; book lift with building mgmt.','Loading dock clearance ok for Luton vans.'],
               'crew_recommendation':'3-person crew','equipment':['dollies','blankets','straps']}}],
  'depots':[
    {'id':'depot_1','label':'Depot: Battersea, SW11','lat':51.465,'lng':-0.151},
    {'id':'depot_2','label':'Depot: Stratford, E15','lat':51.54,'lng':0.001}
  ]
}

ADDR_BY_ID = {a['id']:a for a in SAMPLE['addresses']}
DEPOT_BY_ID = {d['id']:d for d in SAMPLE['depots']}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R*c

def sandbox_geocode(text: str, center_lat=51.509, center_lng=-0.118):
    seed = abs(hash(text)) % 10000
    random.seed(seed)
    lat_off = random.uniform(-0.03, 0.03)
    lng_off = random.uniform(-0.05, 0.05)
    return {'id': f'sandbox_{seed}', 'label': f'{text} (sandbox match)', 'lat': center_lat + lat_off, 'lng': center_lng + lng_off}

@app.get('/api/sample_addresses')
def sample_addresses():
    return {'customers':[{'id':a['id'],'label':a['label']} for a in SAMPLE['addresses']],
            'depots':[{'id':d['id'],'label':d['label']} for d in SAMPLE['depots']]}

@app.post('/api/intake')
async def intake(payload: Dict[str, Any] = Body(...)):
    cust_id = payload.get('customer_address_id'); depot_id = payload.get('depot_id')
    cust_text = payload.get('customer_address_text'); depot_text = payload.get('depot_address_text')

    if cust_id and depot_id:
        if cust_id not in ADDR_BY_ID: return {'error':'unknown customer address'}
        if depot_id not in DEPOT_BY_ID: return {'error':'unknown depot'}
        return {'origin': DEPOT_BY_ID[depot_id], 'dest': ADDR_BY_ID[cust_id], 'mode':'mock_ids'}

    if cust_text and depot_text:
        if GOOGLE_API_KEY:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    g = 'https://maps.googleapis.com/maps/api/geocode/json'
                    rs = await client.get(g, params={'address': depot_text, 'key': GOOGLE_API_KEY})
                    rc = await client.get(g, params={'address': cust_text,  'key': GOOGLE_API_KEY})
                    o = rs.json(); d = rc.json()
                    if o.get('status')=='OK' and d.get('status')=='OK':
                        oo = o['results'][0]; dd = d['results'][0]
                        origin = {'id':'live_origin','label':oo['formatted_address'],'lat':oo['geometry']['location']['lat'],'lng':oo['geometry']['location']['lng']}
                        dest   = {'id':'live_dest','label':dd['formatted_address'],'lat':dd['geometry']['location']['lat'],'lng':dd['geometry']['location']['lng']}
                        return {'origin': origin, 'dest': dest, 'mode':'live_text'}
            except Exception:
                pass
        origin = sandbox_geocode(depot_text, 51.472, -0.142)
        dest   = sandbox_geocode(cust_text,  51.515, -0.141)
        return {'origin': origin, 'dest': dest, 'mode':'sandbox_text'}

    return {'error':'invalid_payload','hint':'Use mock IDs or free-text addresses.'}

@app.get('/api/property-image')
def property_image(address_id: Optional[str] = Query(None), lat: Optional[float] = Query(None), lng: Optional[float] = Query(None)):
    if address_id:
        a = ADDR_BY_ID.get(address_id)
        if not a: return {'error':'unknown address'}
        if GOOGLE_API_KEY:
            params = {'size':'640x360','location':f'{a["lat"]},{a["lng"]}','key':GOOGLE_API_KEY}
            sv_url = 'https://maps.googleapis.com/maps/api/streetview?' + urllib.parse.urlencode(params)
            sat = 'https://maps.googleapis.com/maps/api/staticmap?' + urllib.parse.urlencode({'center':f'{a["lat"]},{a["lng"]}','zoom':'18','size':'320x180','maptype':'satellite','key':GOOGLE_API_KEY})
            return {'image_url': sv_url, 'satellite_url': sat, 'type_guess': a['type_guess'], 'source':'live_if_available'}
        return {'image_url': a['image_url'], 'satellite_url': a['satellite_url'], 'type_guess': a['type_guess'], 'source':'mock'}
    if lat is not None and lng is not None:
        if GOOGLE_API_KEY:
            params = {'size':'640x360','location':f'{lat},{lng}','key':GOOGLE_API_KEY}
            sv_url = 'https://maps.googleapis.com/maps/api/streetview?' + urllib.parse.urlencode(params)
            sat = 'https://maps.googleapis.com/maps/api/staticmap?' + urllib.parse.urlencode({'center':f'{lat},{lng}','zoom':'18','size':'320x180','maptype':'satellite','key':GOOGLE_API_KEY})
            return {'image_url': sv_url, 'satellite_url': sat, 'type_guess': None, 'source':'live'}
        return {'image_url':'https://placehold.co/640x360?text=Street+View+Sandbox','satellite_url':'https://placehold.co/320x180?text=Satellite+Sandbox','type_guess':None,'source':'sandbox'}
    return {'error':'missing_params','hint':'Provide address_id or lat/lng.'}

@app.get('/api/access-insights')
def access_insights(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id)
    if not a: return {'error':'unknown address'}
    return a['access']

@app.get('/api/route')
async def route(origin_id: Optional[str] = Query(None), dest_id: Optional[str] = Query(None),
          origin_lat: Optional[float] = Query(None), origin_lng: Optional[float] = Query(None),
          dest_lat: Optional[float] = Query(None), dest_lng: Optional[float] = Query(None)):
    if origin_lat is not None and origin_lng is not None and dest_lat is not None and dest_lng is not None:
        if GOOGLE_API_KEY:
            try:
                url = 'https://maps.googleapis.com/maps/api/directions/json'
                params = {'origin': f'{origin_lat},{origin_lng}', 'destination': f'{dest_lat},{dest_lng}', 'departure_time': 'now', 'traffic_model':'best_guess', 'key': GOOGLE_API_KEY}
                data = (await httpx.AsyncClient(timeout=15.0).get(url, params=params)).json()
                if data.get('status')=='OK':
                    leg = data['routes'][0]['legs'][0]
                    eta = int(leg.get('duration_in_traffic', leg['duration'])['value']/60)
                    km = round(leg['distance']['value']/1000.0, 1)
                    return {'distance_km': km, 'eta_minutes': eta, 'incidents': [], 'leave_by': 'Plan 10 min buffer', 'polyline': None, 'source':'live'}
            except Exception:
                pass
        km = haversine(origin_lat, origin_lng, dest_lat, dest_lng)
        cong = random.uniform(0.9, 1.3)
        eta = max(5, int((km / 25.0) * 60 * cong))
        incidents = ['Congestion near ring road (sandbox).'] if cong>1.2 else (['Slower traffic than usual (sandbox).'] if cong>1.05 else [])
        poly = {'type':'LineString','coordinates':[[origin_lng,origin_lat],[dest_lng,dest_lat]]}
        return {'distance_km': round(km,1), 'eta_minutes': eta, 'incidents': incidents, 'leave_by': 'Leave within 15 min', 'polyline': poly, 'source':'sandbox'}

    if origin_id and dest_id:
        o = DEPOT_BY_ID.get(origin_id); d = ADDR_BY_ID.get(dest_id)
        if not o or not d: return {'error':'unknown origin/dest'}
        km = haversine(o['lat'], o['lng'], d['lat'], d['lng'])
        cong = random.uniform(0.85, 1.35)
        eta = max(5, int((km / 25.0) * 60 * cong))
        incidents = ['Moderate traffic on arterial road (mock).'] if cong>1.1 else []
        poly = {'type':'LineString','coordinates':[[o['lng'],o['lat']],[d['lng'],d['lat']]]}
        return {'distance_km': round(km,1), 'eta_minutes': eta, 'incidents': incidents, 'leave_by':'Leave now' if eta<90 else 'Leave within 15 min', 'polyline': poly, 'source':'mock'}

    return {'error':'missing_params','hint':'Provide origin/dest — either IDs or lat/lng.'}

@app.get('/api/parking')
def parking(address_id: str = Query(...)):
    rules = {
        'cust_1': {'cpz':'Westminster CPZ A (mock)','restrictions':['No loading 7–10am','Residents only 8:30–18:30'],'red_route':False,'bus_lane':True,'bay_types':['Pay & Display','Residents Permit'],'waiver_required':True},
        'cust_2': {'cpz':'City of Westminster CPZ B (mock)','restrictions':['Pay & Display 8–18:30'],'red_route':False,'bus_lane':False,'bay_types':['Pay & Display'],'waiver_required':False},
        'cust_3': {'cpz':'Private estate (mock)','restrictions':['Loading dock managed access'],'red_route':False,'bus_lane':False,'bay_types':['Loading Bay'],'waiver_required':False}
    }
    return rules.get(address_id, {'cpz':'Unknown','restrictions':[],'red_route':False,'bus_lane':False,'bay_types':[],'waiver_required':False})

@app.get('/api/building')
def building(address_id: str = Query(...)):
    meta = {
        'cust_1': {'floors': 3, 'lift': False, 'door_width_cm': 85, 'stair_width_cm': 90, 'rear_access': False},
        'cust_2': {'floors': 4, 'lift': False, 'door_width_cm': 80, 'stair_width_cm': 85, 'rear_access': False},
        'cust_3': {'floors': 50, 'lift': True, 'door_width_cm': 90, 'stair_width_cm': 110, 'rear_access': True}
    }
    return meta.get(address_id, {'floors': None, 'lift': None, 'door_width_cm': None, 'stair_width_cm': None, 'rear_access': None})

@app.get('/api/safety')
def safety(address_id: str = Query(...)):
    hazards = {
        'cust_1': {'width_restriction': '2.0m (mock)', 'low_bridge': None, 'one_way': True, 'steep_gradient': False, 'crime_risk': 'Medium'},
        'cust_2': {'width_restriction': None, 'low_bridge': None, 'one_way': False, 'steep_gradient': False, 'crime_risk': 'Low'},
        'cust_3': {'width_restriction': '2.4m (estate gate) (mock)', 'low_bridge': None, 'one_way': True, 'steep_gradient': False, 'crime_risk': 'Low'}
    }
    return hazards.get(address_id, {'width_restriction': None, 'low_bridge': None, 'one_way': None, 'steep_gradient': None, 'crime_risk': None})

@app.get('/api/weather')
async def weather(lat: float = Query(...), lng: float = Query(...), date: Optional[str] = None):
    try:
        url = 'https://api.open-meteo.com/v1/forecast'
        params = {'latitude': lat, 'longitude': lng, 'hourly': 'temperature_2m,precipitation,wind_speed_10m', 'current_weather': 'true'}
        j = (await httpx.AsyncClient(timeout=10.0).get(url, params=params)).json()
        cw = j.get('current_weather', {})
        temp = cw.get('temperature'); wind = cw.get('windspeed')
        cond = 'Clear' if (cw.get('weathercode',0) in (0,1)) else 'Cloudy'
        precip_chance = 50 if cond!='Clear' else 10
        return {'date': date or str(datetime.date.today()), 'condition': cond, 'temp_c': temp, 'wind_kmh': wind, 'precip_chance_pct': precip_chance, 'impact': [], 'source':'live'}
    except Exception:
        pass
    conditions = ['Clear', 'Partly Cloudy', 'Cloudy', 'Light Rain', 'Heavy Rain', 'Windy']
    temp = round(random.uniform(8, 24), 1)
    wind = round(random.uniform(5, 28), 1)
    cond = random.choice(conditions)
    precip = 70 if 'Rain' in cond else (20 if cond=='Cloudy' else 5)
    impact = []
    if 'Rain' in cond: impact.append('Protect fabrics; allow extra loading time.')
    if wind > 20: impact.append('High wind: secure items; use extra straps.')
    return {'date': date or str(datetime.date.today()), 'condition': cond, 'temp_c': temp, 'wind_kmh': wind, 'precip_chance_pct': precip, 'impact': impact, 'source':'sandbox'}

@app.get('/api/compliance')
def compliance(address_id: str = Query(...)):
    a = ADDR_BY_ID.get(address_id, {'label':'Unknown'})
    base_url = 'https://council.example/parking-waiver'
    waiver_link = f"{base_url}?address={urllib.parse.quote_plus(a['label'])}&date=tbd&vehicle=Luton+van"
    checklist = [
        {'item':'Dynamic risk assessment completed','status':'pending'},
        {'item':'Parking/waiver checked','status':'pending'},
        {'item':'Lift booked (if applicable)','status':'pending'},
        {'item':'Customer confirmed access notes','status':'pending'}
    ]
    return {'waiver_required': True if address_id=='cust_1' else False, 'waiver_link': waiver_link, 'risk_checklist': checklist}
