
def scalar_bar_args(title):
    return {
        "title":title.replace(":"," — "), "vertical":True,
        "position_x":0.88, "position_y":0.12, "width":0.075, "height":0.76,
        "color":"#f0f3f6", "title_font_size":12, "label_font_size":10,
        "background_color":"#20262d", "n_labels":7, "fmt":"%.4g",
    }
