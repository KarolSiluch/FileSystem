import tkinter as tk
import disc


class HexDiskVisualizer:
    def __init__(self, root, file_system: disc.Disc):
        self.fs = file_system
        self.root = root
        self.root.title("Podgląd Pamięci Dysku (Hex View)")

        self.BYTE_SIZE = 25
        self.BYTES_PER_ROW = 32
        self.FONT_SIZE = 8

        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        toolbar = tk.Frame(main_frame, pady=5)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="Odśwież Widok", command=self.draw_hex_grid).pack(side=tk.LEFT, padx=10)
        self.status_label = tk.Label(toolbar, text="Gotowy", fg="blue")
        self.status_label.pack(side=tk.LEFT, padx=10)

        legend_frame = tk.Frame(main_frame, pady=5)
        legend_frame.pack(side=tk.BOTTOM, fill=tk.X)
        self.create_legend(legend_frame)

        self.canvas_frame = tk.Frame(main_frame)
        self.canvas_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        self.v_scroll = tk.Scrollbar(self.canvas_frame, orient=tk.VERTICAL)
        self.canvas = tk.Canvas(self.canvas_frame, bg="#f0f0f0", yscrollcommand=self.v_scroll.set)

        self.v_scroll.config(command=self.canvas.yview)
        self.v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.setup_text_viewer(main_frame)

        self.root.after(100, self.draw_hex_grid)

    def setup_text_viewer(self, parent):
        viewer_frame = tk.LabelFrame(parent, text="Podgląd Zawartości", padx=5, pady=5)
        viewer_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        text_scroll = tk.Scrollbar(viewer_frame)
        text_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_display = tk.Text(viewer_frame, height=8, state='disabled', yscrollcommand=text_scroll.set)
        self.text_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        text_scroll.config(command=self.text_display.yview)

        self.text_display.tag_config("INFO", foreground="black")
        self.text_display.tag_config("ERROR", foreground="red")
        self.text_display.tag_config("SUCCESS", foreground="green", font=("Arial", 9, "bold"))
        self.text_display.tag_config("DATA", foreground="blue", font=("Courier", 9))

    def console_log(self, message: str, tag: str = "INFO"):
        self.text_display.config(state='normal')
        self.text_display.insert(tk.END, f"> {message}\n", tag)
        self.text_display.see(tk.END)
        self.text_display.config(state='disabled')

    def create_legend(self, parent):
        colors = [
            ("#FFCCCC", "Blok Kontrolny"),
            ("#CCFFCC", "Deskryptory"),
            ("#CCCCFF", "Mapa Bitowa"),
            ("#FFFFCC", "Dane"),
        ]
        for color, text in colors:
            lbl = tk.Label(parent, text=f"  {text}  ", bg=color, relief="solid", borderwidth=1, font=("Arial", 8))
            lbl.pack(side=tk.LEFT, padx=5)

    def get_color_for_byte(self, index):
        if index < disc.FILE_DESCRIPTOR_TABLE:
            return "#FFCCCC"
        if index < disc.ALLOCATION_TABLE:
            return "#CCFFCC"
        if index < disc.DATA:
            return "#CCCCFF"
        if index < disc.END:
            return "#FFFFCC"
        return "#DDDDDD"

    def draw_hex_grid(self):
        self.status_label.config(text="Rysowanie... proszę czekać")
        self.canvas.delete("all")
        self.root.update()

        data = self.fs.getBytearray()
        total_bytes = len(data)

        x_start = 10
        y_start = 10

        for i in range(total_bytes):
            byte_val = data[i]

            row = i // self.BYTES_PER_ROW
            col = i % self.BYTES_PER_ROW

            x1 = x_start + col * self.BYTE_SIZE
            y1 = y_start + row * self.BYTE_SIZE
            x2 = x1 + self.BYTE_SIZE
            y2 = y1 + self.BYTE_SIZE

            color = self.get_color_for_byte(i)

            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="gray")

            hex_text = f"{byte_val:02X}"

            text_color = "black" if byte_val != 0 else "#AAAAAA"

            self.canvas.create_text(
                x1 + self.BYTE_SIZE / 2,
                y1 + self.BYTE_SIZE / 2,
                text=hex_text,
                fill=text_color,
                font=("Courier", self.FONT_SIZE)
            )

        total_height = y_start + (total_bytes // self.BYTES_PER_ROW + 1) * self.BYTE_SIZE
        total_width = x_start + self.BYTES_PER_ROW * self.BYTE_SIZE

        self.canvas.config(scrollregion=(0, 0, total_width + 20, total_height + 20))
        self.status_label.config(text=f"Wyświetlono {total_bytes} bajtów")


def run_step_1():
    app.console_log("--- [ETAP 1] Symulacja Awarii ---")

    f_desc = fs.open('n1')

    app.console_log(f"Początkowe dane w pliku: \"{fs.read(f_desc)}\"\n")

    try:
        fs.extend_file(f_desc, 'KluczoweDane' * 3, error=True)
    except RuntimeError:
        app.console_log("--- Wystąpił oczekiwany błąd zapisu! ---")
        app.console_log(f"Stan pliku po przerwaniu:  \"{fs.read(fs.open('n1'))}\"\n")

    app.draw_hex_grid()

    action_button.config(
        text="Uruchom Naprawę (Etap 2)",
        command=run_step_2
    )


def run_step_2():
    app.console_log("--- [ETAP 2] Naprawa Systemu ---")

    fs.repair()
    app.console_log(f"Stan pliku po naprawie:  \"{fs.read(fs.open('n1'))}\"\n")

    app.draw_hex_grid()
    action_button.config(text="Gotowe", state="disabled")


root = tk.Tk()
root.geometry("900x700")
root.title("Symulator Awarii Systemu Plików")

fs = disc.Disc()
fs.create_file('n1', 'DanePoczatkowe')
f_desc = fs.open('n1')
app = HexDiskVisualizer(root, fs)

control_frame = tk.Frame(root, pady=20, bg="#dddddd")
control_frame.pack(side=tk.BOTTOM, fill=tk.X)

action_button = tk.Button(
    control_frame,
    text="Rozpocznij Symulację (Etap 1)",
    font=("Arial", 14, "bold"),
    bg="#e1e1e1",
    command=run_step_1
)
action_button.pack(ipadx=20, ipady=10)

root.mainloop()
