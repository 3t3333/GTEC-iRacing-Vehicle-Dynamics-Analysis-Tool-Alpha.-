# Deprecated: CustomTkinter and Tkinter are removed for headless/Chromebook compatibility.
# This function remains to prevent breaking existing imports, but defaults to standard Matplotlib.

def show_ctk_graph(fig, title):
    import matplotlib.pyplot as plt
    # Fallback to standard matplotlib
    fig.canvas.manager.set_window_title(title)
    plt.show(block=True)
