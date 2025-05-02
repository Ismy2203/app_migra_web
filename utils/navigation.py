def change_frame(app, new_frame_func):
    for widget in app.winfo_children():
        widget.pack_forget()
    new_frame_func(app)
