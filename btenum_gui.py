import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
from bleak import BleakClient, BleakScanner
import asyncio
import random
import bleak
import json
import time
import threading


class BluetoothEnumeratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Bluetooth Device Enumerator")
        self.root.geometry("900x600")
        
        self.enumeration_data = {}
        self.is_running = False
        self.enum_thread = None
        
        # Create UI elements
        self.create_widgets()
        
    def create_widgets(self):
        # Button frame at the top
        button_frame = ttk.Frame(self.root, padding="10")
        button_frame.pack(side=tk.TOP, fill=tk.X)
        
        # Buttons
        self.start_btn = ttk.Button(button_frame, text="Start Enumeration", command=self.start_enumeration)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(button_frame, text="Stop Enumeration", command=self.stop_enumeration, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.save_btn = ttk.Button(button_frame, text="Save Results (JSON)", command=self.save_results)
        self.save_btn.pack(side=tk.LEFT, padx=5)
        
        self.export_btn = ttk.Button(button_frame, text="Export to TXT", command=self.export_to_txt)
        self.export_btn.pack(side=tk.LEFT, padx=5)
        
        # Console/output area
        console_frame = ttk.Frame(self.root, padding="10")
        console_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        ttk.Label(console_frame, text="Enumeration Console:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
        
        self.console = scrolledtext.ScrolledText(console_frame, wrap=tk.WORD, height=20, font=('Courier', 9))
        self.console.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
    def log(self, message):
        """Add message to console"""
        self.console.insert(tk.END, message + "\n")
        self.console.see(tk.END)
        self.root.update_idletasks()
        
    def start_enumeration(self):
        """Start the enumeration process"""
        if self.is_running:
            return
            
        self.is_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.console.delete(1.0, tk.END)
        self.enumeration_data = {}
        
        self.log("Starting Bluetooth enumeration...")
        self.log("=" * 80)
        
        # Run enumeration in a separate thread
        self.enum_thread = threading.Thread(target=self.run_enumeration_thread, daemon=True)
        self.enum_thread.start()
        
    def run_enumeration_thread(self):
        """Run the enumeration in a separate thread"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self.enumeration_data = loop.run_until_complete(self.run_enumeration())
            loop.close()
            
            self.log("=" * 80)
            self.log(f"Enumeration complete! Found {len(self.enumeration_data)} devices.")
        except Exception as e:
            self.log(f"Error during enumeration: {str(e)}")
        finally:
            self.is_running = False
            self.root.after(0, self.enumeration_finished)
            
    def enumeration_finished(self):
        """Called when enumeration is complete"""
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
    def stop_enumeration(self):
        """Stop the enumeration process"""
        self.is_running = False
        self.log("Stopping enumeration...")
        self.stop_btn.config(state=tk.DISABLED)
        
    async def read_gatt_char(self, client, address, char_uuid):
        """Read a GATT characteristic"""
        if not self.is_running:
            return ''
            
        value = ''
        try:
            value = await client.read_gatt_char(char_uuid)
        except:
            pass
        return value
        
    async def run_enumeration(self):
        """Main enumeration logic"""
        devices = await BleakScanner.discover()
        enumeration = {}
        random.shuffle(devices)
        
        for d in devices:
            if not self.is_running:
                break
                
            self.log(f"Found device: {d.address} | Name: {d.name} | RSSI: {d.rssi} dBm")
            device_data = await self.enumerate_device(d.address)
            
            enumeration[d.address] = {
                'name': str(d.name),
                'details': device_data,
                'rssi': d.rssi
            }
            
        return enumeration
        
    async def enumerate_device(self, address):
        """Enumerate a specific device"""
        if not self.is_running:
            return {}
            
        device_data = {}
        try:
            async with BleakClient(address, timeout=10.0) as client:
                self.log(f"  Connecting to {address}...")
                
                connected = client.is_connected
                device_data['connected'] = str(connected)
                
                if connected:
                    self.log(f"  Connected! Enumerating services...")
                    services = await client.get_services()
                    device_data['services'] = []
                    
                    for service in services:
                        if not self.is_running:
                            break
                            
                        service_data = {'uuid': str(service.uuid), 'characteristics': []}
                        
                        for characteristic in service.characteristics:
                            if not self.is_running:
                                break
                                
                            attribute = await self.read_gatt_char(client, address, characteristic.uuid)
                            
                            if type(attribute) == bytearray:
                                try:
                                    data = attribute.decode('utf-8')
                                except:
                                    data = attribute
                            elif type(attribute) == str:
                                data = attribute
                            else:
                                data = attribute
                                
                            if len(str(data)) > 0:
                                service_data['characteristics'].append(str(data))
                                
                        device_data['services'].append(service_data)
                    
                    self.log(f"  Disconnecting from {address}")
                    
        except asyncio.exceptions.TimeoutError:
            self.log(f"  Timeout connecting to {address}")
        except bleak.exc.BleakDeviceNotFoundError:
            self.log(f"  Failed to connect to {address} (device not found)")
        except bleak.exc.BleakError as e:
            self.log(f"  Failed to connect to {address} (error: {str(e)})")
        except Exception as e:
            self.log(f"  Unexpected error with {address}: {str(e)}")
            
        return device_data
        
    def save_results(self):
        """Save results to JSON file"""
        if not self.enumeration_data:
            messagebox.showwarning("No Data", "No enumeration data to save!")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"bluetooth_enumeration_{round(time.time())}.json"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    json.dump(self.enumeration_data, f, indent=2)
                self.log(f"Results saved to {filename}")
                messagebox.showinfo("Success", f"Results saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                
    def export_to_txt(self):
        """Export results to TXT file"""
        if not self.enumeration_data:
            messagebox.showwarning("No Data", "No enumeration data to export!")
            return
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"bluetooth_enumeration_{round(time.time())}.txt"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write("Bluetooth Device Enumeration Results\n")
                    f.write("=" * 80 + "\n\n")
                    
                    for address, data in self.enumeration_data.items():
                        f.write(f"Device: {address}\n")
                        f.write(f"  Name: {data.get('name', 'Unknown')}\n")
                        f.write(f"  RSSI: {data.get('rssi', 'N/A')} dBm\n")
                        f.write(f"  Connected: {data.get('details', {}).get('connected', 'False')}\n")
                        
                        services = data.get('details', {}).get('services', [])
                        if services:
                            f.write(f"  Services: {len(services)}\n")
                            for service in services:
                                f.write(f"    UUID: {service.get('uuid', 'Unknown')}\n")
                                chars = service.get('characteristics', [])
                                if chars:
                                    f.write(f"      Characteristics: {len(chars)}\n")
                        f.write("\n" + "-" * 80 + "\n\n")
                        
                self.log(f"Results exported to {filename}")
                messagebox.showinfo("Success", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export file: {str(e)}")


def main():
    root = tk.Tk()
    app = BluetoothEnumeratorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
