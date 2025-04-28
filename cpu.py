from time import sleep
import inspect
import threading
from tkinter import messagebox


class Hex(): 
    def __init__(self, val = '0', bits = 2): 
        self.bits = bits
        self.val = self._hex(int(val, 16))

    def _hex(self, val):
        if val < 0: 
            val = pow(2, self.bits*4) - abs(val)
        
        val = hex(val)[2:]
        val = val.rjust(self.bits, '0')
        return val[-self.bits:].upper()


    def __add__(self, other): 
        return self._hex(int(self.val, 16) + int(other.val, 16))
        

    def __sub__(self, other: 'Hex'): 
        new_val = self._hex(-int(other.val, 16))
        return self + Hex(new_val, self.bits)
    
    def __eq__(self, other): 
        return int(self.val, 16) == int(other.val, 16)
    
    def __str__(self): 
        return self.val
    
    def __and__(self, other): 
        return self._hex(int(self.val, 16) & int(other.val, 16))
    
    def __or__(self, other): 
        return self._hex(int(self.val, 16) | int(other.val, 16))


class CPU:
    def __init__(self, freq = 1):
        self.AR = Hex(bits=2).val   # Address Register (8 bits)
        self.PC = Hex(bits=2).val     # Program Counter (8 bits)
        self.DR = Hex(bits=3).val     # Data Register (12 bits)
        self.AC = Hex(bits=3).val     # Accumulator (12 bits)
        self.INPR = Hex(bits=1).val   # Input Register (8 bits)
        self.IR = Hex(bits=3).val     # instruction Register (12 bits)
        self.TR = Hex(bits=3).val     # Temporary Register (12 bits)
        self.TM = Hex(bits=2).val     # Timer Register (8 bits)
        self.PRC = Hex(bits=1).val    # Priority Register (3 bits)
        self.TAR = Hex(bits=1).val    # Table Address Register (3 bits)
        self.TP = Hex(bits=1).val     # Total Processes (3 bits)
        self.NS = Hex(bits=1).val     # Number of Stops (3 bits)
        self.OUTR = Hex(bits=1).val    # Output Register (8 bits)
        self.SC = Hex(bits=1).val
        self.PSR = {'S': 0, 'A1' : 0, 'A0' : 0, 'E': 0, 'AC': Hex('0',3).val, 'PC0': Hex('0').val, 'PC':Hex('0').val}

        # Flip-Flops
        self.I = 0      # Interrupt Flip-Flop
        self.E = 0      # Enable Flip-Flop
        self.R = 0      # Read Flip-Flop
        self.C = 0      # Carry Flip-Flop
        self.SW = 0     # Switch Flip-Flop
        self.IEN = 0    # Interrupt Enable Flip-Flop
        self.FGI = 0    # Input Flag
        self.FGO = 0    # Output Flag
        self.S = 0      # Start Flip-Flop
        self.GS = 0     # General Status Flip-Flop
        self.A0 = 0     # A0 Flip-Flop
        self.A1 = 0     # A1 Flip-Flop
        self.clk = freq


        self.running = False
        self.execute = False
        self.stepping = False
        self.lock = threading.Lock()
        self.ui = None
        self.update_ui = False 
        self.memory_ptr = 'AR'

        # Main Memory (256 words, each 12 bits)

        self.main_memory = [''] * 256

        # Secondary Memory (8 rows, 7 columns)
        # Each row represents a tuple: (S, A1, A0, E, AC, PC0, PC)
        self.secondary_memory = [
            {'S': '', 'A1' : '', 'A0' : '', 'E': '', 'AC': '', 'PC0': '', 'PC': ''} for _ in range(8)
        ]

        self.changed_vars = []
        ## OTHER GLOBAL VARIABLE
        self.bits = {
            'AR' : 2, # Address Register (8 bits)
            'PC' : 2, # Program Counter (8 bits)
            'DR' : 3, # Data Register (12 bits)
            'AC' : 3, # Accumulator (12 bits)
            'INPR' : 1, # Input Register (8 bits)
            'IR' : 3, # instruction Register (12 bits)
            'TR' : 3, # Temporary Register (12 bits)
            'TM' : 2, # Timer Register (8 bits)
            'PRC' : 1, # Priority Register (3 bits)
            'TAR' : 1, # Table Address Register (3 bits)
            'TP' : 1, # Total Processes (3 bits)
            'NS' : 1, # Number of Stops (3 bits)
            'OUT' : 1 # Output Register (8 bits)
        }

        self.instruction_map = {
            "AND": self.AND_instruction,
            "ADD": self.ADD_instruction,
            "SUB": self.SUB_instruction,
            "OR": self.OR_instruction,
            "CAL": self.CAL_instruction,
            "LDA": self.LDA_instruction,
            "STA": self.STA_instruction,
            "BR": self.BR_instruction,
            "ISA": self.ISA_instruction,
            "SWT": self.SWT_instruction,
            "AWT": self.AWT_instruction,
            "CLE": self.CLE_instruction,
            "CMA": self.CMA_instruction,
            "CME": self.CME_instruction,
            "CIR": self.CIR_instruction,
            "CIL": self.CIL_instruction,
            "SZA": self.SZA_instruction,
            "SZE": self.SZE_instruction,
            "ICA": self.ICA_instruction,
            "ESW": self.ESW_instruction,
            "DSW": self.DSW_instruction,
            "HLT": self.HLT_instruction,
            "FORK": self.FORK_instruction,
            "RST": self.RST_instruction,
            "UTM": self.UTM_instruction,
            "LDP": self.LDP_instruction,
            "SPA": self.SPA_instruction,
            "INP": self.INP_instruction,
            "OUT": self.OUT_instruction,
            "SKI": self.SKI_instruction,
            "SKO": self.SKO_instruction,
            "EI": self.EI_instruction,
        }


    def fetch(self):
        self.AR = self.PC
        self.block(['AR']) 

        self.IR = self.main_memory[int(self.AR, 16)]
        self.PC = Hex(self.PC) + Hex('1') 
        self.block(['IR', 'PC'])

    def decode(self):
        codes = self.IR.split(' ')
        if len(codes) == 1:
            return codes[0].strip().upper(), None,False
        elif len(codes) == 2:
            self.AR = Hex(codes[1].upper().strip()).val
            self.block(['AR'])
            return codes[0],self.AR,False
        else:
            self.AR = Hex(codes[1].upper().strip()).val
            self.I = 1
            self.block(['AR'])
            return codes[0].strip().upper(),codes[1].strip().upper,True

    @staticmethod
    def hex_op(hex1, hex2, bits = 3, func = lambda x, y : x + y): 
        if bits == 3: 
            return f"{func(int(hex1, 16), int(hex2, 16)):03x}".upper()

        if bits == 2: 
            return f"{func(int(hex1, 16), int(hex2, 16)):02x}".upper()
    
    @staticmethod
    def minus(x, y): return x - y

    def block(self, changed_var = [], last = False): 
        # print(f"Changed Vars: {changed_var}")
        # print(f"Fetch {inspect.stack()[1].function}")

        if last: 
            self.changed_vars = changed_var + ['C']
            if Hex(self.TM) == Hex('0'): 
                self.C = self.SW
                self.stepping = False
            
            self.R = int(self.IEN and (self.FGI or self.FGO))
            self.memory_ptr = 'PC'
        else: 
            self.changed_vars = changed_var + ['SC']
            self.SC = Hex(self.SC,1) + Hex('1')
            self.memory_ptr = 'AR'
        
        self.update_ui = True

        if not self.running and last: return
        sleep(1/self.clk) 
        while self.update_ui: pass
        
        # if last == True: 
        #     self.stepping = False
        #     return

        # with self.lock: 
        #     self.execute = False 

        # if self.stepping and not self.running and not last: 
        #     while self.execute == False and self.stepping and self.running == False: pass
        #     if self.running: 
        #         sleep(1/self.clk) 
        #         while self.update_ui: pass
        
        # print(f"comming out of block with parent function {inspect.stack()[1].function}")

    def ioInterrupt(self): 
        self.PSR["S"] = self.S
        self.PSR["A1"] = self.A1
        self.PSR["A0"] = self.A0
        self.PSR["E"] = self.E
        self.PSR["PC"] = self.PC
        self.PSR["AC"] = self.AC
        self.AR = Hex(self.PRC).val
        temp = int(self.main_memory[int(self.AR, 16)], 16)
        self.PSR["PC0"] = self.secondary_memory[temp]['PC0']
        self.block(['AR', 'PSR'])

        self.TAR = self.main_memory[int(self.AR, 16)]
        if int(self.TAR, 16) >= 8: 
            raise ValueError(f'Invalid PID: {self.TAR}')
        self.TAR = Hex(self.TAR, 1).val
        self.block(['TAR'])

        self.AR = '09'
        self.block(['AR'])

        self.secondary_memory[int(self.TAR, 16)] = self.PSR.copy()
        self.PC = self.main_memory[int(self.AR, 16)]
        self.IEN, self.SW, self.R, self.SC = 0,0,0,Hex('0',1).val
        self.FGI, self.FGO = 0,0
        self.block(['PC', 'IEN', 'SW', 'R', 'SC', 'FGI', 'FGO'], True)

    def contextSwitch(self):
        self.PSR["S"] = self.S
        self.PSR["A1"] = self.A1
        self.PSR["A0"] = self.A0
        self.PSR["E"] = self.E
        self.PSR["PC"] = self.PC
        self.PSR["AC"] = self.AC
        self.AR = self.PRC
        temp = int(self.main_memory[int(self.AR, 16)], 16)
        self.PSR["PC0"] = self.secondary_memory[temp]['PC0']

        # breakpoint()
        self.block(['AR', 'PSR'])

        self.TAR = self.main_memory[int(self.AR, 16)]
        if int(self.TAR, 16) >= 8: 
            raise ValueError(f'Invalid PID: {self.TAR}')
        self.TAR = Hex(self.TAR, 1).val 
        self.block(['TAR'])

        self.AR = '08'
        self.PRC = Hex(self.PRC, 1) + Hex('1')
        self.block(['AR', 'PRC'])

        self.secondary_memory[int(self.TAR, 16)] = self.PSR.copy()
        self.TM = Hex(self.main_memory[int(self.AR, 16)]).val
        if (Hex(self.PRC,1) == Hex(self.TP)):
            self.PRC = Hex('0', 1).val
        self.block(['PRC', 'TM'])        

        self.AR = self.PRC
        self.block(['AR'])

        self.TAR = self.main_memory[int(self.AR, 16)]
        self.block(['TAR'])

        self.PSR = self.secondary_memory[int(self.TAR, 16)].copy()
        self.block(['PSR'])

        self.PC = self.PSR["PC"]
        self.AC = self.PSR["AC"]
        self.E = self.PSR["E"]
        self.A0 = self.PSR["A0"]
        self.A1 = self.PSR["A1"]
        self.S = self.PSR["S"]
        self.C = 0
        if (self.S == 0):
            self.C = 1
        self.SC = Hex('0', 1).val
        self.block(['PC', 'AC', 'E', 'A0', 'A1', 'S', 'C', 'SC'], True)

    def CAL_instruction(self):
        self.DR = Hex(self.main_memory[int(self.AR, 16)],3).val
        self.block(['DR'])

        if self.A0 == 0 and self.A1 == 0:
            self.AC = Hex(self.AC,3) + Hex(self.DR,3)

        elif self.A0 == 1 and self.A1 == 0:
            self.AC = Hex(self.AC,3) - Hex(self.DR,3)

        elif self.A0 == 0 and self.A1 == 1:
            self.AC = Hex(self.AC,3) & Hex(self.DR,3)
        else:
            self.AC = Hex(self.AC,3) | Hex(self.DR,3)

        self.TM = Hex(self.TM) - Hex('1') 
        self.SC = Hex('0',1).val
        self.block(['AC', 'TM', 'SC'], True)

    def LDA_instruction(self):
        self.DR = Hex(self.main_memory[int(self.AR, 16)], 3).val
        self.block(['DR'])

        self.AC = self.DR
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['AC', 'SC', 'TM'], True)

    def STA_instruction(self):
        self.main_memory[int(self.AR, 16)] = self.AC
        self.block(['M'])

        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['TM'], True)


    def BR_instruction(self):
        self.PC = Hex(self.AR).val
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1')  

        self.block(['PC', 'TM', 'SC'], True)

    def ISA_instruction(self):
        self.DR = Hex(self.main_memory[int(self.AR, 16)],3).val
        self.block(['DR'])

        self.DR = Hex(self.DR,3) + Hex('1',3)
        self.block(['DR'])

        self.main_memory[int(self.AR, 16)] = self.DR
        if self.DR == self.AC:
            self.PC = Hex(self.PC) + Hex('1') 
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['DR', 'PC', 'TM', 'SC'], True)

    def SWT_instruction(self):
        self.PSR["PC"] = self.PC
        self.PSR["AC"] = self.AC
        self.PSR["E"] = self.E
        self.PSR["A0"] = self.A0
        self.PSR["A1"] = self.A1
        self.PSR["S"] = self.S
        temp = int(self.main_memory[int(self.PRC, 16)], 16)
        self.PSR["PC0"] = self.secondary_memory[temp]['PC0']
        
        self.TR = Hex(self.AR,3).val 
        self.block(['PSR', 'TR'])

        self.AR = self.PRC
        self.block(['AR'])

        self.TAR = self.main_memory[int(self.AR, 16)]
        if int(self.TAR, 16) >= 8: 
            raise ValueError(f'Invalid PID: {self.TAR}')
        self.TAR = Hex(self.TAR, 1).val

        self.block(['TAR'])

        self.secondary_memory[int(self.TAR, 16)] = self.PSR.copy()
        self.PRC = Hex(self.TR, 1).val
        self.AR = Hex(self.TR, 2).val
        self.block(['PRC', 'AR'])
        

        self.TAR = self.main_memory[int(self.AR, 16)]
        self.block(['TAR'])

        self.PSR = self.secondary_memory[int(self.TAR, 16)].copy()
        self.AR = '08'
        self.block(['PSR', 'AR'])

        self.PC = self.PSR["PC"]
        self.AC = self.PSR["AC"]
        self.E = self.PSR["E"]
        self.A0 = self.PSR["A0"]
        self.A1 = self.PSR["A1"]
        self.S = 1
        self.TM = self.main_memory[int(self.AR, 16)]
        if self.PSR["S"] == 0:
            self.NS = Hex(self.NS) - Hex('1')
        self.TAR = Hex(self.TAR, 1).val
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'AC', 'E', 'A0', 'A1', 'S', 'TM', 'NS', 'SC', 'TM'], True)
    

    def AWT_instruction(self):
        self.TAR = self.main_memory[int(self.AR, 16)]
        if int(self.TAR, 16) >= 8: 
            raise ValueError(f"Invalid PID: {self.TAR}")
        self.TAR = Hex(self.TAR,1).val
        self.block(['TAR'])

        self.PSR = self.secondary_memory[int(self.TAR, 16)].copy()
        self.block(['PSR'])

        if self.PSR["S"] == 1:
            self.PC = Hex(self.PC) - Hex('1')
            self.C = 1
        
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'C', 'SC', 'TM'], True)

    def CLE_instruction(self):
        self.E = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['E', 'SC', 'TM'], True)

    def CMA_instruction(self):
        self.AC = Hex(bits=3)._hex(~int(self.AC,16) & ((1 << 12) - 1))
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['AC', 'SC', 'TM'], True)

    def CME_instruction(self):
        self.E = ~self.E % 2
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['E', 'SC', 'TM'], True)

    def CIR_instruction(self):

        Lsb = int(self.AC, 16) & 1 
        self.AC = Hex(bits=3)._hex(int(self.AC, 16) >> 1 | (self.E << 11))
        self.E = Lsb
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['AC', 'E', 'SC', 'TM'], True)

    def CIL_instruction(self):
        Msb = (int(self.AC,16) >> 11) & 1
        # self.AC = self.hex_op(self.AC, '0', func= lambda x, y: ((self.AC << 1) & ((1 << 12) - 1)) | self.E)
        self.AC = Hex(bits=3)._hex(((int(self.AC, 16) << 1) & ((1 << 12) - 1)) | self.E)
        self.E = Msb
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['AC', 'E', 'SC', 'TM'], True)


    def SZA_instruction(self):
        if Hex(self.AC, 3) == Hex('0'):
            self.PC = Hex(self.PC) + Hex('1') 
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'SC', 'TM'], True)

    def SZE_instruction(self):
        if self.E == 0:
            self.PC = Hex(self.PC) + Hex('1')     
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'SC', 'TM'], True)

    def ICA_instruction(self):
        self.AC = Hex(self.AC) + Hex('1')
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['AC', 'SC', 'TM'], True)

    def ESW_instruction(self):
        self.SW = 1
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['SW', 'SC', 'TM'], True)

    def DSW_instruction(self):
        self.SW = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['SW', 'SC', 'TM'], True)

    def ADD_instruction(self):
        self.A0 = 0
        self.A1 = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['A0', 'A1', 'SC', 'TM'], True)
    
    def SUB_instruction(self):
        self.A0 = 1
        self.A1 = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['A0', 'A1', 'TM', 'SC'], True) 

    def AND_instruction(self):
        self.A0 = 0
        self.A1 = 1
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['A0', 'A1', 'TM', 'SC'], True)

    def OR_instruction(self):
        self.A0 = 1
        self.A1 = 1
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['A0', 'A1', 'TM', 'SC'], True)

    def HLT_instruction(self):
        if self.S: 
            self.NS = Hex(self.NS, 1) + Hex('1')
        self.S = 0
        self.PC = Hex(self.PC) - Hex('1')
        self.block(['S', 'NS'])

        if Hex(self.NS) == Hex(self.TP):
            self.GS = 0
        self.S = 0
        self.C = 1
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['S', 'GS', 'PC', 'C', 'SC', 'TM'], True)

    def FORK_instruction(self):
        self.PSR["PC"] = self.PC
        self.PSR["AC"] = self.AC
        self.PSR["E"] = self.E
        self.PSR["A0"] = self.A0
        self.PSR["A1"] = self.A1
        self.PSR["S"] = self.S
        temp = int(self.main_memory[int(self.PRC, 16)], 16)
        self.PSR["PC0"] = self.secondary_memory[temp]['PC0']
        if Hex(self.TP) == Hex('7'): 
            raise ValueError('Cannot create more than 8 processes')
        self.AR = Hex(self.TP).val
        self.TP = Hex(self.TP,1) + Hex('1')
        self.block(['PSR', 'AR', 'TP'])


        self.TAR = self.main_memory[int(self.AR, 16)]
        self.block(['TAR'])

        self.secondary_memory[int(self.TAR, 16)] = self.PSR.copy()
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['SC', 'TM'], True)

    def RST_instruction(self):
        self.AR = self.PRC
        self.block(['AR'])
        
        self.TAR =  self.main_memory[int(self.AR, 16)]
        self.block(['TAR'])

        self.PSR = self.secondary_memory[int(self.TAR, 16)].copy()
        self.block(['PSR'])

        self.PSR["PC"] = self.PSR["PC0"]
        self.PSR["AC"] = '000'
        self.PSR["S"] = 0
        self.PSR["A0"] = 0
        self.PSR["A1"] = 0
        self.PSR["E"] = 0
        self.PC = self.PSR['PC0']
        self.AC = Hex('0', 3).val
        self.A0, self.A1, self.E = 0,0,0
        self.block(['PSR', 'PC', 'AC', 'A0', 'A1', 'S', 'E'])

        self.secondary_memory[int(self.TAR,16)] = self.PSR.copy()
        self.SC = Hex('0',1).val
        self.C = 1
        if not self.S: self.NS = Hex(self.NS,1) - Hex('0')
        self.S = 0
        self.block(['PSR', 'S', 'SC'], True)


    def UTM_instruction(self):
        self.AR = '08'
        self.block(['AR'])
        self.TM = Hex(self.main_memory[int(self.AR, 16)], 2).val
        self.SC = Hex('0',1).val
        self.block(['TM', 'SC'], True)

    def LDP_instruction(self):
        self.AR = self.PRC
        self.block(['AR'])

        self.TAR = self.main_memory[int(self.AR, 16)]
        self.block(['TAR'])

        self.PSR = self.secondary_memory[int(self.TAR, 16)]
        self.block(['PSR'])

        self.PC = self.PSR["PC"]
        self.AC = self.PSR["AC"]
        self.E = self.PSR["E"]
        self.A0 = self.PSR["A0"]
        self.A1 = self.PSR["A1"]
        self.S = self.PSR["S"]
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'AC', 'A0', 'A1', 'S', 'E', 'SC', 'TM'], True)

    def SPA_instruction(self):
        self.AR = self.PRC
        self.block(['AR'])

        if self.main_memory[int(self.AR, 16)] == self.AC:
            self.PC = Hex(self.PC) + Hex('1') 

        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['SC', 'TM'], True)

    def INP_instruction(self):
        self.AC = Hex(self.INPR,3).val
        self.FGI = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['AC', 'FGI', 'SC', 'TM'], True)
    
    def OUT_instruction(self):
        self.OUTR = Hex(self.AC,1).val
        self.FGO = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['OUTR', 'FGO', 'SC', 'TM'],True)

    def SKI_instruction(self):
        if self.FGI == 1:
            self.PC = Hex(self.PC) + Hex('1') 
        
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'SC', 'TM'], True)

    def SKO_instruction(self):
        if self.FGO == 1:
            self.PC = Hex(self.PC) + Hex('1') 
        
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['PC', 'SC', 'TM'], True)

    def EI_instruction(self):
        self.IEN = 1
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['IEN', 'SC', 'TM'], True)

    def DI_instruction(self):
        self.IEN = 0
        self.SC = Hex('0',1).val
        self.TM = Hex(self.TM) - Hex('1') 
        self.block(['IEN', 'SC', 'TM'], True)


    def run_next(self):
        if not self.GS: return

        print('Thread Created')
        self.stepping = True
        try: 
            if (self.C and self.SW) or not self.S:
                self.contextSwitch()
            
            elif self.R or (self.IEN and (self.FGI or self.FGO)): 
                if not self.R: 
                    self.R = 1
                    self.block(['R']) 
                self.ioInterrupt()


            else:
                self.fetch()
                opcode, address, I_address = self.decode()
                if I_address == True:
                    self.AR = self.main_memory[int(self.AR, 16)]
                    self.block(['AR'])
                
                if opcode in self.instruction_map:
                    self.instruction_map[opcode]()  
                else:
                    raise ValueError(f'unknown instructions {opcode}')

        except ValueError as v: 
            messagebox.showerror(message=v)
        # print(self.secondary_memory)


        print('Thread exited')
        self.stepping = False
    
    def run_code(self): 
        while self.running: 
            self.run_next()
            if not self.GS: 
                messagebox.showinfo(message="Execution stopped/not started. Global Start is 0")
                self.running = False
        