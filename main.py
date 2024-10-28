import socket
import threading
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.clock import mainthread
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.label import MDLabel
from kivy.uix.image import Image

# Function to get response from ESP8266 for the given path
def get_response_from_esp8266(ip, path):
    # Create a socket object
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Set timeout for the socket (5 seconds in this case)
    client_socket.settimeout(1)

    try:
        # Connect to the ESP8266 server
        print(f"Connecting to {ip} on port 80...")
        client_socket.connect((ip, 80))
        print("Connected successfully!")

        # Construct the HTTP GET request manually
        request = f"GET /{path} HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n"
        print(f"Sending request:\n{request}")

        # Send the HTTP GET request to the ESP8266
        client_socket.sendall(request.encode('utf-8'))

        # Receive the response with timeout
        response = b""
        while True:
            try:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                response += chunk
            except socket.timeout:
                print("Socket timeout, no response from ESP8266")
                break

        if response:
            # Decode and print the full HTTP response
            response_str = response.decode()
            print("Full Response from ESP8266:")
            print(response_str)

            # Extract the body of the response (after headers)
            body_start = response_str.find("\r\n\r\n") + 4
            body = response_str[body_start:]
            print("Body of Response:", body)
        else:
            print("No response received from ESP8266")

    except socket.timeout:
        print("Connection timed out.")
    
    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close the socket connection
        client_socket.close()
        print("Socket closed.")
    return body

# Retry mechanism for sending requests
def try_get_response(ip, path, retries=3):
    for attempt in range(retries):
        response = get_response_from_esp8266(ip, path)
        if response:
            return response
        print(f"Attempt {attempt+1} failed. Retrying...")
    return "N/A"

# Function to send request to ESP8266 with parameters
def send_request_to_esp8266(ip, message):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(1)  # Increased timeout to 10 seconds

    try:
        client_socket.connect((ip, 80))
        request = f"GET /get?{message} HTTP/1.1\r\nHost: {ip}\r\nConnection: close\r\n\r\n"
        client_socket.sendall(request.encode('utf-8'))

        response = b""
        while True:
            chunk = client_socket.recv(4096)
            if not chunk:
                break
            response += chunk

        if response:
            print("Response from ESP8266:", response.decode())
        else:
            print("No response received from ESP8266")

    except socket.timeout:
        print("Connection timed out.")
    
    except Exception as e:
        print(f"Error: {e}")

    finally:
        client_socket.close()

KV = '''
MDScreen:
    MDBoxLayout:
        orientation: 'vertical'
        padding: 20
        spacing: 10
        
        # Display the water tank image
        Image:
            source: 'water_tank.png'
            size_hint: None, None
            size: 200, 200
            pos_hint: {'center_x': 0.5}
        
        # Horizontal layout for h1 input and submit button
        MDBoxLayout:
            orientation: 'horizontal'
            spacing: 10
            MDTextField:
                id: h1_input
                hint_text: "Enter h1 in cm (exp: 40)"
                mode: "rectangle"
                size_hint_x: 0.7  # Adjust the width of the text field
            MDRaisedButton:
                text: "Submit h1"
                on_press: app.submit_h1()
                md_bg_color: 0.01, 0.81, 0.9, 0.9

        # Horizontal layout for h2 input and submit button
        MDBoxLayout:
            orientation: 'horizontal'
            spacing: 10
            MDTextField:
                id: h2_input
                hint_text: "Enter h2 in cm (exp: 180)"
                mode: "rectangle"
                size_hint_x: 0.7  # Adjust the width of the text field
            MDRaisedButton:
                text: "Submit h2"
                on_press: app.submit_h2()
                md_bg_color: 0.01, 0.81, 0.9, 0.9 

        # Displaying measured distance, battery voltage, and last reception time
        MDLabel:
            id: measured_distance
            text: "Measured Distance: cm"
            halign: "center"
            theme_text_color: "Primary"

        MDLabel:
            id: battery_voltage
            text: "Battery Voltage: V"
            halign: "center"
            theme_text_color: "Primary"

        MDLabel:
            id: last_reception
            text: "Time spent for last reception: min"
            halign: "center"
            theme_text_color: "Primary"
'''

# Main App Class
class CLevelApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.ip = "192.168.4.1"  # ESP8266 IP Address

        # Schedule parameter update every 5 seconds
        Clock.schedule_interval(self.start_update_thread, 3)

        return Builder.load_string(KV)

    def submit_h1(self):
        h1_value = self.root.ids.h1_input.text
        print(f"H1 Submitted: {h1_value}")

        # Run network operation in a separate thread
        threading.Thread(target=self.send_h1_in_background, args=(h1_value,)).start()

    def submit_h2(self):
        h2_value = self.root.ids.h2_input.text
        print(f"H2 Submitted: {h2_value}")

        # Run network operation in a separate thread
        threading.Thread(target=self.send_h2_in_background, args=(h2_value,)).start()

    def send_h1_in_background(self, h1_value):
        # Send request to ESP8266 with the h1 value
        send_request_to_esp8266("192.168.4.1", f"input_h1={h1_value}")

    def send_h2_in_background(self, h2_value):
        # Send request to ESP8266 with the h2 value
        send_request_to_esp8266("192.168.4.1", f"input_h2={h2_value}")

    def start_update_thread(self, dt):
        # Start a new thread to fetch and update parameters
        update_thread = threading.Thread(target=self.update_parameters)
        update_thread.daemon = True  # Ensure the thread exits when the app closes
        update_thread.start()

    def update_parameters(self):
        # Retry fetching parameters if needed
        measured_distance = try_get_response(self.ip, "distance")
        battery_voltage = try_get_response(self.ip, "volt")
        last_reception = try_get_response(self.ip, "time")

        # Update the display in the main thread
        self.update_display(measured_distance, battery_voltage, last_reception)

    @mainthread
    def update_display(self, measured_distance, battery_voltage, last_reception):
        self.root.ids.measured_distance.text = f"Measured Distance: {measured_distance} cm"
        self.root.ids.battery_voltage.text = f"Battery Voltage: {battery_voltage} V"
        self.root.ids.last_reception.text = f"Time spent for last reception: {last_reception} min"

if __name__ == "__main__":
    CLevelApp().run()
