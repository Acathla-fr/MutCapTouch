#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from migen import *
import random
from mutcaptouch import CapTouch

num_x_pads=4
num_y_pads=4

clk = ClockSignal()
#rst = ResetSignal()

# x are lines, y are columns

def touch_generator(dut, datas):
    #while( (dut.batch-1)*num_x_pads < len(datas) ):
    while( (dut.batch_r-1)*num_x_pads < len(datas) ):
        print("Batch : ", dut.batch_r)
        prng = random.Random(42)
        while prng.randrange(4):
            yield
        while ( yield dut.ctrl.storage == 0 ) :
            yield   # wait for the capture to start
        if( dut.batch_r*num_x_pads >= len(datas) ):
            exit()

        for i in range(dut.max_delay):
            for j in range(num_x_pads):
                if( datas[j+num_x_pads*dut.batch_r] == i ):
                    yield dut.lines_i[j].eq(1)      # Put line number j up
                    print("Line ",j," up at tick ",i)
            yield                                   # yield a clock tick even if no line changed state
        for i in range(num_x_pads):
            yield dut.lines_i[i].eq(0)      # Put all lines down (needed for simulation only)
        dut.batch_r+=1

def touch_checker(dut, datas):
    while(dut.batch_w*num_x_pads < len(datas)):
        prng = random.Random(42)
        index = 0
        #while prng.randrange(4):
        #    yield
        yield from dut.ctrl.write(1)    # trigger a capture
        yield from dut.ctrl.write(0)    # trigger a capture

        #while ( yield dut.ev.captouch_done.trigger == 0 ) : # Wait for FIFO to be filled with data
        while ( yield  dut.fifo.sink.ready == 1 ) :  # Wait for FIFO to be full
            yield

        data = yield from dut.capdata.read()
        while ( yield dut.fifo.source.valid == 1 ) : # Read FIFO until it's empty 
                                                     # (should be empty after the exact number of values read)
            data = yield from dut.capdata.read()
            print("Data: ", data, "index : ", index)
            if data != datas[index+dut.batch_w*num_x_pads]:
                dut.errors += 1
                print("Error : expected : ",datas[index+dut.batch_w*num_x_pads], "; received : ", data )
            index+=1

        yield dut.ev.captouch_done.clear.eq(1)
        dut.batch_w+=1

def test_captouch():
    dut=CapTouch(4,4)
    dut.errors=0
    min_delay = 6
    dut.max_delay = 32
    prng = random.Random(17)
    dut.batch_r=dut.batch_w=0
    datas=[]
    for k in range(4):
        datas += [prng.randrange(min_delay,dut.max_delay) for i in range(num_x_pads)]    # Generate the fake delays we want to measure
    print(datas)
    generators = [
        touch_generator(dut, datas),
        touch_checker(dut, datas)
    ]
    run_simulation(dut, generators, vcd_name="captouch.vcd")
    if dut.errors != 0 :
        print("Number of errors : ", dut.errors)

if __name__ == "__main__":
    test_captouch()
