import struct
import numpy as np
import os
import re

class IBTChannel:
    def __init__(self, name, data, unit=""):
        self.name = name
        self.data = np.array(data)
        self.unit = unit

class IBTData:
    def __init__(self, file_path, meta_only=False, overrides=None):
        self.file_path = file_path
        self.channels = {}
        self.meta_only = meta_only
        self.overrides = overrides or {} # Dictionary of physics constants
        self.head = type('Head', (), {'driver': 'iRacing User', 'vehicleid': 'iRacing Car', 'venue': 'iRacing Track', 'shortcomment': ''})()
        self._parse()

    def _parse(self):
        with open(self.file_path, 'rb') as f:
            # 1. Read Header
            f.seek(0)
            header_data = f.read(64)
            session_info_len = struct.unpack('<i', header_data[16:20])[0]
            session_info_offset = struct.unpack('<i', header_data[20:24])[0]
            num_vars = struct.unpack('<i', header_data[24:28])[0]
            var_header_offset = struct.unpack('<i', header_data[28:32])[0]
            buf_len = struct.unpack('<i', header_data[36:40])[0]
            buf_offset = struct.unpack('<i', header_data[52:56])[0]

            # 2. Extract Session Info (YAML)
            f.seek(session_info_offset)
            session_info_raw = f.read(session_info_len).decode('iso-8859-1', errors='ignore')
            self.head.session_info_yaml = session_info_raw
            self._parse_yaml_setup(session_info_raw)

            # 3. Extract Variable Headers
            var_headers = []
            f.seek(var_header_offset)
            for i in range(num_vars):
                raw = f.read(144)
                v_type = struct.unpack('<i', raw[0:4])[0]
                v_offset = struct.unpack('<i', raw[4:8])[0]
                v_name = raw[16:48].decode('iso-8859-1').strip('\0')
                v_unit = raw[48:80].decode('iso-8859-1').strip('\0')
                var_headers.append({'type': v_type, 'offset': v_offset, 'name': v_name, 'unit': v_unit})

            # 4. Parse Telemetry Samples
            f.seek(0, os.SEEK_END)
            file_size = f.tell()
            num_samples = (file_size - buf_offset) // buf_len
            
            vars_to_parse = var_headers
            if self.meta_only:
                vars_to_parse = [v for v in var_headers if v['name'] == 'Lap']

            if vars_to_parse:
                f.seek(buf_offset)
                raw_bytes = f.read(num_samples * buf_len)
                
                type_map = {0: np.int8, 1: np.bool_, 2: np.int32, 3: np.uint32, 4: np.float32, 5: np.float64}

                for v in vars_to_parse:
                    t = v['type']
                    offset = v['offset']
                    np_type = type_map.get(t, np.float32)
                    try:
                        arr = np.ndarray(shape=(num_samples,), dtype=np_type, buffer=raw_bytes, offset=offset, strides=(buf_len,))
                        self.channels[v['name']] = IBTChannel(v['name'], arr.astype(float), v['unit'])
                    except Exception:
                        self.channels[v['name']] = IBTChannel(v['name'], np.zeros(num_samples), v['unit'])

            if not self.meta_only:
                self._apply_aliases()

    def _parse_yaml_setup(self, yaml_str):
        track = re.search(r'TrackDisplayName:\s*(.*?)\n', yaml_str)
        if track: self.head.venue = track.group(1).strip()
        car = re.search(r'DriverCarName:\s*(.*?)\n', yaml_str)
        if not car: car = re.search(r'CarPath:\s*(.*?)\n', yaml_str)
        if car: self.head.vehicleid = car.group(1).strip()

        if self.meta_only: return

        def get_val(key_pattern):
            m = re.search(key_pattern + r':\s*([-+]?\d*\.\d+|\d+)', yaml_str)
            return float(m.group(1)) if m else None

        setup_map = {
            'LFcoldPressure': r'LeftFront:\s+StartingPressure',
            'RFcoldPressure': r'RightFront:\s+StartingPressure',
            'LRcoldPressure': r'LeftRear:\s+StartingPressure',
            'RRcoldPressure': r'RightRear:\s+StartingPressure',
            'LFrideHeight': r'LeftFront:\s+RideHeight',
            'RFrideHeight': r'RightFront:\s+RideHeight',
            'LRrideHeight': r'LeftRear:\s+RideHeight',
            'RRrideHeight': r'RightRear:\s+RideHeight',
            'SpringRateFL': r'LeftFront:\s+SpringRate',
            'SpringRateFR': r'RightFront:\s+SpringRate',
            'SpringRateRL': r'LeftRear:\s+SpringRate',
            'SpringRateRR': r'RightRear:\s+SpringRate',
            'RearWing': r'WingAngle',
            'BrakeBias': r'BrakePressureBias',
        }

        for motec_key, ir_pattern in setup_map.items():
            val = get_val(ir_pattern)
            if val is not None:
                self.channels[motec_key] = IBTChannel(motec_key, [val], "")

    def _apply_aliases(self):
        # ... (Existing Aliases: Accel, Lap, Ride Height, etc)
        if 'LatAccel' in self.channels: self.channels['G Force Lat'] = IBTChannel('G Force Lat', self.channels['LatAccel'].data / 9.80665, "G")
        if 'LongAccel' in self.channels: self.channels['G Force Long'] = IBTChannel('G Force Long', self.channels['LongAccel'].data / 9.80665, "G")
        if 'Lap' in self.channels: self.channels['Lap Number'] = self.channels['Lap']
        if 'LapDist' in self.channels: self.channels['Lap Distance'] = self.channels['LapDist']
        if 'SessionTime' in self.channels: self.channels['Time'] = self.channels['SessionTime']
        
        for corner in ['FL', 'FR', 'RL', 'RR']:
            names = [f'LFcarrideheight', f'LFrideHeight', f'LFshdeflect', f'LFshockDefl'] if corner == 'FL' else \
                    ([f'RFcarrideheight', f'RFrideHeight', f'RFshdeflect', f'RFshockDefl'] if corner == 'FR' else \
                    ([f'LRcarrideheight', f'LRrideHeight', f'LRshdeflect', f'LRshockDefl'] if corner == 'RL' else \
                    [f'RRcarrideheight', f'RRrideHeight', f'RRshdeflect', f'RRshockDefl']))
            
            for n in names:
                if n in self.channels:
                    self.channels[f'Ride Height {corner}'] = IBTChannel(f'Ride Height {corner}', self.channels[n].data, "m")
                    break

        # Physics Model Override Injection
        # ---------------------------------------------------------
        model = self.overrides.get('physics_model', {})
        springs = model.get('spring_rate_npm', {}) # Expects N/m
        mrs = model.get('motion_ratios', {})      # Expects 0.0 - 1.0
        
        for corner in ['FL', 'FR', 'RL', 'RR']:
            # 1. Determine Spring Rate (k)
            # Priority: SimGit Override > YAML Setup > Generic Fallback (1000.0 N/mm -> 1M N/m)
            k = springs.get(corner)
            if k is None:
                yaml_key = f'SpringRate{corner}'
                if yaml_key in self.channels:
                    k = self.channels[yaml_key].data[0] * 1000.0 # Convert N/mm to N/m
                else:
                    k = 1000.0 * 1000.0 # Standard fallback
            
            # 2. Determine Motion Ratio (MR)
            mr = mrs.get(corner, 1.0) # Default to 1:1 if not provided
            
            # 3. Calculate Wheel Rate (Kw = K * MR^2)
            kw = k * (mr ** 2)
            
            # 4. Map Deflection to Suspension Load
            defl_names = [f'LFshockdeflect', f'LFshockDefl'] if corner == 'FL' else \
                         ([f'RFshockdeflect', f'RFshockDefl'] if corner == 'FR' else \
                         ([f'LRshockdeflect', f'LRshockDefl'] if corner == 'RL' else \
                         [f'RRshockdeflect', f'RRshockDefl']))
            
            for n in defl_names:
                if n in self.channels:
                    # Suspension Load (Newtons) = Deflection(m) * Wheel Rate (N/m)
                    self.channels[f'Suspension Load {corner}'] = IBTChannel(f'Suspension Load {corner}', self.channels[n].data * kw, "N")
                    break

    def __getitem__(self, key): return self.channels[key]
    def __contains__(self, key): return key in self.channels
    def __iter__(self): return iter(self.channels)

def fromfile(file_path, meta_only=False, overrides=None):
    return IBTData(file_path, meta_only=meta_only, overrides=overrides)
