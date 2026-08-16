import tkinter as tk
import mmap
import os
import glob

DEVICE = "/dev/piuio_full0"

# Number of bytes exposed by the device that we care about.
NUM_BYTES = 32

# ============================================================================
# SENSOR MAPPING
# ============================================================================
#
# Format:
#
#     (byte_index, bit_position): (pad, panel, sensor)
#
# pad:
#     1 or 2
#
# panel:
#     1 through 9
#
# sensor:
#     "top"
#     "left"
#     "right"
#     "bottom"

SENSOR_MAP = {
    # P1 UpLeft
    (0 * 8 + 0, 0): (1, 1, "right"),
    (1 * 8 + 0, 0): (1, 1, "left"),
    (2 * 8 + 0, 0): (1, 1, "bottom"),
    (3 * 8 + 0, 0): (1, 1, "top"),

    # P1 UpRight
    (0 * 8 + 0, 1): (1, 3, "right"),
    (1 * 8 + 0, 1): (1, 3, "left"),
    (2 * 8 + 0, 1): (1, 3, "bottom"),
    (3 * 8 + 0, 1): (1, 3, "top"),

    # P1 Center
    (0 * 8 + 0, 2): (1, 5, "right"),
    (1 * 8 + 0, 2): (1, 5, "left"),
    (2 * 8 + 0, 2): (1, 5, "bottom"),
    (3 * 8 + 0, 2): (1, 5, "top"),

    # P1 DownLeft
    (0 * 8 + 0, 3): (1, 7, "right"),
    (1 * 8 + 0, 3): (1, 7, "left"),
    (2 * 8 + 0, 3): (1, 7, "bottom"),
    (3 * 8 + 0, 3): (1, 7, "top"),

    # P1 DownLeft
    (0 * 8 + 0, 4): (1, 9, "right"),
    (1 * 8 + 0, 4): (1, 9, "left"),
    (2 * 8 + 0, 4): (1, 9, "bottom"),
    (3 * 8 + 0, 4): (1, 9, "top"),

    # P2 UpLeft
    (0 * 8 + 2, 0): (2, 1, "right"),
    (1 * 8 + 2, 0): (2, 1, "left"),
    (2 * 8 + 2, 0): (2, 1, "bottom"),
    (3 * 8 + 2, 0): (2, 1, "top"),

    # P2 UpRight
    (0 * 8 + 2, 1): (2, 3, "right"),
    (1 * 8 + 2, 1): (2, 3, "left"),
    (2 * 8 + 2, 1): (2, 3, "bottom"),
    (3 * 8 + 2, 1): (2, 3, "top"),

    # P2 Center
    (0 * 8 + 2, 2): (2, 5, "right"),
    (1 * 8 + 2, 2): (2, 5, "left"),
    (2 * 8 + 2, 2): (2, 5, "bottom"),
    (3 * 8 + 2, 2): (2, 5, "top"),

    # P2 DownLeft
    (0 * 8 + 2, 3): (2, 7, "right"),
    (1 * 8 + 2, 3): (2, 7, "left"),
    (2 * 8 + 2, 3): (2, 7, "bottom"),
    (3 * 8 + 2, 3): (2, 7, "top"),

    # P2 DownLeft
    (0 * 8 + 2, 4): (2, 9, "right"),
    (1 * 8 + 2, 4): (2, 9, "left"),
    (2 * 8 + 2, 4): (2, 9, "bottom"),
    (3 * 8 + 2, 4): (2, 9, "top"),
}


NUM_PADS = 2
NUM_PANELS = 9

SENSOR_NAMES = (
    "top",
    "left",
    "right",
    "bottom",
)

