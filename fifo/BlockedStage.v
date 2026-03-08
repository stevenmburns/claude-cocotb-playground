// BlockedStage: registered pipeline stage with pass-through backpressure.
// io_inp_ready is combinatorially equal to io_out_ready (backpressure passes
// straight through). Data advances only when the downstream is ready.
// Port names follow Chisel-generated convention (clock/reset, io_*).
module BlockedStage (
    input  wire        clock,
    input  wire        reset,
    output wire        io_inp_ready,
    input  wire        io_inp_valid,
    input  wire [15:0] io_inp_bits,
    input  wire        io_out_ready,
    output reg         io_out_valid,
    output reg  [15:0] io_out_bits
);
    assign io_inp_ready = io_out_ready;

    always @(posedge clock) begin
        if (reset) begin
            io_out_valid <= 1'b0;
        end else if (io_out_ready) begin
            io_out_valid <= io_inp_valid;
            if (io_inp_valid)
                io_out_bits <= io_inp_bits;
        end
    end
endmodule
