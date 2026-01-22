#!/usr/bin/env python3

#
# This file is part of LiteX-Boards.
#
# Copyright (c) 2019 Sean Cross <sean@xobs.io>
# Copyright (c) 2018 David Shah <dave@ds0.me>
# Copyright (c) 2020 Florent Kermarrec <florent@enjoy-digital.fr>
# SPDX-License-Identifier: BSD-2-Clause

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer
from migen.genlib.cdc import MultiReg

from litex.gen import *

from litex_boards.platforms import lattice_ice40up5k_evn
from litex.build.lattice.programmer import IceStormProgrammer

from litex.soc.cores.ram import Up5kSPRAM
from litex.soc.cores.clock import iCE40PLL
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *
from litex.soc.cores.led import LedChaser

from litex.build.generic_platform import *

# CRG ----------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        assert sys_clk_freq == 12e6
        self.rst    = Signal()
        self.cd_sys = ClockDomain()
        self.cd_por = ClockDomain()

        # # #

        # Clk/Rst
        sys = platform.request("clk12")
        platform.add_period_constraint(sys, 1e9/12e6)

        # Power On Reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal("sys"))
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # Sys Clk
        self.comb += self.cd_sys.clk.eq(sys)
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~por_done)


# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, bios_flash_offset, sys_clk_freq=12e6,
        with_led_chaser = True,
        **kwargs):
        platform = lattice_ice40up5k_evn.Platform()

        # CRG --------------------------------------------------------------------------------------
        self.crg = _CRG(platform, sys_clk_freq)

        # SoCCore ----------------------------------------------------------------------------------
        # Disable Integrated ROM/SRAM since too large for iCE40 and UP5K has specific SPRAM.
        kwargs["integrated_sram_size"] = 0
        kwargs["integrated_rom_size"]  = 0
        SoCCore.__init__(self, platform, sys_clk_freq, ident="LiteX SoC on Lattice iCE40UP5k EVN breakout board", **kwargs)
       # CPU --------------------------------------------------------------------------------------

        if (self.cpu_type == "vexriscv") and (self.cpu_variant == "lite"):
            self.cpu.use_external_variant("rtl/VexRiscv_Lite.v")

        # 128KB SPRAM (used as SRAM) ---------------------------------------------------------------
        self.spram = Up5kSPRAM(size=128 * KILOBYTE)
        #self.bus.add_slave("sram", self.spram.bus, SoCRegion(size=128 * KILOBYTE))
        self.bus.add_slave("sram", self.spram.bus, SoCRegion(origin=self.mem_map["sram"], size=128 * KILOBYTE))

        # SPI Flash --------------------------------------------------------------------------------
        # 4x mode is not possible on this board since WP and HOLD pins are not connected to the FPGA
        from litespi.modules import MX25L3235D
        #from mx25l3232f import MX25L3233F
        from litespi.opcodes import SpiNorFlashOpCodes as Codes
        self.add_spi_flash(mode="1x", module=MX25L3235D(Codes.READ_1_1_1))

        #flashsize=0x400000
        #from spi_flash import SpiFlash
        #pads = platform.request("spiflash")
        #self.submodules.spiflash = SpiFlash(pads, div=2, dummy=0, endianness=self.cpu.endianness)
        #spiflash_region = SoCRegion(origin=self.mem_map.get("spiflash", None), size=flashsize)
        #self.bus.add_slave(name="spiflash", slave=self.spiflash.bus, region=spiflash_region)


        # Add ROM linker region --------------------------------------------------------------------
        self.bus.add_region("rom", SoCRegion(
            origin = self.bus.regions["spiflash"].origin + bios_flash_offset,
            size   = 64 * KILOBYTE,
            linker = True)
        )
        self.cpu.set_reset_address(self.bus.regions["rom"].origin)

        # Leds -------------------------------------------------------------------------------------
        if with_led_chaser:
            self.leds = LedChaser(
                pads         = platform.request_all("user_led_n"),
                sys_clk_freq = sys_clk_freq)

        # Add a UARTBone bridge --------------------------------------------------------------------
        debug_uart = False
        if debug_uart:
            self.add_uartbone()

        # Captouch ---------------------------------------------------------------------------------
        # Pin distribution
        #_GPIOs = [
        #  ("pads_x", 0,
        #   Subsignal("0", Pins("J2:0"), IOStandard("LVCMOS33")),
        #   Subsignal("1", Pins("J2:1"), IOStandard("LVCMOS33")),
        #   Subsignal("2", Pins("J2:3"), IOStandard("LVCMOS33")),
        #   Subsignal("3", Pins("J2:4"), IOStandard("LVCMOS33")),
        #  ),
        #  ("pads_y", 0,
        #   Subsignal("0", Pins("J2:5"), IOStandard("LVCMOS33")),
        #   Subsignal("1", Pins("J2:6"), IOStandard("LVCMOS33")),
        #   Subsignal("2", Pins("J2:7"), IOStandard("LVCMOS33")),
        #   Subsignal("3", Pins("J2:8"), IOStandard("LVCMOS33")),
        #  )
        #]
        _GPIOs = [
          ("pads_x", 0, Pins("J2:0"), IOStandard("LVCMOS33")),
          ("pads_x", 1, Pins("J2:1"), IOStandard("LVCMOS33")),
          ("pads_x", 2, Pins("J2:3"), IOStandard("LVCMOS33")),
          ("pads_x", 3, Pins("J2:4"), IOStandard("LVCMOS33")),

          ("pads_y", 0, Pins("J2:5"), IOStandard("LVCMOS33")),
          ("pads_y", 1, Pins("J2:6"), IOStandard("LVCMOS33")),
          ("pads_y", 2, Pins("J2:7"), IOStandard("LVCMOS33")),
          ("pads_y", 3, Pins("J2:8"), IOStandard("LVCMOS33")),
        ]
        self.platform.add_extension(_GPIOs)

        # Module Instanciation
        from mutcaptouch import CapTouch
        n=m=4
        self.submodules.captouch = CapTouch(n,m)

        # Tristate pins (cannot be simulated)
        _l = [] # TSTriple()
        for index in range(n):
            _l.append(TSTriple())
            pad=self.platform.request("pads_x")
            self.specials += _l[index].get_tristate(pad)
            self.comb += _l[index].oe.eq(self.captouch.lines_oe[index])
            self.comb += _l[index].o.eq(self.captouch.lines_o[index])
            self.specials += MultiReg(_l[index].i, self.captouch.lines_i[index])
        _c = [] # TSTriple()
        for index in range(m):
            _c.append(TSTriple())
            pad=self.platform.request("pads_y")
            self.specials += _c[index].get_tristate(pad)
            self.comb += _c[index].oe.eq(self.captouch.cols_oe[index])
            self.comb += _c[index].o.eq(self.captouch.cols_o[index])
            self.specials += MultiReg(_c[index].i, self.captouch.cols_i[index])

        if not ( (self.cpu_type == "serv") | (self.cpu_type == None)):    # Add IRQs
            self.irq.add("captouch", use_loc_if_exists=True)



