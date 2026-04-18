import re

with open("website_preview.html", "r") as f:
    content = f.read()

# Define the modal HTML and JavaScript
modal_html = """
    <!-- Modal Container -->
    <div id="feature-modal" class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 opacity-0 pointer-events-none transition-opacity duration-300">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-black/60 backdrop-blur-sm cursor-pointer" onclick="closeModal()"></div>
        
        <!-- Modal Content -->
        <div class="relative w-full max-w-3xl bg-[#111] border border-white/10 rounded-2xl shadow-2xl flex flex-col max-h-[90vh] transform scale-95 transition-transform duration-300" id="modal-content-box">
            
            <!-- Modal Header -->
            <div class="flex items-center justify-between p-6 border-b border-white/5 bg-[#0a0a0a] rounded-t-2xl">
                <div class="flex items-center gap-4">
                    <div id="modal-icon" class="w-10 h-10 rounded-lg bg-accent-cyan/10 flex items-center justify-center text-accent-cyan">
                        <!-- Icon injected via JS -->
                    </div>
                    <h3 id="modal-title" class="text-2xl font-bold tracking-tight">Feature Title</h3>
                </div>
                <button onclick="closeModal()" class="p-2 rounded-full hover:bg-white/10 text-white/40 hover:text-white transition-colors">
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                </button>
            </div>

            <!-- Modal Body -->
            <div class="p-6 overflow-y-auto">
                <div class="space-y-8">
                    <!-- Description -->
                    <div>
                        <h4 class="text-xs font-bold text-white/30 uppercase tracking-wider mb-2">Engineering Context</h4>
                        <p id="modal-desc" class="text-white/80 leading-relaxed text-lg"></p>
                    </div>

                    <!-- Requirements -->
                    <div>
                        <h4 class="text-xs font-bold text-white/30 uppercase tracking-wider mb-3">Required Telemetry Channels</h4>
                        <div id="modal-reqs" class="flex flex-wrap gap-2">
                            <!-- Badges injected via JS -->
                        </div>
                    </div>

                    <!-- Example CLI Output -->
                    <div>
                        <h4 class="text-xs font-bold text-white/30 uppercase tracking-wider mb-3">Console Output Example</h4>
                        <div class="rounded-xl bg-black border border-white/10 p-4 overflow-x-auto">
                            <pre id="modal-cli" class="font-mono text-sm leading-relaxed text-accent-cyan/90"></pre>
                        </div>
                    </div>
                </div>
            </div>
            
        </div>
    </div>

    <!-- Feature Data & Logic -->
    <script>
        const featuresData = {
            'setup-prediction': {
                title: 'Setup Prediction Engine',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></svg>',
                desc: 'Input setup changes (like ARB stiffness) to predict outside tire load shifts and visualize ghost roll gradients.',
                reqs: ['G Force Lat', 'Ride Height FL/FR/RL/RR', 'Vehicle Mass/Track Width'],
                cli: `┌───────────────────────────────────────┐\n│ Setup Prediction Engine               │\n│ Target: +2 Clicks Front ARB           │\n│ Predicted F Roll Grad: 8.90 mm/G      │\n│ Expected Balance Shift: +2.1% Front   │\n└───────────────────────────────────────┘`
            },
            'roll-gradient': {
                title: 'Roll Gradient Analysis',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="16"/></svg>',
                desc: 'Calculates the roll gradient (mm/G) for both the front and rear axles by analyzing lateral G-forces against dynamic ride heights. This provides a clear, empirical Roll Balance percentage, allowing engineers to definitively tune Anti-Roll Bars (ARBs) and spring rates for perfect mid-corner mechanical grip.',
                reqs: ['G Force Lat', 'Ride Height FL', 'Ride Height FR', 'Ride Height RL', 'Ride Height RR'],
                cli: `┌───────────────────────────────────────┐\n│ Front Roll Gradient: 10.80 mm/G       │\n│ Rear Roll Gradient:  10.10 mm/G       │\n└───────────────────────────────────────┘\n┌───────────────────────────────────────┐\n│ Roll Balance (Higher % = Softer end): │\n│ Front: 51.7% | Rear: 48.3%            │\n└───────────────────────────────────────┘`
            },
            'aero-rake': {
                title: 'Dynamic Aero/Rake',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m13 2-2 2.5h3L12 7"/><path d="m13 17-2 2.5h3L12 22"/><path d="M18 9c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4Z"/><path d="M6 9c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4Z"/><path d="M18 23c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4Z"/><path d="M6 23c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4Z"/><path d="M12 2v20"/></svg>',
                desc: 'Maps vehicle rake (Rear Ride Height - Front Ride Height) against GPS/Wheel speed on straights (filtering out heavy cornering/braking). OpenDAV performs a linear regression to output your exact aero platform movement in mm/mph. Stop guessing your end-of-straight splitter height and start engineering it.',
                reqs: ['Speed', 'G Force Lat', 'G Force Long', 'Ride Height FL/FR/RL/RR'],
                cli: `  Max Speed: 168.4 mph\n  Rake Adjustment: -0.1450 mm/mph\n\n┌───────────────────────────────────────┐\n│ Modeled Rake at speeds:               │\n│ @  50 mph: 24.5 mm                    │\n│ @ 100 mph: 17.2 mm                    │\n│ @ 150 mph: 10.0 mm                    │\n│ @ 168 mph (Max):  7.4 mm              │\n└───────────────────────────────────────┘`
            },
            'tire-analysis': {
                title: 'Empirical Tire Analysis',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 4v10.54a4 4 0 1 1-4 0V4a2 2 0 0 1 4 0Z"/></svg>',
                desc: 'Scans your entire stint, correlating lap times with Inner/Center/Outer tire temperatures and dynamic pressures. By identifying the exact thermal and pressure conditions during your fastest laps, OpenDAV provides the empirical Optimal Window for your specific setup and driving style.',
                reqs: ['Tyre Temp (Inner/Center/Outer)', 'Tyre Pressure (FL/FR/RL/RR)', 'Lap Time'],
                cli: `┌─────────────────────────────────────────────────┐\n│ [ OPTIMAL SETUP (Based on fastest lap 4) ]      │\n│ Fastest Time:     126.800 s                     │\n│ Optimal Avg Temp: 84.5°C                        │\n│ Optimal Peak Temp: 92.1°C                       │\n│ Optimal Avg Press: 26.5 psi                     │\n└─────────────────────────────────────────────────┘`
            },
            'sector-analysis': {
                title: 'Sector Analysis',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/><line x1="15" x2="15" y1="6" y2="21"/></svg>',
                desc: 'Break down performance sector-by-sector to find exactly where time is being gained or lost.',
                reqs: ['Distance', 'Time', 'Speed'],
                cli: `┌───────────────────────────────────────┐\n│ Sector 1: 34.200s (-0.150s)           │\n│ Sector 2: 45.100s (+0.200s)           │\n│ Sector 3: 20.500s (-0.050s)           │\n└───────────────────────────────────────┘`
            },
            'setup-viewer': {
                title: 'Setup Viewer',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
                desc: 'Instantly parse and visualize your car setup parameters directly from the telemetry file.',
                reqs: ['All Static Setup Channels'],
                cli: `┌───────────────────────────────────────┐\n│ Setup Configuration Loaded            │\n│ Spring FL: 120 N/mm                   │\n│ Spring FR: 120 N/mm                   │\n│ ARB Front: Pos 3                      │\n└───────────────────────────────────────┘`
            },
            'math-sandbox': {
                title: 'Custom Math Sandbox',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
                desc: 'A powerful, sandboxed environment allowing race engineers to define custom derived channels on the fly. Input Python-syntax mathematical formulas combining any loaded MoTeC channels to evaluate custom suspension histograms, slip angles, or driver inputs without writing a full script.',
                reqs: ['Any valid MoTeC Channel loaded via .ld'],
                cli: `┌───────────────────────────────────────┐\n│ Custom Channel Evaluation:            │\n│ Formula: (FL_Speed - GPS_Speed) / GPS │\n│ Evaluated: Slip Ratio FL              │\n│ Status: Plotted to Matplotlib         │\n└───────────────────────────────────────┘`
            },
            'fuel-correlation': {
                title: 'Fuel Correlation',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 22L15 22L15 7L3 7L3 22Z"/><path d="M18 22L21 22L21 11L18 11L18 22Z"/><path d="M15 7L18 11"/><path d="M12 7L12 3L15 3"/><path d="M6 11L12 11"/><path d="M6 15L12 15"/></svg>',
                desc: 'Analyzes lap pace degradation mapped against fuel burn (liters/lap) and starting tire conditions. Pinpoint the exact lap where your fuel load and tire lifecycle perfectly intersect for peak qualifying or race pace.',
                reqs: ['Fuel Level', 'Lap Time', 'Tyre Temps'],
                cli: `┌───────────────────────────────────────┐\n│ Fuel & Pace Correlation               │\n│ Peak Pace Lap: 5                      │\n│ Fuel at Peak: 24.5 L                  │\n│ Pace Deg/Lap: +0.085s                 │\n└───────────────────────────────────────┘`
            },
            'automator': {
                title: 'OpenDAV Automator',
                icon: '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
                desc: 'The ultimate time-saver. Point the Automator at a directory of .ld files, and it will silently run every OpenDAV module. It generates a comprehensive text report and exports high-resolution Plotly/Matplotlib graphs into a neatly organized _Analysis subfolder.',
                reqs: ['Valid telemetry directory containing .ld and .id files'],
                cli: `┌───────────────────────────────────────┐\n│ OpenDAV Automator Running...             │\n│ Processing Stint_1.ld [1/4]           │\n│ - Generated Rake_Graph.png            │\n│ - Generated Roll_Report.txt           │\n│ Status: 100% Complete.                │\n└───────────────────────────────────────┘`
            }
        };

        const modal = document.getElementById('feature-modal');
        const contentBox = document.getElementById('modal-content-box');
        
        function openModal(id) {
            const data = featuresData[id];
            if(!data) return;

            document.getElementById('modal-title').textContent = data.title;
            document.getElementById('modal-icon').innerHTML = data.icon;
            document.getElementById('modal-desc').textContent = data.desc;
            document.getElementById('modal-cli').textContent = data.cli;

            const reqsContainer = document.getElementById('modal-reqs');
            reqsContainer.innerHTML = '';
            data.reqs.forEach(req => {
                const span = document.createElement('span');
                span.className = 'px-3 py-1 text-sm rounded-full bg-accent-pink/10 text-accent-pink border border-accent-pink/20';
                span.textContent = req;
                reqsContainer.appendChild(span);
            });

            modal.classList.remove('opacity-0', 'pointer-events-none');
            contentBox.classList.remove('scale-95');
            document.body.style.overflow = 'hidden';
        }

        function closeModal() {
            modal.classList.add('opacity-0', 'pointer-events-none');
            contentBox.classList.add('scale-95');
            document.body.style.overflow = 'auto';
        }
    </script>
</body>
"""

