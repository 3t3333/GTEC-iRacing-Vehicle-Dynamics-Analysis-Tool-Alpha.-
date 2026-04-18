from fpdf import FPDF
import re

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(45, 138, 226) # #2D8AE2
        self.cell(0, 10, 'OpenDAV Vehicle Dynamics Analysis System', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'Aerodynamics Mathematical Architecture & Channel Guide', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_text_color(210, 117, 29) # #D2751D
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(2)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.set_text_color(0, 0, 0)
        
        # Sanitize unicode characters for FPDF (latin-1)
        body = body.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        body = body.replace(u'\u201c', '"').replace(u'\u201d', '"') # Left/Right double quotes
        body = body.replace(u'\u2018', "'").replace(u'\u2019', "'") # Left/Right single quotes
        body = body.replace(u'\u2014', "-").replace(u'\u2013', "-") # Em/En dashes
        
        self.multi_cell(0, 6, body)
        self.ln(4)

pdf = PDF()
pdf.add_page()

# Intro
pdf.chapter_title('1. INTRODUCTION: Kinematic Approximation')
text = """OpenDAV employs an advanced methodology known as "Kinematic Approximation" to calculate aerodynamic loads from standard racing simulators (like iRacing). Because sims do not output raw aerodynamic data (such as CL or pure Aero Newtons) in standard telemetry files (.ibt), OpenDAV reverse-engineers the aerodynamic forces entirely by analyzing the compression of the suspension system under load."""
pdf.chapter_body(text)

# Channels
pdf.chapter_title('2. REQUIRED TELEMETRY CHANNELS')
text = """To map downforce and aero balance, OpenDAV intercepts the following variables from the telemetry arrays:

Speed Channels:
- 'Speed', 'Ground Speed', 'Velocity', or 'virt_body_v'

Ride Height Channels (Axes):
- 'Ride Height FL' or 'LFrideHeight'
- 'Ride Height FR' or 'RFrideHeight'
- 'Ride Height RL' or 'LRrideHeight'
- 'Ride Height RR' or 'RRrideHeight'

Suspension Deflection/Load Channels:
- 'LFshockdeflect' or 'LFshockDefl' (Mapped internally to 'Suspension Load FL')
- 'RFshockdeflect' or 'RFshockDefl' (Mapped internally to 'Suspension Load FR')
- 'LRshockdeflect' or 'LRshockDefl' (Mapped internally to 'Suspension Load RL')
- 'RRshockdeflect' or 'RRshockDefl' (Mapped internally to 'Suspension Load RR')

Setup Metadata (YAML Extracted):
- 'SpringRateFL', 'SpringRateFR', 'SpringRateRL', 'SpringRateRR'

Filter Channels:
- 'LatAccel' or 'lat'
- 'LongAccel' or 'long'"""
pdf.chapter_body(text)

# Force Conversion
pdf.chapter_title('3. STEP 1: FORCE CONVERSION (Hooke\'s Law)')
text = """The raw data from iRacing for the suspension load is actually logged as "Shock Deflection" (meters). To convert this geometric distance into physical force (Newtons), OpenDAV actively parses the car's setup YAML to extract the front and rear Spring Rates.

Formula: F = k * x

Load_FL (Newtons) = LFshockDefl (meters) * 1000 * SpringRateFL (N/mm)

*Note: If the car (like the Porsche 992 Cup) does not have adjustable spring rates in its setup file, OpenDAV defaults to a 1000 multiplier, producing an accurate ratio of "Units of Compression" rather than raw Newtons, which preserves the mathematical integrity of the 2D mapping surface."""
pdf.chapter_body(text)

# Static Baseline
pdf.chapter_title('4. STEP 2: STATIC BASELINE (Removing Mechanical Weight)')
text = """Before we can find downforce, we must subtract the static mass of the car (chassis, fuel, and driver) pressing down on the springs.

Condition: The script isolates telemetry frames where:
1. Speed < 15 km/h
2. Absolute Lateral G < 0.1G
3. Absolute Longitudinal G < 0.1G

Calculation: It takes the median force on each corner during this low-speed, zero-G window.
Static_Weight = Static_FL + Static_FR + Static_RL + Static_RR"""
pdf.chapter_body(text)

pdf.add_page()

# Dynamic Aero
pdf.chapter_title('5. STEP 3: DYNAMIC ISOLATION & DOWNFORCE')
text = """With the static mass established, OpenDAV looks exclusively at high-speed telemetry to calculate the physical air pushing down on the chassis.

Condition: Speed > 100 km/h (Filters out mechanical noise and low-speed pitch).

Total Dynamic Load = (Load_FL + Load_FR + Load_RL + Load_RR)
TOTAL DOWNFORCE (N) = Total Dynamic Load - Static_Weight

For Aero Balance, the formula splits the axles:
Downforce_Front = (Load_FL + Load_FR) - (Static_FL + Static_FR)
Downforce_Rear = (Load_RL + Load_RR) - (Static_RL + Static_RR)

AERO BALANCE (% Front) = (Downforce_Front / TOTAL DOWNFORCE) * 100
*The Aero Balance is then rigidly clamped between 0% and 100% to discard physically impossible values caused by sensor noise or aggressive bottoming-out.*"""
pdf.chapter_body(text)

# Spatial Mathematics
pdf.chapter_title('6. ADVANCED SPATIAL MATHEMATICS (The Visuals)')
text = """Once the arrays of Downforce and Aero Balance values are generated, OpenDAV translates them into professional engineering Contour Maps.

1. "Real" Peak Downforce (KDE)
Instead of plotting the single highest anomaly spike as the max downforce, OpenDAV runs the entire array through a Gaussian Kernel Density Estimate (KDE) to build a smooth probability curve, extracting the 98th Percentile as the true, reliable aerodynamic ceiling.

2. Target Golden Pose
The "Golden Box" is defined as 75% to 90% of the Real Peak Downforce. OpenDAV extracts all Front/Rear Ride Height coordinates within this window. It then runs a second 2-Dimensional KDE to find the exact geometrical Mode (the highest density point). This is printed as the "Target Golden Pose" - the most stable aerodynamic platform the car achieves on track.

3. Triangulation & The Convex Hull
To build the Contour map, OpenDAV uses Delaunay Triangulation to link the X (Front Ride Height) and Y (Rear Ride Height) telemetry dots into a mesh. It calculates the "Convex Hull" (the tightest possible rubber band around the outer points). 

4. cKDTree Anti-Hallucination Masking
Because mathematical triangulations often span across empty space (interpolating data where the car never physically drove), OpenDAV deploys a cKDTree spatial partitioner. It calculates the exact distance between every triangle in the map and the nearest actual telemetry dot. If a triangle is in an "empty valley" (> 4% axis span away from real data), it is deleted. This effectively shrink-wraps the heatmap around empirical data only."""
pdf.chapter_body(text)

pdf.output('OpenDAV_Aero_Mathematics_Guide.pdf')
print("PDF Generated Successfully.")