# Flash --------------------------------------------------------------------------------------------

def flash(bios_flash_offset, target="lattice_ice40up5k_evn"):
    from litex.build.dfu import DFUProg
    prog = IceStormProgrammer()
    bitstream  = open("build/"+target+"/gateware/"+target+".bin",  "rb")
    #bios       = open("build/"+target+"/software/bios/bios.bin", "rb")
    bios       = open("app.bin", "rb")
    image      = open("build/"+target+"/image.bin", "wb")
    # Copy bitstream at 0x00000000
    for i in range(0x00000000, 0x00020000):
        b = bitstream.read(1)
        if not b:
            image.write(0xff.to_bytes(1, "big"))
        else:
            image.write(b)
    # Copy bios at 0x00020000
    for i in range(0x00000000, 0x00010000):
        b = bios.read(1)
        if not b:
            image.write(0xff.to_bytes(1, "big"))
        else:
            image.write(b)
    bitstream.close()
    bios.close()
    image.close()
    print("Flashing bitstream (+bios)")
    prog.flash(0x0, "build/"+target+"/image.bin")

# Build --------------------------------------------------------------------------------------------

def main():
    from litex.build.parser import LiteXArgumentParser
    parser = LiteXArgumentParser(platform=lattice_ice40up5k_evn.Platform, description="LiteX SoC on Lattice iCE40UP5k EVN breakout board.")
    parser.add_target_argument("--sys-clk-freq",      default=12e6, type=float, help="System clock frequency.")
    parser.add_target_argument("--bios-flash-offset", default="0x20000",        help="BIOS offset in SPI Flash.")
    parser.add_target_argument("--flash",             action="store_true",      help="Flash Bitstream.")
    args = parser.parse_args()

    soc = BaseSoC(
        bios_flash_offset = int(args.bios_flash_offset, 0),
        sys_clk_freq      = args.sys_clk_freq,
        **parser.soc_argdict
    )
    builder = Builder(soc, **parser.builder_argdict)
    if args.build:
        builder.build(**parser.toolchain_argdict)

    if args.flash:
        flash(args.bios_flash_offset)

if __name__ == "__main__":
    main()
