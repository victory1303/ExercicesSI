# graphe.py (version : on garde seulement bleu + jaune, on supprime la ligne rouge)
import os
import googlemaps
import json
import webbrowser
from datetime import datetime

# --------- CONFIG ----------
API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyAwd1S8sAWIMsxdSvHrkk55v62gf6MlDH8")
gmaps = googlemaps.Client(key=API_KEY)

# Définir les arrêts/candidats
stops = [
    "Rond-point Victoire, Kinshasa, DRC",          # START
    "Marché Central, Kinshasa, DRC",
    "Avenue du 30 Juin & Boulevard du 30 Juin, Kinshasa",
    "Hôpital Général, Kinshasa, DRC",
    "Gare Centrale, Kinshasa, DRC"                 # END
]
START = stops[0]
END = stops[-1]

# Trois variantes de routes
route_waypoints = [
    [],  # route A
    ["Marché Central, Kinshasa, DRC"],  # route B
    [
        "Avenue du 30 Juin & Boulevard du 30 Juin, Kinshasa",
        "Hôpital Général, Kinshasa, DRC"
    ]  # route C
]

# ----------- GÉOCODAGE ----------
def geocode(address):
    res = gmaps.geocode(address)
    if not res:
        raise RuntimeError("Geocode failed for " + address)
    loc = res[0]["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"]}

coords = {}
for s in stops:
    try:
        coords[s] = geocode(s)
    except Exception as e:
        print("Geocode error:", s, e)
        coords[s] = None

print("Coords obtenues pour les arrêts.")

# ----------- RÉCUPÉRATION DES ROUTES ----------
routes = []
for wp_list in route_waypoints:
    print("Requesting directions with waypoints:", wp_list)
    try:
        directions = gmaps.directions(
            origin=START,
            destination=END,
            mode="driving",
            waypoints=wp_list if wp_list else None,
            departure_time="now",
            alternatives=False
        )
    except Exception as e:
        print("Directions API error:", e)
        directions = None

    if not directions:
        raise RuntimeError("Aucune direction retournée pour waypoints=" + str(wp_list))

    overview_poly = directions[0].get("overview_polyline", {}).get("points")
    stops_count = len(wp_list)

    distance = 0
    duration = 0
    for leg in directions[0].get("legs", []):
        if "distance" in leg:
            distance += leg["distance"].get("value", 0)
        if "duration" in leg:
            duration += leg["duration"].get("value", 0)

    routes.append({
        "waypoints": wp_list,
        "stops_count": stops_count,
        "poly": overview_poly,
        "distance_m": distance,
        "duration_s": duration
    })

# ----------- COULEURS DES ROUTES (keep only two: blue + yellow) ----------
# We sort by stops_count and assign blue to best, yellow to second, the rest -> None (skipped)
order = sorted(range(len(routes)), key=lambda i: routes[i]["stops_count"])
colors_per_index = [None] * len(routes)
palette = ["blue", "yellow"]  # only two colors
for rank, idx in enumerate(order):
    if rank < len(palette):
        colors_per_index[idx] = palette[rank]
    else:
        colors_per_index[idx] = None  # skip this route (no color => won't be drawn)

# ----------- EXPORT JSON POUR HTML ----------
html_routes = []
for i, r in enumerate(routes):
    html_routes.append({
        "poly": r["poly"],
        "stops_count": r["stops_count"],
        "distance_m": r["distance_m"],
        "duration_s": r["duration_s"],
        "waypoints": r["waypoints"],
        "color": colors_per_index[i]
    })

major_stop_icons = {}
for r in routes:
    for w in r["waypoints"]:
        major_stop_icons[w] = True

markers = []
for s in stops:
    markers.append({
        "title": s,
        "coord": coords[s],
        "is_major": bool(major_stop_icons.get(s, False)),
        "is_end": (s == END),
        "is_start": (s == START)
    })

