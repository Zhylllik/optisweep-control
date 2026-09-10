import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import csv
import time

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import pyvisa


GPIB_ADDRESS = "GPIB0::20::INSTR"
TIMEOUT_MS = 10000

current_wavelength = None
current_power_dbm = None


def get_instrument():
    rm = pyvisa.ResourceManager()
    instrument = rm.open_resource(GPIB_ADDRESS)
    instrument.timeout = TIMEOUT_MS
    return instrument


def read_sweep_params():
    try:
        start = int(entry_start.get().strip())
        stop = int(entry_stop.get().strip())
        step = float(entry_step.get().strip())
        speed = int(entry_speed.get().strip())
        mode = mode_var.get()
    except ValueError:
        messagebox.showerror("Ошибка", "Все значения Sweep должны быть числами.")
        return None

    if not 1480 <= start <= 1650:
        messagebox.showerror("Ошибка", "Start должен быть от 1480 до 1650 nm.")
        return None
    if not 1480 <= stop <= 1650:
        messagebox.showerror("Ошибка", "Stop должен быть от 1480 до 1650 nm.")
        return None
    if stop <= start:
        messagebox.showerror("Ошибка", "Stop должен быть больше Start.")
        return None
    if not 0.01 <= step <= 10:
        messagebox.showerror("Ошибка", "Step должен быть от 0.01 до 10 nm.")
        return None
    if not 1 <= speed <= 100:
        messagebox.showerror("Ошибка", "Speed должен быть от 1 до 100 nm/s.")
        return None

    return start, stop, step, speed, mode


def send_sweep_params(show_success=True):
    params = read_sweep_params()
    if not params:
        return None

    start, stop, step, speed, mode = params

    try:
        instrument = get_instrument()
        instrument.write("wav:swe:mode " + mode)
        instrument.write(f"wav:swe:start {start} nm")
        instrument.write(f"wav:swe:stop {stop} nm")
        instrument.write(f"wav:swe:spe {speed} nm/s")
        instrument.write(f"wav:swe:step {step} nm")
        instrument.write("wav:swe:cycl 1")
        instrument.close()

        if show_success:
            messagebox.showinfo("Готово", "Параметры Sweep переданы.")
        return params
    except Exception as exc:
        messagebox.showerror("Ошибка", str(exc))
        return None


def run_sweep():
    params = send_sweep_params(show_success=False)
    if not params:
        return

    start, stop, step, speed, _ = params
    points = int(np.floor((stop - start) / step)) + 1
    avg_time = 1e-4

    try:
        instrument = get_instrument()
        instrument.write("sour0:pow:state on")
        instrument.write(f"sens4:func:par:logg {points},{avg_time}")
        instrument.write("sens4:func:stat stab,star")
        instrument.write("sour0:wav:swe:llog 1")
        instrument.write("wav:swe 1")

        estimated_seconds = abs(stop - start) / max(speed, 1)
        time.sleep(estimated_seconds + 2)
        instrument.close()

        read_and_plot()
    except Exception as exc:
        messagebox.showerror("Ошибка", str(exc))


def read_receiver_params():
    try:
        avg_time = float(entry_avg_time.get().strip())
        range_mode = range_mode_var.get()
        level = int(level_var.get())
        unit = unit_var.get()
        wavelength = int(entry_receiver_wavelength.get().strip())
    except ValueError:
        messagebox.showerror("Ошибка", "Некорректный ввод в блоке фотоприёмника.")
        return None

    if not 80 <= avg_time <= 100:
        messagebox.showerror("Ошибка", "Atim должен быть от 80 до 100 US.")
        return None
    if not 1500 <= wavelength <= 1600:
        messagebox.showerror("Ошибка", "Wavelength должен быть от 1500 до 1600 nm.")
        return None

    return avg_time, range_mode, level, unit, wavelength


def send_receiver_params():
    params = read_receiver_params()
    if not params:
        return

    avg_time, range_mode, level, unit, wavelength = params

    try:
        instrument = get_instrument()
        instrument.write("init4:cont 1")
        instrument.write(f"sens4:pow:atim {avg_time}US")
        instrument.write("sens4:pow:rang:auto " + range_mode)
        instrument.write(f"sens4:pow:rang {level} DBM")
        instrument.write("sens4:pow:unit " + unit)
        instrument.write(f"sens4:pow:wav {wavelength}nm")
        instrument.close()
        messagebox.showinfo("Готово", "Параметры фотоприёмника переданы.")
    except Exception as exc:
        messagebox.showerror("Ошибка", str(exc))


def configure_triggers():
    try:
        instrument = get_instrument()
        instrument.write("trig:conf LOOP")
        instrument.write("TRIG4:OUTP DIS")
        instrument.write("TRIG4:INP SME")
        instrument.write("TRIG0:OUTP STF")
        instrument.write("TRIG0:INP IGN")
        instrument.close()
        messagebox.showinfo("Готово", "Триггеры настроены.")
    except Exception as exc:
        messagebox.showerror("Ошибка", str(exc))


