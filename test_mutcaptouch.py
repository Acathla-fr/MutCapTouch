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
  #yield e.reg_ctrl.fields.start.eq(1)
  #while ( yield e.source.valid) == 0:
  #  yield
  #while ( yield e.lines_oe) == 1: # Wait for the start of a cycle
  #  yield
  delay = [0] * len(x_pads)     # Create an empty array of size "len(x_pads)"

  for n in range(10):       # n captures
      #yield e.trig.eq(1)    # Start a cycle
      #yield
      #yield e.trig.eq(0)
      yield from e.ctrl.write(1)
      yield

      for i in range(len(x_pads)):
          delay[i] = randrange(1,max_delay)  # Wait for a random number of cycles to simulate capture
                                    # Each entry of delay[] is the time to wait before a line to go up,
                                    # simulating a touch (or noise)
      for i in range(max_delay-1):
        for j in range(len(x_pads)):
            if( delay[j] == i ):
                yield e.lines_i[j].eq(1)    # Put line number j up
        yield                               # yield a clock tick even if no line changed state
      yield
      yield
      while ( yield e.loop_id == len(y_pads)-1 ):
          yield
      for i in range(len(x_pads)):
          #yield e.source.data
          yield from e.capdata.read()
      
      while ( yield e.ev.captouch_done.pending == 0):
          yield
      yield e.ev.captouch_done.clear.eq(1)
      yield e.ev.captouch_done.clear.eq(0)
      for i in range(len(x_pads)):
          yield e.lines_i[i].eq(0)  # Put back lines at 0, not sure it's usefull
      yield
      for i in range(42):
          yield

def test_captouch():
    dut=CapTouch(4,4)
    run_simulation(dut, testbench(dut), vcd_name="captouch.vcd")

if __name__ == "__main__":
    test_captouch()
