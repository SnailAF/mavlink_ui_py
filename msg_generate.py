"""
    V1.0
    2024.05.24 
    ZGQ
    实现根据mavlink的xml文件自动生成对应的UI界面
    说明：
    本脚本会根据xml文件自动生成4个新的py脚本,分别为:
    1. main.py 主界面，运行此文件即可
    2. serial_init.py    串口初始化部分，
    3. serial_send.py    串口发送部分，
    4. serial_receive.py 串口接收部分，

    使用方法：
    1. 将xml文件放在msg_generate.py相同的文件夹下
    2. 运行msg_generate.py
    3. 生成的UI界面会自动保存在新建的文件夹下
    4. 运行main.py。
    
    注意：
    1. 串口号需要手动输入，没有全局检测，因为检测时发现不了虚拟串口，就没有增加。
    2. 需要手动使用mavlink生成工具生成对应的mavlink py文件
    3. 需要手动将接收和发送代码中的 from detect import * 改为自己的生成的py文件名
"""
import xml.etree.ElementTree as ET
import os
import shutil

# 更改工作目录到脚本所在的目录
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

def generate_send_code(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    ui_code = ""
    # Add import statements and class definition
    ui_code += "import tkinter as tk\n"
    ui_code += "from pymavlink import mavutil\n"
    ui_code += "from detect import *\n\n"
    ui_code += "class SerialSendFrame(tk.Frame):\n"
    ui_code += "    def __init__(self, master):\n"
    ui_code += "        super().__init__(master)\n\n"
    ui_code += "        self.master = master\n\n"
    ui_code += "        self.create_widgets()\n"
    ui_code += "    def create_widgets(self):\n"
    ui_code += "        tk.Label(self, text='System ID:').grid(row=0, column=0)\n"
    ui_code += "        self.target_system_entry = tk.Entry(self)\n"
    ui_code += "        self.target_system_entry.grid(row=0, column=1)\n"
    ui_code += "        tk.Label(self, text='Component ID:').grid(row=0, column=2)\n"
    ui_code += "        self.target_component_entry = tk.Entry(self)\n"
    ui_code += "        self.target_component_entry.grid(row=0, column=3)\n"
    row = 1
    for message in root.findall("messages/message"):
        message_name = message.get("name")

        # Add labels and entry widgets for each field
        ui_code += f"\n\n\t\t# UI for {message_name}\n"

        column = 1
        for field in message.findall("field"):
            field_name = field.get("name")
            if field.get("name") != "target_system" and  field.get("name") != "target_component":
                ui_code += f"        tk.Label(self, text='{field_name}:').grid(row={row}, column={column})\n"
                ui_code += f"        self.{field_name}_entry = tk.Entry(self)\n"
                ui_code += f"        self.{field_name}_entry.grid(row={row}, column={column+1})\n"
                column += 2
        # Add send button for the message
        ui_code += f"        tk.Button(self, text='Send {message_name}', command=self.send_{message_name.lower()}).grid(row={row}, column=0)\n"
        row += 1

    for message in root.findall("messages/message"):
        message_name = message.get("name")

        # Add send function for each message
        ui_code += f"\n\n    def send_{message_name.lower()}(self):\n"
        ui_code += "         if self.master.serial_init_frame.serial_connection:\n"
        ui_code += f"            try:\n"

        for field in message.findall("field"):
            field_name = field.get("name")
            if field.get("type") != "float" :
                field_type = "int"
            else:
                field_type = "float"
            ui_code += f"                {field_name} = {field_type}(self.{field_name}_entry.get())\n"

        # Construct MAVLink message
        ui_code += f"                msg = MAVLink_{message_name.lower()}_message(\n"
        for field in message.findall("field"):
            field_name = field.get("name")
            ui_code += f"                    {field_name},\n"
        ui_code += "                )\n"

        # Send the message
        ui_code += "                self.master.serial_init_frame.mav.send(msg)\n"

        ui_code += "            except ValueError as e:\n"
        ui_code += "                print(f'Error: {{e}}. Please enter valid values for all fields.')\n"

    return ui_code


def generate_recevie_code(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    ui_code = ""
    # Add import statements and class definition
    ui_code += """
import tkinter as tk
import threading
import time
from detect import *
    """    
    ui_code += """
def msg_to_hex(msg):
    return ' '.join(f'{byte:02x}' for byte in msg.get_msgbuf())

class SerialReceiveFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.text = tk.Text(self)
        self.text.pack(fill=tk.BOTH, expand=True)
        self.text.insert("1.0", f"\\n\\n\\n\\n\\n\\n\\n\\n\\n\\n")
        #self.text.config(state=tk.DISABLED)

        self.running = False
        self.master = master

        self.start_receiving()

    def start_receiving(self):
        self.running = True
        threading.Thread(target=self.receive_data, daemon=True).start()

    def stop_receiving(self):
        self.running = False

    def update_display(self):
        # Clear text widget
        self.text.delete(1.0, tk.END)
    # Function to convert message to hex
    def receive_data(self):
        while self.running:
            if self.master.serial_init_frame.serial_connection :
                while True:
                    while self.master.serial_init_frame.serial_connection.inWaiting() > 0:
                        char = self.master.serial_init_frame.serial_connection.read()  # Read a byte
                        if char:
                            msg = self.master.serial_init_frame.mav.parse_char(char)
                            if msg is not None:
                                print(msg)
        """
    ui_code += "\n"
    row = 1
    for message in root.findall("messages/message"):
        message_name = message.get("name")
        ui_code += f"                                if msg.get_type() == '{message_name.upper()}':\n"
        ui_code += f"                                   self.text.delete(\"{row}.0\", \"{row}.end\")\n"
        ui_code += f"                                   self.text.insert(\"{row}.0\", f\"{{msg}}\")\n"
        row += 1
    ui_code += """
                            time.sleep(0.01)
    """
    return ui_code

def generate_main():
    code = """
import tkinter as tk
from serial_init import SerialInitFrame
from serial_receive import SerialReceiveFrame
from serial_send import SerialSendFrame

class SerialApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Serial Communication App")

        # Initialize frames
        self.serial_init_frame = SerialInitFrame(self)
        self.serial_send_frame = SerialSendFrame(self)       
        self.serial_receive_frame = SerialReceiveFrame(self)

        # Layout the frames
        self.serial_init_frame.pack(side=tk.TOP, fill=tk.X)
        self.serial_send_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.serial_receive_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    app = SerialApp()
    app.mainloop()
"""
    return code

def generate_serial_init():
    code = """
import tkinter as tk
import serial
from detect import *
class SerialInitFrame(tk.Frame):
    def __init__(self, master):
        super().__init__(master)

        self.serial_connection = None

        self.mav = None

        self.port_label = tk.Label(self, text="Port:")
        self.port_label.pack(side=tk.LEFT)

        self.port_entry = tk.Entry(self)
        self.port_entry.insert(tk.END, "COM11")  # 设置默认端口为 COM11
        self.port_entry.pack(side=tk.LEFT)

        self.baud_label = tk.Label(self, text="Baud:")
        self.baud_label.pack(side=tk.LEFT)

        self.baud_entry = tk.Entry(self)
        self.baud_entry.insert(tk.END, "115200")  # 设置默认波特率为 115200
        self.baud_entry.pack(side=tk.LEFT)

        self.connect_button = tk.Button(self, text="Connect", command=self.connect_serial)
        self.connect_button.pack(side=tk.LEFT)

    def connect_serial(self):
        port = self.port_entry.get()
        baud = int(self.baud_entry.get())
        try:
            self.serial_connection = serial.Serial(
                port,
                baud,
                timeout=1
            )
            self.mav = MAVLink(self.serial_connection)
            print(f"Opened {self.port.get()} at {self.baudrate.get()} baud")
        except Exception as e:
            print(f"Failed to open serial port: {e}")


    """
    return code

if __name__ == "__main__":
    code = ""
    xml_file = "detect_mavlink.xml"  # 修改为你的 XML 文件路径
    # 创建新文件夹
    folder_path = os.path.splitext(os.path.basename(xml_file))[0]
    os.makedirs(folder_path, exist_ok=True)
    shutil.copy(xml_file, folder_path)
    
    # 生成发送代码
    file_path = os.path.join(folder_path, "serial_send.py")
    code = generate_send_code(xml_file)
    with open(file_path, 'w') as file:
        file.write(code)

    # 生成接收代码
    file_path = os.path.join(folder_path, "serial_receive.py")
    code = generate_recevie_code(xml_file)
    with open(file_path, 'w') as file:
        file.write(code)
        
    # 生成主代码
    file_path = os.path.join(folder_path, "main.py")
    code = generate_main()
    with open(file_path, 'w') as file:
        file.write(code)
        
    # 生成初始化代码
    file_path = os.path.join(folder_path, "serial_init.py")
    code = generate_serial_init()
    with open(file_path, 'w') as file:
        file.write(code)

