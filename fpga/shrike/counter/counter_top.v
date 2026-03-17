// counter_top.v — 2-output divider with RP2040 enable input
//
// 50 MHz clock → prescaler → 2 toggle outputs (when enabled)
//   out0: 100.0 KHz  (GPIO0 / PIN 13 / FPGA_IO0)
//   out1:  50.0 KHz  (GPIO1 / PIN 14 / FPGA_IO1)
//   enable: RP2040 GPIO5 (RP_IO5) → FPGA PIN 15 (GPIO2) via jumper wire
//
// When enable is low, counter holds and outputs freeze.
(* top *)
module counter_top (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *) input  wire enable,
    (* iopad_external_pin *) output wire out0,
    (* iopad_external_pin *) output wire out0_oe,
    (* iopad_external_pin *) output wire out1,
    (* iopad_external_pin *) output wire out1_oe
);

    parameter PRESCALE = 250;  // 50 MHz / 250 = 200 KHz toggle rate → 100 KHz square wave

    // Power-on reset (16 cycles)
    reg [3:0] rst_cnt = 0;
    wire rst = ~rst_cnt[3];
    always @(posedge clk)
        if (rst) rst_cnt <= rst_cnt + 1;

    // Clock enable — must be high for the FPGA oscillator to run
    assign clk_en = 1'b1;

    // Output enables — active high
    assign out0_oe = 1'b1;
    assign out1_oe = 1'b1;

    // Synchronise enable input to clk domain
    reg enable_sync0 = 0, enable_sync1 = 0;
    always @(posedge clk) begin
        enable_sync0 <= enable;
        enable_sync1 <= enable_sync0;
    end

    // Prescaler: counts 0..PRESCALE-1, pulses tick once per period
    localparam W = $clog2(PRESCALE);
    reg [W-1:0] pre_cnt = 0;
    wire tick = (pre_cnt == PRESCALE - 1);

    always @(posedge clk) begin
        if (rst)
            pre_cnt <= 0;
        else if (enable_sync1) begin
            if (tick)
                pre_cnt <= 0;
            else
                pre_cnt <= pre_cnt + 1;
        end
    end

    // 2-bit toggle counter
    reg [1:0] toggle = 0;

    always @(posedge clk) begin
        if (rst)
            toggle <= 0;
        else if (enable_sync1 && tick)
            toggle <= toggle + 1;
    end

    assign out0 = toggle[0];  // 100.0 KHz
    assign out1 = toggle[1];  //  50.0 KHz

endmodule
