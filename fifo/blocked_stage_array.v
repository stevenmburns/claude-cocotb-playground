// N-stage chain of blocked_stage_wrap instances.
// BlockedStage has inp_r = out_r (combinatorial), creating a chain
// mid_r[N] -> mid_r[N-1] -> ... -> mid_r[0]. Verilator cannot prove
// the chain is acyclic across generate instances, so we suppress the
// false-positive UNOPTFLAT warning. Packed arrays are used for mid_r
// (same pattern as decoupled_stage_array.v).
module blocked_stage_array #(
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
    wire [N:0]             mid_v;
    /* verilator lint_off UNOPTFLAT */
    wire [N:0]             mid_r;
    /* verilator lint_on UNOPTFLAT */
    wire [WIDTH*(N+1)-1:0] mid_d;

    assign mid_v[0]         = inp_v;
    assign mid_d[WIDTH-1:0] = inp_d;
    assign inp_r            = mid_r[0];
    assign out_v            = mid_v[N];
    assign out_d            = mid_d[N*WIDTH +: WIDTH];
    assign mid_r[N]         = out_r;

    genvar i;
    generate
        for (i = 0; i < N; i = i + 1) begin : stages
            blocked_stage_wrap #(.WIDTH(WIDTH)) u (
                .clk  (clk),
                .rst  (rst),
                .inp_r(mid_r[i]),
                .inp_v(mid_v[i]),
                .inp_d(mid_d[i*WIDTH +: WIDTH]),
                .out_r(mid_r[i+1]),
                .out_v(mid_v[i+1]),
                .out_d(mid_d[(i+1)*WIDTH +: WIDTH])
            );
        end
    endgenerate
endmodule
