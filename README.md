# OptiSweep Control

OptiSweep Control is a Python desktop application for controlling optical wavelength sweep measurements over GPIB/VISA, reading measurement results, plotting them directly in the application, and exporting acquired data.

The project targets laboratory configurations based on the Agilent 816x Lightwave Measurement family, including:

- **Agilent 8163A/B Lightwave Multimeter**
- **Agilent 8164A/B Lightwave Measurement System**
- **Agilent 8166A/B Lightwave Multichannel System**

Compatibility of individual commands depends on the optical source, photoreceiver/power-sensor modules, slot/channel configuration, firmware, and supported SCPI command set of the connected system.

## Features

- Configure sweep start and stop wavelength.
- Configure wavelength step and sweep speed.
- Select STEP or CONT sweep mode.
- Validate entered measurement parameters before sending commands.
- Send sweep settings without starting a sweep.
- Run a wavelength sweep.
- Configure photoreceiver averaging time, range mode, range, power unit and wavelength.
- Configure source and photoreceiver trigger routing.
- Send the IEEE 488.2 `*CLS` command.
- Read data from a completed sweep.
- Convert acquired power values to dBm.
- Display wavelength vs. power directly in the Tkinter GUI.
- Save results as CSV, TXT, or PNG.
- Select an output folder, with the user's Documents directory used by default.

## Current instrument configuration

The current application configuration uses:

```text
VISA resource: GPIB0::20::INSTR
Optical source / TLS channel: 0
Photoreceiver channel: 4
```

Change the address or channel identifiers in `main.py` if your laboratory configuration differs.

## GUI parameter limits

### Sweep

```text
Start wavelength: 1480–1650 nm
Stop wavelength:  1480–1650 nm
Step:             0.01–10 nm
Speed:            1–100 nm/s
Mode:             STEP / CONT
```

The stop wavelength must be greater than the start wavelength.

### Photoreceiver

```text
Averaging time: 80–100 us
Range mode:     Auto / Manual
Range:          -60, -50, -40, -30, -20, -10, 0, 10, 20 dBm
Power unit:     dBm / W
Wavelength:     1500–1600 nm
```

## Requirements

- Python 3.7+
- Working VISA implementation/driver on the computer
- Compatible Agilent 816x mainframe and installed optical modules
- Python packages from `requirements.txt`

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Then run:

```bash
python main.py
```

### PyCharm

Open the repository folder as a PyCharm project, select the Python interpreter containing the dependencies, and run `main.py`.

## Project structure

```text
optisweep-control/
├── main.py
├── README.md
├── requirements.txt
└── .gitignore
```

## Export

After measurement data have been read, the right side of the interface displays the sweep graph. Results can be exported as:

- **CSV** — wavelength and power columns
- **TXT** — wavelength and power columns
- **PNG** — graph image

The default output location is the current user's **Documents** folder. A different folder can be selected in the interface.

## Hardware and safety note

This application communicates with laboratory optical equipment. Before starting a measurement, verify the installed modules, optical connections, permissible measurement ranges, GPIB/VISA configuration, and the command support of the connected instrument.

Follow the manufacturer's operating instructions and applicable laser-safety procedures.

## Status

OptiSweep Control is currently a laboratory/educational application. Future improvements can include automatic VISA resource discovery, configurable module channels, richer measurement metadata, and additional plotting/export tools.
