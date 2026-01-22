#include <stdio.h>

#include <generated/csr.h>
#include <generated/mem.h>
#include <generated/soc.h>

#include <irq.h>
#include "hardmuca.h"

static volatile unsigned int int_counter = 0;

void hmc_isr(void) {
    printf("Interrupt works!\n");
    int_counter++;
    //captouch_ev_pending_write(CAPTOUCH_INTERRUPT);  // Clear interrupt?
}

void hmc_init(void);
void hmc_init(void) {
    captouch_ev_pending_write(captouch_ev_pending_read());
    captouch_ev_enable_write(CAPTOUCH_INTERRUPT);

    printf("Initializing HMC interrupts...\n");

    if(irq_attach) {
        printf("IRQ number %d attributed to capacitive sensor\n", CAPTOUCH_INTERRUPT);
        irq_attach(CAPTOUCH_INTERRUPT, hmc_isr);
    }   
    else
        printf("No IRQ!\n");
    irq_setmask(irq_getmask() | (1 << CAPTOUCH_INTERRUPT ));
}
void dump_registers(void);
void dump_registers(void) {
    printf("Data : 0x%08lx\n", captouch_capdata_read());
    printf("Status : 0x%08lx\n", captouch_status_read());
    printf("Ctrl : 0x%08lx\n", captouch_ctrl_read());
    printf("ev_status : 0x%08lx\n", captouch_ev_status_read());
    printf("ev_pending: 0x%08lx\n", captouch_ev_pending_read());
    printf("ev_enable: 0x%08lx\n", captouch_ev_enable_read());
    printf("ctrl_scratch: 0x%08lx\n", ctrl_scratch_read());
    printf("ctrl_bus_errors: 0x%08lx\n", ctrl_bus_errors_read());
    printf("Interrupts counter : %d\n", int_counter);
}
void read_capture(void);
void read_capture(void){
    printf("Interrupts counter : %d\n", int_counter);
    captouch_ctrl_write(1);
    while(captouch_ev_status_read() == 0);  // Wait for event
    while((captouch_status_read() & (1<<CSR_CAPTOUCH_STATUS_FIFO_EMPTY_OFFSET)) == 0 ) { // While FIFO not empty
        printf("Data : 0x%08lx\n", captouch_capdata_read());
    }
}

void hardmuca(void);
void hardmuca(void) {
    printf("\n _   _               _ __  __        ____      \n");
    printf("| | | | __ _ _ __ __| |  \\/  |_   _ / ___|__ _ \n");
    printf("| |_| |/ _` | '__/ _` | |\\/| | | | | |   / _` |\n");
    printf("|  _  | (_| | | | (_| | |  | | |_| | |__| (_| |\n");
    printf("|_| |_|\\__,_|_|  \\__,_|_|  |_|\\__,_|\\____\\__,_|\n");

//    dump_registers();
    read_capture();
}
