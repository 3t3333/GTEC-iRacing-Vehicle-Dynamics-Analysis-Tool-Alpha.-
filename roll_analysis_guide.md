# Roll Gradient Analysis: A Guide for Setup Building

The Roll Gradient Analysis tool calculates exactly how your car's suspension responds to cornering forces. Instead of estimating raw static spring/ARB stiffness values—which requires complex math and an exact 3D model of your car's geometry—this tool calculates the **dynamic roll response** straight from your telemetry. 

## The Math Behind It
When you turn the steering wheel, Lateral G-Forces (`LatAccel` or `G Force Lat`) push the car sideways, causing the chassis to roll. 

The tool performs a linear regression between two variables during the stint:
1. **Lateral G-Force (G)**
2. **Suspension Displacement (mm)** 
   - *Calculated using the difference between the Left and Right Ride Heights.* 
   - `Roll_Front = RideHeight_FL - RideHeight_FR`
   - `Roll_Rear = RideHeight_RL - RideHeight_RR`

By mapping out thousands of data points where the Lateral G is > 0.5 (to filter out straights), it plots a line of best fit (`y = mx + b`). 

The slope of this line (`m`) is your **Roll Gradient**: exactly how many millimeters the car rolls per 1.0G of cornering force.

## How to Use This for Setup Building

This gives you a perfect objective measurement of your car's **Mechanical Balance**. 

### 1. Understanding Roll Distribution (%)
The tool calculates what percentage of the total roll is happening at the front vs. the rear. 
- **Higher Percentage = Softer End.** If your Roll Balance is `Front: 55% | Rear: 45%`, the front suspension is doing more of the rolling because it is mechanically softer than the rear.
- **Oversteer / Understeer:** If a car is understeering mid-corner, you can look at your Roll Distribution. Stiffening the rear (via springs or ARB) will reduce the rear's percentage, transferring load faster and helping the car rotate.

### 2. A/B Testing Setup Changes
When you change an Anti-Roll Bar (ARB) in the setup menu from "Setting 3" to "Setting 5", you rarely know exactly *how much* stiffer it actually is in the real world. 

With this tool, you can:
1. Run 5 laps on "Setting 3"
2. Run 5 laps on "Setting 5"
3. Run the Multi-File Roll Gradient Analysis. 

The tool will immediately show you exactly how many mm/G you lost or gained, giving you a quantified metric of what that ARB click actually did to the car.

### 3. Aero Platform Stability
If you are driving a high-downforce car, aerodynamic platforms need to remain flat to produce maximum grip. If you see a very high Total Roll Gradient (e.g., >25 mm/G), your car is rolling significantly during corners, which could be stalling your diffuser or throwing the aero balance off. Stiffening the entire car to bring the gradients down can stabilize the aero platform.