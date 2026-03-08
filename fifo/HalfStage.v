// HalfStage: single-slot elastic buffer.
// Accepts new data only when the slot is empty (io_inp_ready = ~io_out_valid).
// No combinatorial path from io_out_ready to io_inp_ready.
// Port names follow Chisel-generated convention (clock/reset, io_*).
module HalfStage (
    input  wire        clock,
    input  wire        reset,
    output wire        io_inp_ready,
    input  wire        io_inp_valid,
    input  wire [15:0] io_inp_bits,
    input  wire        io_out_ready,
    output reg         io_out_valid,
    output reg  [15:0] io_out_bits
);
    assign io_inp_ready = ~io_out_valid;

    always @(posedge clock) begin
        if (reset) begin
            io_out_valid <= 1'b0;
        end else begin
            if (io_inp_valid && io_inp_ready) begin
                io_out_bits  <= io_inp_bits;
                io_out_valid <= 1'b1;
            end else if (io_out_valid && io_out_ready) begin
                io_out_valid <= 1'b0;
            end
        end
    end
endmodule