def send_cls():
    try:
        instrument = get_instrument()
        instrument.write("*CLS")
        instrument.close()
        messagebox.showinfo("Готово", "*CLS выполнена.")
    except Exception as exc:
        messagebox.showerror("Ошибка", str(exc))


def read_and_plot():
    global current_wavelength, current_power_dbm

    try:
        instrument = get_instrument()
        start = float(instrument.query("SOUR:WAV:STAR?"))
        stop = float(instrument.query("SOUR:WAV:STOP?"))
        power = instrument.query_binary_values(
            "SENS4:FUNC:RES?",
            datatype="d",
            is_big_endian=False,
        )
        instrument.close()

        power = np.asarray(power, dtype=float)
        if power.size == 0:
            raise ValueError("Прибор не вернул данные Sweep.")
        if np.any(power <= 0):
            raise ValueError("Получены нулевые или отрицательные значения мощности.")

        current_power_dbm = 10 * np.log10(power) + 30
        current_wavelength = np.linspace(start, stop, len(current_power_dbm))
        update_plot()
        read_status.config(text=f"Считано точек: {len(current_power_dbm)}")
    except Exception as exc:
        messagebox.showerror("Ошибка чтения", str(exc))


def update_plot():
    plot_axis.clear()
    plot_axis.plot(current_wavelength, current_power_dbm)
    plot_axis.set_title("Sweep result")
    plot_axis.set_xlabel("Wavelength (nm)")
    plot_axis.set_ylabel("Power (dBm)")
    plot_axis.grid(True)
    plot_figure.tight_layout()
    plot_canvas.draw()


def choose_save_folder():
    selected = filedialog.askdirectory(initialdir=save_folder_var.get())
    if selected:
        save_folder_var.set(selected)


def save_results():
    if current_wavelength is None or current_power_dbm is None:
        messagebox.showwarning("Нет данных", "Сначала выполните Sweep или нажмите «Считать данные».")
        return

    folder = Path(save_folder_var.get())
    folder.mkdir(parents=True, exist_ok=True)
    selected_format = save_format_var.get()
    timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")

    try:
        if selected_format == "CSV":
            filepath = folder / f"sweep_{timestamp}.csv"
            with filepath.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Wavelength (nm)", "Power (dBm)"])
                writer.writerows(zip(current_wavelength, current_power_dbm))
        elif selected_format == "TXT":
            filepath = folder / f"sweep_{timestamp}.txt"
            np.savetxt(
                filepath,
                np.column_stack((current_wavelength, current_power_dbm)),
                header="Wavelength (nm)\tPower (dBm)",
                delimiter="\t",
                comments="",
            )
        else:
            filepath = folder / f"sweep_{timestamp}.png"
            plot_figure.savefig(filepath, dpi=150)

        messagebox.showinfo("Сохранено", f"Результат сохранён:\n{filepath}")
    except Exception as exc:
        messagebox.showerror("Ошибка сохранения", str(exc))


win = tk.Tk()
win.title("OptiSweep Control")
win.geometry("1120x720")
win.minsize(1000, 650)

main = tk.Frame(win)
main.pack(fill="both", expand=True, padx=10, pady=10)
main.grid_columnconfigure(1, weight=1)
main.grid_rowconfigure(0, weight=1)

left_panel = tk.Frame(main)
left_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 10))

right_panel = tk.LabelFrame(main, text="Read Sweep", padx=10, pady=10)
right_panel.grid(row=0, column=1, sticky="nsew")
right_panel.grid_columnconfigure(0, weight=1)
right_panel.grid_rowconfigure(0, weight=1)

frame_sweep = tk.LabelFrame(left_panel, text="Sweep parameters", padx=10, pady=10)
frame_sweep.pack(fill="x", pady=(0, 8))

tk.Label(frame_sweep, text="Start (1480-1650 nm)").grid(row=0, column=0, sticky="w")
entry_start = tk.Entry(frame_sweep, width=10)
entry_start.grid(row=0, column=1, padx=5)
entry_start.insert(0, "1500")

tk.Label(frame_sweep, text="Stop (1480-1650 nm)").grid(row=1, column=0, sticky="w")
entry_stop = tk.Entry(frame_sweep, width=10)
entry_stop.grid(row=1, column=1, padx=5)
entry_stop.insert(0, "1530")

tk.Label(frame_sweep, text="Step (0.01-10 nm)").grid(row=2, column=0, sticky="w")
entry_step = tk.Entry(frame_sweep, width=10)
entry_step.grid(row=2, column=1, padx=5)
entry_step.insert(0, "1")

tk.Label(frame_sweep, text="Speed (1-100 nm/s)").grid(row=3, column=0, sticky="w")
entry_speed = tk.Entry(frame_sweep, width=10)
entry_speed.grid(row=3, column=1, padx=5)
entry_speed.insert(0, "5")

