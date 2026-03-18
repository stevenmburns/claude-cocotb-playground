// uart_tx_test.v — test uart_tx module with external reset and heartbeat
(* top *)
module uart_tx_test #(
    parameter CLKS_PER_BIT = 434
) (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *)                 input  wire ext_rst,
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

    // UART TX
    reg        tx_start = 0;
    wire       tx_busy;

    uart_tx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_tx (
        .clk     (clk),
        .rst     (rst),
        .tx_byte (8'h55),
        .tx_start(tx_start),
        .tx_line (uart_tx),
        .tx_busy (tx_busy)
    );

    // Send 0x55 repeatedly
    reg [15:0] delay_cnt = 0;
    always @(posedge clk) begin
        tx_start <= 1'b0;
        if (!rst && !tx_busy) begin
            if (delay_cnt == 16'd50000) begin
                tx_start  <= 1'b1;
                delay_cnt <= 0;
            end else begin
                delay_cnt <= delay_cnt + 1;
            end
        end
    end

endmodule
