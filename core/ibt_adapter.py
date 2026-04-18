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
    def __init__(self, file_path, meta_only=False):
        self.file_path = file_path
        self.channels = {}
        self.meta_only = meta_only
        self.head = type('Head', (), {'driver': 'iRacing User', 'vehicleid': 'iRacing Car', 'venue': 'iRacing Track', 'shortcomment': ''})()
        self._parse()

    def _parse(self):
        with open(self.file_path, 'rb') as f:
            # 1. Read Header (irsdk_header struct)
            f.seek(0)
            header_data = f.read(64)
            version = struct.unpack('<i', header_data[0:4])[0]
            tick_rate = struct.unpack('<i', header_data[8:12])[0]
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
            
            # Optimization: If meta_only, we only parse the Lap channel if it exists
            # to allow lap counting, otherwise skip everything else.
            vars_to_parse = var_headers
            if self.meta_only:
                vars_to_parse = [v for v in var_headers if v['name'] == 'Lap']

            if vars_to_parse:
                f.seek(buf_offset)
                raw_bytes = f.read(num_samples * buf_len)
                
                type_map = {
                    0: np.int8,
                    1: np.bool_,
                    2: np.int32,
                    3: np.uint32,
                    4: np.float32,
                    5: np.float64
                }

                for v in vars_to_parse:
                    t = v['type']
                    offset = v['offset']
                    np_type = type_map.get(t, np.float32)
                    
                    try:
                        arr = np.ndarray(
                            shape=(num_samples,),
                            dtype=np_type,
                            buffer=raw_bytes,
                            offset=offset,
                            strides=(buf_len,)
                        )
                        self.channels[v['name']] = IBTChannel(v['name'], arr.astype(float), v['unit'])
                    except Exception:
                        self.channels[v['name']] = IBTChannel(v['name'], np.zeros(num_samples), v['unit'])

            if not self.meta_only:
                self._apply_aliases()

    def _parse_yaml_setup(self, yaml):
        # Metadata
        track = re.search(r'TrackDisplayName:\s*(.*?)\n', yaml)
        if track: self.head.venue = track.group(1).strip()
        car = re.search(r'DriverCarName:\s*(.*?)\n', yaml)
        if not car: car = re.search(r'CarPath:\s*(.*?)\n', yaml)
        if car: self.head.vehicleid = car.group(1).strip()

        if self.meta_only:
            return

        # Map typical iRacing setup names to MoTeC-like names for the viewer
        def get_val(key_pattern):
            m = re.search(key_pattern + r':\s*([-+]?\d*\.\d+|\d+)', yaml)
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
        if 'LatAccel' in self.channels:
            self.channels['G Force Lat'] = IBTChannel('G Force Lat', self.channels['LatAccel'].data / 9.80665, "G")
        if 'LongAccel' in self.channels:
            self.channels['G Force Long'] = IBTChannel('G Force Long', self.channels['LongAccel'].data / 9.80665, "G")
        
        if 'Lap' in self.channels:
            self.channels['Lap Number'] = self.channels['Lap']
        if 'LapDist' in self.channels:
            self.channels['Lap Distance'] = self.channels['LapDist']
        if 'SessionTime' in self.channels:
            self.channels['Time'] = self.channels['SessionTime']
        
        # Ride Heights (iRacing natively exports these as LF, RF, LR, RR in meters)
        if 'LFcarrideheight' in self.channels:
            self.channels['Ride Height FL'] = IBTChannel('Ride Height FL', self.channels['LFcarrideheight'].data, "m")
        elif 'LFrideHeight' in self.channels:
            self.channels['Ride Height FL'] = IBTChannel('Ride Height FL', self.channels['LFrideHeight'].data, "m")
        elif 'LFshdeflect' in self.channels:
            self.channels['Ride Height FL'] = IBTChannel('Ride Height FL', self.channels['LFshdeflect'].data, "m")
        elif 'LFshockDefl' in self.channels:
            self.channels['Ride Height FL'] = IBTChannel('Ride Height FL', self.channels['LFshockDefl'].data, "m")

        if 'RFcarrideheight' in self.channels:
            self.channels['Ride Height FR'] = IBTChannel('Ride Height FR', self.channels['RFcarrideheight'].data, "m")
        elif 'RFrideHeight' in self.channels:
            self.channels['Ride Height FR'] = IBTChannel('Ride Height FR', self.channels['RFrideHeight'].data, "m")
        elif 'RFshdeflect' in self.channels:
            self.channels['Ride Height FR'] = IBTChannel('Ride Height FR', self.channels['RFshdeflect'].data, "m")
        elif 'RFshockDefl' in self.channels:
            self.channels['Ride Height FR'] = IBTChannel('Ride Height FR', self.channels['RFshockDefl'].data, "m")

        if 'LRcarrideheight' in self.channels:
            self.channels['Ride Height RL'] = IBTChannel('Ride Height RL', self.channels['LRcarrideheight'].data, "m")
        elif 'LRrideHeight' in self.channels:
            self.channels['Ride Height RL'] = IBTChannel('Ride Height RL', self.channels['LRrideHeight'].data, "m")
        elif 'LRshdeflect' in self.channels:
            self.channels['Ride Height RL'] = IBTChannel('Ride Height RL', self.channels['LRshdeflect'].data, "m")
        elif 'LRshockDefl' in self.channels:
            self.channels['Ride Height RL'] = IBTChannel('Ride Height RL', self.channels['LRshockDefl'].data, "m")

        if 'RRcarrideheight' in self.channels:
            self.channels['Ride Height RR'] = IBTChannel('Ride Height RR', self.channels['RRcarrideheight'].data, "m")
        elif 'RRrideHeight' in self.channels:
            self.channels['Ride Height RR'] = IBTChannel('Ride Height RR', self.channels['RRrideHeight'].data, "m")
        elif 'RRshdeflect' in self.channels:
            self.channels['Ride Height RR'] = IBTChannel('Ride Height RR', self.channels['RRshdeflect'].data, "m")
        elif 'RRshockDefl' in self.channels:
            self.channels['Ride Height RR'] = IBTChannel('Ride Height RR', self.channels['RRshockDefl'].data, "m")

        # Shock Velocities
        if 'LFshockvel' in self.channels:
            self.channels['Damper Pos FL'] = IBTChannel('Damper Pos FL', self.channels['LFshockvel'].data, "m/s")
        elif 'LFshockVel' in self.channels:
            self.channels['Damper Pos FL'] = IBTChannel('Damper Pos FL', self.channels['LFshockVel'].data, "m/s")
            
        if 'RFshockvel' in self.channels:
            self.channels['Damper Pos FR'] = IBTChannel('Damper Pos FR', self.channels['RFshockvel'].data, "m/s")
        elif 'RFshockVel' in self.channels:
            self.channels['Damper Pos FR'] = IBTChannel('Damper Pos FR', self.channels['RFshockVel'].data, "m/s")
            
        if 'LRshockvel' in self.channels:
            self.channels['Damper Pos RL'] = IBTChannel('Damper Pos RL', self.channels['LRshockvel'].data, "m/s")
        elif 'LRshockVel' in self.channels:
            self.channels['Damper Pos RL'] = IBTChannel('Damper Pos RL', self.channels['LRshockVel'].data, "m/s")
            
        if 'RRshockvel' in self.channels:
            self.channels['Damper Pos RR'] = IBTChannel('Damper Pos RR', self.channels['RRshockvel'].data, "m/s")
        elif 'RRshockVel' in self.channels:
            self.channels['Damper Pos RR'] = IBTChannel('Damper Pos RR', self.channels['RRshockVel'].data, "m/s")

        # Suspension Load mapping (Required for Aero Mapping tool)
        # Use real spring rates if we found them in the YAML setup. 
        # Note: iRacing usually outputs N/mm. Deflection is in meters.
        # To get Newtons: Deflection(m) * 1000(mm/m) * SpringRate(N/mm)
        k_fl = self.channels['SpringRateFL'].data[0] * 1000.0 if 'SpringRateFL' in self.channels else 1000.0
        k_fr = self.channels['SpringRateFR'].data[0] * 1000.0 if 'SpringRateFR' in self.channels else 1000.0
        k_rl = self.channels['SpringRateRL'].data[0] * 1000.0 if 'SpringRateRL' in self.channels else 1000.0
        k_rr = self.channels['SpringRateRR'].data[0] * 1000.0 if 'SpringRateRR' in self.channels else 1000.0

        if 'LFshockdeflect' in self.channels:
            self.channels['Suspension Load FL'] = IBTChannel('Suspension Load FL', self.channels['LFshockdeflect'].data * k_fl, "N")
        elif 'LFshockDefl' in self.channels:
            self.channels['Suspension Load FL'] = IBTChannel('Suspension Load FL', self.channels['LFshockDefl'].data * k_fl, "N")

        if 'RFshockdeflect' in self.channels:
            self.channels['Suspension Load FR'] = IBTChannel('Suspension Load FR', self.channels['RFshockdeflect'].data * k_fr, "N")
        elif 'RFshockDefl' in self.channels:
            self.channels['Suspension Load FR'] = IBTChannel('Suspension Load FR', self.channels['RFshockDefl'].data * k_fr, "N")

        if 'LRshockdeflect' in self.channels:
            self.channels['Suspension Load RL'] = IBTChannel('Suspension Load RL', self.channels['LRshockdeflect'].data * k_rl, "N")
        elif 'LRshockDefl' in self.channels:
            self.channels['Suspension Load RL'] = IBTChannel('Suspension Load RL', self.channels['LRshockDefl'].data * k_rl, "N")

        if 'RRshockdeflect' in self.channels:
            self.channels['Suspension Load RR'] = IBTChannel('Suspension Load RR', self.channels['RRshockdeflect'].data * k_rr, "N")
        elif 'RRshockDefl' in self.channels:
            self.channels['Suspension Load RR'] = IBTChannel('Suspension Load RR', self.channels['RRshockDefl'].data * k_rr, "N")


    def __getitem__(self, key):
        return self.channels[key]

    def __contains__(self, key):
        return key in self.channels

    def __iter__(self):
        return iter(self.channels)

def fromfile(file_path, meta_only=False):
    return IBTData(file_path, meta_only=meta_only)