class DancePad:
    PANEL_SIZE = 130

    def __init__(self, parent, pad_number):
        self.pad_number = pad_number

        # sensor_state[panel][sensor_name]
        self.sensor_state = [
            {
                sensor: False
                for sensor in SENSOR_NAMES
            }
            for _ in range(NUM_PANELS)
        ]

        # sensor_widgets[panel][sensor_name] = Tk widget
        self.sensor_widgets = [
            {}
            for _ in range(NUM_PANELS)
        ]

        # Text displaying the mapping for each sensor.
        self.mapping_labels = [
            {}
            for _ in range(NUM_PANELS)
        ]

        self.build(parent)

    def build(self, parent):
        outer = tk.Frame(
            parent,
            bd=2,
            relief=tk.RIDGE,
            padx=12,
            pady=12,
        )

        outer.pack(
            side=tk.LEFT,
            padx=15,
            pady=15,
        )

        tk.Label(
            outer,
            text=f"PAD {self.pad_number}",
            font=("Arial", 18, "bold"),
        ).pack(pady=(0, 10))

        pad_frame = tk.Frame(outer)
        pad_frame.pack()

        for panel_index in range(NUM_PANELS):
            row = panel_index // 3
            col = panel_index % 3

            panel = tk.Frame(
                pad_frame,
                width=self.PANEL_SIZE,
                height=self.PANEL_SIZE,
                bd=2,
                relief=tk.RIDGE,
            )

            panel.grid(
                row=row,
                column=col,
                padx=3,
                pady=3,
            )

            panel.grid_propagate(False)

            # Panel number
            tk.Label(
                panel,
                text=f"{panel_index + 1}",
                font=("Arial", 8),
            ).place(
                x=5,
                y=5,
            )

            self.create_sensors(
                panel_index,
                panel,
            )

    def create_sensors(self, panel_index, parent):
        """
        Sensor positions:

                    TOP
             ┌─────────────┐
             │             │
             │             │
        LEFT │    PANEL    │ RIGHT
             │             │
             │             │
             └─────────────┘
                   BOTTOM
        """

        positions = {
            "top": (42, 8, 46, 14),
            "left": (8, 42, 14, 46),
            "right": (108, 42, 14, 46),
            "bottom": (42, 108, 46, 14),
        }

        for sensor, (
            x,
            y,
            width,
            height,
        ) in positions.items():

            # Don't render sensors that aren't mapped.
            if not self.is_sensor_mapped(panel_index, sensor):
                continue

            # Container so we can put the mapping text next to
            # the sensor without changing the sensor itself.
            container = tk.Frame(
                parent,
                width=width,
                height=height,
            )

            container.place(
                x=x,
                y=y,
            )

            sensor_widget = tk.Frame(
                container,
                width=width,
                height=height,
                bg="gray",
                bd=1,
                relief=tk.SOLID,
            )

            sensor_widget.pack(
                fill=tk.BOTH,
                expand=True,
            )

            self.sensor_widgets[
                panel_index
            ][sensor] = sensor_widget

            # Make sensors clickable for manual testing.
            sensor_widget.bind(
                "<Button-1>",
                lambda event,
                p=panel_index,
                s=sensor: self.toggle_sensor(p, s),
            )

    def set_sensor(self, panel, sensor, state):
        state = bool(state)

        self.sensor_state[panel][sensor] = state

        widget = self.sensor_widgets[panel][sensor]

        widget.configure(
            bg="lime" if state else "gray"
        )

    def get_sensor(self, panel, sensor):
        return self.sensor_state[panel][sensor]

    def toggle_sensor(self, panel, sensor):
        self.set_sensor(
            panel,
            sensor,
            not self.get_sensor(panel, sensor),
        )

    def is_sensor_mapped(self, panel, sensor):
        return any(
            mapped_pad == self.pad_number
            and mapped_panel == panel + 1
            and mapped_sensor == sensor
            for mapped_pad, mapped_panel, mapped_sensor
            in SENSOR_MAP.values()
        )


class Application:
    def __init__(self, root):
        self.root = root

        root.title("PIUIO Full Sensor State")

        # --------------------------------------------------------------------
        # Open device
        # --------------------------------------------------------------------

        # open up the gamepad endpoint to force the driver to poll
        for path in glob.glob("/dev/input/js*"):
            try:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                print("opened", path)
                break
            except PermissionError:
                pass

        # open the debug endpoint
        self.fd = os.open(
            DEVICE,
            os.O_RDONLY,
        )

        self.mm = mmap.mmap(
            self.fd,
            mmap.PAGESIZE,
            flags=mmap.MAP_SHARED,
            prot=mmap.PROT_READ,
        )

        # --------------------------------------------------------------------
        # Build GUI
        # --------------------------------------------------------------------

        self.pads = [
            DancePad(
                root,
                pad_number=1,
            ),
            DancePad(
                root,
                pad_number=2,
            ),
        ]

        # Raw byte display
        self.raw_label = tk.Label(
            root,
            text="",
            font=("Courier", 10),
            justify=tk.LEFT,
        )

        self.raw_label.pack(
            pady=(0, 10),
        )

        # Start polling
        self.update()

        root.protocol(
            "WM_DELETE_WINDOW",
            self.close,
        )

    def update(self):
        """
        Read the mmap and update every mapped sensor.
        """

        inputs = self.mm[:NUM_BYTES]

        # Process every configured sensor mapping.
        for (
            byte_index,
            bit_position,
        ), (
            pad,
            panel,
            sensor,
        ) in SENSOR_MAP.items():

            # Ignore mappings outside the available data.
            if byte_index >= len(inputs):
                continue

            byte_value = inputs[byte_index]

            pressed = not bool(
                byte_value &
                (1 << bit_position)
            )

            self.pads[pad - 1].set_sensor(
                panel - 1,
                sensor,
                pressed,
            )

        # Show raw data underneath the pads.
        self.update_raw_display(inputs)

        # Poll every 10 ms.
        self.root.after(
            10,
            self.update,
        )

    def update_raw_display(self, inputs):
        lines = []

        for i in range(0, len(inputs), 8):
            chunk = inputs[i:i + 8]

            line = (
                f"{i:02d}: "
                + " ".join(
                    f"{value:02x}"
                    for value in chunk
                )
            )

            lines.append(line)

        self.raw_label.configure(
            text="\n".join(lines),
        )

    def close(self):
        self.mm.close()
        os.close(self.fd)
        self.root.destroy()


def main():
    root = tk.Tk()

    Application(root)

    root.mainloop()


if __name__ == "__main__":
    main()