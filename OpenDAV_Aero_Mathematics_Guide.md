# OpenDAV: Aerodynamic Mathematics Guide

## 1. The Problem: Isolating Aerodynamics
Telemetry systems do not have 'downforce sensors'. Instead, they record suspension loads or shock deflections. The load on a suspension system is a combination of three distinct forces:
1. **Static Weight** (The mass of the car)
2. **Mechanical Weight Transfer** (Pitch from braking, roll from cornering, track elevation/G-forces)
3. **Aerodynamic Downforce**

OpenDAV's mathematical engine isolates Aerodynamic Downforce by calculating and subtracting the mechanical forces in real-time.

## 2. Step 1: Calculating Raw Suspension Load
If the car provides direct load sensors (e.g., `Suspension Load FL`), we use them. For cars that only output shock deflection (e.g., Porsche 992 Cup), OpenDAV calculates the force using Hooke's Law, fused with the precise Spring Rates and Motion Ratios extracted via the OpenDAV STO Parser.

```python
WheelRate = SpringRate * (MotionRatio ** 2)
CornerLoad = ShockDeflection * WheelRate
```
*Channels Used: `LFshockDefl`, `SpringRateFL` (from STO/SimGit Model)*

## 3. Step 2: Establishing Static Weight
To remove the base mass of the car, OpenDAV scans the telemetry for 'Coast-Down' or 'Static' zones. It looks for moments where the car is traveling under 15 km/h with near-zero lateral and longitudinal G-forces (e.g., exiting the pit lane).

```python
StaticWeight = Median(Load_FL + Load_FR + Load_RL + Load_RR) # at Speed < 15km/h
```

## 4. Step 3: Vertical G Compensation (The Elevation Fix)
On tracks with high elevation changes (like Mount Panorama or Eau Rouge at Spa), the track geometry compresses the suspension. If a car drives through a dip at +1.5G, its mechanical weight increases by 50%. If this is not subtracted, it manifests as a massive, false downforce spike.

iRacing logs `VertAccel` in absolute $m/s^2$ (where $9.81 m/s^2$ is 1G resting on earth). OpenDAV calculates a dynamic gravity multiplier.

```python
Vert_G_Factor = VertAccel_Channel / 9.80665
Dynamic_Mechanical_Weight = StaticWeight * Vert_G_Factor
```

## 5. Step 4: Isolating Downforce & Aero Balance
With the dynamic mechanical weight accounted for, OpenDAV isolates the pure aerodynamic forces acting on the chassis.

```python
Total_Downforce = Total_Corner_Loads - Dynamic_Mechanical_Weight
Aero_Front = Front_Corner_Loads - (Front_StaticWeight * Vert_G_Factor)

Aero_Balance_% = (Aero_Front / Total_Downforce) * 100
```

## 6. Step 5: Aerodynamic Coefficients
To compare aerodynamic efficiency across different speeds, OpenDAV normalizes the force into an Aerodynamic Lift Coefficient Area ($C_L \cdot A$). This represents the car's aerodynamic footprint independent of velocity.

```python
ClA = (2 * Total_Downforce) / (Air_Density * Velocity^2)
```
*Channels Used: `air_density` (kg/m^3), `Speed` (m/s)*
