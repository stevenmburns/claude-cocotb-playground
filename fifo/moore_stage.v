// Moore pipeline stage (2-slot elastic buffer).
// Both inp_r and out_v are registered (no combinatorial path from out_r to inp_r).
// Cleaned up from Chisel-generated MooreStage.v.
module moore_stage #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,
    output reg              inp_r,
    input  wire             inp_v,
    input  wire [WIDTH-1:0] inp_d,
    input  wire             out_r,
    output reg              out_v,
    output reg  [WIDTH-1:0] out_d
);
    reg [WIDTH-1:0] data_aux;

    always @(posedge clk) begin
        if (rst) begin
            inp_r <= 1'b1;
            out_v <= 1'b0;
        end else if (inp_r && !out_v) begin
            // EMPTY: always ready; latch input when valid
            if (inp_v) begin
                out_d <= inp_d;
                out_v <= 1'b1;
            end
            // inp_r stays 1
        end else if (inp_r && out_v) begin
            // ONE ITEM
            if (!inp_v && out_r) begin
                out_v <= 1'b0;          // drain only -> EMPTY
            end else if (inp_v && out_r) begin
                out_d <= inp_d;         // pass-through -> ONE
            end else if (inp_v && !out_r) begin
                data_aux <= inp_d;      // stash overflow -> FULL
                inp_r    <= 1'b0;
            end
            // !inp_v && !out_r: hold -> ONE
        end else begin
            // FULL (!inp_r && out_v)
            if (out_r) begin
                out_d <= data_aux;      // drain aux -> ONE
                inp_r <= 1'b1;
            end
        end
    end
endmodule
