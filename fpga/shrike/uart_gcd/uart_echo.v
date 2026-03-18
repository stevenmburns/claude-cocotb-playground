// uart_echo.v — receive one byte, send it back immediately
//
// Minimal test to verify UART RX and TX paths on hardware.
(* top *)
module uart_echo #(
    parameter CLKS_PER_BIT = 434
) (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *)                 input  wire uart_rx,
    (* iopad_external_pin *)                 output wire uart_tx,
    (* iopad_external_pin *)                 output wire uart_tx_oe
);

    assign clk_en     = 1'b1;
    assign uart_tx_oe = 1'b1;

    // Power-on reset (16 cycles)
    reg [3:0] rst_cnt = 4'hF;
    reg       rst     = 1'b1;
    always @(posedge clk) begin
        if (rst_cnt != 0) begin
            rst_cnt <= rst_cnt - 1;
            rst     <= 1'b1;
        end else begin
            rst <= 1'b0;
        end
    end

    // UART RX
    wire [7:0] rx_byte;
    wire       rx_valid;

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (
        .clk     (clk),
        .rst     (rst),
        .rx_line (uart_rx),
        .rx_byte (rx_byte),
        .rx_valid(rx_valid)
    );

    // UART TX
    reg  [7:0] tx_byte;
    reg        tx_start;
    wire       tx_busy;

    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (
        .clk     (clk),
        .rst     (rst),
        .tx_byte (tx_byte),
        .tx_start(tx_start),
        .tx_line (uart_tx),
        .tx_busy (tx_busy)
    );

    // Echo: when a byte arrives and TX is idle, send it back
    always @(posedge clk) begin
        tx_start <= 1'b0;
        if (!rst && rx_valid && !tx_busy) begin
            tx_byte  <= rx_byte;
            tx_start <= 1'b1;
        end
    end

endmodule
