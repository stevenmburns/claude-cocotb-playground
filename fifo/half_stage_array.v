// N-stage chain of half_stage_wrap instances.
// HalfStage has no combinatorial path from out_r to inp_r, so Verilator
// can resolve mid_r without UNOPTFLAT. Unpacked arrays are used (same
// pattern as moore_stage_array.v).
module half_stage_array #(
    parameter N     = 4,
    parameter WIDTH = 16
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
    wire             mid_v [0:N];
    wire             mid_r [0:N];
    wire [WIDTH-1:0] mid_d [0:N];

    assign mid_v[0] = inp_v;
    assign mid_d[0] = inp_d;
    assign inp_r    = mid_r[0];
    assign out_v    = mid_v[N];
    assign out_d    = mid_d[N];
    assign mid_r[N] = out_r;

    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : stages
            half_stage_wrap #(.WIDTH(WIDTH)) u (
                .clk  (clk),
                .rst  (rst),
                .inp_r(mid_r[i]),
                .inp_v(mid_v[i]),
                .inp_d(mid_d[i]),
                .out_r(mid_r[i+1]),
                .out_v(mid_v[i+1]),
                .out_d(mid_d[i+1])
            );
        end
    endgenerate
endmodule
