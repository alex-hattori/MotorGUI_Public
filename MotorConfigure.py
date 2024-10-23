import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports

setup_items = {
    "g": 0, "k": 1, "b": 2, "l": 3, "p": 4, "v": 5, "x": 6, "d": 7, 
    "a": 8, "o": 9, "q": 10, "i": 11, "m": 12, "t": 13
}

STATE_MENU = 0
STATE_ZERO = 1
STATE_LOAD = 2
STATE_WRITE = 3
STATE_CALIBRATE = 4
STATE_UNDEFINED = 5

# Preset values (13 elements per preset, filled with random float numbers)
PRESET_FRONT_LEFT_PIVOT =  [6.0,0.023,200,4,500,200,500,5,1,10,7,6,0,1000]
PRESET_FRONT_LEFT_WHEEL =  [6.4,0.023,200,4,500,200,500,5,1,10,7,5,0,1000]
PRESET_FRONT_RIGHT_PIVOT = [6.0,0.023,200,4,500,200,500,5,1,10,7,4,0,1000]
PRESET_FRONT_RIGHT_WHEEL = [6.4,0.023,200,4,500,200,500,5,1,10,7,3,0,1000]
PRESET_BACK_LEFT_PIVOT =   [6.0,0.023,200,4,500,200,500,5,1,10,7,8,0,1000]
PRESET_BACK_LEFT_WHEEL =   [6.4,0.023,200,4,500,200,500,5,1,10,7,7,0,1000]
PRESET_BACK_RIGHT_PIVOT =  [6.0,0.023,200,4,500,200,500,5,1,10,7,2,0,1000]
PRESET_BACK_RIGHT_WHEEL =  [6.4,0.023,200,4,500,200,500,5,1,10,7,1,0,1000]
PRESET_RC_PWM =            [1.0,0.023,200,4,3.14,0.0,1.0,0.01,1,10,7,1,0,-1] ## Kp = 1.0, Kd = 0.01. Commanded between -pi and pi radians for 1ms-2ms RCPWM
PRESET_RC_PWM_VEL =        [1.0,0.023,200,4,0.0,20.0,0.0,0.01,1,10,7,1,0,-1] ## Kp = 0.0, Kd = 0.01. Commanded between -20 and 20 rad/s for 1ms-2ms RCPWM

class SerialPortGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Motor Configurator")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)  # Handle window close

        # Dropdown for serial ports
        self.port_var = tk.StringVar()
        self.port_menu = ttk.Combobox(self.root, textvariable=self.port_var, state="readonly")
        self.port_menu.grid(row=0, column=0, sticky='w')

        # Connect Button
        self.connect_button = tk.Button(self.root, text="Connect", command=self.connect_to_serial)
        self.connect_button.grid(row=0, column=1, sticky='w')

        # MENU_STATE Indicator
        self.menu_state_indicator = tk.Label(self.root, text="NOT READY", fg="red")
        self.menu_state_indicator.grid(row=0, column=2, sticky='w')

        self.load_button = tk.Button(self.root, text="Load Settings", command=self.load_settings)
        self.load_button.grid(row=1, column=0, sticky='w')

        self.write_button = tk.Button(self.root, text="Write Settings", command=self.write_settings)
        self.write_button.grid(row=1, column=1, sticky='w')

        self.zero_button = tk.Button(self.root, text="Zero", command=self.zero_device)
        self.zero_button.grid(row=1, column=2, sticky='w')

        self.calibrate_button = tk.Button(self.root, text="Calibrate", command=self.calibrate_device)
        self.calibrate_button.grid(row=1, column=3, sticky='w')

        # Status labels
        self.status_label = tk.Label(self.root, text="Status: Not Connected")
        self.status_label.grid(row=0, column=3, sticky='w')

        self.calibration_label = tk.Label(self.root, text="Calibration: N/A")
        self.calibration_label.grid(row=2, column=3, sticky='w')

        # Zero position label
        self.zero_position_label = tk.Label(self.root, text="Zero Position: N/A")
        self.zero_position_label.grid(row=2, column=2, sticky='w')

        # Firmware label
        self.firmware_label = tk.Label(self.root, text="Firmware Version: N/A")
        self.firmware_label.grid(row=2, column=0, sticky='w')

        # Setup values display
        setup_labels_text = [
            "Gear Ratio:",
            "Kt (N*m/A):",
            "Current Bandwidth (100-2000) (Hz):",
            "Current Limit (0.0-8.0) (A):",
            "Position Limit (rad):",
            "Velocity Limit (rad/s):",
            "Kp Limit (0.0 - 1000.0) (N*m/rad):",
            "Kd Limit (0.0 - 5.0) (N*m/rad/s):",
            "Calibration Current (0.0-4.0) (A):",
            "Torque Communication Limit (N*m):",
            "Pole Pairs:",
            "CAN ID (0-127):",
            "CAN Master ID (0-127):",
            "CAN Timeout (0-100000) (cycles):"
        ]

        self.setup_labels = []
        self.input_boxes = []
        self.current_values = [0.0] * len(setup_labels_text)  # Initialize with zeros

        for i, text in enumerate(setup_labels_text):
            label = tk.Label(self.root, text=text + " N/A")
            label.grid(row=6 + i, column=0, sticky='w')  # Left justified
            self.setup_labels.append(label)

            input_box = tk.Entry(self.root)
            input_box.grid(row=6 + i, column=1)
            input_box.bind("<KeyRelease>", lambda event, index=i: self.check_input_background(index))  # Check background on key release
            self.input_boxes.append(input_box)

        preset_label = tk.Label(self.root, text="Presets")
        preset_label.grid(row=6, column=2, sticky='w')  # Left justified

        # Create the buttons
        btn_front_left_pivot = tk.Button(self.root, text="Front Left Pivot", command=lambda: self.populate_inputs(PRESET_FRONT_LEFT_PIVOT))
        btn_front_left_pivot.grid(row=7, column=2, sticky='w')

        btn_front_left_wheel = tk.Button(self.root, text="Front Left Wheel", command=lambda: self.populate_inputs(PRESET_FRONT_LEFT_WHEEL))
        btn_front_left_wheel.grid(row=7, column=3, sticky='w')

        btn_front_right_pivot = tk.Button(self.root, text="Front Right Pivot", command=lambda: self.populate_inputs(PRESET_FRONT_RIGHT_PIVOT))
        btn_front_right_pivot.grid(row=8, column=2, sticky='w')

        btn_front_right_wheel = tk.Button(self.root, text="Front Right Wheel", command=lambda: self.populate_inputs(PRESET_FRONT_RIGHT_WHEEL))
        btn_front_right_wheel.grid(row=8, column=3, sticky='w')

        btn_back_left_pivot = tk.Button(self.root, text="Back Left Pivot", command=lambda: self.populate_inputs(PRESET_BACK_LEFT_PIVOT))
        btn_back_left_pivot.grid(row=9, column=2, sticky='w')

        btn_back_left_wheel = tk.Button(self.root, text="Back Left Wheel", command=lambda: self.populate_inputs(PRESET_BACK_LEFT_WHEEL))
        btn_back_left_wheel.grid(row=9, column=3, sticky='w')

        btn_back_right_pivot = tk.Button(self.root, text="Back Right Pivot", command=lambda: self.populate_inputs(PRESET_BACK_RIGHT_PIVOT))
        btn_back_right_pivot.grid(row=10, column=2, sticky='w')

        btn_back_right_wheel = tk.Button(self.root, text="Back Right Wheel", command=lambda: self.populate_inputs(PRESET_BACK_RIGHT_WHEEL))
        btn_back_right_wheel.grid(row=10, column=3, sticky='w')

        btn_rc_pwm = tk.Button(self.root, text="RC PWM POS", command=lambda: self.populate_inputs(PRESET_RC_PWM))
        btn_rc_pwm.grid(row=11, column=2, sticky='w')

        btn_rc_pwm_vel = tk.Button(self.root, text="RC PWM VEL", command=lambda: self.populate_inputs(PRESET_RC_PWM_VEL))
        btn_rc_pwm_vel.grid(row=11, column=3, sticky='w')

        # Start automatic port detection
        self.ports = []
        self.serial_connection = None
        self.in_menu_state = False
        self.running = True
        self.refresh_ports()
        self.check_ports()
        self.messages = []
        self.state = STATE_UNDEFINED
        self.needReload = False

    def populate_inputs(self, preset_values):
        # Clear the current values in the input boxes
        for i, input_box in enumerate(self.input_boxes):
            # Populate each input box with the preset values
            input_box.delete(0, tk.END)  # Clear the existing value
            input_box.insert(0, str(preset_values[i]))  # Insert the new preset value
        self.check_all_inputs()

    def refresh_ports(self):
        self.ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_menu['values'] = self.ports

        if not self.ports:
            self.port_var.set('')  # Clear the current selection
        elif self.port_var.get() not in self.ports:
            self.port_menu.current(0)  # Select the first port in the list

    def check_ports(self):
        current_ports = [port.device for port in serial.tools.list_ports.comports()]
        if set(current_ports) != set(self.ports):
            self.refresh_ports()

        if self.running:
            if(self.serial_connection is None):
                self.root.after(1000, self.check_ports)  # Check every second

    def connect_to_serial(self):
        self.serial_connection = None
        selected_port = self.port_var.get()

        if selected_port:
            try:
                # Open the serial connection
                self.serial_connection = serial.Serial(selected_port, baudrate=921600, timeout=.001)
                self.status_label.config(text=f"Status: Connected to {selected_port}")
                self.in_menu_state = False  # Assume we're not in MENU_STATE initially
                self.state = STATE_UNDEFINED
                self.read_serial_output()
            except serial.SerialException as e:
                self.status_label.config(text=f"Status: Failed to connect: {e}")
        else:
            self.status_label.config(text="Status: No port selected")

    def update_menu_state_indicator(self):
        if self.state == STATE_MENU:
            self.menu_state_indicator.config(text="IS READY", fg="green")
        else:
            self.menu_state_indicator.config(text="NOT READY", fg="red")

    def read_serial_output(self):
        if(not self.serial_connection is None):
            if(self.state == STATE_UNDEFINED):
                self.write_char('e')
                self.write_char(chr(27))
                self.state = STATE_MENU
            else:
                try:
                    output = self.serial_connection.readline().decode('latin-1').strip()
                    if output:
                        # print(f"Received: {output}")  # Debugging output
                        if "MENU_STATE" in output:
                            self.state = STATE_MENU
                            if(self.needReload):
                                self.load_settings()
                                self.needReload = False
                        elif "Firmware Version Number: Release " in output:
                            firmware_text = output.split("Release ")[-1]
                            self.firmware_label.config(text="Firmware version: " + firmware_text, fg="green")
                        else:
                            if(self.state == STATE_ZERO):
                                self.parse_zero_pos(output)
                            elif(self.state == STATE_LOAD):
                                self.parse_setup_values(output)
                            elif(self.state == STATE_WRITE):
                                self.parse_writing_values(output)
                            elif(self.state == STATE_CALIBRATE):
                                self.parse_calibrate_values(output)
                                
                        # Update menu state indicator
                        self.update_menu_state_indicator()
                    
                except serial.SerialException:
                    pass
            self.root.after(1, self.read_serial_output)
                
            
    def parse_zero_pos(self, output):
        if "Saved new zero position:" in output:
            zero_position = output.split(":")[-1].strip()
            try:
                zero_position = float(zero_position)
                # print(f"Detected zero position: {zero_position}")  # Debugging output
                self.zero_position_label.config(text=f"Zero Position: {zero_position}")
            except ValueError:
                print(f"Failed to parse zero position: {output}")  # Debugging

    def parse_setup_values(self, output):
        if len(output) > 1 and output[0] in setup_items:
            parts = output.split()
            if len(parts) >= 4:
                try:
                    current_value = float(parts[-1])  # The last element is the current value
                    index = setup_items[output[0]]
                    self.current_values[index] = current_value  # Store the current value for comparison
                    self.setup_labels[index].config(text=f"{self.setup_labels[index]['text'].split(':')[0]}: {current_value}")
                    self.input_boxes[index].delete(0, tk.END)  # Clear previous input
                    self.input_boxes[index].insert(0, current_value)  # Set the loaded value
                    self.check_input_background(index)  # Check input background color
                    if(output[0] == max(setup_items, key=setup_items.get)): ## final row
                        self.write_char(chr(27))
                except ValueError:
                    pass
                    # print(f"Failed to parse setup value: {output}")
    def parse_writing_values(self, output):
        if(output[0] == max(setup_items, key=setup_items.get)):
            if(len(self.messages) > 0):
                self.write_message(self.messages[-1])
                # print(self.messages[-1])
                self.messages.remove(self.messages[-1])
            else:
                self.write_char(chr(27))
                self.needReload = True
    def parse_calibrate_values(self, output):
        if("Wrong pole pairs" in output):
            # print("Wrong pole pairs")
            self.calibration_label.config(text="Calibration Failed. Wrong pole pairs")
        elif("E_ZERO:" in output):
            # print("Success")
            self.calibration_label.config(text="Calibration Success")
        else:
            values = output.split(" ")
            if(len(values)==4):
                try:
                    electric_angle = float(values[1])/16384*2.0*3.1415
                    self.calibration_label.config(text="Calibration: "+str(round(electric_angle,2)))
                except Exception as e:
                    pass

    def check_input_background(self, index):
        try:
            user_value = float(self.input_boxes[index].get())
            if user_value != self.current_values[index]:
                self.input_boxes[index].config(bg='red')  # Change background to red
            else:
                self.input_boxes[index].config(bg='white')  # Reset background color
        except ValueError:
            self.input_boxes[index].config(bg='red')  # If invalid input, set red

    def check_all_inputs(self):
        for index, input_box in enumerate(self.input_boxes):
            self.check_input_background(index)

    def load_settings(self):
        if(self.state == STATE_MENU):
            if self.serial_connection:
                self.write_char('s')
                self.state = STATE_LOAD
                # print("Sent: Load settings command")  # Debugging output

    def write_char(self,char_cmd):
        self.serial_connection.write(char_cmd.encode('ascii'))

    def write_message(self,message):
        for char in message:
            self.write_char(char)
        self.write_char(chr(13))

    def write_settings(self):
        self.clear_serial()
        if(self.state == STATE_MENU):
            self.state = STATE_WRITE
            if self.serial_connection:
                self.write_char('s')
                self.messages = []
                for index, input_box in enumerate(self.input_boxes):
                    # Wait until the input box is not red (i.e., the value matches)
                    if input_box.cget('bg') == 'red':
                        try:
                            # Get the current value from the input box
                            value = float(input_box.get())
                            # Send the correct message to the device
                            char_label = [key for key, value in setup_items.items() if value == index]
                            message = char_label[0]+str(value)  # Create a message with index and value
                            self.messages.append(message)
                        except ValueError:
                            pass
                # print(self.messages)
                # print("Sent: Write settings command")  # Debugging output
    def clear_serial(self):
        # print("Clearing serial")
        if self.serial_connection:
            output = self.serial_connection.read(self.serial_connection.in_waiting)
            while output:
                output = self.serial_connection.read(self.serial_connection.in_waiting)
                # print("CLEAR" + output.decode('utf-8'))

    def zero_device(self):
        if self.serial_connection:
            self.write_char('z')
            self.state = STATE_ZERO
            # print("Sent: Zero command")  # Debugging output

    def calibrate_device(self):
        if(self.state == STATE_MENU):
            if self.serial_connection:
                self.state = STATE_CALIBRATE
                self.calibration_label.config(text="Calibration: Measure PP")
                self.write_char('c')
                # print("Sent: Calibrate command")  # Debugging output

    def on_closing(self):
        self.running = False
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()  # Ensure the serial connection is closed
            print("Serial connection closed.")  # Debugging output
        self.root.destroy()  # Close the GUI

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialPortGUI(root)
    root.mainloop()
