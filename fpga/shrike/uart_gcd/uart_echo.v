// uart_echo.v — receive one byte, send it back immediately
//
// Minimal test to verify UART RX and TX paths on hardware.
// External reset via RP2040 GPIO2 → FPGA GPIO3 (PIN 16) PCB trace.
// Heartbeat on GPIO0 (FPGA_IO0), UART on GPIO1 (FPGA_IO1).
(* top *)
module uart_echo #(
    parameter CLKS_PER_BIT = 434
) (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *)                 input  wire ext_rst,
    (* iopad_external_pin *)                 input  wire uart_rx,
    (* iopad_external_pin *)                 output wire debug,
    (* iopad_external_pin *)                 output wire debug_oe,
    (* iopad_external_pin *)                 output wire uart_tx,
    (* iopad_external_pin *)                 output wire uart_tx_oe
);

    assign clk_en     = 1'b1;
    assign uart_tx_oe = 1'b1;
    assign debug_oe   = 1'b1;

    // Synchronise external reset to clk domain
    reg rst_sync0 = 0, rst_sync1 = 0;
    always @(posedge clk) begin
        rst_sync0 <= ext_rst;
        rst_sync1 <= rst_sync0;
    end
    wire rst = rst_sync1;

    // Heartbeat on debug pin
    reg [19:0] hb_cnt = 0;
    always @(posedge clk)
        hb_cnt <= hb_cnt + 1;
    assign debug = hb_cnt[18];

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
    reg  [7:0] tx_byte = 0;
    reg        tx_start = 0;
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
