module fifo #(
    parameter DEPTH = 16,
    parameter WIDTH = 8
) (
    input  wire             clk,
    input  wire             rst,

    // Input side (producer)
    input  wire             inp_v,
    input  wire [WIDTH-1:0] inp_d,
    output wire             inp_r,

    // Output side (consumer)
    input  wire             out_r,
    output wire [WIDTH-1:0] out_d,
    output wire             out_v
);

    localparam ADDR_W = $clog2(DEPTH);
    /* verilator lint_off WIDTHTRUNC */
    localparam [ADDR_W-1:0] LAST = DEPTH - 1;
    /* verilator lint_on WIDTHTRUNC */

    reg [WIDTH-1:0]  mem  [0:DEPTH-1];
    reg [ADDR_W-1:0] head;   // read pointer
    reg [ADDR_W-1:0] tail;   // write pointer
    reg [ADDR_W:0]   count;

    assign inp_r = (count != DEPTH);
    assign out_v = (count != 0);
    assign out_d = mem[head];

    always @(posedge clk) begin
        if (rst) begin
            head  <= 0;
            tail  <= 0;
            count <= 0;
        end else begin
            if (inp_v && inp_r) begin
                mem[tail] <= inp_d;
                tail      <= (tail == LAST) ? 0 : tail + 1;
            end
            if (out_r && out_v) begin
                head <= (head == LAST) ? 0 : head + 1;
            end
            // Update count
            case ({inp_v && inp_r, out_r && out_v})
                2'b10: count <= count + 1;
                2'b01: count <= count - 1;
                default: count <= count;
            endcase
        end
    end

endmodule
