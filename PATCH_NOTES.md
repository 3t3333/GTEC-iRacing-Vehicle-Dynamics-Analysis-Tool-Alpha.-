# GTEC Analysis Software - Alpha 1.1 Patch Notes

### 🚀 Major Features
* **Custom Math Graphing Tool (Sandbox):** Added a brand new sandbox environment where engineers can input custom mathematical formulas (e.g., `([Wheel Speed FL] + [Wheel Speed FR]) / 2`) and instantly graph the results as a high-fidelity line plot. Supports targeting a specific sector, a full lap (`fl`), or the entire stint (`fs`).
* **GTEC Preset Automator:** Introduced an automated batch-reporting tool. Users can now create, save, and load "presets" that string multiple analysis tools together. When run, the Automator bypasses all GUI interactions, operates silently in the background, and generates a timestamped `report.txt` file along with saved PNGs of every graph.
* **Multi-Engine GUI Support:** GTEC now ships with 3 completely distinct graphing engines. You can cycle through these via the new `Settings` menu:
  1. **Legacy Matplotlib:** The original, fast, standalone graphing window.
  2. **Plotly Web (Beta):** A modern, HTML-based browser graphing engine with buttery smooth zooming, panning, and native interactive tooltips.
  3. **CustomTkinter (Beta):** A sleek, dark-mode native Windows GUI wrapper that embeds the Matplotlib graphs for high-performance, large-dataset rendering.

### ✨ Quality of Life & UI Polish
* **VDA Console Branding:** Completely redesigned the terminal splash and exit screens. Replaced the generic box with a bold `VDA` (Vehicle Dynamics Analysis) ASCII logo.
* **24-bit TrueColor Gradients:** The splash and exit screens now feature a smooth, top-to-bottom Grey-to-White color gradient, giving the terminal a highly professional engineering aesthetic.
* **Dynamic Splash Loading:** The ASCII logo is now loaded dynamically from a `splash.txt` file, allowing easy swapping of the console branding without touching Python code.
* **"Full Lap" and "Full Stint" Macros:** In any tool that asks for a distance window (like Sector Analysis), you can now simply type `fl` to automatically calculate and analyze the entire length of the fastest lap, or `fs` to analyze the entire loaded stint.
* **Empirical Tire Analysis:** The Sector Tire Temp Performance graph now uses actual empirical data (the average of the top 3 fastest laps) to place its "Optimal" marker, rather than relying on the mathematical vertex of the quadratic curve fit.

### 🧹 Cleanup & Focus
* **Vehicle Dynamics Purity:** Removed the `Sector Analysis` and `Interactive Line Graph Viewer` (driver inputs) tools from the main menu. These driver coaching tools have been archived and reserved for a future, separate Driver Performance software suite. GTEC is now 100% focused on Vehicle Dynamics Engineering.
* **Global Error Catching:** Re-engineered the startup and execution sequence. If the software ever encounters a fatal crash or missing dependency, it will gracefully trap the error, print a detailed stack trace to the terminal, and wait for the user to press Enter rather than abruptly closing the window.
* **Auto-Patcher Enhancements:** The startup Auto-Patcher has been updated to silently install the newly required libraries (`plotly` and `customtkinter`) if they are missing from the system.

### 🛠️ Developer & Build Updates
* **PyInstaller Support:** Rewrote multiple internal paths and dependency checks (`sys._MEIPASS`) so the software can be flawlessly compiled into a single, standalone Windows `.exe` using PyInstaller.
* **GitHub Readiness:** Generated a clean `README.md`, a `requirements.txt`, and a strict `.gitignore` to prepare the repository for public/team sharing.
