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

from platforms import olimex_ice40hx8k_evn
from litex.build.lattice.programmer import IceStormProgrammer

from litex.soc.cores.ram import Up5kSPRAM
from litex.soc.cores.clock import iCE40PLL
from litex.soc.integration.soc_core import *
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.builder import *
from litex.soc.cores.led import LedChaser

from litex.build.generic_platform import *

from litex.soc.interconnect import wishbone

# CRG ----------------------------------------------------------------------------------------------

class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq):
        self.rst    = Signal()
        self.cd_sys = ClockDomain()
        self.cd_sys100 = ClockDomain(reset_less=True)
        self.cd_por = ClockDomain(reset_less=True)

        # # #

        # Clk/Rst
        clk100 = platform.request("clk100")
        self.cd_sys100.clk.eq(clk100)
        rst_n = platform.request("user_btn_n")
        platform.add_period_constraint(clk100, 10)

        # Power On Reset
        por_count = Signal(16, reset=2**16-1)
        por_done  = Signal()
        self.comb += self.cd_por.clk.eq(ClockSignal())
        self.comb += por_done.eq(por_count == 0)
        self.sync.por += If(~por_done, por_count.eq(por_count - 1))

        # PLL
        self.pll = pll = iCE40PLL(primitive="SB_PLL40_CORE")
        self.comb += pll.reset.eq(~rst_n)
        pll.register_clkin(clk100, 100e6)
        pll.create_clkout(self.cd_sys, sys_clk_freq, with_reset=False)

        # Sys Clk
        self.specials += AsyncResetSynchronizer(self.cd_sys, ~por_done | ~pll.locked)
        platform.add_period_constraint(self.cd_sys.clk, 1e9/sys_clk_freq)


# AsyncSRAM ------------------------------------------------------------------------------------------

class AsyncSRAM(LiteXModule):
    def __init__(self, platform, size):
        addr_width = 18
        data_width = 16
        self.bus = wishbone.Interface(data_width=data_width,adr_width=addr_width)
        realsram = platform.request("sram")
        addr = realsram.addr
        data = realsram.data
        wen = realsram.we
        cen = realsram.cs
        oe = realsram.oe
        ########################
        tristate_data = TSTriple(data_width)
        self.specials += tristate_data.get_tristate(data)
        ########################
        chip_ena = self.bus.cyc & self.bus.stb & self.bus.sel[0]
        write_ena = (chip_ena & self.bus.we)
        ########################
        # external write enable, 
        # external chip enable, 
        # internal tristate write enable
        ########################
        self.comb += [
            cen.eq(~chip_ena),
            wen.eq(~write_ena),
            tristate_data.oe.eq(write_ena),
            oe.eq(tristate_data.oe),
        ]
        ########################
        # address and data
        ########################
        self.comb += [
            addr.eq(self.bus.adr[:addr_width]),
            self.bus.dat_r.eq(tristate_data.i[:data_width]),
            tristate_data.o.eq(self.bus.dat_w[:data_width])
        ]
        ########################
        # generate ack
        ########################
        self.sync += [
            self.bus.ack.eq(self.bus.cyc & self.bus.stb & ~self.bus.ack),
        ]
        ########################

def addAsyncSram(soc, platform, name, origin, size):
    ram_bus = wishbone.Interface(data_width=soc.bus.data_width)
    ram     = AsyncSRAM(platform,size)
    soc.bus.add_slave(name, ram.bus, SoCRegion(origin=origin, size=size, mode="rw", linker=False))
    soc.check_if_exists(name)
    soc.logger.info("SRAM {} {} {}.".format(
        colorer(name),
        colorer("added", color="green"),
        soc.bus.regions[name]))
    setattr(soc.submodules, name, ram)

# BaseSoC ------------------------------------------------------------------------------------------

class BaseSoC(SoCCore):
    def __init__(self, bios_flash_offset, sys_clk_freq=100e6,
        with_led_chaser = True,
        **kwargs):
        platform = olimex_ice40hx8k_evn.Platform()

        # CRG --------------------------------------------------------------------------------------
        self.crg = _CRG(platform, sys_clk_freq)

        # SoCCore ----------------------------------------------------------------------------------
        # Disable Integrated ROM/SRAM since too large for iCE40 and UP5K has specific SPRAM.
        kwargs["integrated_sram_size"] = 8192
        kwargs["integrated_rom_size"]  = 0
        SoCCore.__init__(self, platform, sys_clk_freq, ident="LiteX SoC on Olimex iCE40HX8K EVN breakout board", **kwargs)
       # CPU --------------------------------------------------------------------------------------

        if (self.cpu_type == "vexriscv") and (self.cpu_variant == "lite"):
            self.cpu.use_external_variant("rtl/VexRiscv_Lite.v")

        # Async RAM --------------------------------------------------------------------------------
        #addAsyncSram(self,platform,"sram", 0x40000000, 512 * KILOBYTE)

        # SPI Flash --------------------------------------------------------------------------------
        # 4x mode is not possible on this board since WP and HOLD pins are not connected to the FPGA
        from litespi.modules import W25Q16JV
        from litespi.opcodes import SpiNorFlashOpCodes as Codes
        self.add_spi_flash(mode="1x", module=W25Q16JV(Codes.READ_1_1_1))

        # Add ROM linker region --------------------------------------------------------------------
        self.bus.add_region("rom", SoCRegion(
            origin = self.bus.regions["spiflash"].origin + bios_flash_offset,
            size   = 64 * KILOBYTE,
            linker = True)
        )
        self.cpu.set_reset_address(self.bus.regions["rom"].origin)

        # Leds -------------------------------------------------------------------------------------
        with_led_chaser=True
        if with_led_chaser:
            self.leds = LedChaser(
                pads         = platform.request_all("user_led"),
                sys_clk_freq = sys_clk_freq)

        # Add a UARTBone bridge --------------------------------------------------------------------
        debug_uart = False
        if debug_uart:
            self.add_uartbone()

# Flash --------------------------------------------------------------------------------------------

def flash(bios_flash_offset, target="olimex_ice40hx8k_evn"):
    from litex.build.dfu import DFUProg
    prog = IceStormProgrammer()
    bitstream  = open("build/"+target+"/gateware/"+target+".bin",  "rb")
    bios       = open("build/"+target+"/software/bios/bios.bin", "rb")
    image      = open("build/"+target+"/image.bin", "wb")
    # Copy bitstream at 0x00000000
    for i in range(0x00000000, 0x00030000):
        b = bitstream.read(1)
        if not b:
            image.write(0xff.to_bytes(1, "big"))
        else:
            image.write(b)
    # Copy bios at 0x00030000
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
    parser = LiteXArgumentParser(platform=olimex_ice40hx8k_evn.Platform, description="LiteX SoC on Lattice Olimex iCE40hx8k EVN breakout board.")
    parser.add_target_argument("--sys-clk-freq",      default=25e6, type=float, help="System clock frequency.")
    parser.add_target_argument("--bios-flash-offset", default="0x30000",        help="BIOS offset in SPI Flash.")
    parser.add_target_argument("--flash",             action="store_true",      help="Flash Bitstream.")
    parser.add_target_argument("--with-sram",         action="store_true",      help="Add external 512KB SRAM")
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
