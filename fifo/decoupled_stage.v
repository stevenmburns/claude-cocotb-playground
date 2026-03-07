module decoupled_stage #(
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,
    output wire             inp_r,
    input  wire             inp_v,
    input  wire [WIDTH-1:0] inp_d,
    input  wire             out_r,
    output wire             out_v,
    output wire [WIDTH-1:0] out_d
);
    reg             out_valid;
    reg [WIDTH-1:0] out_bits;

    assign inp_r = out_r | ~out_valid;
    assign out_v = out_valid;
    assign out_d = out_bits;

    always @(posedge clk) begin
        if (rst)
            out_valid <= 1'b0;
        else
            out_valid <= inp_v | ~inp_r;
        if (inp_r)
            out_bits <= inp_d;
    end
endmodule