# Replace </body> with the modal_html
content = content.replace("</body>", modal_html)

# Add onclick to the feature cards
def inject_onclick(match):
    full_card = match.group(0)
    title = match.group(1)
    
    # Map title to id
    id_map = {
        'Setup Prediction Engine': 'setup-prediction',
        'Roll Gradient Analysis': 'roll-gradient',
        'Dynamic Aero/Rake': 'aero-rake',
        'Empirical Tire Analysis': 'tire-analysis',
        'Sector Analysis': 'sector-analysis',
        'Setup Viewer': 'setup-viewer',
        'Custom Math Sandbox': 'math-sandbox',
        'Fuel Correlation': 'fuel-correlation',
        'OpenDAV Automator': 'automator'
    }
    
    feature_id = id_map.get(title, '')
    
    # inject onclick and cursor-pointer
    replaced = full_card.replace('class="group p-8', f'onclick="openModal(\'{feature_id}\')" class="cursor-pointer group p-8')
    return replaced

# Regex to find feature cards and extract their title to inject onclick
# Looks for: <div class="group p-8... > ... <h3 class="text-xl font-bold mb-3">TITLE</h3> ... </div>
import re
pattern = re.compile(r'<div class="group p-8 rounded-2xl bg-white/\[0\.02\].*?<h3 class="text-xl font-bold mb-3">(.*?)</h3>.*?</div>', re.DOTALL)

content = pattern.sub(inject_onclick, content)

# Write back
with open("website_preview.html", "w") as f:
    f.write(content)

