// 8N1 UART Receiver
// Parameter: CLKS_PER_BIT = clk_freq / baud_rate
//   Default: 50 MHz / 9600 = 5208
module uart_rx #(
    parameter CLKS_PER_BIT = 5208
) (
    input  wire       clk,
    input  wire       rst,
    input  wire       rx_line,
    output reg  [7:0] rx_byte,
    output reg        rx_valid   // 1-cycle pulse when rx_byte is valid
);

    // State encoding
    localparam IDLE    = 2'd0;
    localparam START   = 2'd1;
    localparam DATA    = 2'd2;
    localparam STOP    = 2'd3;

    reg [1:0]  state;
    reg [12:0] clk_cnt;   // counts up to CLKS_PER_BIT-1
    reg [2:0]  bit_idx;   // 0..7
    reg [7:0]  shift_reg;

    // Double-flop the rx line to avoid metastability
    reg rx_sync0, rx_sync1;
    always @(posedge clk) begin
        rx_sync0 <= rx_line;
        rx_sync1 <= rx_sync0;
    end

    always @(posedge clk) begin
        if (rst) begin
            state    <= IDLE;
            clk_cnt  <= 0;
            bit_idx  <= 0;
            shift_reg<= 0;
            rx_byte  <= 0;
            rx_valid <= 0;
        end else begin
            rx_valid <= 0;   // default: pulse low

            case (state)
                IDLE: begin
                    clk_cnt <= 0;
                    bit_idx <= 0;
                    if (rx_sync1 == 1'b0)   // falling edge = start bit
                        state <= START;
                end

                // Wait until middle of start bit to confirm it is still low
                START: begin
                    if (clk_cnt == (CLKS_PER_BIT / 2 - 1)) begin
                        if (rx_sync1 == 1'b0) begin
                            clk_cnt <= 0;
                            state   <= DATA;
                        end else begin
                            state   <= IDLE;  // glitch
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 1;
                    end
                end

                // Sample each data bit at the centre of its bit period
                DATA: begin
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt              <= 0;
                        shift_reg[bit_idx]   <= rx_sync1;
                        if (bit_idx == 3'd7) begin
                            bit_idx <= 0;
                            state   <= STOP;
                        end else begin
                            bit_idx <= bit_idx + 1;
                        end
                    end else begin
                        clk_cnt <= clk_cnt + 1;
                    end
                end

                // Wait through the stop bit, then publish the byte
                STOP: begin
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        rx_valid <= 1;
                        rx_byte  <= shift_reg;
                        clk_cnt  <= 0;
                        state    <= IDLE;
                    end else begin
                        clk_cnt <= clk_cnt + 1;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
