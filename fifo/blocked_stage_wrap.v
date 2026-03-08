// Thin wrapper that adapts BlockedStage's Chisel-generated port names
// (clock/reset, io_inp_*, io_out_*) to the testbench convention
// (clk/rst, inp_v/inp_r/inp_d, out_v/out_r/out_d).
module blocked_stage_wrap #(parameter WIDTH = 16) (
    input  wire             clk,
    input  wire             rst,
    output wire             inp_r,
    input  wire             inp_v,
    input  wire [WIDTH-1:0] inp_d,
    input  wire             out_r,
    output wire             out_v,
    output wire [WIDTH-1:0] out_d
);
    BlockedStage u (
        .clock        (clk),
        .reset        (rst),
        .io_inp_ready (inp_r),
        .io_inp_valid (inp_v),
        .io_inp_bits  (inp_d),
        .io_out_ready (out_r),
        .io_out_valid (out_v),
        .io_out_bits  (out_d)
    );
endmodule
