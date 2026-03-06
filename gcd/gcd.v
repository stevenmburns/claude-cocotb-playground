// Iterative GCD of two 12-bit unsigned numbers (Euclidean algorithm)
module gcd (
    input  wire        clk,
    input  wire        rst,
    input  wire        start,
    input  wire [11:0] a,
    input  wire [11:0] b,
    output reg  [11:0] result,
    output reg         done
);

    reg [11:0] x, y;
    reg        running;

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
            if (y == 0) begin
                result  <= x;
                done    <= 1;
                running <= 0;
            end else begin
                x <= y;
                y <= x % y;
            end
        end else begin
            done <= 0;
        end
    end

endmodule
