import re

with open('core/ibt_adapter.py', 'r') as f:
    content = f.read()

# Add saving of yaml to self.head
if "self.head.session_info_yaml = session_info_raw" not in content:
    content = content.replace("self._parse_yaml_setup(session_info_raw)", 
                              "self.head.session_info_yaml = session_info_raw\n            self._parse_yaml_setup(session_info_raw)")

# Extract spring rates
if "'SpringRateFL'" not in content:
    spring_maps = """
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
"""
    content = re.sub(r'setup_map = \{[^}]+\}', spring_maps, content, flags=re.MULTILINE)

with open('core/ibt_adapter.py', 'w') as f:
    f.write(content)
