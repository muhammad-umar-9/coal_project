import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from cpu import CPU, Hex
import yaml
import threading
import time
import sys

class UI:
    def __init__(self, cpu: CPU):
        self.cpu = cpu

        # Main Window
        self.root = tk.Tk()
        self.root.title("Basic Computer Simulation")

        # Running text and request
        self.run_button_text = tk.StringVar(value="Run")
        self.stop_requested = False

        # self.root.geometry("800x600")
        self.registers_names = ["AR", "PC", "DR", "AC", "INPR", "IR", "TR", "TM", "PRC", "TAR", "TP", "NS", "OUTR", "SC", "PSR"]
        self.flip_flops_names = ["I", "E", "R", "C", "SW", "IEN", "FGI", "FGO", "S", "GS", "A0", "A1"]
        self.can_edit = {'AR', 'PC', 'PRC', 'INPR', 'NS', 'TAR', 'IEN', 'SW', 'FGI', 'FGO', 'S', 'GS'}
        self.prev_state = {}

        # self.prev_changed_values = self.registers_names + self.flip_flops_names
        self.prev_changed_values = [] 
        self.loading = False
        # self.cpu.set_ui(self)

        memory_frame = tk.Frame(self.root)
        memory_frame.pack(anchor=tk.W)
        # Main Memory Table
        self.create_main_memory_table(memory_frame)

        # Flip-Flops Panel
        self.create_flip_flops_panel(memory_frame)

        # Registers Panel
        self.create_registers_panel(memory_frame)

        smf = tk.Frame(memory_frame)
        smf.pack(side=tk.LEFT, anchor=tk.N)
        # Secondary Memory Table
        self.create_secondary_memory_table(smf)
        self.create_buttons(smf) 

        def on_closing(): self.root.destroy(); sys.exit()
        # Start the main loop
        self.ui_loop()
        self.update_ui()
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()


    def step_code(self, buttons = True):
        def update_buttons(): 
            self.load_button.config(state='disabled')
            self.run_button.config(state='disabled')
            self.step_button.config(state='disabled')
            while self.cpu.stepping and not self.load_button: pass
            if self.cpu.GS == 0: 
                if not self.loading: messagebox.showinfo(message="Execution stopped/not started. Global Start is 0")
                self.cpu.running = False
                self.cpu.stepping = False

            self.load_button.config(state='normal')
            self.run_button.config(state='normal')
            self.step_button.config(state='normal')



        if self.cpu.stepping == False: 
            try: 
                self.step_running = threading.Thread(target = self.cpu.run_next,daemon=True).start()
            except ValueError as v: 
                messagebox.showerror(message=v)
            if buttons: threading.Thread(target=update_buttons, daemon=True).start()

        # else: 
        #     with self.cpu.lock: 
        #         self.cpu.execute = True


    def run_code(self):
        def run(): 
            while self.cpu.running:
                if self.cpu.stepping == False: 
                    self.step_code(False)

    
                if self.cpu.GS == 0: 
                    if not self.loading: messagebox.showinfo(message="Execution stopped/not started. Global Start is 0")
                    self.load_button.config(state='normal')
                    self.step_button.config(state='normal')
                    self.run_button.config(text='Run')
                    self.cpu.running = False
                    break
                time.sleep(0.1)
        
    
        if self.cpu.running == False: 
            self.cpu.running = True
            self.load_button.config(state='disabled')
            self.step_button.config(state='disabled')
            self.run_button.config(text='Stop')
            threading.Thread(target=self.cpu.run_code, daemon=True).start()
        else: 
            self.load_button.config(state='normal')
            self.step_button.config(state='normal')
            self.run_button.config(text='Run')
            self.cpu.running = False
            if not self.cpu.GS: messagebox.showinfo(message="Execution stopped/not started. Global Start is 0")



    def load_program(self): 
        exp = tk.Tk()
        exp.withdraw()  
        file_path = filedialog.askopenfilename(title="Select a file", filetypes=(("Yaml Files", "*.yaml"),))

        if file_path is None or file_path == '': 
            messagebox.showerror(message='Cannot Load file')
            return 

        print(f"{file_path} is loaded")

        self.cpu.stepping = False
        self.cpu.running = False
        self.loading = True
        time.sleep(0.1)
        self.cpu.__init__(self.cpu.clk)

        self.cpu.changed_vars = []
        try: 
            file = open(file_path, 'r') 
            config = yaml.safe_load(file)
            if 'REG' in config: 
                for r, v in config['REG'].items(): 
                    if getattr(self.cpu, r, None) is None: raise ValueError(f"No such register as {r}")

                    if r == 'PSR': 
                        v = v.split('-')
                        if len(v) != 7: raise ValueError("Invalid PSR register format")
                        val = {'S': int(v[0])%2, 'A1': int(v[1])%2, 'A0': int(v[2])%2, 'E': int(v[3])%2, 
                            'AC': Hex(str(v[4],3)).val, 'PC0': Hex(str(v[5])).val, 'PC': Hex(str(v[6])).val}
                        setattr(self.cpu, r, val)
                        self.prev_state[r] = val
                    else: 
                        setattr(self.cpu, r, Hex(str(v),self.cpu.bits[r]).val)
                        self.prev_state[r] = Hex(str(v),self.cpu.bits[r]).val
                    self.cpu.changed_vars.append(r)

            if 'FF' in config: 
                for f, v in config['FF'].items(): 
                    if getattr(self.cpu, f, None) is None: raise ValueError(f"No such flip flop as {f}")
                    setattr(self.cpu, f, int(v) % 2)
                    self.cpu.changed_vars.append(f)

                
            if 'M' in config: 
                for l, v in config['M'].items(): 
                    l = int(str(l), 16)
                    if l > 255 or l < 0: raise ValueError(f"Address out of bounds")
                    if isinstance(v, list): 
                        for i, _v in enumerate(v): 
                            _v = str(_v)
                            if len(_v): 
                                if len(_v.split()) <= 3: self.cpu.main_memory[i+l] = _v.strip()
                                else: raise ValueError(f"Invalid instruction/operand at location {Hex(str(l)).val}: {_v.strip()}")
                    else: 
                        v = str(v)
                        if len(v): 
                            if len(v.split()) <= 3: self.cpu.main_memory[l] = v.strip()
                            else: raise ValueError(f"Invalid instruction/operand at location {Hex(str(l)).val}: {v.strip()}")
                        
            if 'M2' in config: 
                for l, p in config['M2'].items(): 
                    l == int(l)
                    if l >= 8 or l < 0: raise ValueError(f"Invalid M2 location {l}")

                    cols = ['S', 'A1', 'A0', 'E', 'AC', 'PC0', 'PC']
                    if any(c not in p for c in cols): raise ValueError(f"Invalid M2 configuration at location {l}")
                    p['PC'] = Hex(str(p['PC'])).val
                    p['PC0'] = Hex(str(p['PC0'])).val
                    p['AC'] = Hex(str(p['AC']),3).val
                    self.cpu.secondary_memory[l] = p 


            if self.cpu.main_memory[8] == '': raise ValueError('Time value not specified at location 8')
            self.cpu.TM = Hex(self.cpu.main_memory[8]).val
            self.cpu.TP = Hex(str(len(config['M2'])),1).val if 'M2' in config else '1'
            if not ('REG' in config and 'PC' in config['REG']): 
                if self.cpu.secondary_memory[0]['PC'] != '': 
                    self.cpu.PC = Hex(str(self.cpu.secondary_memory[0]['PC']), 2).val
                    self.cpu.changed_vars.append('PC')

            self.cpu.changed_vars.append('TM')
            self.cpu.changed_vars.append('TP')
        
        except ValueError as v: 
            messagebox.showerror(message=v)
            self.cpu.__init__(self.cpu.clk)

        self.loading = False 
        self.cpu.memory_ptr = 'PC'
        self.update_ui()
        self.update_selected_ui()
    

    def create_flip_flops_panel(self, frame):

        flip_flops_frame = tk.LabelFrame(frame, text="Flip-Flops", padx=10, pady=10)
        flip_flops_frame.pack(side=tk.LEFT, fill=tk.Y, anchor=tk.W)

        self.flip_flops = {}
        for i, ff in enumerate(self.flip_flops_names):
            var = tk.StringVar(value=str(getattr(self.cpu, ff)))
            lbl = tk.Label(flip_flops_frame, text=f"{ff}:")
            lbl.grid(row = i, column= 0, pady = 1)
            entry = tk.Entry(flip_flops_frame, textvariable=var, width=10,justify='center')
            entry.grid(row = i, column = 1, pady = 1)
            self.flip_flops[ff] = [var, entry]
            self.prev_state[ff] = str(getattr(self.cpu, ff))

            if ff in self.can_edit: 
                def on_change(event, ff_name, var_instance, show_error = False):
                    if self.cpu.stepping: 
                        if show_error: messagebox.showerror("error", "can't change value during instruction execution")
                        var_instance.set(getattr(self.cpu, ff_name))
                        return "break"
                    
                    setattr(self.cpu, ff_name, int(var_instance.get()) % 2)
                    self.cpu.changed_vars = [ff_name]
                    self.update_selected_ui()

                entry.config(bg='yellow')
                


                entry.bind("<FocusOut>", lambda event, f=ff, v=var: on_change(event, f, v, False))
                entry.bind("<Return>", lambda event, f=ff, v=var: on_change(event, f, v, True))

            else: 
                entry.bind("<KeyPress>", lambda e : "break")  
                entry.bind("<KeyRelease>", lambda e: "break")  
                entry.bind("<FocusOut>", lambda e: None)  





    def create_registers_panel(self, frame):
        # Create a frame for registers
        registers_frame = tk.LabelFrame(frame, text="Registers", padx=10, pady=10)
        registers_frame.pack(side=tk.LEFT, fill=tk.Y, anchor=tk.W)

        self.registers = {}
        for i, reg in enumerate(self.registers_names):
            width = 12 if reg != 'PSR' else 17 
            if reg == 'PSR':
                psr_value = getattr(self.cpu, reg, {})
                formatted_psr = '-'.join(str(value) for key, value in psr_value.items())
                var = tk.StringVar(value=str(formatted_psr))
            else:
                var = tk.StringVar(value=str(getattr(self.cpu, reg)))

            lbl = tk.Label(registers_frame, text=f"{reg}:")
            lbl.grid(row=i, column=0, pady=1)
            entry = tk.Entry(registers_frame, textvariable=var, width=width, justify='center')
            entry.grid(row=i, column=1, pady=1)

            self.registers[reg] = [var, entry]
            self.prev_state[reg] = str(getattr(self.cpu, reg))

            if reg == 'PSR': 
                self.prev_state[reg] = '-'.join(str(value) for key, value in psr_value.items())

            if reg in self.can_edit: 
                def on_change(event, reg_name, var_instance, show_error = False):
                    if self.cpu.stepping: 
                        if show_error: messagebox.showerror("error", "can't change value during instruction execution")
                        var_instance.set(getattr(self.cpu, reg_name))
                        return "break"

                    val = var_instance.get()
                    if val == '' or val is None:
                        if show_error: messagebox.showerror("error", "can't assign an empty value")
                    else: 
                        setattr(self.cpu, reg_name, Hex(var_instance.get(), self.cpu.bits[reg_name]).val)
                    
                    self.cpu.changed_vars = [reg_name]
                    self.update_selected_ui()


                entry.config(bg='yellow')

                entry.bind("<FocusOut>", lambda event, r=reg, v=var: on_change(event, r, v, False))
                entry.bind("<Return>", lambda event, r=reg, v=var: on_change(event, r, v, True))

            else: 
                entry.bind("<KeyPress>", lambda e : "break")  
                entry.bind("<KeyRelease>", lambda e: "break")  
                entry.bind("<FocusOut>", lambda e: None)  



    def create_main_memory_table(self, frame):
        # Create a frame for main memory
        f = tk.Frame(self.root)
        f.pack(side = tk.LEFT)
        main_memory_frame = tk.LabelFrame(frame, text="Main Memory", padx=10, pady=10)
        main_memory_frame.pack(side=tk.LEFT, fill=tk.Y)

        self.main_memory_table = ttk.Treeview(main_memory_frame, columns=("Address", "Value"), show="headings", height=7)
        self.main_memory_table.heading("Address", text="Address")
        self.main_memory_table.column("Address", width=50, anchor=tk.CENTER)

        self.main_memory_table.heading("Value", text="Instructions")
        self.main_memory_table.column("Value", width=200, anchor=tk.CENTER)
        self.main_memory_table.pack(fill=tk.BOTH, expand=True)

        # Populate memory table
        for address, value in enumerate(self.cpu.main_memory):
            self.main_memory_table.insert("", "end", values=(f"{address:02x}".upper(), value))

        row_id = self.main_memory_table.get_children()[int(getattr(self.cpu, 'PC'),16)] 
        self.main_memory_table.selection_set(row_id)  
        self.main_memory_table.focus(row_id)
        self.main_memory_table.see(row_id)
        self.main_memory_table.bind("<Double-1>", self.on_memory_edit)

    def create_secondary_memory_table(self, frame):
        # Create a frame for secondary memory
        secondary_memory_frame = tk.LabelFrame(frame, text="Secondary Memory", padx=10, pady=10)
        secondary_memory_frame.pack(side=tk.TOP)

        self.secondary_memory_table = ttk.Treeview(secondary_memory_frame, columns=("S", "A1", "A0", "E", "AC", "PC0", "PC"), show="headings", height=8)
        for i, col in enumerate(["S", "A1", "A0", "E", "AC", "PC0", "PC"]):
            id = f"#{i+1}"
            self.secondary_memory_table.heading(id, text=col)
            self.secondary_memory_table.column(id, width=50, anchor=tk.CENTER)
        self.secondary_memory_table.pack(fill=tk.BOTH, expand=True)

        # Populate secondary memory table
        for row in self.cpu.secondary_memory:
            self.secondary_memory_table.insert("", "end", values=list(row.values()))
        
        # pid = self.cpu.main_memory[int(getattr(self.cpu, 'PRC'))]
        # if pid != '': 
        #     pid = int(pid)
        pid = int(getattr(self.cpu, 'TAR'))
        row_id = self.secondary_memory_table.get_children()[pid] 
        self.secondary_memory_table.selection_set(row_id)  
        self.secondary_memory_table.focus(row_id)
        self.secondary_memory_table.see(row_id)
        self.secondary_memory_table.bind("<Double-1>", self.on_secondary_memory_edit)

    def create_buttons(self,frame): 
        # Create a frame for the buttons
        button_frame = tk.Frame(frame, padx=10, pady=10)
        button_frame.pack(expand=True, fill=tk.BOTH)

        # Configure the frame to center the buttons
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        button_frame.columnconfigure(2, weight=1)
        button_frame.columnconfigure(3, weight=1)

        # Create the buttons
        self.load_button = tk.Button(button_frame, text="Load", command=self.load_program)
        self.step_button = tk.Button(button_frame, text="Step", command=self.step_code)
        self.run_button = tk.Button(button_frame, text="Run", command=self.run_code)


        selected_option = tk.StringVar()
        selected_option.set(str(self.cpu.clk)+"hz")
        options = ["0.2hz", "0.5hz", "1hz", "20hz"]
        dropdown = tk.OptionMenu(button_frame, selected_option, *options)
        dropdown.config(bg='white')
        
        # Position the buttons in the grid
        self.load_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.step_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.run_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        dropdown.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        def clk_change(*args): self.cpu.clk = float(selected_option.get()[:-2])
        selected_option.trace_add('write', clk_change)
    

    def ui_loop(self): 
        if cpu.update_ui: 
            # start = time.perf_counter()
            # self.update_ui(selected=False)
            self.update_selected_ui()
            # print(time.perf_counter() - start)
            cpu.update_ui = False
        
        # if self.cpu.stepping == False and self.cpu.running == False: 

        self.root.after(5, self.ui_loop)
    

    def update_selected_ui(self): 
        for r in self.prev_changed_values: 
            entry = None
            if r in self.registers: 
                (_, entry) = self.registers[r]
            elif r in self.flip_flops: 
                (_, entry) = self.flip_flops[r]
            
            if entry is not None : 
                if r in self.can_edit: entry.config(bg='yellow', fg='black')
                else: entry.config(bg='white', fg='black')

        for r in self.cpu.changed_vars: 
            entry = None
            if r in self.registers: 
                # if r == 'AR': mem_pointer = 'AR'
                # if r == 'PRC': mem_pointer = 'PRC'
                (var, entry) = self.registers[r]
    
            elif r in self.flip_flops: 
                (var, entry) = self.flip_flops[r]

            # if r == 'M': mem_pointer = 'AR' 
            if entry is not None : 
                # breakpoint()
                entry.config(bg='blue', fg='white')
                if r == 'PSR': 
                    cols = ['S', 'A1', 'A0', 'E', 'AC', 'PC0', 'PC']
                    val = '-'.join([str(self.cpu.PSR[c]) for c in cols])
                else: val = getattr(self.cpu, r)
                var.set(val)
        
        self.prev_changed_values = self.cpu.changed_vars.copy()

        row_id = self.main_memory_table.get_children()[int(getattr(self.cpu, self.cpu.memory_ptr),16)] 
        self.main_memory_table.selection_set(row_id)  
        self.main_memory_table.focus(row_id)
        self.main_memory_table.see(row_id)

        row_id = self.main_memory_table.get_children()[int(getattr(self.cpu, 'AR'),16)] 
        address = getattr(self.cpu, 'AR')
        row_id = self.main_memory_table.get_children()[int(address,16)] 
        self.main_memory_table.item(row_id, values=(Hex(address).val, self.cpu.main_memory[int(address, 16)],))

        pid = int(getattr(self.cpu, 'TAR'))
        # if pid != '': 
        #     pid = int(pid)

        row_id = self.secondary_memory_table.get_children()[pid] 
        self.secondary_memory_table.selection_set(row_id)  
        self.secondary_memory_table.focus(row_id)
        self.secondary_memory_table.see(row_id)

        row = self.cpu.secondary_memory[pid].copy()
        values = []
        for col in ["S", "A1", "A0", "E", "AC", "PC0", "PC"]:
            values.append(str(row[col]))
        self.secondary_memory_table.item(row_id, values=values)


    def clear_selected(self):
        for  _, entry in self.flip_flops.values():
            entry.config(bg='white', fg='black')

        for  _, entry in self.registers.values():
            entry.config(bg='white', fg='black')

    def update_ui(self, selected = False):
        if self.loading: return
        # if self.cpu.execute: return
        # if self.cpu.stepping: breakpoint() 

        # Update flip-flops
        for ff, (var, entry) in self.flip_flops.items():
            val = str(getattr(self.cpu,ff))
            if val != self.prev_state[ff]: 
                entry.config(bg='blue', fg='white')
                self.prev_state[ff] = val
                self.prev_changed_values.append(ff)
            else: 
                if ff in self.can_edit: entry.config(bg='yellow', fg='black')
                else: entry.config(bg='white', fg='black')
            # entry.config(state = "normal")
            var.set(val)
            # entry.config(state = "disabled")

        # Update registers
        mem_pointer = 'PC'
        for reg, (var, entry) in self.registers.items():
            val = getattr(self.cpu, reg)
            if reg == "PSR":
                val =  '-'.join(str(value) for key, value in val.items())
            else: 
                val = str(val)
            if val != self.prev_state[reg]: 
                # if reg == 'AR': mem_pointer = 'AR'
                entry.config(bg='blue', fg='white')
                self.prev_state[reg] = val
                self.prev_changed_values.append(reg)
            else: 
                if reg in self.can_edit: entry.config(bg='yellow', fg='black')
                else: entry.config(bg='white', fg='black')
            var.set(val)

        # Update main memory
        row_id = self.main_memory_table.get_children()[int(getattr(self.cpu, 'PC'),16)] 
        self.main_memory_table.selection_set(row_id)  
        self.main_memory_table.focus(row_id)
        self.main_memory_table.see(row_id)

        if selected: 
            address = getattr(self.cpu, 'PC')
            row_id = self.main_memory_table.get_children()[int(address,16)] 
            self.main_memory_table.item(row_id, values=(address, self.cpu.main_memory[int(address, 16)],))

        else: 
            for address, (child, value) in enumerate(zip(self.main_memory_table.get_children(), self.cpu.main_memory)):
                self.main_memory_table.item(child, values=(f"{address:02x}".upper(), value,))

        # Update secondary memory
        pid = int(getattr(self.cpu, 'TAR'))
        # if pid != '': 
        #     pid = int(pid)
        row_id = self.secondary_memory_table.get_children()[pid] 
            # if int(getattr(self.cpu, 'GS')) == 1: 
        self.secondary_memory_table.selection_set(row_id)  
        self.secondary_memory_table.focus(row_id)
        self.secondary_memory_table.see(row_id)

        for i, (child, row) in enumerate(zip(self.secondary_memory_table.get_children(), self.cpu.secondary_memory)):
            values = []
            for col in ["S", "A1", "A0", "E", "AC", "PC0", "PC"]:
                values.append(str(row[col]))
            self.secondary_memory_table.item(child, values=values)

    def on_memory_edit(self, event):
        if self.cpu.running or self.cpu.stepping: return

        item_id = self.main_memory_table.identify_row(event.y)
        column = self.main_memory_table.identify_column(event.x)

        if column != "#2" or not item_id: return

        current_value = self.main_memory_table.item(item_id, "values")[1]
        
        entry = tk.Entry(self.root)
        entry.insert(0, current_value)
        entry.place(x=event.x_root - self.root.winfo_rootx() - 50, y=event.y_root - self.root.winfo_rooty())
        entry.focus()

        def save_value():
            new_value = entry.get()
            
            self.main_memory_table.item(item_id, values=(self.main_memory_table.item(item_id, "values")[0], new_value))
            
            address = int(self.main_memory_table.item(item_id, "values")[0], 16)
            self.cpu.main_memory[address] = new_value

            entry.destroy()

        entry.bind("<Return>", lambda e: save_value())
        entry.bind("<FocusOut>", lambda e: save_value())

    def on_secondary_memory_edit(self, event):
        if self.cpu.running or self.cpu.stepping: return

        item_id = self.secondary_memory_table.identify_row(event.y)
        column_id = int(self.secondary_memory_table.identify_column(event.x)[1:]) - 1
        

        columns = ["S", "A1", "A0", "E", "AC", "PC0", "PC"]
        current_value = self.secondary_memory_table.item(item_id, "values")[column_id]

        entry = tk.Entry(self.root)
        entry.insert(0, current_value)
        entry.place(x=event.x_root - self.root.winfo_rootx() - 50, y=event.y_root - self.root.winfo_rooty())
        entry.focus()

        def save_value():
            new_value = entry.get()
            if new_value == '': 
                entry.destroy()
                return "break"
            
            if column_id in range(4): 
                new_value = str(int(new_value) % 2)
            elif column_id == 4: 
                new_value = Hex(str(new_value), 3).val
            else: 
                new_value = Hex(str(new_value)).val

            values =  list(self.secondary_memory_table.item(item_id, "values"))
            values[column_id] = new_value
            self.secondary_memory_table.item(item_id, values=values)
            
            address = (int(item_id[1:]) - 1) %8 
            self.cpu.secondary_memory[address][columns[column_id]] = new_value

            entry.destroy()

        # entry.bind("<Return>", lambda e: "break")
        # entry.bind("<FocusOut>", lambda e: "break")
        entry.bind("<Return>", lambda e: save_value())
        entry.bind("<FocusOut>", lambda e: save_value())


cpu = CPU()
ui = UI(cpu)