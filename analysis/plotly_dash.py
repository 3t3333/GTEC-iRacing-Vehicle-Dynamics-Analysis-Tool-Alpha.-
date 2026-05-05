import os
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import griddata

def generate_monash_dashboard(f_rh, r_rh, total_df, lat_g, long_g, time, file_basename, export_dir):
    """
    Generates the interactive Plotly Monash-Style L3 Dashboard.
    """
    print("  [+] Building Interactive L3 Dashboard (Plotly)...")

    # Safety checks
    if len(f_rh) < 10:
        print("      [!] Not enough aero data points to build contour.")
        return

    # Subsample data if it's too massive for browser rendering (Plotly gets sluggish > 20k points)
    if len(f_rh) > 15000:
        idx = np.linspace(0, len(f_rh)-1, 15000, dtype=int)
        f_s, r_s, z_s, lg, lng, t_s = f_rh[idx], r_rh[idx], total_df[idx], lat_g[idx], long_g[idx], time[idx]
    else:
        f_s, r_s, z_s, lg, lng, t_s = f_rh, r_rh, total_df, lat_g, long_g, time

    f_min, f_max = np.min(f_s), np.max(f_s)
    r_min, r_max = np.min(r_s), np.max(r_s)
    
    # 100x100 grid
    grid_x, grid_y = np.mgrid[f_min:f_max:100j, r_min:r_max:100j]
    
    print("      Interpolating scattered telemetry into Aero Map grid...")
    grid_z = griddata((f_s, r_s), z_s, (grid_x, grid_y), method='linear')

    fig = make_subplots(
        rows=2, cols=2,
        column_widths=[0.35, 0.65],
        row_heights=[0.6, 0.4],
        specs=[[{"type": "scatter"}, {"type": "contour"}],
               [{"type": "scatter", "colspan": 2}, None]],
        subplot_titles=("G-Plot (Friction Circle)", "Aero Map & Ride Height Envelope", "Dynamic Ride Height (Time Series)")
    )

    # Custom OpenDAV Colorscale (Deep Blue -> Magenta -> Orange)
    opendav_colorscale = [
        [0.0, "#0f172a"],   # Dark Slate
        [0.2, "#2D8AE2"],   # Blue
        [0.6, "#FF1493"],   # Pink
        [1.0, "#D2751D"]    # Orange
    ]

    # 1. G-Plot (Friction Circle)
    fig.add_trace(
        go.Scatter(
            x=lg, y=lng, 
            mode='markers+lines', 
            marker=dict(color='#0ea5e9', size=2),
            line=dict(color='rgba(14, 165, 233, 0.3)', width=1), 
            name="G-Vector",
            hoverinfo="text",
            text=[f"Lat: {x:.2f}G<br>Long: {y:.2f}G<br>Time: {t:.2f}s" for x, y, t in zip(lg, lng, t_s)]
        ),
        row=1, col=1
    )

    # 2. Aero Contour
    fig.add_trace(
        go.Contour(
            x=np.linspace(f_min, f_max, 100),
            y=np.linspace(r_min, r_max, 100),
            z=grid_z.T,
            colorscale=opendav_colorscale,
            showscale=True,
            colorbar=dict(title="Downforce (N)", len=0.6, y=0.8),
            contours=dict(coloring='heatmap', showlines=True, start=np.nanmin(grid_z), end=np.nanmax(grid_z), size=(np.nanmax(grid_z)-np.nanmin(grid_z))/15),
            line=dict(color='rgba(255,255,255,0.2)', width=0.5)
        ),
        row=1, col=2
    )
    
    # Add the ride height envelope path over the contour
    fig.add_trace(
        go.Scatter(
            x=f_s, y=r_s, 
            mode='lines', 
            line=dict(color='rgba(255, 255, 255, 0.6)', width=1.5), 
            name="RH Envelope",
            hoverinfo="text",
            text=[f"FRH: {x:.1f}mm<br>RRH: {y:.1f}mm<br>DF: {z:.1f}N<br>Time: {t:.2f}s" for x, y, z, t in zip(f_s, r_s, z_s, t_s)]
        ),
        row=1, col=2
    )

    # 3. Time Series Ride Heights
    fig.add_trace(
        go.Scatter(
            x=t_s, y=f_s, 
            mode='lines', 
            line=dict(color='#0ea5e9', width=2), 
            name="Front RH",
            hoverinfo="text",
            text=[f"Front RH: {x:.1f}mm<br>Time: {t:.2f}s" for x, t in zip(f_s, t_s)]
        ),
        row=2, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=t_s, y=r_s, 
            mode='lines', 
            line=dict(color='#f59e0b', width=2), 
            name="Rear RH",
            hoverinfo="text",
            text=[f"Rear RH: {x:.1f}mm<br>Time: {t:.2f}s" for x, t in zip(r_s, t_s)]
        ),
        row=2, col=1
    )

    # Layout & Styling
    fig.update_layout(
        template="plotly_dark",
        title=dict(
            text=f"<b>OpenDAV L3: Dynamic Aero Dashboard</b><br><span style='font-size:12px; color:#94a3b8;'>{file_basename}</span>",
            x=0.05
        ),
        height=900,
        showlegend=False,
        hovermode="x unified", # Synchronizes hover across the time-series!
        plot_bgcolor="#0b0f19",
        paper_bgcolor="#0b0f19",
        font=dict(family="Consolas, 'Courier New', monospace", color="#e2e8f0")
    )

    # G-Plot formatting (Square/Circle aspect ratio)
    fig.update_xaxes(title_text="Lat G", row=1, col=1, range=[-2.5, 2.5], gridcolor="#1e293b", zerolinecolor="#334155")
    fig.update_yaxes(title_text="Long G", row=1, col=1, scaleanchor="x", scaleratio=1, range=[-2.5, 2.5], gridcolor="#1e293b", zerolinecolor="#334155")

    # Aero Map formatting
    fig.update_xaxes(title_text="Front Ride Height (mm)", row=1, col=2, gridcolor="#1e293b")
    fig.update_yaxes(title_text="Rear Ride Height (mm)", row=1, col=2, gridcolor="#1e293b")

    # Time Series formatting
    fig.update_xaxes(title_text="Time (s)", row=2, col=1, gridcolor="#1e293b", showspikes=True, spikemode="across", spikethickness=1, spikecolor="#f59e0b")
    fig.update_yaxes(title_text="Ride Height (mm)", row=2, col=1, gridcolor="#1e293b")

    out_path = os.path.join(export_dir, f"L3_Dashboard_{file_basename}.html")
    fig.write_html(out_path)
    print(f"      [+] Interactive Plotly HTML saved to: {out_path}")
    
    # Automatically open in the user's default web browser
    try:
        import webbrowser
        webbrowser.open('file://' + os.path.abspath(out_path))
    except:
        pass
