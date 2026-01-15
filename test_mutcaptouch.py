#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from migen import *
from random import *
from mutcaptouch import CapTouch

x_pads = [1, 2, 3, 4]
y_pads = [5, 6, 7, 8]
clk = ClockSignal()
#rst = ResetSignal()

#e = CapTouch(len(x_pads), len(y_pads))
# x are lines, y are columns

max_delay = 16

def testbench(e):
  yield
  delay = [0] * len(x_pads)     # Create an empty array of size "len(x_pads)"

  for n in range(10):       # n captures
      yield from e.ctrl.write(1)
      yield

      for i in range(len(x_pads)):
          delay[i] = randrange(1,max_delay)  # Wait for a random number of cycles to simulate capture
                                    # Each entry of delay[] is the time to wait before a line to go up,
                                    # simulating a touch (or noise)
      for i in range(max_delay):
        for j in range(len(x_pads)):
            if( delay[j] == i ):
                yield e.lines_i[j].eq(1)    # Put line number j up
                print("Line ",j," up at tick ",i)
        yield                               # yield a clock tick even if no line changed state

      yield                         # Wait for 
      yield                         # FIFO to be filled
      while ( yield e.ev.captouch_done.status ) == 0  : # Wait for FIFO to be fully filled
        yield

      #yield from e.capdata.read()   # BUG?
      for i in range(len(x_pads)):
          #yield e.source.data
          data = yield from e.capdata.read()
          yield
          print("Data received: ", data, "index : ", i)
      
      while ( yield e.status.fields.fifo_empty == 0):
          yield
      for i in range(len(x_pads)):
          yield e.lines_i[i].eq(0)  # Put back lines at 0, needed for simulation
      yield
      for i in range(12):
          yield

def test_captouch():
    dut=CapTouch(4,4)
    run_simulation(dut, testbench(dut), vcd_name="captouch.vcd")

if __name__ == "__main__":
    test_captouch()
