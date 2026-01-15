#include <stdio.h>

#include <generated/csr.h>
#include <generated/mem.h>
#include <generated/soc.h>

#include <irq.h>
#include "hardmuca.h"
void hmc_isr(void) {
    printf("Interrupt works!\n");
}

void hmc_init(void);
void hmc_init(void) {
    captouch_ev_pending_write(captouch_ev_pending_read());
    captouch_ev_enable_write(0);

    printf("Initializing HMC interrupts...\n");

    if(irq_attach)
        irq_attach(CAPTOUCH_INTERRUPT, hmc_isr);
    irq_setmask(irq_getmask() | (1 << CAPTOUCH_INTERRUPT ));
}

void hardmuca(void);
void hardmuca(void) {
    printf("\n _   _               _ __  __        ____      \n");
    printf("| | | | __ _ _ __ __| |  \\/  |_   _ / ___|__ _ \n");
    printf("| |_| |/ _` | '__/ _` | |\\/| | | | | |   / _` |\n");
    printf("|  _  | (_| | | | (_| | |  | | |_| | |__| (_| |\n");
    printf("|_| |_|\\__,_|_|  \\__,_|_|  |_|\\__,_|\\____\\__,_|\n");


    printf("Data : 0x%08lx\n", captouch_capdata_read());

    captouch_ctrl_write(1);
    }
