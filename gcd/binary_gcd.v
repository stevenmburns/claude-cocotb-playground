// Iterative GCD of two unsigned numbers
// Algorithm: Knuth TAOCP §4.5.2 "unscaled" binary GCD (no final left-shift)
//   m = lowest bit shared by a and b; used as the unit of oddness throughout.
// Same external interface as gcd.v.  Parameterized width, default 24 bits.
module binary_gcd #(
    parameter WIDTH = 24
) (
    input  wire             clk,
    input  wire             rst,
    input  wire             start,
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    output reg  [WIDTH-1:0] result,
    output reg              done
);

    reg [WIDTH-1:0]   ax, bx;   // working copies
    reg [WIDTH-1:0]   m;        // lowest shared power-of-2 bit, fixed for life of computation
    reg signed [WIDTH:0] t;     // signed accumulator; WIDTH+1 bits to hold -(max WIDTH-bit value)
    reg               running;

    // Compute lowest set bit of (a|b): s & -s  (2's complement trick)
    wire [WIDTH-1:0] s_init = a | b;
    wire [WIDTH-1:0] m_init = s_init & (~s_init + 1'b1);

    // Absolute value of t (valid when t != 0)
    wire [WIDTH:0]   neg_t  = -t;
    wire [WIDTH-1:0] t_abs  = t[WIDTH] ? neg_t[WIDTH-1:0] : t[WIDTH-1:0];

    always @(posedge clk) begin
        if (rst) begin
            ax      <= 0;
            bx      <= 0;
            m       <= 0;
            t       <= 0;
            result  <= 0;
            done    <= 0;
            running <= 0;
        end else if (start && !running) begin
            if (a == 0) begin
                result  <= b;
                done    <= 1;
            end else if (b == 0) begin
                result  <= a;
                done    <= 1;
            end else begin
                ax      <= a;
                bx      <= b;
                m       <= m_init;
                // t = -b if (a & m_init) else a   (Python reference)
                t       <= |(a & m_init) ? -$signed({1'b0, b}) : $signed({1'b0, a});
                done    <= 0;
                running <= 1;
            end
        end else if (running) begin
            if (t == 0) begin
                // Loop done; a holds the GCD
                result  <= ax;
                done    <= 1;
                running <= 0;
            end else if (|(t & {1'b0, m})) begin
                // t is odd at scale m — update a or b, then t = a - b
                if (!t[WIDTH]) begin              // t > 0
                    ax <= t[WIDTH-1:0];
                    t  <= $signed({1'b0, t[WIDTH-1:0]}) - $signed({1'b0, bx});
                end else begin                    // t < 0
                    bx <= t_abs;
                    t  <= $signed({1'b0, ax}) - $signed({1'b0, t_abs});
                end
            end else begin
                // t is even at scale m — halve it (arithmetic right shift)
                t <= t >>> 1;
            end
        end else begin
            done <= 0;
        end
    end

endmodule
