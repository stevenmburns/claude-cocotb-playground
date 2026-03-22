// Iterative GCD of two unsigned numbers (subtraction-based Euclidean)
// Parameterized width, default 24 bits.
module gcd #(
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

    reg [WIDTH-1:0] x, y;
    reg              running;

    always @(posedge clk) begin
        if (rst) begin
            x       <= 0;
            y       <= 0;
            result  <= 0;
            done    <= 0;
            running <= 0;
        end else if (start && !running) begin
            x       <= a;
            y       <= b;
            done    <= 0;
            running <= 1;
        end else if (running) begin
            if (x == 0) begin
                result  <= y;
                done    <= 1;
                running <= 0;
            end else if (y == 0) begin
                result  <= x;
                done    <= 1;
                running <= 0;
            end else if (x >= y) begin
                x <= x - y;
            end else begin
                y <= y - x;
            end
        end else begin
            done <= 0;
        end
    end

endmodule
