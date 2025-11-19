#!/usr/bin/python3
# -*- coding: utf-8 -*-

from migen import *
from migen.fhdl.specials import Tristate

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import *
from litex.soc.cores.gpio import GPIOOut, GPIOTristate


class CapTouch(Module, AutoCSR):
    def __init__(self, num_lines, num_cols):
        dw=32
        fifo_depth=num_lines*num_cols
        self.source = stream.Endpoint([("data", dw)])
        self.capture_done = Signal(num_lines)
        self.i = Signal(max=num_lines)  # Counter to iterate through the measures at the end of a capture
        self.trig = Signal()    # Trigger the start of a capture
        # Counters
        counter = Signal(dw) # Time counter
        buf = Array(Signal(dw) for a in range(num_lines))

        # Lines
        self.lines_pads = Signal(num_lines)
        # Columns
        self.cols_pads = Signal(num_cols)
        # OutputEnable
        self.oe = Signal(num_cols)
        
        # Tristate (done in top file so it can be simulated here)
        self.lines_oe = Signal(num_lines)
        self.lines_o = Signal(num_lines)
        self.lines_i = Signal(num_lines)
        self.cols_oe = Signal(num_cols)
        self.cols_o = Signal(num_cols)
        self.cols_i = Signal(num_cols)

        # CSR
        fields = [
          CSRField("start", reset=0, size=1, description="Start the measurement"),
          CSRField("values", reset=0, size=31, description="Measurements"),
        ]

        self.reg_ctrl = CSRStorage(32, fields=fields)

        ###

        # FIFO module -> CPU

        self.fifo = fifo = stream.SyncFIFO([("data", dw)], fifo_depth, buffered=True)
        self.submodules += fifo

        self.submodules.fsm = FSM(reset_state="START")

        self.sync += [
                If(counter < (2**dw-1),
                   counter.eq(counter+1))]
        #for a in range(num_lines):
        #    self.sync += If(((self.lines_i[a] == 1) & self.fsm.ongoing("RUN") & self.capture_done[a] == 0),
        #       self.capture_done[a].eq(1),
        #       buf[a].eq(counter), 
        #    )


        self.fsm.act("START",
            # All lines set to zero and columns to one
            self.lines_oe.eq(2**num_lines - 1),
            self.lines_o.eq(0),
            self.cols_oe.eq(2**num_cols -1),
            self.cols_o.eq(2**num_cols -1),
            #self.capture_done.eq(0),
            NextValue(counter, 0),
            #counter.eq(0),
            #i.eq(0),
            If(self.trig == 1, NextState("RUN"))
        )

        self.fsm.act("RUN",
            # Switch each line to input/read mode
            self.lines_oe.eq(0),
            #If((self.lines_i[0] == 1) & (self.capture_done[0] == 0),
            #   NextValue(buf[0], counter),
            #   NextValue(self.capture_done[0], 1)),
            # Copy the value of counter in the buffer of each line reaching 1
            If( self.lines_i >= (2**num_lines-1), #| counter == (2**dw-1), # Every line is up or timeout
                NextState("SAVE")
            )
        )
        # Trick to add that same block for each line in the FSM
        for a in range(num_lines):
            self.fsm.act("RUN",
               If((self.lines_i[a] == 1) & (self.capture_done[a] == 0),
               NextValue(buf[a], counter),
               NextValue(self.capture_done[a], 1))
            )

        self.fsm.act("SAVE",
            # "Serialization" (fill the FIFO)
            NextValue(self.source.data, buf[self.i]),
            NextValue(self.source.valid, 1),
            If(self.i == num_lines-1,
               NextState("START"),
               NextValue(self.i, 0),
               NextValue(self.capture_done, 0)
            ).Else(
                NextValue(self.i, self.i+1)
            )

        )

