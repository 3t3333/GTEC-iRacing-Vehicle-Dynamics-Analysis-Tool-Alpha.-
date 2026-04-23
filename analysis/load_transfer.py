import os
import sys
import numpy as np
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yaml
import ui.splash as splash
from ui.metadata_printer import print_session_metadata
from ui.graphing import show_ctk_graph
from core.config import get_gui_mode

def run_tlltd_analyzer(sessions, headless=False, headless_config=None):
    while True:
        if not headless:
            splash.print_header("Total Lateral Load Transfer Distribution (TLLTD)")
            
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            metadata = session.get('metadata', {})
            
            if not headless:
                print(f"\nAnalyzing: {os.path.basename(file_path)}")
                print_session_metadata(data, channels, metadata)
            
            # 1. Find Required Channels
            fl_ch, fr_ch = 'Suspension Load FL', 'Suspension Load FR'
            rl_ch, rr_ch = 'Suspension Load RL', 'Suspension Load RR'
            lat_g_ch = None
            for ch in ['LatAccel', 'LatG', 'G Force Lat', 'lat']:
                if ch in data or ch in channels.values(): lat_g_ch = ch; break

            required = [fl_ch, fr_ch, rl_ch, rr_ch]
            if not lat_g_ch:
                if not headless: print("  [!] Missing Lateral G channel.")
                continue
            missing = [ch for ch in required if ch not in data]
            if missing:
                if not headless: print(f"  [!] Missing suspension load channels: {missing}")
                continue

            # 2. Load Data
            fl_l = data[fl_ch].data
            fr_l = data[fr_ch].data
            rl_l = data[rl_ch].data
            rr_l = data[rr_ch].data
            lat_g = data[channels.get('lat', lat_g_ch)].data
            if np.max(np.abs(lat_g)) > 10: lat_g = lat_g / 9.81 # m/s^2 fallback

            # 3. Filter for significant cornering (Lat G > 0.8)
            mask = np.abs(lat_g) > 0.8
            if not np.any(mask):
                if not headless: print("  [!] Not enough cornering data (>0.8G) to establish TLLTD.")
                continue
                
            # Delta loads
            # We use absolute difference as a proxy for transfer on that axle
            d_front = np.abs(fl_l[mask] - fr_l[mask])
            d_rear = np.abs(rl_l[mask] - rr_l[mask])
            d_total = d_front + d_rear
            
            # Calculate TLLTD
            # Filter out points where d_total is too small to avoid noise
            valid = d_total > 50 
            if not np.any(valid):
                if not headless: print("  [!] Load transfer too low for calculation.")
                continue
                
            tlltd_f = (d_front[valid] / d_total[valid]) * 100.0
            
            avg_tlltd_f = np.median(tlltd_f)
            avg_tlltd_r = 100.0 - avg_tlltd_f
            
            # Static Weight Distribution (at < 15km/h, low G)
            speed_ch = None
            for ch in ['Speed', 'Ground Speed', 'Velocity', 'virt_body_v']:
                if ch in data: speed_ch = ch; break
            
            static_f_bias = 50.0
            if speed_ch:
                v_ms = data[speed_ch].data
                if np.max(v_ms) > 150: v_ms /= 3.6
                static_m = (v_ms < 10) & (np.abs(lat_g) < 0.1)
                if np.any(static_m):
                    s_f = np.median(fl_l[static_m] + fr_l[static_m])
                    s_r = np.median(rl_l[static_m] + rr_l[static_m])
                    static_f_bias = (s_f / (s_f + s_r)) * 100.0

            PINK = '\033[95m'
            CYAN = '\033[96m'
            RESET = "\033[0m"
            
            if not headless:
                print("\n  ┌" + "─" * 98 + "┐")
                print("  │ " + "[ TLLTD - LATERAL LOAD TRANSFER ]".ljust(92) + " │")
                print("  │ " + f"Front TLLTD: {CYAN}{avg_tlltd_f:.1f}%{RESET}".ljust(96 + len(CYAN) + len(RESET)) + " │")
                print("  │ " + f"Rear TLLTD:  {PINK}{avg_tlltd_r:.1f}%{RESET}".ljust(96 + len(PINK) + len(RESET)) + " │")
                print("  │ " + f"Static Weight Bias: {static_f_bias:.1f}% Front".ljust(92) + " │")
                print("  └" + "─" * 98 + "┘")

            file_basename = os.path.basename(file_path)
            l1_preview = f"""
        L1: TLLTD BALANCE (SUMMARY)                       LOAD TRANSFER DISTRIBUTION               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ FRONT AXLE:  [██████----] {avg_tlltd_f:.1f}%      │      
 │                                         │   │ REAR AXLE:   [████------] {avg_tlltd_r:.1f}%      │      
 │                                         │   │                                         │      
 │                                         │   │  MECHANICAL BALANCE BIAS:               │      
 │        [ AXLE DISTRIBUTION ]            │   │  {'FRONT' if avg_tlltd_f > static_f_bias else 'REAR'} BIASED vs STATIC WEIGHT             │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXES: FRONT vs REAR                 │   │ [BARS]: PERCENTAGE OF TOTAL TRANSFER    │      
 │ [Y] AXIS: TRANSFER PERCENTAGE (%)       │   │ [TEXT]: EMPIRICAL ROLL STIFFNESS RATIO  │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  FILE: {file_basename}
  VEHICLE: {metadata.get('car', 'UNKNOWN')}
  
  >> [USE CASE]: QUANTIFY MECHANICAL BALANCE. HIGHER FRONT TLLTD INDUCES UNDERSTEER."""

            if not headless:
                print(l1_preview)

            while True:
                if headless:
                    if headless_config.get('_ran'): return
                    headless_config['_ran'] = True
                    ans_raw = f"print l1 < {headless_config['project']}"
                else:
                    ans_raw = input(f"\\n  Select action ('open L1', 'print L1', 'p' to go back < proj): ").strip().lower()
                
                ans = ans_raw.split('<')[0].strip().lower()
                
                if ans == 'p':
                    break
                    
                if ans in ['open l1', 'print l1']:
                    if not headless: print("  [+] Building TLLTD Distribution Graph...")
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams.update({
                        'font.family': ['Consolas', 'DejaVu Sans Mono', 'monospace'],
                        'figure.dpi': 144,  # High-DPI Retina rendering
                        'axes.linewidth': 1.2,
                        'grid.alpha': 0.15,
                        'xtick.direction': 'in',
                        'ytick.direction': 'in',
                        'scatter.edgecolors': 'none'
                    })
                    fig = plt.figure(figsize=(10, 7), num='OpenDAV - TLLTD Analysis')

                    # Bar chart
                    ax = plt.gca()
                    labels = ['Static Bias', 'Dynamic TLLTD']
                    fronts = [static_f_bias, avg_tlltd_f]
                    rears = [100.0 - static_f_bias, avg_tlltd_r]
                    
                    x = np.arange(len(labels))
                    width = 0.35
                    
                    ax.bar(x, fronts, width, label='Front Axle', color='#2D8AE2', alpha=0.9)
                    ax.bar(x, rears, width, bottom=fronts, label='Rear Axle', color='#FF1493', alpha=0.9)
                    
                    ax.set_ylabel('Percentage (%)')
                    ax.set_title(f'Axle Load Distribution & TLLTD\\n{file_basename}')
                    ax.set_xticks(x)
                    ax.set_xticklabels(labels)
                    ax.legend()
                    
                    # Annotations
                    for i in range(len(labels)):
                        ax.text(i, fronts[i]/2, f'{fronts[i]:.1f}%', ha='center', va='center', color='white', fontweight='bold')
                        ax.text(i, fronts[i] + rears[i]/2, f'{rears[i]:.1f}%', ha='center', va='center', color='white', fontweight='bold')

                    plt.tight_layout()

                    if ans == 'open l1':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - TLLTD")
                        else: plt.show()
                    else:
                        import datetime
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"TLLTD_L1_{timestamp}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                        else:
                            os.makedirs("exports", exist_ok=True)
                            export_path = f"exports/{file_out}"
                            plt.savefig(export_path, dpi=300, bbox_inches='tight')
                            plt.close(fig)
                            if not headless: print(f"  [+] Saved to {export_path}")
                else:
                    if not headless: print("  [!] Invalid command.")
        
        if headless: return
        print("\n" + "─"*100)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            splash.show_exit_screen()
            sys.exit(0)
        break
