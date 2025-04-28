# YAML Configuration File Explanation

This document explains the structure and usage of the provided YAML configuration file, which is used to initialize registers, flip-flops, primary memory (M), and secondary memory (M2). Additionally, it includes details on how to specify indirect addresses.

---

## **Structure Overview**

### **1. REG (Registers)**
The `REG` section initializes the registers with their initial values:
- **Key:** Register name (e.g., `TP`)
- **Value:** Hexadecimal or integer value representing the register’s state.

#### Example:
```yaml
REG:
  TP: 4  # Total Processes
```

### **2. FF (Flip-Flops)**
The `FF` section sets the initial states of the flip-flops:
- **Key:** Flip-flop name (e.g., `GS`)
- **Value:** Binary state (`0` or `1`).

#### Example:
```yaml
FF:
  GS: 1  # Global Start
  S: 1   # Start
  SW: 1  # Switching
```

### **3. M (Primary Memory)**
The `M` section initializes the primary memory with:
- **Direct Addressing:** Specific hexadecimal addresses associated with values or lists.
- **Relative Addressing:** Lists of instructions stored sequentially relative to a starting address.

#### Example:
```yaml
M:
  0:
    - 0
    - 1
    - 2  # Order of context switching
  8: 5  # Number of instructions between context switches
  0A: 8  # Multiplicand
  0B: 2  # Multiplier or divider
  1A:    # Multiplication instructions
    - 0
    - ADD
    - LDA 0C
    - CAL 0A
    - STA 0C
    - HLT
```

#### Indirect Addressing
To specify indirect addressing, use the format:
```
[instruction] [hex-address] I
```
For example:
```yaml
  2A:
    - LDA 0B I
```
This specifies that the instruction should reference the value at the address stored in `0B`.

---

### **4. M2 (Secondary Memory)**
The `M2` section sets the initial states for processes in secondary memory:
- **Key:** Octal address.
- **Value:** A dictionary defining the program counter (`PC`), alternate counter (`PC0`), accumulator (`AC`), and other flags.

#### Example:
```yaml
M2:
  0:
    PC: 1B
    PC0: 1B
    AC: 0
    E: 0
    A0: 0
    A1: 0
    S: 1
```
