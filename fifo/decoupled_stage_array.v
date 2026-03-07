module decoupled_stage_array #(
    parameter N     = 4,
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
    // Packed arrays let Verilator track individual bit dependencies,
    // which is necessary for mid_r: decoupled_stage has a combinatorial
    // path inp_r <- out_r, so Verilator must see mid_r[i] <- mid_r[i+1]
    // as a directed chain, not a cycle.
    wire [N:0]             mid_v;
    // mid_r carries backpressure: inp_r[i] is combinatorially derived from
    // out_r[i] inside decoupled_stage, forming a directed chain
    // mid_r[N] -> mid_r[N-1] -> ... -> mid_r[0].  Verilator cannot prove
    // the chain is acyclic across generate instances, so suppress the
    // false-positive UNOPTFLAT warning.
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
            decoupled_stage #(.WIDTH(WIDTH)) u (
                .clk(clk), .rst(rst),
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
