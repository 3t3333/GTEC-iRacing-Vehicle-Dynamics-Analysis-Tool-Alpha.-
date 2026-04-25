import os
import re

with open('analysis/tire_energy.py', 'r') as f:
    content = f.read()

# Update input prompt
content = content.replace(
    "ans_raw = input(f\"\\n  Select action ('open L1/L2/L3', 'print L1/L2/L3', 'p' to go back < proj): \").strip().lower()",
    "ans_raw = input(f\"\\n  Select action ('open L1/L2/L3', 'print L1/L2/L3/L4', 'p' to go back < proj): \").strip().lower()"
)

# Update UI preview
ui_preview_old = """        L3: SECTOR-BY-SECTOR DYNAMICS (LINES)
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │      [ BAR ] OVERALL LAP ENERGY         │   │      [ PIE ] OVERALL AXLE BIAS          │
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
    ┌────────────────────────┐  ┌────────────────────────┐  ┌────────────────────────┐
    │   SECTOR 1 (0-33%)     │  │   SECTOR 2 (33-66%)    │  │   SECTOR 3 (66-100%)   │
    │   [LINE] FL,FR,RL,RR   │  │   [LINE] FL,FR,RL,RR   │  │   [LINE] FL,FR,RL,RR   │
    └────────────────────────┘  └────────────────────────┘  └────────────────────────┘"""

ui_preview_new = ui_preview_old + """

        L4: BATCH SECTOR REPORT (L1 PER SECTOR)
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │ [S1 REPORT] -> TireEnergy_S1.png        │   │ [S2 REPORT] -> TireEnergy_S2.png        │      
 ├─────────────────────────────────────────┤   ├─────────────────────────────────────────┤      
 │ [S3 REPORT] -> TireEnergy_S3.png        │   │ [FULL LAP]  -> TireEnergy_Full.png      │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      """

content = content.replace(ui_preview_old, ui_preview_new)

# Add L4 logic
# We'll add it after L2/L3 blocks

