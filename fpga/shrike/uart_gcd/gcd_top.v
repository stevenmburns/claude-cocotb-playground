// Top-level 24-bit GCD over UART for Vicharak Shrike (SLG47910V)
//
// Protocol (8N1 @ 115200 baud, 50 MHz on-chip oscillator):
//   Host  → FPGA : 3 bytes a (LSB first)
//   Host  → FPGA : 3 bytes b (LSB first)
//   FPGA  → Host : 3 bytes result = gcd(a, b) (LSB first)
//
// External reset via RP2040 GPIO2 → FPGA GPIO3 (PIN 16) PCB trace.
(* top *)
module gcd_top #(
    parameter CLKS_PER_BIT = 434,
    parameter WIDTH = 24
) (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *)                 input  wire ext_rst,
    (* iopad_external_pin *)                 input  wire uart_rx,
    (* iopad_external_pin *)                 output wire uart_tx,
    (* iopad_external_pin *)                 output wire uart_tx_oe
);

    assign clk_en     = 1'b1;
    assign uart_tx_oe = 1'b1;

    // -----------------------------------------------------------------------
    // External reset synchroniser
    // -----------------------------------------------------------------------
    reg rst_sync0 = 0, rst_sync1 = 0;
    always @(posedge clk) begin
        rst_sync0 <= ext_rst;
        rst_sync1 <= rst_sync0;
    end
    wire rst = rst_sync1;

    // -----------------------------------------------------------------------
    // UART RX / TX instances
    // -----------------------------------------------------------------------
    wire [7:0] rx_byte;
    wire       rx_valid;

    uart_rx #(.CLKS_PER_BIT(CLKS_PER_BIT)) u_rx (
        .clk     (clk),
        .rst     (rst),
        .rx_line (uart_rx),
        .rx_byte (rx_byte),
        .rx_valid(rx_valid)
    );

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

    // -----------------------------------------------------------------------
    // GCD core
    // -----------------------------------------------------------------------
    reg  [WIDTH-1:0] gcd_a = 0, gcd_b = 0;
    reg              gcd_start = 0;
    wire [WIDTH-1:0] gcd_result;
    wire             gcd_done;

    gcd #(.WIDTH(WIDTH)) u_gcd (
        .clk   (clk),
        .rst   (rst),
        .start (gcd_start),
        .a     (gcd_a),
        .b     (gcd_b),
        .result(gcd_result),
        .done  (gcd_done)
    );

    // -----------------------------------------------------------------------
    // Control FSM — 3-byte RX for a, 3-byte RX for b, 3-byte TX for result
    // -----------------------------------------------------------------------
    localparam RX_A0      = 4'd0;   // receive a[7:0]
    localparam RX_A1      = 4'd1;   // receive a[15:8]
    localparam RX_A2      = 4'd2;   // receive a[23:16]
    localparam RX_B0      = 4'd3;   // receive b[7:0]
    localparam RX_B1      = 4'd4;   // receive b[15:8]
    localparam RX_B2      = 4'd5;   // receive b[23:16]
    localparam START_GCD  = 4'd6;
    localparam COMPUTING  = 4'd7;
    localparam TX_R0      = 4'd8;   // send result[7:0]
    localparam TX_WAIT0   = 4'd9;
    localparam TX_R1      = 4'd10;  // send result[15:8]
    localparam TX_WAIT1   = 4'd11;
    localparam TX_R2      = 4'd12;  // send result[23:16]
    localparam TX_WAIT2   = 4'd13;

    reg [3:0]        state = 0;
    reg [WIDTH-1:0]  result_reg = 0;

    always @(posedge clk) begin
        gcd_start <= 1'b0;
        tx_start  <= 1'b0;

        if (rst) begin
            state      <= RX_A0;
            gcd_a      <= 0;
            gcd_b      <= 0;
            result_reg <= 0;
        end else begin
            case (state)
                RX_A0: if (rx_valid) begin
                    gcd_a[7:0] <= rx_byte;
                    state      <= RX_A1;
                end

                RX_A1: if (rx_valid) begin
                    gcd_a[15:8] <= rx_byte;
                    state       <= RX_A2;
                end

                RX_A2: if (rx_valid) begin
                    gcd_a[23:16] <= rx_byte;
                    state        <= RX_B0;
                end

                RX_B0: if (rx_valid) begin
                    gcd_b[7:0] <= rx_byte;
                    state      <= RX_B1;
                end

                RX_B1: if (rx_valid) begin
                    gcd_b[15:8] <= rx_byte;
                    state       <= RX_B2;
                end

                RX_B2: if (rx_valid) begin
                    gcd_b[23:16] <= rx_byte;
                    state        <= START_GCD;
                end

                START_GCD: begin
                    gcd_start <= 1'b1;
                    state     <= COMPUTING;
                end

                COMPUTING: if (gcd_done) begin
                    result_reg <= gcd_result;
                    state      <= TX_R0;
                end

                TX_R0: begin
                    tx_byte  <= result_reg[7:0];
                    tx_start <= 1'b1;
                    state    <= TX_WAIT0;
                end

                TX_WAIT0: if (!tx_busy && !tx_start) begin
                    state <= TX_R1;
                end

                TX_R1: begin
                    tx_byte  <= result_reg[15:8];
                    tx_start <= 1'b1;
                    state    <= TX_WAIT1;
                end

                TX_WAIT1: if (!tx_busy && !tx_start) begin
                    state <= TX_R2;
                end

                TX_R2: begin
                    tx_byte  <= result_reg[23:16];
                    tx_start <= 1'b1;
                    state    <= TX_WAIT2;
                end

                TX_WAIT2: if (!tx_busy && !tx_start) begin
                    state <= RX_A0;
                end

                default: state <= RX_A0;
            endcase
        end
    end

endmodule
