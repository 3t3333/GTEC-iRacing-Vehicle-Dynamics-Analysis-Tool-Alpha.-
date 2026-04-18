from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(45, 138, 226) # #2D8AE2
        self.cell(0, 10, 'OpenDAV Vehicle Dynamics Analysis System', 0, 1, 'C')
        self.set_font('Arial', 'I', 10)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, 'Advanced Mechanical Analysis & Tire Work Guide', 0, 1, 'C')
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
        body = body.replace('"', '"').replace('"', '"').replace("'", "'").replace("'", "'")
        self.multi_cell(0, 6, body)
        self.ln(4)

pdf = PDF()
pdf.add_page()

# Intro
pdf.chapter_title('1. INTRODUCTION: Advanced Vehicle Dynamics')
text = """While aerodynamic mapping provides insight into the high-speed platform of a race car, mechanical grip is governed by how the chassis distributes load to the tires. OpenDAV goes beyond simple tire temperatures by employing advanced vehicle dynamics concepts inspired by race engineering literature (e.g., Race Car Vehicle Dynamics by Milliken & Milliken). By mathematically reconstructing Tire Work, Yaw Moments, and Load Transfer Distribution, OpenDAV allows engineers to quantify the root causes of understeer, oversteer, and tire degradation."""
pdf.chapter_body(text)

# Tire Energy
pdf.chapter_title('2. TIRE ENERGY & WORK PROFILER')
text = """Tire temperatures are a delayed symptom of friction. The actual cause of tire degradation is Energy Dissipation (Work). In physics, Work is defined as Force multiplied by Distance, and Power (Work Rate) is Force multiplied by Velocity.

To calculate how much energy a tire is absorbing during a lap, OpenDAV uses the following telemetry proxy:
Work Rate (Power) = Vertical Load (N) * Combined G-Force * Vehicle Speed (m/s)

1. Vertical Load (Fz) dictates the maximum potential friction the tire can generate.
2. Combined G-Force (sqrt(LatG^2 + LongG^2)) acts as a normalized proxy for the horizontal force (Fxy) the tire is currently transmitting to the road.
3. Vehicle Speed (V) scales the force into Power (Watts).

By integrating this Work Rate over the duration of the lap, OpenDAV calculates the Total Energy Expenditure (in kilojoules) for each corner of the car. This instantly highlights which axle or specific tire is being overworked by the current roll stiffness or toe/camber setup."""
pdf.chapter_body(text)

# Milliken Moment Method
pdf.chapter_title('3. YAW MOMENT MAPPING (The Milliken Method)')
text = """The Milliken Moment Method (MMM) is a cornerstone of vehicle dynamics used to quantify handling balance. Instead of relying on subjective driver feedback ("the car understeers mid-corner"), MMM plots the car's Yawing Moment against its Lateral Acceleration.

OpenDAV approaches this by mapping the relationship between Steering Angle, Yaw Rate, and Speed. 
- Kinematic Yaw Rate: The mathematical yaw rate the car *should* have based purely on the steering angle, wheelbase, and speed (assuming zero tire slip).
- Actual Yaw Rate: The gyroscope-measured rotation of the chassis.

When the Actual Yaw Rate is lower than the Kinematic Yaw Rate during cornering, the front tires are slipping more than the rears (Understeer). When the Actual Yaw Rate is higher, the rear tires are slipping more (Oversteer). By mapping this delta across the friction circle, OpenDAV can output a precise "Understeer Gradient" (deg/G), proving exactly how a setup change shifted the mechanical balance."""
pdf.chapter_body(text)

pdf.add_page()

# TLLTD
pdf.chapter_title('4. TOTAL LATERAL LOAD TRANSFER DISTRIBUTION (TLLTD)')
text = """When a car corners, weight transfers from the inside tires to the outside tires. Because tires are load-sensitive (they lose efficiency as vertical load increases), the axle that takes the majority of this load transfer will lose grip first.

TLLTD is the percentage of total lateral weight transfer absorbed by the front axle versus the rear axle. It is primarily controlled by the Anti-Roll Bars (ARBs), Spring Rates, and Roll Center Heights.

OpenDAV calculates empirical TLLTD by measuring the dynamic corner weights from the suspension load channels during peak Lateral G phases. 
For example, if the car transfers 2000N of load during a 1.5G corner, and the front axle accounts for 1200N of that transfer, the Front TLLTD is 60%. Increasing the Front ARB stiffness will increase this percentage, intentionally overworking the front tires to induce understeer and stabilize the rear of the car."""
pdf.chapter_body(text)

# Pitch Centers
pdf.chapter_title('5. PITCH CENTER & ANTI-GEOMETRY ANALYSIS')
text = """During heavy braking or acceleration, the chassis pitches forward or backward, drastically altering the aerodynamic platform (Ride Heights). 

Suspension designers use "Anti-Dive" and "Anti-Squat" geometry to physically resist this pitching motion using suspension arm angles rather than just stiffening the springs. OpenDAV maps the Pitch Gradient by isolating pure longitudinal G-forces (0 Lat G) and plotting the ratio of Front vs. Rear suspension travel.

By comparing the Pitch Gradient of two setups, OpenDAV can prove if a spring change was successful in stabilizing the aerodynamic platform under braking, ensuring the car remains within its "Golden Box" of peak downforce without compromising low-speed mechanical compliance."""
pdf.chapter_body(text)

pdf.output('OpenDAV_Vehicle_Dynamics_Guide.pdf')
print("PDF Generated Successfully.")