# ----------- TEMPLATE HTML (draw only routes with color != null) ----------
html_template = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Graphes: Victoire -> Gare Centrale (bleu + jaune)</title>
  <style>
    html, body, #map {{ height: 100%; margin: 0; padding: 0; }}
    #map {{ height: 100vh; width: 100%; }}
    .legend {{
      background: white;
      padding: 10px;
      font-size: 14px;
      box-shadow: 0 2px 6px rgba(0,0,0,0.3);
      margin: 10px;
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <div id="legend" class="legend"></div>

  <script>
    const ROUTES = {json.dumps(html_routes)};
    const MARKERS = {json.dumps(markers)};
    const API_KEY = "{API_KEY}";

    function initMap() {{
      const start = MARKERS.find(m => m.is_start).coord;
      const map = new google.maps.Map(document.getElementById('map'), {{
        zoom: 13,
        center: start,
        mapTypeId: 'roadmap'
      }});

      const bounds = new google.maps.LatLngBounds();
      const destMarker = MARKERS.find(m => m.is_end && m.coord);
      const destLatLng = destMarker ? new google.maps.LatLng(destMarker.coord.lat, destMarker.coord.lng) : null;

      ROUTES.forEach((r, idx) => {{
        // skip routes without color (we removed red)
        if (!r.color) return;

        const path = google.maps.geometry.encoding.decodePath(r.poly || "");
        const latLngs = path.map(p => new google.maps.LatLng(p.lat(), p.lng()));

        // TRIM near destination to avoid tiny overshoot
        let usedLatLngs = latLngs;
        if (destLatLng && latLngs.length > 0) {{
          let minIdx = latLngs.length - 1;
          let minDist = Infinity;
          for (let i = 0; i < latLngs.length; i++) {{
            const d = google.maps.geometry.spherical.computeDistanceBetween(latLngs[i], destLatLng);
            if (d < minDist) {{
              minDist = d;
              minIdx = i;
            }}
          }}
          usedLatLngs = latLngs.slice(0, Math.min(minIdx + 1, latLngs.length));
          const last = usedLatLngs[usedLatLngs.length - 1];
          if (last && google.maps.geometry.spherical.computeDistanceBetween(last, destLatLng) > 5) {{
            usedLatLngs.push(destLatLng);
          }}
        }}

        const line = new google.maps.Polyline({{
          path: usedLatLngs,
          strokeColor: r.color,
          strokeOpacity: 0.95,
          strokeWeight: (r.color === 'blue') ? 8 : 6,
          map: map
        }});

        const info = new google.maps.InfoWindow();
        line.addListener('click', (ev) => {{
          const content = `<div><b>${{idx+1}}</b><br/>Arrêts: ${{r.stops_count}}<br/>Distance: ${{Math.round(r.distance_m)}} m<br/>Durée: ${{Math.round(r.duration_s)}} s</div>`;
          info.setContent(content);
          info.setPosition(ev.latLng);
          info.open(map);
        }});

        usedLatLngs.forEach(p => bounds.extend(p));
      }});

      // markers
      MARKERS.forEach(m => {{
        if (!m.coord) return;
        let icon = null;
        if (m.is_end) icon = 'http://maps.google.com/mapfiles/ms/icons/green-dot.png';
        else if (m.is_start) icon = 'http://maps.google.com/mapfiles/ms/icons/blue-dot.png';
        else if (m.is_major) icon = 'http://maps.google.com/mapfiles/ms/icons/black-dot.png';
        else icon = 'http://maps.google.com/mapfiles/ms/icons/red-dot.png';

        const marker = new google.maps.Marker({{
          position: m.coord,
          map: map,
          title: m.title,
          icon: icon
        }});

        const iw = new google.maps.InfoWindow({{
          content: `<div><b>${{m.title}}</b></div>`
        }});

        marker.addListener('click', () => iw.open(map, marker));
        bounds.extend(new google.maps.LatLng(m.coord.lat, m.coord.lng));
      }});

      map.fitBounds(bounds);

      const legend = document.getElementById('legend');
      // Updated legend: only blue and yellow routes
      legend.innerHTML = `
        <div><b>Légende</b></div>
        <div><img src="http://maps.google.com/mapfiles/ms/icons/blue-dot.png"> Départ (Victoire)</div>
        <div><img src="http://maps.google.com/mapfiles/ms/icons/green-dot.png"> Arrivée (Gare Centrale)</div>
        <div><img src="http://maps.google.com/mapfiles/ms/icons/black-dot.png"> Grand arrêt</div>
        <div style="margin-top:6px"><span style="display:inline-block;width:16px;height:6px;background:blue;margin-right:6px"></span> Trajet — moins d'arrêts (bleu)</div>
        <div><span style="display:inline-block;width:16px;height:6px;background:yellow;margin-right:6px"></span> Trajet — moyen (jaune)</div>
      `;
      map.controls[google.maps.ControlPosition.RIGHT_TOP].push(legend);
    }}
  </script>

  <script async src="https://maps.googleapis.com/maps/api/js?key={API_KEY}&libraries=geometry&callback=initMap"></script>
</body>
</html>
"""

# ----------- SAUVEGARDE HTML -----------
out_file = "graph_routes_victoire_gare.html"
with open(out_file, "w", encoding="utf-8") as f:
    f.write(html_template)

print("Fichier généré :", out_file)
webbrowser.open("file://" + os.path.abspath(out_file))
