// Top-level GCD over UART for Vicharak Shrike (SLG47910V)
//
// Protocol (8N1 @ 115200 baud, 50 MHz on-chip oscillator):
//   Host  → FPGA : byte a
//   Host  → FPGA : byte b
//   FPGA  → Host : byte result (lower 8 bits of gcd(a, b))
//
// The 8-bit inputs are zero-extended to 12 bits for gcd.v.
(* top *)
module gcd_top #(
    parameter CLKS_PER_BIT = 434
) (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,        // 50 MHz on-chip oscillator
    (* iopad_external_pin *)                 output wire clk_en,     // clock enable (always 1)
    (* iopad_external_pin *)                 input  wire uart_rx,       // UART RX from RP2040
    (* iopad_external_pin *)                 output wire uart_tx,       // UART TX to RP2040
    (* iopad_external_pin *)                 output wire uart_tx_oe,       // output enable for uart_tx
    // Logic-analyser debug outputs (spare right-side pins, no OE needed)
    (* iopad_external_pin *)                 output wire dbg_rx_valid,     // pulses when UART RX receives a byte  → GPIO16 PIN7 xy[31:1]_out0
    (* iopad_external_pin *)                 output wire dbg_gcd_done,     // pulses when GCD finishes            → GPIO14 PIN5 xy[31:15]_out0
    (* iopad_external_pin *)                 output wire dbg_gcd_done_oe   // OE for dbg_gcd_done (always 1)     → GPIO14 PIN5 xy[31:15]_out1
);

    assign clk_en          = 1'b1;
    assign uart_tx_oe      = 1'b1;
    assign dbg_rx_valid    = rx_valid;
    assign dbg_gcd_done    = gcd_done;
    assign dbg_gcd_done_oe = 1'b1;

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

    // -----------------------------------------------------------------------
    // GCD core
    // -----------------------------------------------------------------------
    reg  [11:0] gcd_a, gcd_b;
    reg         gcd_start;
    wire [11:0] gcd_result;
    wire        gcd_done;

    gcd u_gcd (
        .clk   (clk),
        .rst   (rst),
        .start (gcd_start),
        .a     (gcd_a),
        .b     (gcd_b),
        .result(gcd_result),
        .done  (gcd_done)
    );

    // -----------------------------------------------------------------------
    // Power-on reset: hold rst high for ~16 clocks
    // -----------------------------------------------------------------------
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

    // -----------------------------------------------------------------------
    // Control FSM
    // -----------------------------------------------------------------------
    localparam WAIT_A    = 3'd0;
    localparam WAIT_B    = 3'd1;
    localparam START_GCD = 3'd2;
    localparam COMPUTING = 3'd3;
    localparam SEND      = 3'd4;
    localparam WAIT_SEND = 3'd5;

    reg [2:0] state;
    reg [7:0] reg_a;

    always @(posedge clk) begin
        // Defaults: pulses are 1 cycle wide
        gcd_start <= 1'b0;
        tx_start  <= 1'b0;

        if (rst) begin
            state <= WAIT_A;
            reg_a <= 8'd0;
            gcd_a <= 12'd0;
            gcd_b <= 12'd0;
        end else begin
            case (state)
                // Wait for first byte (operand a)
                WAIT_A: begin
                    if (rx_valid) begin
                        reg_a <= rx_byte;
                        state <= WAIT_B;
                    end
                end

                // Wait for second byte (operand b)
                WAIT_B: begin
                    if (rx_valid) begin
                        gcd_a <= {4'b0000, reg_a};  // zero-extend to 12 bits
                        gcd_b <= {4'b0000, rx_byte};
                        state <= START_GCD;
                    end
                end

                // Assert start for one clock cycle
                START_GCD: begin
                    gcd_start <= 1'b1;
                    state     <= COMPUTING;
                end

                // Wait for GCD core to finish
                COMPUTING: begin
                    if (gcd_done) begin
                        tx_byte  <= gcd_result[7:0];
                        state    <= SEND;
                    end
                end

                // Pulse tx_start for one cycle; tx_busy goes high next cycle
                SEND: begin
                    tx_start <= 1'b1;
                    state    <= WAIT_SEND;
                end

                // Wait for UART TX to finish (tx_busy goes low), then restart
                WAIT_SEND: begin
                    if (!tx_busy) begin
                        state <= WAIT_A;
                    end
                end

                default: state <= WAIT_A;
            endcase
        end
    end

endmodule
