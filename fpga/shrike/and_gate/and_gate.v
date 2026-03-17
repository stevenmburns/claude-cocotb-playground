// and_gate.v — 2-input AND gate for logic analyser debug
//
// GPIO1 (PIN 14) & GPIO2 (PIN 15) → GPIO0 (PIN 13)
// Output registered on clk to satisfy ForgeFPGA place-and-route.
(* top *)
module and_gate (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *) input  wire in0,
    (* iopad_external_pin *) input  wire in1,
    (* iopad_external_pin *) output wire out0,
    (* iopad_external_pin *) output wire out0_oe
);

    assign clk_en  = 1'b1;
    assign out0_oe = 1'b1;

    reg out0_reg = 0;

    always @(posedge clk)
        out0_reg <= in0 & in1;

    assign out0 = out0_reg;

endmodule
