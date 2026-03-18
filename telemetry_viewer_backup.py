def run_telemetry_viewer(sessions):
    while True:
        clear_screen()
        print("="*60)
        print(" GteC | Interactive Line Graph Viewer")
        print("="*60)
        
        for session in sessions:
            file_path = session['file_path']
            data = session['data']
            channels = session['channels']
            print(f"\nAnalyzing: {os.path.basename(file_path)}")
            
            # Find Channels
            def get_ch(names):
                return next((ch for ch in names if ch in data), None)
            
            lat_g_ch = get_ch(['G Force Lat', 'LatAccel', 'LatG'])
            speed_ch = get_ch(['Ground Speed', 'Speed'])
            fl_spd_ch = get_ch(['Wheel Speed FL', 'LFspeed'])
            fr_spd_ch = get_ch(['Wheel Speed FR', 'RFspeed'])
            rl_spd_ch = get_ch(['Wheel Speed RL', 'LRspeed'])
            rr_spd_ch = get_ch(['Wheel Speed RR', 'RRspeed'])
            thr_ch = get_ch(['Throttle', 'Throttle Position', 'ThrottleRaw'])
            brk_ch = get_ch(['Brake', 'Brake Pedal Position', 'BrakeRaw'])
            gear_ch = get_ch(['Gear'])
            
            req = [lat_g_ch, speed_ch, fl_spd_ch, fr_spd_ch, rl_spd_ch, rr_spd_ch, thr_ch, brk_ch, gear_ch]
            if not all(req):
                missing = [n for n, c in zip(['LatG', 'Speed', 'FL_Spd', 'FR_Spd', 'RL_Spd', 'RR_Spd', 'Throttle', 'Brake', 'Gear'], req) if not c]
                print(f"  [!] Missing channels for full telemetry view: {missing}")
                continue
                
            lap_arr = data[channels['lap']].data
            time_arr = data[channels['time']].data
            dist_arr = data[channels['dist']].data
            laps = np.unique(lap_arr)
            
            # Find fastest valid lap
            lap_times = []
            for lap in laps:
                idx = np.where(lap_arr == lap)[0]
                if len(idx) < 100: continue
                lap_times.append((lap, time_arr[idx][-1] - time_arr[idx][0]))
                
            if not lap_times:
                print("  [!] No valid laps found.")
                continue
                
            median_time = np.median([t[1] for t in lap_times])
            valid_laps = [t for t in lap_times if median_time * 0.89 <= t[1] <= median_time * 1.11]
            if not valid_laps:
                print("  [!] No laps within valid threshold.")
                continue
                
            fastest_lap, fastest_time = min(valid_laps, key=lambda x: x[1])
            idx = np.where(lap_arr == fastest_lap)[0]
            
            # Extract Data for Fastest Lap
            dist = dist_arr[idx]
            
            def safe_get_data(ch_name):
                try:
                    return data[ch_name].data[idx]
                except Exception:
                    return np.zeros(len(idx))

            lat_g = safe_get_data(lat_g_ch)
            speed = safe_get_data(speed_ch)
            
            # Speeds might be in km/h or mph or m/s, but we just plot raw
            fl_spd = safe_get_data(fl_spd_ch)
            fr_spd = safe_get_data(fr_spd_ch)
            front_spd_avg = (fl_spd + fr_spd) / 2.0
            
            rl_spd = safe_get_data(rl_spd_ch)
            rr_spd = safe_get_data(rr_spd_ch)
            rear_spd_avg = (rl_spd + rr_spd) / 2.0
            
            thr = safe_get_data(thr_ch)
            brk = safe_get_data(brk_ch)
            gear = safe_get_data(gear_ch)
            
            ans = input(f"\n  Launch telemetry graph for Lap {int(fastest_lap)} ({fastest_time:.3f}s)? (y/n): ").strip().lower()
            if ans == 'y':
                print("  [+] Building interactive telemetry trace... (Close the window to continue)")
                
                if GUI_MODE == 2:
                    fig = make_subplots(rows=6, cols=1, shared_xaxes=True,
                                        vertical_spacing=0.05,
                                        subplot_titles=("Lateral G", "Front Wheel Speed & Ground Speed", "Throttle", "Brake", "Rear Wheel Speed", "Gear"))
                    
                    fig.add_trace(go.Scatter(x=dist, y=lat_g, mode='lines', line=dict(color='cyan', width=1.5)), row=1, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=front_spd_avg, mode='lines', line=dict(color='yellow', width=1.5), name='Avg Front Whl Spd'), row=2, col=1)
                    fig.add_trace(go.Scatter(x=dist, y=speed, mode='lines', line=dict(color='deeppink', width=1.5, dash='dash'), name='Ground Speed'), row=2, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=thr, mode='lines', line=dict(color='lime', width=1.5)), row=3, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=brk, mode='lines', line=dict(color='red', width=1.5)), row=4, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=rear_spd_avg, mode='lines', line=dict(color='orange', width=1.5)), row=5, col=1)
                    
                    fig.add_trace(go.Scatter(x=dist, y=gear, mode='lines', line=dict(color='white', width=1.5, shape='vh')), row=6, col=1)
                    
                    fig.update_layout(
                        title=f"Telemetry Trace - Lap {int(fastest_lap)}<br>{os.path.basename(file_path)}",
                        template="plotly_dark",
                        font=dict(family="Consolas", size=11),
                        height=900,
                        showlegend=False
                    )
                    fig.update_xaxes(title_text="Lap Distance (m)", row=6, col=1)
                    fig.show()

                else:
                    plt.style.use('dark_background')
                    plt.rcParams['font.family'] = 'Consolas'
                    
                    fig, axs = plt.subplots(6, 1, figsize=(14, 10), sharex=True, num='GTEC - Telemetry Viewer')
                    fig.suptitle(f"Telemetry Trace - Lap {int(fastest_lap)}\n{os.path.basename(file_path)}", fontsize=16, fontweight='bold')
                    
                    # 1. Lateral G
                    axs[0].plot(dist, lat_g, color='cyan', linewidth=1.5)
                    axs[0].set_ylabel("Lat G", fontsize=11)
                    axs[0].grid(True, linestyle='--', alpha=0.3)
                    
                    # 2. Front Wheel Speed & Ground Speed
                    axs[1].plot(dist, front_spd_avg, color='yellow', linewidth=1.5, label='Avg Front Whl Spd')
                    axs[1].plot(dist, speed, color='deeppink', linewidth=1.5, linestyle='--', label='Ground Speed')
                    axs[1].set_ylabel("Front Spd", fontsize=11)
                    axs[1].legend(loc='upper right', fontsize=9, framealpha=0.5)
                    axs[1].grid(True, linestyle='--', alpha=0.3)
                    
                    # 3. Throttle
                    axs[2].plot(dist, thr, color='lime', linewidth=1.5)
                    axs[2].set_ylabel("Throttle", fontsize=11)
                    axs[2].set_ylim(-5, 105)
                    axs[2].grid(True, linestyle='--', alpha=0.3)
                    
                    # 4. Brake
                    axs[3].plot(dist, brk, color='red', linewidth=1.5)
                    axs[3].set_ylabel("Brake", fontsize=11)
                    axs[3].grid(True, linestyle='--', alpha=0.3)
                    
                    # 5. Rear Wheel Speed
                    axs[4].plot(dist, rear_spd_avg, color='orange', linewidth=1.5)
                    axs[4].set_ylabel("Rear Spd", fontsize=11)
                    axs[4].grid(True, linestyle='--', alpha=0.3)
                    
                    # 6. Gear
                    axs[5].plot(dist, gear, color='white', linewidth=1.5, drawstyle='steps-post')
                    axs[5].set_ylabel("Gear", fontsize=11)
                    axs[5].set_xlabel("Lap Distance (m)", fontsize=13)
                    axs[5].set_yticks(np.arange(0, max(gear)+2, 1))
                    axs[5].grid(True, linestyle='--', alpha=0.3)
                    
                    plt.tight_layout()
                    # Adjust top to fit suptitle
                    plt.subplots_adjust(top=0.92, hspace=0.15)
    
                    if GUI_MODE == 3:
                        show_ctk_graph(fig, "GTEC - Telemetry Viewer")
                    else:
                        plt.show()

        print("\n" + "="*60)
        inp = input("Press Enter to return to Tools Menu or 'q' to quit: ").strip().lower()
        if inp == 'q':
            show_exit_screen()
            sys.exit(0)
        break