mode_var = tk.StringVar(value="STEP")
tk.Label(frame_sweep, text="Mode").grid(row=4, column=0, sticky="w")
tk.Radiobutton(frame_sweep, text="STEP", variable=mode_var, value="STEP").grid(row=4, column=1, sticky="w")
tk.Radiobutton(frame_sweep, text="CONT", variable=mode_var, value="CONT").grid(row=4, column=2, sticky="w")

tk.Button(frame_sweep, text="Передать данные", command=send_sweep_params).grid(row=5, column=0, pady=7)
tk.Button(frame_sweep, text="Запустить Sweep", command=run_sweep).grid(row=5, column=1, pady=7)

frame_receiver = tk.LabelFrame(left_panel, text="Фотоприёмник", padx=10, pady=10)
frame_receiver.pack(fill="x", pady=8)

tk.Label(frame_receiver, text="Atim (80-100 US)").grid(row=0, column=0, sticky="w")
entry_avg_time = tk.Entry(frame_receiver, width=10)
entry_avg_time.grid(row=0, column=1, padx=5)
entry_avg_time.insert(0, "100")

tk.Label(frame_receiver, text="Mode").grid(row=1, column=0, sticky="w")
range_mode_var = tk.StringVar(value="0")
tk.Radiobutton(frame_receiver, text="Auto", variable=range_mode_var, value="1").grid(row=1, column=1, sticky="w")
tk.Radiobutton(frame_receiver, text="Manual", variable=range_mode_var, value="0").grid(row=1, column=2, sticky="w")

tk.Label(frame_receiver, text="Range (dBm)").grid(row=2, column=0, sticky="w")
level_var = tk.StringVar(value="-20")
level_values = [-60, -50, -40, -30, -20, -10, 0, 10, 20]
tk.OptionMenu(frame_receiver, level_var, *level_values).grid(row=2, column=1, sticky="w")

tk.Label(frame_receiver, text="Unit").grid(row=3, column=0, sticky="w")
unit_var = tk.StringVar(value="0")
tk.Radiobutton(frame_receiver, text="dBm", variable=unit_var, value="0").grid(row=3, column=1, sticky="w")
tk.Radiobutton(frame_receiver, text="W", variable=unit_var, value="1").grid(row=3, column=2, sticky="w")

tk.Label(frame_receiver, text="Wavelength (1500-1600 nm)").grid(row=4, column=0, sticky="w")
entry_receiver_wavelength = tk.Entry(frame_receiver, width=10)
entry_receiver_wavelength.grid(row=4, column=1, padx=5)
entry_receiver_wavelength.insert(0, "1550")

tk.Button(frame_receiver, text="Передать данные", command=send_receiver_params).grid(row=5, column=0, pady=7)

frame_triggers = tk.LabelFrame(left_panel, text="Triggers", padx=10, pady=10)
frame_triggers.pack(fill="x", pady=8)
tk.Label(frame_triggers, text="Настройка triggers").pack(anchor="w")
tk.Button(frame_triggers, text="Запустить triggers", command=configure_triggers).pack(pady=(5, 0))

frame_cls = tk.LabelFrame(left_panel, text="Service", padx=10, pady=10)
frame_cls.pack(fill="x", pady=8)
tk.Label(frame_cls, text="CLS").pack(anchor="w")
tk.Button(frame_cls, text="Запустить cls", command=send_cls).pack(pady=(5, 0))

plot_figure, plot_axis = plt.subplots(figsize=(7, 5))
plot_axis.set_title("Sweep result")
plot_axis.set_xlabel("Wavelength (nm)")
plot_axis.set_ylabel("Power (dBm)")
plot_axis.grid(True)
plot_figure.tight_layout()

plot_canvas = FigureCanvasTkAgg(plot_figure, master=right_panel)
plot_canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

read_controls = tk.Frame(right_panel)
read_controls.grid(row=1, column=0, sticky="ew", pady=(10, 0))
read_controls.grid_columnconfigure(1, weight=1)

tk.Button(read_controls, text="Считать данные", command=read_and_plot).grid(row=0, column=0, padx=(0, 8), pady=4)
read_status = tk.Label(read_controls, text="Данные ещё не считаны", anchor="w")
read_status.grid(row=0, column=1, sticky="ew")

save_folder_var = tk.StringVar(value=str(Path.home() / "Documents"))
tk.Label(read_controls, text="Папка:").grid(row=1, column=0, sticky="w", pady=4)
tk.Entry(read_controls, textvariable=save_folder_var).grid(row=1, column=1, sticky="ew", pady=4)
tk.Button(read_controls, text="Выбрать...", command=choose_save_folder).grid(row=1, column=2, padx=(8, 0), pady=4)

save_format_var = tk.StringVar(value="CSV")
tk.Label(read_controls, text="Формат:").grid(row=2, column=0, sticky="w", pady=4)
tk.OptionMenu(read_controls, save_format_var, "CSV", "TXT", "PNG").grid(row=2, column=1, sticky="w", pady=4)
tk.Button(read_controls, text="Сохранить результат", command=save_results).grid(row=2, column=2, padx=(8, 0), pady=4)

win.mainloop()
