with open('analysis/aero_mapping.py', 'r') as f:
    content = f.read()

# Update UI Prompts
content = content.replace(
    "ans_raw = input(f\"\\n  Select action ('open L1', 'print L1', 'open L2', 'print L2', 'p' to go back < proj): \").strip().lower()",
    "ans_raw = input(f\"\\n  Select action ('open L1/L2/L3', 'print L1/L2/L3', 'p' to go back < proj): \").strip().lower()"
)
content = content.replace(
    "print(\"  [!] Invalid command. Try 'open L1/L2', 'print L1/L2', or 'p'.\")",
    "print(\"  [!] Invalid command. Try 'open L1/L2/L3', 'print L1/L2/L3', or 'p'.\")"
)

# Replace the L2 preview block to add L3 preview
l2_preview_str = """        L2: 2D INTERPOLATION (PRIMARY)                    2D INTERPOLATION (REFERENCE)               
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │                                         │   │ SETUP SHIFT: Wing [3->5], RH [50->48]   │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │                                         │   │                                         │      
 │ [X] AXIS: FRONT RIDE HEIGHT             │   │ [X] AXIS: FRONT RIDE HEIGHT             │      
 │ [Y] AXIS: REAR RIDE HEIGHT              │   │ [Y] AXIS: REAR RIDE HEIGHT              │      
 │ [C] MAP:  AB % DENSITY                  │   │ [C] MAP:  AB % DENSITY                  │      
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘      
 
  >> [USE CASE]: DIRECTLY COMPARE AERODYNAMIC TOPOGRAPHY SHIFTS BETWEEN TWO SETUP ITERATIONS."""

l3_preview_str = l2_preview_str + """

        L3: TARGET DELTA ANALYZER (MIGRATION & STABILITY)
 ┌───────────────────────────────────────────────────────────────────────────────────────┐
 │        [ SHADED LINE CHART ] DYNAMIC AERO BALANCE OVER TRACK DISTANCE                 │
 │       [ RED SHADING ] = MIGRATION SPIKE (OVERSTEER / LINE OF DEATH CROSSED)           │
 │       [ BLUE SHADING ] = SAFE ZONE (UNDERSTEER / CENTER OF PRESSURE BEHIND COG)       │
 └───────────────────────────────────────────────────────────────────────────────────────┘
 ┌─────────────────────────────────────────┐   ┌─────────────────────────────────────────┐      
 │     [ SCATTER ] RIDE HEIGHT ENVELOPE    │   │      [ LINE ] PITCH KINEMATICS          │
 │       VERIFY MECHANICAL PLATFORM        │   │        VERIFY BRAKING STABILITY         │
 └─────────────────────────────────────────┘   └─────────────────────────────────────────┘
  
  >> [USE CASE]: DIAGNOSE IF AERO VARIANCE IS CAUSED BY MECHANICAL PLATFORM FAILURE OR PITCH SENSITIVITY.
"""

content = content.replace(l2_preview_str, l3_preview_str)

