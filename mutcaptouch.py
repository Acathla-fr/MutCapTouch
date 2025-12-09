#!/usr/bin/python3
# -*- coding: utf-8 -*-

from migen import *
from migen.fhdl.specials import Tristate
from migen.genlib.fifo import SyncFIFO

from litex.soc.interconnect.csr import *
from litex.soc.interconnect import *
from litex.soc.cores.gpio import GPIOOut, GPIOTristate


class CapTouch(Module, AutoCSR):
    def __init__(self, num_lines, num_cols):
        dw=32   # To be adjusted to the max time a capture can last
        timeout=12**6   # Timeout (number of cycles to wait max, dependent on freq)
        fifo_depth=num_lines*num_cols
        #self.source = stream.Endpoint([("data", dw)])
        self.loop_id = Signal(max=num_lines)  # Counter to iterate through the measures at the end of a capture
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
          CSRField("start", size=1, pulse=True, description="Start the measurement"),
          CSRField("fifo_empty", size=1, description="FIFO empty if 1"),
          CSRField("fifo_full", size=1, description="FIFO full if 1"),
        ]

        self.capdata = CSR(dw)

        #self.ctrl = CSRStorage(32, fields=fields)
        self._fifo  = CSRStatus()
        self.ctrl = CSRStorage(1, reset_less=True,
            fields=[CSRField("start", size=1, pulse=True, description="*Field*: bit", values=[
                ("1", "ENABLED", "Starts the capture")]),
            ])

        self.fifo = fifo = stream.SyncFIFO([("data", dw)], fifo_depth, buffered=True)
        self.submodules += fifo

        ###

        # FIFO module -> CPU

        self.submodules.fsm = FSM(reset_state="IDLE")

        self.comb += [
            # FIFO --> CSR.
            self.capdata.w.eq(fifo.source.data),
            #fifo.source.ready.eq(self.ev.data.clear),
            # Status.
            self._fifo.status.eq(~fifo.source.valid),
            #self.ctrl.fields.fifo_empty.eq(~fifo.source.valid),
            #self.ctrl.fields.fifo_full.eq(~fifo.sink.ready),
        ]

#        self.sync += [
#                If(counter < (2**dw-1),
#                   counter.eq(counter+1)) ]

        self.fsm.act("IDLE",
            If(self.ctrl.fields.start == True,
                NextState("RUN")),
            # All lines set to zero and columns to one
            self.lines_oe.eq(2**num_lines - 1),
            self.lines_o.eq(0),
            self.cols_oe.eq(2**num_cols - 1),
            self.cols_o.eq(2**num_cols - 1),
            NextValue(counter, 0),
            NextValue(self.ctrl.fields.start, 0),  # Reset the register because the pulse parameter does not do what you think it should do
        )

        self.fsm.act("RUN",
            # Switch each line to input/read mode
            self.lines_oe.eq(0),
            If( self.lines_i >= (2**num_lines-1),
                NextState("SAVE")
            ),
            If( counter == timeout, #(2**dw-1),   # Timeout
                NextState("SAVE")
            ).Else(
                NextValue(counter, counter + 1),
            )
        )

        # Trick to add that same block for each line in the FSM
        for a in range(num_lines):
            self.fsm.act("RUN",
                If((self.lines_i[a] == 1) & ( buf[a] == 0 ),
                   NextValue(buf[a], counter),
                   )
                )

        self.fsm.act("SAVE",
            # "Serialization" (fill the FIFO)
            #NextValue(fifo.sink.data, 0xDEADBEEF),
            NextValue(fifo.sink.data, buf[self.loop_id]),
            NextValue(self.loop_id, self.loop_id+1),
            NextValue(fifo.sink.valid, 1),
            If(self.loop_id == num_lines-1,
                NextState("IDLE"),
                NextValue(self.loop_id, 0),
                #NextValue(self.ctrl.fields.start, 0),  # Reset the register because the pulse parameter does not do what you think it should do
            ).Else(
                NextState("SAVE_LOOP")
            )
        )

        self.fsm.act("SAVE_LOOP",
            NextValue(fifo.sink.valid, 0),
            NextState("SAVE"),
        )
