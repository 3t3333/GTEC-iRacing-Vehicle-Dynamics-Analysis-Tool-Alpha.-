import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

def show_ctk_graph(fig, title):
    ctk.set_appearance_mode("Dark")
    app = ctk.CTk()
    app.geometry("1100x750")
    app.title(title)
    
    canvas = FigureCanvasTkAgg(fig, master=app)
    canvas.draw()
    canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
    
    toolbar = NavigationToolbar2Tk(canvas, app)
    toolbar.update()
    canvas.get_tk_widget().pack(side=ctk.TOP, fill=ctk.BOTH, expand=True)
    
    app.mainloop()
