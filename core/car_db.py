import json
import os

CAR_DB_FILE = 'car_specs.json'

# Initial database with some common iRacing cars
DEFAULT_SPECS = {
    "porsche992cup": {"wheelbase": 2.459, "steering_ratio": 14.2},
    "porsche992gt3r": {"wheelbase": 2.507, "steering_ratio": 13.0},
    "ferrari296gt3": {"wheelbase": 2.620, "steering_ratio": 14.0},
    "dallarap217": {"wheelbase": 3.005, "steering_ratio": 15.0},
    "mercedesgt32020": {"wheelbase": 2.625, "steering_ratio": 14.0},
    "bmwm4gt3": {"wheelbase": 2.857, "steering_ratio": 13.0},
    "f360": {"wheelbase": 2.700, "steering_ratio": 14.0},
}

def load_car_specs():
    if os.path.exists(CAR_DB_FILE):
        try:
            with open(CAR_DB_FILE, 'r') as f:
                return json.load(f)
        except:
            return DEFAULT_SPECS
    return DEFAULT_SPECS

def save_car_specs(db):
    with open(CAR_DB_FILE, 'w') as f:
        json.dump(db, f, indent=4)

def get_car_spec(car_name):
    db = load_car_specs()
    # Clean car name (lowercase, no spaces)
    clean_name = car_name.lower().replace(" ", "")
    
    if clean_name in db:
        return db[clean_name]
    
    # Heuristic: check if any key is in the car_name
    for key in db:
        if key in clean_name:
            return db[key]
            
    return None

def update_car_spec(car_name, wheelbase, steering_ratio):
    db = load_car_specs()
    clean_name = car_name.lower().replace(" ", "")
    db[clean_name] = {
        "wheelbase": float(wheelbase),
        "steering_ratio": float(steering_ratio)
    }
    save_car_specs(db)