# The L3 code logic
l3_logic = """
                elif ans in ['open l3', 'print l3']:
                    dist_ch = channels.get('dist')
                    if not dist_ch or dist_ch not in data:
                        print("  [!] Distance channel required for L3 Target Delta Analyzer. Aborting.")
                        continue
                    
                    dist_arr = data[dist_ch].data[aero_mask][valid_df_mask]
                    spd_arr = speed[aero_mask][valid_df_mask]
                    
                    # Sort data by distance for line charts
                    sort_idx = np.argsort(dist_arr)
                    d_s = dist_arr[sort_idx]
                    ab_s = aero_balance[sort_idx]
                    f_rh_s = f_rh[sort_idx]
                    r_rh_s = r_rh[sort_idx]
                    spd_s = spd_arr[sort_idx]
                    rake_s = r_rh_s - f_rh_s
                    
                    print(f"  [+] Target CoG (Center of Gravity) defaults to 45.0%.")
                    target_ab_input = input("      Enter Target Aero Balance % (or press Enter for 45.0): ").strip()
                    try:
                        target_ab = float(target_ab_input) if target_ab_input else 45.0
                    except ValueError:
                        target_ab = 45.0
                    
                    print("  [+] Building Target Delta Analyzer Graph (L3)...")
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
                    
                    fig = plt.figure(figsize=(18, 10), num='OpenDAV - Aero Delta Analyzer (L3)')
                    gs = fig.add_gridspec(2, 2, height_ratios=[1.2, 1], hspace=0.35, wspace=0.25)
                    
                    # Top Pane: Delta Line Chart
                    ax_delta = fig.add_subplot(gs[0, :])
                    
                    # Smooth AB for plotting readability (15-sample window)
                    window = 15
                    sm_ab = np.convolve(ab_s, np.ones(window)/window, mode='same')
                    
                    ax_delta.plot(d_s, sm_ab, color='white', linewidth=1.5, alpha=0.9, label='Dynamic Aero Balance')
                    ax_delta.axhline(target_ab, color='#FFD700', linestyle='--', linewidth=2, label=f'Target (CoG) = {target_ab}%')
                    
                    # Shading Logic (Milliken Line of Death)
                    ax_delta.fill_between(d_s, sm_ab, target_ab, where=(sm_ab > target_ab), interpolate=True, color='#FF1493', alpha=0.4, label='Danger: Forward Migration (Oversteer)')
                    ax_delta.fill_between(d_s, sm_ab, target_ab, where=(sm_ab <= target_ab), interpolate=True, color='#2D8AE2', alpha=0.4, label='Safe: Rearward Migration (Understeer)')
                    
                    ax_delta.set_title(f"Aerodynamic Migration & Stability Trace\\nTarget: {target_ab}%", fontsize=14, pad=15)
                    ax_delta.set_xlabel("Track Distance (m)", fontsize=11)
                    ax_delta.set_ylabel("Aero Balance (%)", fontsize=11)
                    ax_delta.legend(loc='upper right')
                    ax_delta.grid(True, linestyle='--', alpha=0.2)
                    
                    # Bottom Left: Platform Envelope Scatter
                    ax_plat = fig.add_subplot(gs[1, 0])
                    sc = ax_plat.scatter(f_rh_s, r_rh_s, c=spd_s, cmap='plasma', s=4, alpha=0.6, rasterized=True)
                    plt.colorbar(sc, ax=ax_plat, label='Speed')
                    
                    # Draw a bounding box for the target window (approximated by the 25th-75th percentile of AB near target)
                    target_mask = (ab_s >= target_ab - 1.0) & (ab_s <= target_ab + 1.0)
                    if np.any(target_mask):
                        f_min, f_max = np.percentile(f_rh_s[target_mask], 10), np.percentile(f_rh_s[target_mask], 90)
                        r_min, r_max = np.percentile(r_rh_s[target_mask], 10), np.percentile(r_rh_s[target_mask], 90)
                        import matplotlib.patches as patches
                        rect = patches.Rectangle((f_min, r_min), f_max - f_min, r_max - r_min, linewidth=2, edgecolor='#FFD700', facecolor='none', linestyle='--', label='Target Envelope')
                        ax_plat.add_patch(rect)
                        ax_plat.legend(loc='upper right')
                        
                    ax_plat.set_title("Mechanical Platform Attainment", fontsize=12, pad=10)
                    ax_plat.set_xlabel("Front Ride Height (mm)", fontsize=10)
                    ax_plat.set_ylabel("Rear Ride Height (mm)", fontsize=10)
                    ax_plat.grid(True, linestyle='--', alpha=0.2)
                    
                    # Bottom Right: Pitch Kinematics
                    ax_pitch = fig.add_subplot(gs[1, 1])
                    sm_rake = np.convolve(rake_s, np.ones(window)/window, mode='same')
                    ax_pitch.plot(d_s, sm_rake, color='#FF69B4', linewidth=1.5, alpha=0.8, label='Pitch / Rake (mm)')
                    ax_pitch.set_title("Pitch Kinematics (Braking Dive)", fontsize=12, pad=10)
                    ax_pitch.set_xlabel("Track Distance (m)", fontsize=10)
                    ax_pitch.set_ylabel("Rake (RRH - FRH) mm", fontsize=10, color='#FF69B4')
                    ax_pitch.tick_params(axis='y', labelcolor='#FF69B4')
                    
                    ax2 = ax_pitch.twinx()
                    ax2.plot(d_s, spd_s, color='#2D8AE2', linewidth=1.0, alpha=0.5, label='Speed')
                    ax2.set_ylabel("Speed", fontsize=10, color='#2D8AE2')
                    ax2.tick_params(axis='y', labelcolor='#2D8AE2')
                    
                    # Combine legends
                    lines_1, labels_1 = ax_pitch.get_legend_handles_labels()
                    lines_2, labels_2 = ax2.get_legend_handles_labels()
                    ax_pitch.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right')
                    
                    info_text = (f"File: {file_basename}\\nCar: {car_name}\\nAvg AB: {median_ab:.1f}%")
                    plt.figtext(0.02, 0.02, info_text, fontsize=9, color='white', alpha=0.8, va='bottom', ha='left',
                                bbox=dict(facecolor='#1a1a1a', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))

                    plt.tight_layout()

                    if ans == 'open l3':
                        gui_mode = get_gui_mode()
                        if gui_mode == 3: show_ctk_graph(fig, "OpenDAV - Aero Delta Analyzer (L3)")
                        else: plt.show()
                    else:
                        timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
                        file_out = f"F2L3_{timestamp}_{file_basename}.png"
                        if '<' in ans_raw:
                            project_name = ans_raw.split('<')[1].strip().replace('[', '').replace(']', '').strip()
                            from analysis.projects import save_to_project
                            subf = headless_config.get('run_folder') if headless else None
                            save_to_project(fig, project_name, file_out, subfolder=subf)
                            plt.close(fig)
                            if headless: break
                        else:
                            os.makedirs("exports", exist_ok=True)
                            export_path = f"exports/{file_out}"
                            plt.savefig(export_path, dpi=300, bbox_inches='tight')
                            plt.close(fig)
                            print(f"  [+] Saved to {export_path}")
                        if headless: break
"""

# Insert L3 right before: "else: \n print("  [!] Invalid command"
content = content.replace(
    "                else:\n                    print(\"  [!] Invalid command",
    l3_logic + "\n                else:\n                    print(\"  [!] Invalid command"
)

with open('analysis/aero_mapping.py', 'w') as f:
    f.write(content)
