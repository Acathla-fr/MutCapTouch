from litex.build.generic_platform import *
from litex.build.lattice import LatticeiCE40Platform
from litex.build.lattice.programmer import IceStormProgrammer


_io = [
    # Clk / Rst
    ("clk100", 0, Pins("J3"), IOStandard("LVCMOS33")),
    #("btn_rst_n", 0, Pins("N11"), IOStandard("LVCMOS33")), Unusable, hard reset

    # LEDs
    ("user_led", 0, Pins("M12"), IOStandard("LVCMOS33")),
    ("user_led", 1, Pins("R16"), IOStandard("LVCMOS33")),

    # Buttons
    ("user_btn_n", 0, Pins("K11"), IOStandard("LVCMOS33")),
    ("user_btn_n", 1, Pins("P13"), IOStandard("LVCMOS33")),

    # Serial
    ("serial", 0,
        Subsignal("rx", Pins("L11")),
        Subsignal("tx", Pins("T16"), Misc("PULLUP")),
        #Subsignal("rts", Pins("B13"), Misc("PULLUP")),
        #Subsignal("cts", Pins("A15"), Misc("PULLUP")),
        #Subsignal("dtr", Pins("A16"), Misc("PULLUP")),
        #Subsignal("dsr", Pins("B14"), Misc("PULLUP")),
        #Subsignal("dcd", Pins("B15"), Misc("PULLUP")),
        IOStandard("LVCMOS33"),
    ),

    # SPI Flash
    ("spiflash", 0,
        Subsignal("cs_n", Pins("R12"), IOStandard("LVCMOS33")),
        Subsignal("clk", Pins("R11"), IOStandard("LVCMOS33")),
        Subsignal("mosi", Pins("P12"), IOStandard("LVCMOS33")),
        Subsignal("miso", Pins("P11"), IOStandard("LVCMOS33")),
    ),

    # SRAM (K6R4008V1D on rev. B, 
    ("sram", 0,
        Subsignal("addr", Pins("N2 T1 P4 R2 N5 T2 P5 R3 R5 T3",
            "R4 M7 N7 P6 M8 T5 R6 P8"),
            IOStandard("LVCMOS33")),
        Subsignal("data", Pins("T8 P7 N9 T9 M9 R9 K9 P9 R10 L10",
            "P10 N10 T10 T11 T15 T14"),
            IOStandard("LVCMOS33")),
        Subsignal("cs", Pins("T6"), IOStandard("LVCMOS33")),
        Subsignal("oe", Pins("L9"), IOStandard("LVCMOS33")),
        Subsignal("we", Pins("T7"), IOStandard("LVCMOS33"))
    )
]

_connectors = [
    # GPIO1 (34 pins)
    # 1,  2- +5V, GND
    # 3,  4- +3V3, GND
    # 5,  6- PIO3_00/IOL_1A(E4), EXTCLK
    # 7,  8- PIO3_01/IOL_1B(B2), GND
    # 9, 10- PIO3_02/IOL_2A(F5), PIO3_28/IOL_15A(J2)
    #11, 12- PIO3_03/IOL_2B(B1), PIO3_27/IOL_14B(H1)
    #13, 14- PIO3_04/IOL_3A(C1), PIO3_25/IOL_13B(G1)
    #15, 16- PIO3_05/IOL_3B(C2), PIO3_24/IOL_13A(J5)
    #17, 18- PIO3_06/IOL_4A(F4), PIO3_23/IOL_12B(H2)
    #19, 20- PIO3_07/IOL_4B(D2), PIO3_22/IOL_12A(J4)
    #21, 22- PIO3_08/IOL_5A(G5), PIO3_21/IOL_11B(G2)
    #23, 24- PIO3_09/IOL_5B(D1), PIO3_20/IOL_11A(H4)
    #25, 26- PIO3_10/IOL_6A(G4), PIO3_19/IOL_10B(F1)
    #27, 28- PIO3_11/IOL_6B(E3), PIO3_18/IOL_10A(H6)
    #29, 30- PIO3_12/IOL_7A(H5), PIO3_17/IOL_9B(F2)
    #31, 32- PIO3_13/IOL_7B(E2), PIO3_16/IOL_9A(H3)
    #33, 34- PIO3_14/IOL_8A(G3), PIO3_15/IOL_8B(F3)
    ("GPIO1", "E4 B2 F5 B1 C1 C2 F4 D2 G5 D1 G4 E3 H5 E2 G3 F3 H3 F2 H6 F1 H4 G2 J4 H2 J5 G1 H1 J2"),
]

class Platform(LatticeiCE40Platform):
    default_clk_name = "clk100"
    default_clk_period = 10

    def __init__(self, toolchain="icestorm"):
        LatticeiCE40Platform.__init__(self, "ice40-hx8k-ct256", _io, _connectors,
                                 toolchain=toolchain)

    def create_programmer(self):
        return IceStormProgrammer()

    def do_finalize(self, fragment):
        LatticeiCE40Platform.do_finalize(self, fragment)
        self.add_period_constraint(self.lookup_request("clk100", loose=True), 1e9/100e6)

