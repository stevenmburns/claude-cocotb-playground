// static_pins.v — drive two outputs to constant levels for logic analyser debug
//
// out0 = 0, out1 = 1 (active high output enables)
// Map out0 → FPGA_IO0 and out1 → FPGA_IO1 in the synthesis GUI.

module static_pins (
    output wire out0,
    output wire out0_oe,
    output wire out1,
    output wire out1_oe
);

    assign out0    = 1'b0;
    assign out0_oe = 1'b1;
    assign out1    = 1'b1;
    assign out1_oe = 1'b1;

endmodule