l4_logic = """
                elif ans == 'print l4':
                    print("  [+] Generating Batch Sector Reports (L4)...")
                    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                    batch_dir_name = f"TireBatch_{timestamp}_{file_basename}"
                    
                    if '<' in ans_raw:
                        project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                        batch_path = os.path.join("projects", project_name, "reports", batch_dir_name)
                    else:
                        batch_path = os.path.join("exports", batch_dir_name)
                    
                    os.makedirs(batch_path, exist_ok=True)
                    
                    lap_dist = dist_arr[lap_idx]
                    max_d = np.max(lap_dist)
                    s1_m = (lap_dist <= max_d / 3)
                    s2_m = (lap_dist > max_d / 3) & (lap_dist <= 2 * max_d / 3)
                    s3_m = (lap_dist > 2 * max_d / 3)
                    full_m = np.ones_like(lap_dist, dtype=bool)
                    
                    sector_configs = [
                        ("Sector 1", s1_m, "S1"),
                        ("Sector 2", s2_m, "S2"),
                        ("Sector 3", s3_m, "S3"),
                        ("Full Lap", full_m, "Full")
                    ]
                    
                    import matplotx
                    plt.style.use(matplotx.styles.aura['dark'])
                    plt.rcParams.update({
                        'font.family': ['Consolas', 'DejaVu Sans Mono', 'monospace'],
                        'figure.dpi': 144,
                        'axes.linewidth': 1.2,
                        'grid.alpha': 0.15,
                        'xtick.direction': 'in',
                        'ytick.direction': 'in',
                        'scatter.edgecolors': 'none'
                    })

                    for s_name, s_mask, s_suffix in sector_configs:
                        s_wr_fl, s_wr_fr = wr_fl[s_mask], wr_fr[s_mask]
                        s_wr_rl, s_wr_rr = wr_rl[s_mask], wr_rr[s_mask]
                        s_dt = dt[s_mask]
                        s_dist = lap_dist[s_mask]
                        
                        s_e_fl = np.sum(s_wr_fl * s_dt)
                        s_e_fr = np.sum(s_wr_fr * s_dt)
                        s_e_rl = np.sum(s_wr_rl * s_dt)
                        s_e_rr = np.sum(s_wr_rr * s_dt)
                        
                        s_total = s_e_fl + s_e_fr + s_e_rl + s_e_rr
                        if s_total == 0: s_total = 1
                        s_f_pct = ((s_e_fl + s_e_fr) / s_total) * 100
                        s_r_pct = ((s_e_rl + s_e_rr) / s_total) * 100
                        
                        fig = plt.figure(figsize=(15, 8), num=f'OpenDAV - Tire Energy {s_name}')
                        gs = fig.add_gridspec(2, 2, width_ratios=[2.5, 1], height_ratios=[1, 1])
                        
                        ax_line = fig.add_subplot(gs[:, 0])
                        window = 10
                        def smooth(d): return np.convolve(d, np.ones(window)/window, mode='same') if len(d) > window else d
                        
                        ax_line.plot(s_dist, smooth(s_wr_fl), label='FL', color='#2D8AE2', alpha=0.8)
                        ax_line.plot(s_dist, smooth(s_wr_fr), label='FR', color='#63B3ED', alpha=0.8)
                        ax_line.plot(s_dist, smooth(s_wr_rl), label='RL', color='#FF1493', alpha=0.8)
                        ax_line.plot(s_dist, smooth(s_wr_rr), label='RR', color='#FF69B4', alpha=0.8)
                        
                        ax_line.set_title(f"Work Rate - {s_name}", fontsize=14, pad=15)
                        ax_line.set_xlabel("Track Distance (m)", fontsize=11)
                        ax_line.set_ylabel("Est. Work Rate (kW)", fontsize=11)
                        ax_line.legend(loc='upper right')
                        ax_line.grid(True, linestyle='--', alpha=0.2)
                        
                        ax_bar = fig.add_subplot(gs[0, 1])
                        s_energies = [s_e_fl, s_e_fr, s_e_rl, s_e_rr]
                        bars = ax_bar.bar(['FL', 'FR', 'RL', 'RR'], s_energies, color=['#2D8AE2', '#63B3ED', '#FF1493', '#FF69B4'], alpha=0.9)
                        ax_bar.set_title(f"Energy Expenditure ({s_name})", fontsize=12, pad=10)
                        ax_bar.set_ylabel("Energy (kJ)", fontsize=10)
                        
                        ax_pie = fig.add_subplot(gs[1, 1])
                        ax_pie.pie([s_f_pct, s_r_pct], labels=['Front', 'Rear'], colors=['#2D8AE2', '#FF1493'], autopct='%1.1f%%', startangle=90)
                        
                        info_t = f"File: {file_basename}\\nSector: {s_name}\\nLap: {int(lap_num)}"
                        plt.figtext(0.02, 0.02, info_t, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                    bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
                        
                        plt.tight_layout()
                        plt.savefig(os.path.join(batch_path, f"TireEnergy_{s_suffix}_{file_basename}.png"), dpi=200, bbox_inches='tight')
                        plt.close(fig)
                        print(f"      [+] Exported {s_suffix} Report")
                    
                    print(f"  [#] Batch report completed: {batch_path}")
                    if headless: break
"""

# Insert before the invalid command print
content = content.replace(
    "else:\n                    print(\"  [!] Invalid command. Try 'open L1/L2/L3', 'print L1/L2/L3', or 'p'.\")",
    l4_logic + "\n                else:\n                    print(\"  [!] Invalid command. Try 'open L1/L2/L3', 'print L1/L2/L3/L4', or 'p'.\")"
)

# Also fix the existing "Invalid command" message if it didn't have L3/L4 yet
content = content.replace(
    "print(\"  [!] Invalid command. Try 'open L1/L2/L3', 'print L1/L2/L3', or 'p'.\")",
    "print(\"  [!] Invalid command. Try 'open L1/L2/L3', 'print L1/L2/L3/L4', or 'p'.\")"
)

with open('analysis/tire_energy.py', 'w') as f:
    f.write(content)
