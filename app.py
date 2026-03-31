from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


BASE_XG = {
    1:  0.42,   # Central 6-yard box
    2:  0.23,   # Penalty spot area   
    3:  0.13,   # Upper near-post    
    4:  0.13,   # Lower near-post     
    5:  0.07,   # Top corner          
    6:  0.07,   # Bottom corner       
    7:  0.11,   # Central pen area   
    8:  0.08,   # Upper pen area     
    9:  0.08,   # Lower pen area      
    10: 0.06,   # Top of the D        
    11: 0.04,   # Upper outside box   
    12: 0.04,   # Lower outside box   
    13: 0.02,   # Deep midfield       
    14: 0.01,   # Own half            
}

ZONE_NAMES = {
    1:  "Central 6-yard box",      2:  "Penalty spot area",
    3:  "Upper near-post",         4:  "Lower near-post",
    5:  "Top corner",              6:  "Bottom corner",
    7:  "Central penalty area",    8:  "Upper penalty area",
    9:  "Lower penalty area",      10: "Top of the D",
    11: "Upper outside box",       12: "Lower outside box",
    13: "Deep midfield",           14: "Own half",
}

PRESS_MULTIPLIER = {1: 1.35, 2: 1.00, 3: 0.72, 4: 0.52}
PRESS_LABELS = {
    1: "No pressure (no defenders within 8m)",
    2: "1 defender nearby",
    3: "2 defenders nearby",
    4: "3+ defenders nearby",
}


BALANCE_MULTIPLIER = {1: 0.65, 2: 0.88, 3: 1.10, 4: 1.28}
BALANCE_LABELS = {
    1: "0–1 attackers (overloaded defending)",
    2: "2–5 attackers (some support)",
    3: "6–8 attackers (good attacking numbers)",
    4: "9–11 attackers (numerical overload)",
}


def calculate_xg(zone, press, balance):
    raw = BASE_XG[zone] * PRESS_MULTIPLIER[press] * BALANCE_MULTIPLIER[balance]
    return round(max(0.01, min(0.99, raw)), 3)


def xg_rating(xg):
    if xg >= 0.35: return "High Danger",   "#ef4444"
    if xg >= 0.20: return "Good Chance",   "#f97316"
    if xg >= 0.10: return "Moderate",      "#eab308"
    if xg >= 0.04: return "Low Quality",   "#22c55e"
    return               "Speculative",    "#6b7280"


def grid_to_zone(gx, gy):
    """Map 21×17 grid coordinates to zone (1–14).
    gx=0 = own goal end, gx=20 = attacking goal.
    gy=0 = top, gy=16 = bottom.
    Mirrors StatsBomb coordinate space: gx=floor(x_sb/6), gy=floor(y_sb/5)
    """
    if gx <= 1:  return 14
    if gx <= 3:  return 13
    if gx <= 10: return 11 if gy <= 5 else (12 if gy >= 11 else 10)
    if gx <= 15: return 8  if gy <= 5 else (9  if gy >= 11 else 7)
    if gx <= 17: return 3  if gy <= 3 else (4  if gy >= 13 else 2)
    if gy <= 1:  return 5
    if gy <= 5:  return 3
    if gy <= 10: return 1
    if gy <= 14: return 4
    return 6


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    errors = {}
    zone = press = balance = None

    try:
        zone = int(request.form["zone"])
        if zone not in BASE_XG:
            errors["zone"] = "Zone must be between 1 and 14."
    except (KeyError, ValueError):
        errors["zone"] = "Enter a whole number (1–14)."

    try:
        press = int(request.form["press"])
        if press not in PRESS_MULTIPLIER:
            errors["press"] = "Press level must be 1, 2, 3, or 4."
    except (KeyError, ValueError):
        errors["press"] = "Enter a whole number (1–4)."

    try:
        balance = int(request.form["balance"])
        if balance not in BALANCE_MULTIPLIER:
            errors["balance"] = "Balance level must be 1, 2, 3, or 4."
    except (KeyError, ValueError):
        errors["balance"] = "Enter a whole number (1–4)."

    if errors:
        return render_template("index.html", errors=errors, prev=request.form)

    xg            = calculate_xg(zone, press, balance)
    rating, color = xg_rating(xg)

    result = {
        "xg": xg, "rating": rating, "color": color,
        "zone": zone, "press": press, "balance": balance,
        "zone_name":     ZONE_NAMES[zone],
        "base_xg":       BASE_XG[zone],
        "press_mult":    PRESS_MULTIPLIER[press],
        "balance_mult":  BALANCE_MULTIPLIER[balance],
        "press_label":   PRESS_LABELS[press],
        "balance_label": BALANCE_LABELS[balance],
        "formula":       (f"{BASE_XG[zone]:.2f} × "
                          f"{PRESS_MULTIPLIER[press]:.2f} × "
                          f"{BALANCE_MULTIPLIER[balance]:.2f} = {xg:.3f}"),
    }
    return render_template("index.html", result=result, prev=request.form)


@app.route("/grid_zone")
def grid_zone_api():
    """Return the zone for a given grid coordinate."""
    gx = int(request.args.get("gx", 0))
    gy = int(request.args.get("gy", 0))
    z = grid_to_zone(gx, gy)
    return jsonify({"zone": z, "zone_name": ZONE_NAMES[z], "base_xg": BASE_XG[z]})


if __name__ == "__main__":
    app.run(debug=True)
