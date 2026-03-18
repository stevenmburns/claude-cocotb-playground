// 8N1 UART Transmitter
// Parameter: CLKS_PER_BIT = clk_freq / baud_rate
//   Default: 50 MHz / 9600 = 5208
//
// All internal registers reset to 0 (FDRE-compatible).
// tx_line idles at 0 internally; the output is inverted by driving
// tx_line through a registered inverter so Yosys uses FDRE + LUT
// instead of an INV cell that may not be supported on all FPGAs.
module uart_tx #(
    parameter CLKS_PER_BIT = 5208
) (
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] tx_byte,
    input  wire       tx_start,  // 1-cycle pulse to begin transmission
    output reg        tx_line,   // idle high
    output reg        tx_busy
);

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state;
    reg [31:0] clk_cnt;
    reg [2:0]  bit_idx;
    reg [7:0]  shift_reg;

    // Internal inverted signal: 0 = line idle (high), 1 = line asserted (low)
    reg tx_active;

    // Registered inverter — avoids bare INV cell in netlist
    always @(posedge clk)
        tx_line <= ~tx_active;

    always @(posedge clk) begin
        if (rst) begin
            state     <= IDLE;
            clk_cnt   <= 0;
            bit_idx   <= 0;
            shift_reg <= 0;
            tx_active <= 1'b0;   // idle
            tx_busy   <= 1'b0;
        end else begin
            case (state)
                IDLE: begin
                    tx_active <= 1'b0;
                    clk_cnt   <= 0;
                    bit_idx   <= 0;
                    if (tx_start) begin
                        shift_reg <= tx_byte;
                        tx_busy   <= 1'b1;
                        state     <= START;
                    end else begin
                        tx_busy <= 1'b0;
                    end
                end

                // Send start bit (low on wire = active)
                START: begin
                    tx_active <= 1'b1;
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= 0;
                        state   <= DATA;
                    end else begin
                        clk_cnt <= clk_cnt + 1;
                    end
                end

                // Send 8 data bits, LSB first (invert: 1 on wire = 0 active)
                DATA: begin
                    tx_active <= ~shift_reg[bit_idx];
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= 0;
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

                // Send stop bit (high on wire = not active)
                STOP: begin
                    tx_active <= 1'b0;
                    if (clk_cnt == CLKS_PER_BIT - 1) begin
                        clk_cnt <= 0;
                        tx_busy <= 1'b0;
                        state   <= IDLE;
                    end else begin
                        clk_cnt <= clk_cnt + 1;
                    end
                end

                default: state <= IDLE;
            endcase
        end
    end

endmodule
